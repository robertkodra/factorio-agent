"""Conservative base-game rocket budget, including oil co-products and cracking.

No productivity bonuses, initial stock, mining yield bonuses or optimistic fuel
assumptions. Recipe work is not elapsed run time. This never controls the game.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math

from .materials import CATALOG
from .progression import research_plan

RAW = {'iron-ore', 'copper-ore', 'stone', 'coal', 'wood', 'water', 'crude-oil'}
OIL = {'heavy-oil', 'light-oil', 'petroleum-gas'}
ROUTES = {'solid-fuel': 'solid-fuel-from-light-oil'}
MACHINES = {'crafting': ('assembling-machine-1', .5),
            'advanced-crafting': ('assembling-machine-1', .5),
            'crafting-with-fluid': ('assembling-machine-2', .75),
            'chemistry': ('chemical-plant', 1), 'oil-processing': ('oil-refinery', 1),
            'smelting': ('stone-furnace', 1), 'rocket-building': ('rocket-silo', 1)}


def quantities(values):
    if not isinstance(values, dict) or any(not isinstance(k, str) or isinstance(v, bool)
            or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
            for k, v in values.items()):
        raise ValueError('Quantities must be finite, nonnegative numbers')
    return Counter(values)


def production_budget(wanted, catalog=None):
    catalog = catalog or json.loads(CATALOG.read_text())
    recipes = catalog['recipes']
    demand = quantities(wanted)
    stock, raw, oil, batches = Counter(), Counter(), Counter(), Counter()
    visiting = set()

    def expand(item, amount):
        used = min(stock[item], amount)
        stock[item] -= used
        amount -= used
        if amount <= 0:
            return
        if item in RAW:
            raw[item] += amount
            return
        if item in OIL:
            oil[item] += amount
            return
        name = ROUTES.get(item, item)
        if name in visiting:
            raise ValueError('Recipe dependency cycle: ' + name)
        if name not in recipes:
            raise ValueError('No production route: ' + item)
        recipe = recipes[name]
        products = recipe['products']
        if len(products) != 1 or products[0]['name'] != item or (
                products[0].get('probability', 1) != 1 or products[0].get('amount', 0) <= 0):
            raise ValueError('Unsupported uncertain or multiple-product route: ' + name)
        n = math.ceil(amount / products[0]['amount'])
        visiting.add(name)
        for ingredient in recipe['ingredients']:
            expand(ingredient['name'], ingredient['amount'] * n)
        visiting.remove(name)
        batches[name] += n
        stock[item] += n * products[0]['amount'] - amount

    for item, amount in demand.items():
        expand(item, amount)
    if oil:
        # Pin these coefficients to the exported recipes. Reject catalog drift
        # instead of silently applying the wrong refinery balance.
        expected = {
            'advanced-oil-processing': ({'water': 50, 'crude-oil': 100},
                                       {'heavy-oil': 25, 'light-oil': 45, 'petroleum-gas': 55}),
            'heavy-oil-cracking': ({'water': 30, 'heavy-oil': 40}, {'light-oil': 30}),
            'light-oil-cracking': ({'water': 30, 'light-oil': 30}, {'petroleum-gas': 20})}
        for name, (inputs, outputs) in expected.items():
            recipe = recipes[name]
            if ({i['name']: i['amount'] for i in recipe['ingredients']} != inputs or
                {p['name']: p.get('amount') for p in recipe['products']} != outputs or
                any(p.get('probability', 1) != 1 for p in recipe['products'])):
                raise ValueError('Oil coefficients differ from the supported catalog')
        h, l, g = (oil[n] for n in ('heavy-oil', 'light-oil', 'petroleum-gas'))
        refineries = math.ceil(max(h / 25, (l + .75 * h) / 63.75,
                                  (g + 2 * l / 3 + .5 * h) / 97.5))
        while True:
            light_cracks = math.ceil(max(0, g - 55 * refineries) / 20)
            heavy_cracks = math.ceil(max(0, l + 30 * light_cracks - 45 * refineries) / 30)
            if h + 40 * heavy_cracks <= 25 * refineries:
                break
            refineries += 1
        for name, n in [('advanced-oil-processing', refineries),
                        ('heavy-oil-cracking', heavy_cracks),
                        ('light-oil-cracking', light_cracks)]:
            if n:
                batches[name] += n
        raw['crude-oil'] += 100 * refineries
        raw['water'] += 50 * refineries + 30 * (heavy_cracks + light_cracks)
        stock.update({'heavy-oil': 25 * refineries - 40 * heavy_cracks - h,
                      'light-oil': 45 * refineries + 30 * heavy_cracks - 30 * light_cracks - l,
                      'petroleum-gas': 55 * refineries + 20 * light_cracks - g})
    work = []
    for name, n in sorted(batches.items()):
        recipe = recipes[name]
        if recipe['category'] not in MACHINES:
            raise ValueError('No supported machine for category: ' + recipe['category'])
        machine, speed = MACHINES[recipe['category']]
        work.append(dict(recipe=name, batches=n, machine=machine,
                         machine_seconds=n * recipe['energy'] / speed))
    result = dict(factorio_version=catalog['factorio_version'], wanted=dict(demand),
                  raw_materials=dict(raw), recipe_batches=dict(batches),
                  leftovers={k: v for k, v in stock.items() if v}, work=work)
    # Independent conservation check catches duplicate oil credit and missing
    # intermediates across the entire selected production graph.
    balance = Counter(raw)
    for name, n in batches.items():
        for ingredient in recipes[name]['ingredients']:
            balance[ingredient['name']] -= n * ingredient['amount']
        for product in recipes[name]['products']:
            balance[product['name']] += n * product['amount']
    for item in set(balance) | set(demand) | set(stock):
        if abs(balance[item] - demand[item] - stock[item]) > 1e-6:
            raise ValueError('Production conservation failed: ' + item)
    return result


def rocket_plan(completed=(), infrastructure=None, satellite=False):
    catalog = json.loads(CATALOG.read_text())
    research = research_plan(['military-2', 'automation', 'logistics',
                              'electric-mining-drill', 'rocket-silo'], completed, catalog)
    wanted = Counter(research['science'])
    wanted.update({'rocket-silo': 1, 'rocket-part': 100})
    wanted.update(quantities(infrastructure or {}))
    if satellite:
        wanted['satellite'] += 1
    return dict(objective='Launch a base-game rocket through normal mechanics',
                research=research, production=production_budget(dict(wanted), catalog),
                assumptions={'rocket_parts_required': 100, 'productivity_bonus': 0,
                             'satellite_included': satellite,
                             'infrastructure_included': infrastructure or {}},
                limitations=['100 parts is pinned to the base 2.0.77 silo; verify the live prototype.',
                             'No mining, fuel, power, belts, travel, defense or unlisted infrastructure budget.',
                             'Production triggers and current recipe unlocks need live verification.',
                             'Batch totals and machine work do not establish a feasible timed layout.',
                             'Advanced oil and cracking must be unlocked before using that route.'])


def capacity_plan(plan, minutes, utilization=.8):
    """Size recipe cells for a stated production window, not a run-time promise."""
    for value in (minutes, utilization):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('Capacity inputs must be finite numbers')
    if minutes<=0 or not 0<utilization<=1:
        raise ValueError('Positive minutes and utilization in (0,1] required')
    seconds=minutes*60*utilization
    cells=[dict(row, machines=math.ceil(row['machine_seconds']/seconds))
           for row in plan['production']['work']]
    totals=Counter()
    for cell in cells:totals[cell['machine']]+=cell['machines']
    return dict(production_window_minutes=minutes,utilization=utilization,cells=cells,
        machines_by_type=dict(totals),labs=math.ceil(plan['research']['lab_seconds_at_speed_1']/seconds),
        raw_per_minute={n:q/minutes for n,q in plan['production']['raw_materials'].items()},
        limitations=['Assumes every recipe has the entire stated production window.',
                     'Unlock delays shorten actual windows and can require more machines.',
                     'Dedicated recipe cells; machine reuse and productivity are not credited.',
                     'Mining, fuel, power, belts, pipes, travel and construction are not sized.',
                     'Use measured utilization; the supplied utilization is an assumption.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed', nargs='*', default=[])
    parser.add_argument('--infrastructure', default='{}')
    parser.add_argument('--satellite', action='store_true')
    parser.add_argument('--minutes', type=float, help='Optional production window for capacity sizing')
    parser.add_argument('--utilization', type=float, default=.8)
    args = parser.parse_args()
    result=rocket_plan(args.completed, json.loads(args.infrastructure), args.satellite)
    if args.minutes is not None:
        result['capacity']=capacity_plan(result,args.minutes,args.utilization)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
