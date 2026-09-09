"""Offline selector evaluation: constructed cases plus optional recorded snapshots.

This tests bounded decisions and latency, not gameplay success or learned weights.
Raw snapshots, model outputs and timings stay under ignored runtime/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

from .agent import ROOT
from .local_planner import LocalPlanner, load_config


def constructed_cases():
    templates = [
        ('approach', {'health': 250, 'threat': 'multiple approaching biters within 8 tiles'},
         'defense', 'Interrupt work for combat/escape', 'Continue routine delivery'),
        ('low-health', {'health': 33, 'max_health': 250, 'recent_damage': 217},
         'defense', 'Interrupt work and assess combat/escape', 'Continue distant construction'),
        ('fuel', {'health': 250, 'local_threats': 0, 'furnace': {'fuel': 0, 'ore': 30},
                  'inventory': {'coal': 50}, 'in_reach': True},
         'refuel', 'Fuel the starved furnace', 'Add another unfuelled furnace'),
        ('ammo', {'health': 250, 'local_threats': 0, 'planned_trip': 'exposed resource haul',
                  'loaded_ammo': 0, 'magazines_in_reachable_chest': 30},
         'resupply', 'Load existing ammunition before the exposed trip', 'Depart without ammunition'),
        ('power', {'health': 250, 'local_threats': 0, 'lab': {'science': 20, 'powered': False},
                   'power_pole_in_inventory': True},
         'connect', 'Connect the lab to available power and verify supply', 'Craft more science for the unpowered lab'),
        ('path', {'health': 250, 'local_threats': 0, 'navigation_result': 'no_path_progress',
                  'same_route_retries': 2},
         'reroute', 'Inspect obstacles and choose a different reachable service position', 'Repeat the identical failed route'),
        ('queued', {'health': 250, 'local_threats': 0, 'red_pack_craft_queued': 20,
                    'red_packs_completed': 0, 'research_completed': False},
         'verify', 'Check actual science production and lab consumption', 'Declare research complete from the queued crafts'),
        ('fog', {'health': 250, 'route_scan': {'entities': [], 'truncated': True},
                 'route_visibility': 'unknown'},
         'scout', 'Gather permitted route observations before declaring it safe', 'Declare the entire route safe from the empty scan'),
    ]
    rng = random.Random(917)
    cases = []
    for family, obs, wanted, good, bad in templates:
        for variant in range(5):
            # Position is an irrelevant variation, not an independent encounter.
            observation = dict(obs, position={'x': variant * 13, 'y': -variant * 7})
            candidates = [{'id': wanted, 'description': good},
                          {'id': 'alternative', 'description': bad}]
            rng.shuffle(candidates)
            cases.append(dict(id='%s-%d' % (family, variant), provenance='constructed',
                              family=family, observation=observation, candidates=candidates,
                              expected=wanted))
    return cases


def recorded_cases(path):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    snapshots = {}
    for line in raw.splitlines():
        row = json.loads(line)
        data = row.get('data', {})
        if row.get('kind') in ('observe', 'bind'):
            data = data.get('result', {})
        elif row.get('kind') != 'state':
            continue
        if isinstance(data, dict) and 'health' in data and 'tick' in data:
            snapshots[data['tick']] = data
    # Include both near-death readings before sampling routine snapshots.
    ordered = sorted(snapshots.values(), key=lambda s: (s['health'], s['tick']))[:10]
    cases = []
    for s in ordered:
        obs = {k: s[k] for k in ('tick', 'health', 'max_health', 'position', 'inventory', 'ammo', 'crafting') if k in s}
        obs['enemy_observation'] = 'not available in this historical snapshot'
        obs['next_task'] = 'plan a resource trip'
        low = s['health'] < s.get('max_health', 250) * .5
        candidates = [{'id': 'delivery', 'description': 'Immediately begin the next routine resource trip'},
                      {'id': 'defense', 'description': 'Interrupt production and assess survival/escape'},
                      {'id': 'observe', 'description': 'Check permitted current route and threat observations before choosing the trip'}]
        cases.append(dict(id='recorded-%d' % s['tick'], provenance='recorded-snapshot',
                          source_sha256=digest, family='health-triage' if low else 'missing-route-evidence',
                          observation=obs, candidates=candidates,
                          expected='defense' if low else 'observe'))
    return cases


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recorded', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / 'runtime' not in output.parents:
        raise ValueError('Raw evaluation output must be inside runtime/')
    output.mkdir(parents=True, exist_ok=False)
    cases = constructed_cases() + (recorded_cases(args.recorded) if args.recorded else [])
    if args.limit:
        cases = cases[:args.limit]
    config = load_config()
    planner = LocalPlanner(config)
    results = []
    try:
        identity = planner.identity()
        (output / 'manifest.json').write_text(json.dumps(dict(model=identity, config=config,
            cases=len(cases), created_epoch=time.time(),
            limitation='Constructed templates and snapshot triage; no live actions, training, or expert gameplay certification.'), indent=2))
        with (output / 'cases.jsonl').open('x') as f:
            for case in cases:
                f.write(json.dumps(case) + '\n')
        # Separate cold/warm-up request from measured case distribution.
        warmup = planner.decide(cases[0]['observation'], cases[0]['candidates'])
        (output / 'warmup.json').write_text(json.dumps(warmup, indent=2))
        with (output / 'results.jsonl').open('x') as f:
            for case in cases:
                started = time.monotonic()
                try:
                    decision = planner.decide(case['observation'], case['candidates'])
                    row = dict(id=case['id'], provenance=case['provenance'], expected=case['expected'],
                               correct=decision['choice'] == case['expected'], **decision)
                except Exception as exc:
                    row = dict(id=case['id'], provenance=case['provenance'], correct=False,
                               wall_seconds=time.monotonic() - started, error=type(exc).__name__)
                results.append(row)
                f.write(json.dumps(row) + '\n'); f.flush()
                print(json.dumps(row), flush=True)
    finally:
        planner.close()
    latencies = [r['wall_seconds'] for r in results]
    summary = dict(count=len(results), correct=sum(r['correct'] for r in results),
                   invalid=sum('error' in r for r in results), median_seconds=percentile(latencies, .5),
                   p95_seconds=percentile(latencies, .95), maximum_seconds=max(latencies, default=0),
                   over_decision_age=sum(x > config['max_decision_age_seconds'] for x in latencies),
                   groups={p: {'count': sum(r['provenance'] == p for r in results),
                               'correct': sum(r['provenance'] == p and r['correct'] for r in results)}
                           for p in ('constructed', 'recorded-snapshot')})
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
