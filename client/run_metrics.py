"""Stream private scheduler journals into bounded, aggregate cadence reports.

Intervals use native ticks, not rendered input latency. Waiting, travel and
strategic changes must not be relabelled model inference time.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from .agent import ROOT


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def summarize(path):
    jobs = {}
    with Path(path).open() as handle:
        for line in handle:
            if '"job_reconciled"' not in line:
                continue
            row = json.loads(line)
            if row.get('kind') != 'job_reconciled':
                continue
            data = row['data']
            job = data['result']
            if job['status'] not in ('complete', 'failed', 'cancelled'):
                raise ValueError('Expected terminal job receipt')
            if job['finished_tick'] < job['started_tick']:
                raise ValueError('Job timeline regressed')
            existing = jobs.get(job['id'])
            if existing and any(existing['result'][key] != job[key]
                                for key in ('status', 'started_tick', 'finished_tick')):
                raise ValueError('Conflicting receipts for one job')
            jobs[job['id']] = data
    ordered = sorted(jobs.values(), key=lambda d: d['result']['started_tick'])
    gaps, durations, categories, statuses = [], Counter(), Counter(), Counter()
    for index, data in enumerate(ordered):
        job = data['result']
        category = data['skill']['key'].split(':', 1)[0]
        categories[category] += 1
        statuses[job['status']] += 1
        durations[category] += (job['finished_tick'] - job['started_tick']) / 60
        if index:
            gap = (job['started_tick'] - ordered[index - 1]['result']['finished_tick']) / 60
            if gap < 0:
                raise ValueError('Overlapping jobs or multiple timelines; analyze separate phases')
            gaps.append(gap)
    return dict(jobs=len(ordered), statuses=dict(statuses), jobs_by_category=dict(categories),
                job_seconds_by_category=dict(durations),
                span_game_seconds=(ordered[-1]['result']['finished_tick'] -
                    ordered[0]['result']['started_tick']) / 60 if ordered else 0,
                gap_game_seconds=dict(samples=len(gaps), median=percentile(gaps, .5),
                    p95=percentile(gaps, .95), maximum=max(gaps) if gaps else None,
                    total=sum(gaps)),
                limitations=['One journal timeline; duplicate job IDs counted once.',
                             'Native job gaps include supply waits and other unclassified delays.',
                             'Excludes time before first job and after last job.',
                             'Not wall time, reaction latency or rendered smoothness.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if ROOT / 'runtime' not in args.output.resolve().parents:
        parser.error('Run analysis output must stay under ignored runtime/')
    report = summarize(args.journal)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
