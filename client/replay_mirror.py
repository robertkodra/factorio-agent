"""Replay retained journals without a game, measuring storage and cache parity.

The selected entity IDs and source identity are private inputs. Legacy factory
snapshots lack explicit charting evidence; replay domains cannot authorize play.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from .agent import ROOT
from .mirror_log import MirrorLog, Reconstructor, encoded
from .state_mirror import ENTITY_FIELDS, INVENTORY_FIELDS, StateMirror, player_values, select


def replay(source, output, identity, entity_ids):
    source, output = Path(source), Path(output).resolve()
    if ROOT/'runtime' not in output.parents:
        raise ValueError('Replay output must remain under ignored runtime/')
    if not entity_ids or len(entity_ids)>64 or len(set(entity_ids))!=len(entity_ids):
        raise ValueError('Select 1 to 64 unique entity IDs')
    output.mkdir(parents=True,exist_ok=False)
    mirror=StateMirror(identity);log=MirrorLog(output/'mirror.jsonl');rebuilt=Reconstructor()
    hashes=hashlib.sha256();counts=Counter();cost=Counter();full_state_bytes=0;checks=0
    interrupted=[];damage_tick=None;input_bytes=0;row_number=0
    try:
        with source.open('rb') as stream:
            for raw in stream:
                row_number+=1;hashes.update(raw);input_bytes+=len(raw)
                start=time.perf_counter();row=json.loads(raw);cost['source_json_decode_seconds']+=time.perf_counter()-start
                kind=row.get('kind');counts[kind]+=1;data=row.get('data',{});at=row.get('wall_epoch')
                start=time.perf_counter();events=[];expected={}
                if kind=='observation':
                    mirror.player(data,at)
                    expected={'player':player_values(data),'inventory':select(data,INVENTORY_FIELDS)}
                elif kind in ('factory','target_verified'):
                    if kind=='target_verified':data=data['factory']
                    selected=[e for e in data['entities'] if e.get('id') in entity_ids]
                    # Explicit legacy scope: old observations do not prove the
                    # new owned+charted contract. Do not fabricate that evidence.
                    obs=dict(tick=data['tick'],scope='owned_factory_replay',entities=selected,
                             missing=sorted(set(entity_ids)-{e['id'] for e in selected}))
                    mirror.entities(obs,at,entity_ids);mirror.research(data,at)
                    for e in selected:
                        for group,fields in ENTITY_FIELDS.items():
                            value=select(e,fields)
                            if group=='structure':
                                value['presence']='destroyed' if str(e['id']) in mirror.state['tombstones'] else 'observed'
                            expected['entity:%d:%s'%(e['id'],group)]=value
                elif kind=='game_event':
                    if mirror.state['cursor'] is None:
                        # Analysis starts at the first retained event, not at map
                        # creation. Earlier unrecorded history is not certified.
                        mirror.state['cursor']=data['seq']-1
                    mirror.status(dict(tick=data['tick'],sequence=data['seq'],events=[data]),at)
                    events=[data]
                    if data['kind'] in ('factory_damaged','factory_destroyed'):damage_tick=data['tick']
                    if (data['kind']=='cancelled' and (data.get('detail') or {}).get('error')=='factory_defense_interrupt'
                            and damage_tick is not None):
                        interrupted.append(data['tick']-damage_tick);damage_tick=None
                elif kind=='job_reconciled':
                    receipt=data['result'];mirror.receipt(receipt,receipt['finished_tick'],at)
                else:
                    continue
                for key,value in expected.items():
                    if mirror.state['domains'][key]['data'] != value:
                        raise AssertionError('Retained observation projection mismatch: '+key)
                    checks+=1
                cost['projection_update_seconds']+=time.perf_counter()-start
                start=time.perf_counter()
                # Same scoped state serialized in full at every accepted record
                # separates delta savings from removing unrelated factory data.
                full_state_bytes+=len(encoded(dict(state=mirror.checkpoint(),events=events)))
                record=log.append(mirror,events=events)
                cost['encoding_and_write_seconds']+=time.perf_counter()-start
                start=time.perf_counter()
                rebuilt.apply(json.loads(encoded(record)))
                if rebuilt.state != mirror.checkpoint():raise AssertionError('Reconstruction mismatch')
                cost['reconstruction_seconds']+=time.perf_counter()-start
        log.close()
        # Independent second disk pass verifies the actual artifact, including
        # starting again from each periodic checkpoint.
        reader=Reconstructor();tail=None;checkpoint_count=0
        with (output/'mirror.jsonl').open() as stream:
            for line in stream:
                record=json.loads(line);reader.apply(record)
                if record['kind']=='checkpoint':tail=Reconstructor();checkpoint_count+=1
                tail.apply(record)
                if tail.state != reader.state:raise AssertionError('Checkpoint suffix mismatch')
        if reader.state != mirror.checkpoint():raise AssertionError('Disk reconstruction mismatch')
        after=hashlib.sha256()
        with source.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):after.update(block)
        if after.hexdigest()!=hashes.hexdigest():raise AssertionError('Source journal changed during replay')
        implementation={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                        for name in ('state_mirror.py','mirror_log.py','replay_mirror.py')}
        report=dict(source_sha256=hashes.hexdigest(),source_unchanged=True,source_bytes=input_bytes,
                    implementation_sha256=implementation,
                    selected_entities=len(entity_ids),source_records=dict(counts),mirror_records=log.serial,
                    mirror_bytes=log.bytes,full_scoped_state_bytes=full_state_bytes,
                    reduction_vs_original=1-log.bytes/input_bytes,
                    reduction_vs_full_scoped_state=1-log.bytes/full_state_bytes,
                    retained_projection_checks=checks,reconstruction_mismatches=0,
                    checkpoints=checkpoint_count,reconstruction='every record and every checkpoint suffix passed',
                    replay_cpu_seconds=dict(cost),
                    observation_rcon=dict(live_calls=0,latency_seconds=None,
                        note='Offline replay does not measure network, engine read cost or polling cadence.'),
                    native_damage_to_preemption_ticks=dict(samples=len(interrupted),
                        maximum=max(interrupted) if interrupted else None),
                    first_defensive_input_latency_seconds=None,
                    limitations=['Selected entities and fields, not a lossless encoding of the entire original journal.',
                        'Legacy factory charting and pre-stream event history are unverified; replay cannot authorize gameplay.',
                        'Only native events/receipts and mirrored observations enter the compact log; originals are retained.',
                        'CPU timings are local replay work, not gameplay response or RCON speedup.',
                        'No artificial attack, live input, model call or game connection was made.'])
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    except BaseException as exc:
        log.close()
        (output/'failure.json').write_text(json.dumps(dict(error=type(exc).__name__,row=row_number,counts=dict(counts)),indent=2))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--identity',type=Path,required=True);parser.add_argument('--entity-ids',type=Path,required=True)
    args=parser.parse_args()
    result=replay(args.journal,args.output,json.loads(args.identity.read_text()),json.loads(args.entity_ids.read_text()))
    print(json.dumps({k:result[k] for k in ('selected_entities','source_bytes','mirror_bytes',
          'reduction_vs_original','reduction_vs_full_scoped_state','retained_projection_checks','reconstruction_mismatches')},indent=2))


if __name__=='__main__':main()
