"""Read-only early-science capacity and coal reserves for base 2.0.77.

Normal assembler-1 speed is 0.5; a burner drill feeding one stone furnace
produces at most 15 iron/copper plates per minute. Sources and assumptions:
knowledge/speedrun-preparation.md. These estimates do not observe a live factory.
"""
import argparse
from collections import Counter
import json
import math

from .materials import CATALOG
from .progression import solid_budget


def nonnegative(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (
            not math.isfinite(value) or value < 0):
        raise ValueError('Expected a finite nonnegative number')
    return value


def coal_reserve(power_kw, away_seconds, margin=0.25):
    """Whole coal items at full rated fuel draw, including the time margin.

    Coal is 4 MJ; do not credit partially burnt fuel. Apply separately to each
    machine, then subtract its current whole-item inventory when refueling.
    Supply fuel-input power, including efficiency losses if applicable.
    """
    for value in (power_kw, away_seconds, margin):
        nonnegative(value)
    return math.ceil(power_kw * away_seconds * (1 + margin) / 4000)


def science_capacity(red=2, green=0, iron_per_minute=45, copper_per_minute=15):
    for count in (red, green):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError('Assembler counts must be nonnegative integers')
    supply = {'iron-plate': nonnegative(iron_per_minute),
              'copper-plate': nonnegative(copper_per_minute)}
    catalog = json.loads(CATALOG.read_text())
    if catalog['factorio_version'] != '2.0.77':
        raise ValueError('Capacity assumptions require base 2.0.77')
    rates, demand = {}, Counter()
    for name, count in [('automation-science-pack', red), ('logistic-science-pack', green)]:
        rates[name] = count * 0.5 * 60 / catalog['recipes'][name]['energy']
        # Two packs exactly amortize belt/cable batches in these pinned recipes.
        for item, amount in solid_budget({name: 2})['missing_base'].items():
            demand[item] += rates[name] * amount / 2
    scale = min([1.0] + [supply[item] / amount for item, amount in demand.items() if amount])
    return dict(
        factorio_version='2.0.77', nominal_science_per_minute=rates,
        required_plates_per_minute=dict(demand), supplied_plates_per_minute=supply,
        plate_headroom_per_minute={item: supply[item] - demand[item] for item in supply},
        proportional_supply_fraction=scale,
        supply_limited_science_per_minute={name: rate * scale for name, rate in rates.items()},
        minimum_direct_burner_lines={item: math.ceil(amount / 15) for item, amount in demand.items()},
        limitations=['Assumes normal quality, full power and no productivity or speed bonuses.',
                     'Supply fraction preserves the requested red/green ratio; it is not measured throughput.',
                     'Intermediate crafting, delivery, lab capacity, construction and defense are excluded.',
                     'Burner-line counts assume sufficient ore, fuel and clear outputs.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--red', type=int, default=2)
    parser.add_argument('--green', type=int, default=0)
    parser.add_argument('--iron-per-minute', type=float, default=45)
    parser.add_argument('--copper-per-minute', type=float, default=15)
    parser.add_argument('--away-seconds', type=float, default=180)
    args = parser.parse_args()
    try:
        result = science_capacity(args.red, args.green, args.iron_per_minute, args.copper_per_minute)
        result['coal_per_machine_with_25_percent_margin'] = {
            name: coal_reserve(power, args.away_seconds)
            for name, power in [('burner-mining-drill', 150), ('stone-furnace', 90)]}
        result['away_seconds'] = args.away_seconds
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
