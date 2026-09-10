"""Audit observed job durations and idle gaps, including recovery downtime.

Use journals from one uninterrupted world/tick timeline. Native execution time
is not model latency, and gaps include planning, transport and interventions.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


def summarize(rows):
    jobs = {}
    for row in rows:
        kind, data = row.get('kind'), row.get('data', {})
        if kind == 'job_reconciled':
            job, key = data['result'], data['skill']['key']
        elif kind == 'progress':
            job, key = data, 'manual'
        else:
            continue
        if job.get('status') not in ('complete','failed','cancelled') or 'finished_tick' not in job:
            continue
        if job['finished_tick'] < job['started_tick']:
            raise ValueError('Regressing job ticks')
        jobs[job['id']] = (key, job)
    ordered = sorted(jobs.values(), key=lambda v:v[1]['started_tick'])
    gaps = [(b['started_tick']-a['finished_tick'])/60
            for (_,a),(_,b) in zip(ordered,ordered[1:])]
    if any(g < 0 for g in gaps):
        raise ValueError('Overlapping jobs: use one world and executor timeline')
    durations = [(j['finished_tick']-j['started_tick'])/60 for _,j in ordered]
    def distribution(values):
        return dict(count=len(values), total_seconds=sum(values),
                    median_seconds=statistics.median(values) if values else None,
                    maximum_seconds=max(values) if values else None,
                    over_10_seconds=sum(v>10 for v in values),
                    over_20_seconds=sum(v>20 for v in values))
    by_skill = Counter()
    for key, job in ordered:
        by_skill[key.split(':')[0]] += (job['finished_tick']-job['started_tick'])/60
    return dict(jobs=len(jobs), outcomes=dict(Counter(j['status'] for _,j in ordered)),
                execution=distribution(durations), between_jobs=distribution(gaps),
                execution_seconds_by_skill=dict(by_skill),
                limitations=['Only completed, failed or cancelled receipts included; pending work excluded.',
                             'Gaps include controller planning, process downtime and manual intervention.',
                             'Native durations include walking/crafting; these are not inference timings.'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journals',type=Path,nargs='+')
    args=parser.parse_args()
    def rows():
        for path in args.journals:
            with path.open() as stream:
                for line in stream:
                    yield json.loads(line)
    print(json.dumps(summarize(rows()),indent=2))
