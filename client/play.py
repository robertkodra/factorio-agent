"""Dry-run notebook helpers. All actions and observations are recorded locally."""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from .agent import Agent, ROOT

RUN_ID = os.environ.get('FACTORIO_RUN_ID')
if RUN_ID and not re.fullmatch(r'[A-Za-z0-9_-]+', RUN_ID):
    raise ValueError('FACTORIO_RUN_ID must contain only letters, numbers, hyphens, and underscores')
RUN = ROOT / 'runtime/runs' / RUN_ID if RUN_ID else ROOT / 'runtime/notebook'
RUN.mkdir(parents=True, exist_ok=True)


def ensure_run_open():
    if (RUN / 'stop-monitor').exists():
        raise RuntimeError('This run is closed; select a new FACTORIO_RUN_ID')


def log(kind, data):
    ensure_run_open()
    with (RUN / 'actions.jsonl').open('a') as f:
        f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), kind=kind, data=data))+'\n')


def query(lua):
    """Old notebook entrypoint; never transmits code under the no-cheats policy."""
    raise RuntimeError("Arbitrary Lua diagnostics are disabled. Use the bounded "
                       "factory/research_state/observe/scan/inspect operations.")


def call(op, **kwargs):
    ensure_run_open()
    with Agent() as a:
        result=a.request(op, **kwargs)
    log(op, dict(request=kwargs, result=result))
    return result


def run(actions, label, deadline=300):
    job=dict(id=label+'-'+str(time.time_ns()), actions=actions)
    log('plan', job)
    with Agent() as a:
        result=a.request('submit', **job)
        log('submitted', result)
        started=time.monotonic();previous=None
        while time.monotonic()-started < deadline:
            status=a.request('status', id=job['id'])
            marker=(status['status'],status.get('index'))
            if marker!=previous:
                log('progress',status);print(json.dumps(status),flush=True);previous=marker
            if status['status']!='running':
                log('state',a.request('observe'))
                if status['status']!='complete':raise RuntimeError(status)
                return status
            time.sleep(.5)
    raise TimeoutError('Job is still active; inspect its status before continuing')


def milestone(name, detail=None):
    s=call('observe')
    initial=json.loads((RUN/'baseline.json').read_text())
    entry=dict(name=name,tick=s['tick'],elapsed_game_seconds=(s['tick']-initial['state']['tick'])/60,
               elapsed_wall_seconds=time.time()-initial['wall_epoch'],detail=detail)
    log('milestone',entry)
    with (RUN/'milestones.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
    print(json.dumps(entry),flush=True)
    return entry


def walk(x,y,tolerance=0.35):return dict(type='walk',x=x,y=y,tolerance=tolerance)
def mine(name,x,y,count=1,item=None):
    a=dict(type='mine',entity=name,x=x,y=y,count=count,timeout=max(600,count*180+300))
    if item:a['item']=item
    return a
def craft(recipe,count=1):return dict(type='craft',recipe=recipe,count=count)
def place(name,x,y,direction='north'):return dict(type='place',entity=name,x=x,y=y,direction=direction)
def transfer(kind,name,x,y,inventory,item,count):return dict(type=kind,entity=name,x=x,y=y,inventory=inventory,item=item,count=count)
def put(name,x,y,inventory,item,count):return transfer('put',name,x,y,inventory,item,count)
def take(name,x,y,inventory,item,count):return transfer('take',name,x,y,inventory,item,count)
def wait_item(name,x,y,inventory,item,count):return dict(type='wait_inventory',entity=name,x=x,y=y,inventory=inventory,item=item,count=count,timeout=18000)
def await_craft():return dict(type='await_craft')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Initialize a new observed run baseline')
    parser.add_argument('--init', action='store_true', required=True)
    parser.parse_args()
    if not RUN_ID:
        raise SystemExit('Set FACTORIO_RUN_ID to a new run name first')
    ensure_run_open()
    path = RUN / 'baseline.json'
    if path.exists():
        raise SystemExit('Baseline already exists; refusing to overwrite it')
    with Agent() as agent:
        state = agent.request('observe')
    if not state['paused'] or state.get('job', {}).get('status') == 'running':
        raise SystemExit('Pause the game and stop any active job before capturing the baseline')
    with path.open('x') as file:
        json.dump(dict(wall_epoch=time.time(),state=state,policy='no-console-lua-v1',
                       note='Observed baseline; fresh-map provenance must also be recorded.'),file,indent=2)
        file.write('\n')
    print('Created baseline:',path)
