import copy
import json
import unittest

from client.materials import CATALOG
from client.rocket_plan import production_budget, rocket_plan, capacity_plan


class RocketBudgetTests(unittest.TestCase):
    def test_oil_shared_products_are_not_budgeted_as_separate_refineries(self):
        p = production_budget({'heavy-oil': 25, 'light-oil': 45, 'petroleum-gas': 55})
        self.assertEqual(p['recipe_batches'], {'advanced-oil-processing': 1})
        self.assertEqual(p['raw_materials'], {'crude-oil': 100, 'water': 50})
        self.assertEqual(p['leftovers'], {})

    def test_gas_demand_keeps_reserved_lubricant_and_fuel_feeds(self):
        for h in (0, 1, 25, 200):
            for l in (0, 45, 123):
                for g in (1, 55, 1000):
                    p = production_budget({'heavy-oil': h, 'light-oil': l, 'petroleum-gas': g})
                    b = p['recipe_batches']; r = b['advanced-oil-processing']
                    hc, lc = b.get('heavy-oil-cracking', 0), b.get('light-oil-cracking', 0)
                    self.assertGreaterEqual(25*r-40*hc, h)
                    self.assertGreaterEqual(45*r+30*hc-30*lc, l)
                    self.assertGreaterEqual(55*r+20*lc, g)
                    # Independently enumerate all possibilities for fewer batches.
                    for smaller in range(r):
                        for hh in range((25*smaller)//40+1):
                            for ll in range((45*smaller+30*hh)//30+1):
                                self.assertFalse(25*smaller-40*hh >= h and
                                    45*smaller+30*hh-30*ll >= l and 55*smaller+20*ll >= g)

    def test_full_rocket_contains_late_science_and_all_hundred_parts(self):
        p = rocket_plan()
        self.assertEqual(p['production']['wanted']['rocket-part'], 100)
        self.assertGreater(p['research']['science']['utility-science-pack'], 0)
        self.assertGreater(p['production']['raw_materials']['crude-oil'], 0)
        self.assertIn('lubricant', p['production']['recipe_batches'])
        self.assertNotIn('satellite', p['production']['wanted'])
        self.assertEqual(rocket_plan(satellite=True)['production']['wanted']['satellite'], 1)

    def test_bad_inputs_and_changed_oil_formula_fail_closed(self):
        for wanted in ({'iron-plate': -1}, {'coal': float('nan')}, {'coal': True},
                       {'unknown-item': 1}, {'uranium-235': 1}):
            with self.assertRaises(ValueError):
                production_budget(wanted)
        catalog = json.loads(CATALOG.read_text())
        catalog['recipes']['advanced-oil-processing']['products'][0]['amount'] = 100
        with self.assertRaisesRegex(ValueError, 'coefficients'):
            production_budget({'heavy-oil': 1}, catalog)

    def test_batch_rounding_and_all_smelting_costs_are_included(self):
        p = production_budget({'steel-plate': 1, 'copper-cable': 1})
        self.assertEqual(p['raw_materials'], {'iron-ore': 5, 'copper-ore': 1})
        self.assertEqual(p['leftovers'], {'copper-cable': 1})

    def test_capacity_covers_workload_and_does_not_claim_elapsed_time(self):
        plan=rocket_plan();sized=capacity_plan(plan,120,.8)
        for cell in sized['cells']:
            self.assertGreaterEqual(cell['machines']*120*60*.8,cell['machine_seconds'])
            self.assertLess((cell['machines']-1)*120*60*.8,cell['machine_seconds'])
        self.assertGreater(sized['machines_by_type']['stone-furnace'],100)
        for minutes,usage in [(0,.8),(120,1.1),(120,0),(float('nan'),.8)]:
            with self.assertRaises(ValueError):capacity_plan(plan,minutes,usage)
