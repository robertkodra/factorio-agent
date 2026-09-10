"""Explicit live MCP benchmark. Requires a bound engineer in a disposable world.

All observations, action traces, failures, and summaries stay in ignored runtime.
The plan phase mutates the world using the supplied plan. No arbitrary Lua.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import time

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from client.agent import Agent, ROOT
from client.server import MOD_VERSION
from client.tool_schemas import TOOLS


def stats(values):
    values = sorted(values)
    def percentile(p):
        return values[max(0, math.ceil(len(values)*p)-1)]
    return dict(n=len(values), median_ms=percentile(.5), p95_ms=percentile(.95),
                p99_ms=percentile(.99), min_ms=values[0], max_ms=values[-1])


class Benchmark:
    def __init__(self, folder):
        self.folder = folder
        self.samples = {}
        self.trace = (folder/'calls.jsonl').open('x')
        self.params = StdioServerParameters(command=sys.executable, cwd=ROOT,
            args=[str(ROOT/'scripts/run_mcp.py')])

    def record(self, data):
        self.trace.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), **data))+'\n')
        self.trace.flush()

    async def call(self, client, name, arguments=None, group=None):
        arguments = arguments or {}
        start = time.perf_counter_ns()
        try:
            response = await client.call_tool(name, arguments)
        except BaseException as exc:
            self.record(dict(op=name, arguments=arguments, exception=type(exc).__name__,
                             elapsed_ms=(time.perf_counter_ns()-start)/1e6))
            raise
        elapsed = (time.perf_counter_ns()-start)/1e6
        self.record(dict(op=name, arguments=arguments, result=response.structured_content,
                         is_error=response.is_error, elapsed_ms=elapsed, group=group))
        if response.is_error:
            raise RuntimeError(response.structured_content)
        if group:
            self.samples.setdefault(group, []).append(elapsed)
        return response.structured_content

    async def reads(self, client, count):
        before = await self.call(client, 'observe')
        assert not before['paused'], 'Resume the game before measuring normal tick scheduling'
        with Agent() as direct:
            for name, args in [('status', {}), ('observe', {}),
                               ('scan', dict(radius=64, limit=20)), ('factory', {}),
                               ('survey', dict(radius=128, limit=100)),
                               ('placement', dict(entity='stone-furnace', **before['position']))]:
                for _ in range(5):
                    await self.call(client, name, args)
                    direct.request(name, **args)
                for i in range(count):
                    # Alternate pair order to avoid always favouring one transport.
                    for transport in (('mcp', 'rcon') if i % 2 == 0 else ('rcon', 'mcp')):
                        if transport == 'mcp':
                            await self.call(client, name, args, group='mcp_'+name)
                        else:
                            start = time.perf_counter_ns()
                            out = direct.request(name, **args)
                            elapsed = (time.perf_counter_ns()-start)/1e6
                            self.samples.setdefault('rcon_'+name, []).append(elapsed)
                            self.record(dict(op=name, transport='rcon', result=out, elapsed_ms=elapsed))
                print(json.dumps(dict(tool=name, mcp=stats(self.samples['mcp_'+name]),
                                      rcon=stats(self.samples['rcon_'+name]))), flush=True)
        return dict(before=before, after=await self.call(client, 'observe'))

    async def plan(self, client, path, deadline):
        plan = json.loads(path.read_text())
        job = dict(id=self.folder.name, actions=plan['actions'])
        before = await self.call(client, 'observe')
        assert not before['paused'] and before['job']['status'] != 'running'
        start = time.perf_counter()
        submitted = await self.call(client, 'submit', job, group='submit_plan')
        cursor = before['sequence']
        events, snapshots = [], []
        previous = None
        while True:
            status = await self.call(client, 'status', dict(id=job['id'], after=cursor), group='active_status')
            if status['events']:
                events.extend(status['events'])
                cursor = status['events'][-1]['seq']
            marker = (status['status'], status.get('index'))
            if marker != previous:
                print(json.dumps({key:status.get(key) for key in ('id','status','index','total','action','error','tick')}),flush=True)
                previous = marker
            state = await self.call(client, 'observe', group='active_observe')
            snapshots.append(dict(wall_seconds=time.perf_counter()-start, **state))
            if status['status'] != 'running':
                break
            if time.perf_counter()-start > deadline:
                await self.call(client, 'cancel', dict(id=job['id']))
                raise TimeoutError('Plan exceeded the declared wall deadline; job cancelled')
            await anyio.sleep(.1)
        return dict(submitted=submitted, status=status, wall_seconds=time.perf_counter()-start,
                    before=before, after=state, events=events, snapshots=snapshots,
                    success=status['status']=='complete')

    async def control(self, client, count):
        before = await self.call(client, 'observe')
        assert not before['paused'] and before['job']['status'] != 'running'
        trials=[]
        for i in range(count):
            state = await self.call(client, 'observe')
            x,y=state['position']['x'],state['position']['y']
            job_id=self.folder.name+'-'+str(i)
            actions=[dict(type='walk', x=x+(10 if i%2==0 else -10), y=y, timeout=600)]
            accepted=await self.call(client,'submit',dict(id=job_id,actions=actions),group='submit_walk')
            await anyio.sleep(.2)
            moving=await self.call(client,'observe')
            cancelled=await self.call(client,'cancel',dict(id=job_id),group='cancel_walk')
            stopped=await self.call(client,'observe')
            await anyio.sleep(.1)
            after=await self.call(client,'observe')
            assert cancelled['status']=='cancelled',cancelled
            assert not after['walking']['walking'] and stopped['position']==after['position']
            assert moving['walking']['walking'] and moving['position']!=state['position'], moving
            trials.append(dict(accepted=accepted,moving=moving,cancelled=cancelled,stopped=stopped,after=after))
        # Worst-case schema size is measured with ordinary waits, then cancelled.
        with Agent() as direct:
            for size in (1,32,128,512):
                for i in range(5):
                    for transport in (('mcp','rcon') if i%2==0 else ('rcon','mcp')):
                        job_id=self.folder.name+'-batch-'+str(size)+'-'+str(i)+'-'+transport
                        job=dict(id=job_id,actions=[dict(type='wait_ticks',ticks=216000)]*size)
                        if transport=='mcp':
                            await self.call(client,'submit',job,group='submit_'+str(size)+'_actions')
                            await self.call(client,'cancel',dict(id=job_id))
                        else:
                            start=time.perf_counter_ns()
                            out=direct.request('submit',**job)
                            elapsed=(time.perf_counter_ns()-start)/1e6
                            self.samples.setdefault('rcon_submit_'+str(size)+'_actions',[]).append(elapsed)
                            self.record(dict(op='submit',transport='rcon',arguments=job,result=out,elapsed_ms=elapsed))
                            out=direct.request('cancel',id=job_id)
                            self.record(dict(op='cancel',transport='rcon',arguments=dict(id=job_id),result=out))
                print(json.dumps(dict(batch_size=size,mcp=stats(self.samples['submit_'+str(size)+'_actions']),
                                      rcon=stats(self.samples['rcon_submit_'+str(size)+'_actions']))),flush=True)
        return dict(trials=trials,after=await self.call(client,'observe'))

    async def run(self, args):
        started=time.perf_counter()
        async with Client(self.params,mode='legacy') as client:
            startup_ms=(time.perf_counter()-started)*1000
            tools=await client.list_tools()
            assert {tool.name for tool in tools.tools}==set(TOOLS)
            before=await self.call(client,'observe')
            assert before['mods']=={'base':'2.0.77','codex-controller':MOD_VERSION}
            assert before['speed']==1
            await self.call(client,'pause',dict(value=False))
            if args.phase=='reads':
                detail=await self.reads(client,args.samples)
            elif args.phase=='plan':
                detail=await self.plan(client,args.plan,args.deadline)
            else:
                detail=await self.control(client,args.samples)
            paused=await self.call(client,'pause',dict(value=True))
            summary=dict(phase=args.phase,protocol=client.protocol_version,startup_ms=startup_ms,
                         samples={k:stats(v) for k,v in self.samples.items()},detail=detail,paused=paused,
                         source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in (ROOT/'client/mcp_server.py', ROOT/'client/tool_schemas.py',
                                                     ROOT/'mod/codex-controller/control.lua',
                                                     ROOT/'mod/codex-controller/navigation.lua')})
            (self.folder/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
            print(json.dumps(dict(phase=args.phase,startup_ms=startup_ms,
                                 samples=summary['samples'],result_file=str(self.folder/'result.json'))),flush=True)
        return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--phase',choices=('reads','plan','control'),required=True)
    parser.add_argument('--samples',type=int,default=100)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--deadline',type=float,default=240)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.run_id) or not 1<=args.samples<=1000:
        parser.error('Invalid run ID or sample count')
    if not math.isfinite(args.deadline) or not 0<args.deadline<=3600:
        parser.error('Deadline must be finite, positive, and at most 3600 seconds')
    if args.phase=='control' and args.samples>20:
        parser.error('Control phase supports at most 20 movement trials')
    if args.phase=='plan' and args.plan is None:
        parser.error('The plan phase requires an explicit --plan')
    run=ROOT/'runtime/runs'/args.run_id
    if not (run/'baseline.json').exists() or (run/'stop-monitor').exists():
        parser.error('Initialize an open run baseline before benchmarking')
    folder=run/(args.phase+'-'+str(time.time_ns()))
    folder.mkdir()
    bench=Benchmark(folder)
    try:
        anyio.run(bench.run,args)
    except BaseException as exc:
        bench.record(dict(failure=type(exc).__name__,message=str(exc)))
        raise
    finally:
        bench.trace.close()


if __name__=='__main__':
    main()
