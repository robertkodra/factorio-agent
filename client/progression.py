"""Read-only research budgeting from the pinned base-game catalog.

This is a dependency/material estimate, not a gameplay executor or a claim that
recipes are currently unlocked. Technology energy in this export is in ticks.
"""
import argparse
from collections import Counter
import json

from .materials import BASE, CATALOG, budget


def solid_budget(wanted):
    """Reject fluids, uncertain yields and missing recipes before using the early model."""
    recipes = json.loads(CATALOG.read_text())['recipes']
    visited, visiting = set(), set()

    def check(name):
        if name in {'water', 'crude-oil'}:
            raise ValueError('Fluid planning required: ' + name)
        if name in BASE or name in visited:
            return
        if name in visiting:
            raise ValueError('Recipe dependency cycle: ' + name)
        recipe = recipes.get(name)
        if recipe is None:
            raise ValueError('No supported recipe: ' + name)
        products = recipe['products']
        if len(products) != 1 or products[0]['name'] != name or (
                products[0].get('probability', 1) != 1 or 'amount' not in products[0]):
            raise ValueError('Single deterministic product required: ' + name)
        visiting.add(name)
        for ingredient in recipe['ingredients']:
            if ingredient.get('type', 'item') != 'item':
                raise ValueError('Fluid planning required: ' + name)
            check(ingredient['name'])
        visiting.remove(name)
        visited.add(name)

    for name in wanted:
        check(name)
    return budget(wanted)


def research_plan(targets, completed=(), catalog=None):
    catalog = catalog if catalog is not None else json.loads(CATALOG.read_text())
    technologies = catalog['technologies']
    done = set(completed)
    visiting, visited, order = set(), set(), []

    def visit(name):
        if name not in technologies:
            raise ValueError('Unknown technology: ' + name)
        if name in done or name in visited:
            return
        if name in visiting:
            raise ValueError('Technology dependency cycle: ' + name)
        visiting.add(name)
        technology = technologies[name]
        for prerequisite in technology.get('prerequisites', ()):
            visit(prerequisite)
        # Infinite/formula research needs a level-specific planner.
        if 'trigger' not in technology and (
                not isinstance(technology.get('count'), int)
                or technology['count'] < 1):
            raise ValueError('Finite research count required: ' + name)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for target in targets:
        visit(target)
    science = Counter()
    triggers, steps = [], []
    lab_ticks = 0
    for name in order:
        technology = technologies[name]
        step = {'technology': name}
        if 'trigger' in technology:
            step['trigger'] = technology['trigger']
            triggers.append(step.copy())
        else:
            packs = {i['name']: i['amount'] * technology['count']
                     for i in technology['ingredients']}
            science.update(packs)
            ticks = technology['count'] * technology['energy']
            lab_ticks += ticks
            step.update(science=packs, lab_ticks_at_speed_1=ticks)
        steps.append(step)
    return dict(factorio_version=catalog['factorio_version'], steps=steps,
                science=dict(science), production_triggers=triggers,
                lab_seconds_at_speed_1=lab_ticks / 60,
                limitations=['No credit for partially completed research.',
                             'Dependency order is not an optimized gameplay schedule.',
                             'Trigger progress and recipe unlocks require live verification.',
                             'Lab time excludes power/input shortages and travel; multiple labs overlap.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('targets', nargs='+')
    parser.add_argument('--completed', nargs='*', default=[])
    parser.add_argument('--supplies', default='{}', help='Additional item counts as JSON')
    args = parser.parse_args()
    result = research_plan(args.targets, args.completed)
    supplies = json.loads(args.supplies)
    if not isinstance(supplies, dict) or any(
            not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int) or v < 1
            for k, v in supplies.items()):
        parser.error('Supplies must map item names to positive integer counts')
    recipes = json.loads(CATALOG.read_text())['recipes']
    if any(name not in recipes for name in supplies):
        parser.error('Supplies must have a recipe in the pinned catalog')
    wanted = Counter(result['science']) + Counter(supplies)
    result['additional_supplies'] = supplies
    try:
        result['materials'] = solid_budget(wanted)
    except ValueError as error:
        result['materials'] = None
        result['material_budget_unavailable'] = str(error)
    result['limitations'].append('Material model supports early deterministic solid recipes only; '
                                 'production-trigger items, infrastructure and fuel are excluded '
                                 'unless supplied explicitly. It is not a rocket/oil budget.')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
