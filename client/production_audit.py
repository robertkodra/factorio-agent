"""Read-only throughput evidence from two private factory snapshots.

A machine's products_finished counts crafts, not output items. Rates cover only
machines present with the same identity and recipe in both snapshots. Counters
and ticks must move forward; no capacity is inferred from placement alone.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def compare(before, after):
    ticks=after['tick']-before['tick']
    if ticks<=0:
        raise ValueError('Snapshots must advance within the same recorded world')
    old={e['id']:e for e in before['entities'] if e.get('id') is not None}
    rows=[];statuses=Counter()
    for entity in after['entities']:
        if 'products_finished' not in entity:
            continue
        statuses[entity.get('status_name','unknown')]+=1
        previous=old.get(entity.get('id'))
        row=dict(id=entity.get('id'),entity=entity['name'],recipe=entity.get('recipe'),
                 status=entity.get('status_name'),crafting=entity.get('crafting'),
                 powered_network=entity.get('electric_network_id') is not None)
        comparable=(previous and previous['name']==entity['name']
                    and previous.get('recipe')==entity.get('recipe')
                    and 'products_finished' in previous)
        if comparable:
            delta=entity['products_finished']-previous['products_finished']
            if delta<0:
                raise ValueError('Production counter regressed; do not combine episodes')
            row.update(completed_crafts=delta,crafts_per_game_minute=delta*3600/ticks)
        rows.append(row)
    produced={name:amount-before.get('produced',{}).get(name,amount)
              for name,amount in after.get('produced',{}).items()}
    if any(n<0 for n in produced.values()):
        raise ValueError('Item counter regressed; do not combine episodes')
    return dict(elapsed_game_seconds=ticks/60,machines=rows,status_counts=dict(statuses),
                item_production_delta=produced,
                limitations=['Caller must establish that both snapshots belong to the same world.',
                             'A connected power network does not prove adequate power.',
                             'Whole-factory item counters can include engineer hand crafting.',
                             'New or reconfigured machines have no comparable craft rate.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('before',type=Path);p.add_argument('after',type=Path);a=p.parse_args()
    print(json.dumps(compare(json.loads(a.before.read_text()),json.loads(a.after.read_text())),indent=2))


if __name__=='__main__':main()
