import unittest

from client.progression import research_plan, solid_budget


class ProgressionTests(unittest.TestCase):
    def test_military_two_counts_prerequisites_and_green_consumption(self):
        plan = research_plan(['military-2', 'automation', 'gun-turret',
                              'logistics', 'electric-mining-drill'])
        self.assertEqual(plan['science'], {'automation-science-pack': 220,
                                          'logistic-science-pack': 20})
        names = [step['technology'] for step in plan['steps']]
        self.assertEqual(len(names), len(set(names)))
        for prerequisite in ['military', 'steel-processing', 'logistic-science-pack']:
            self.assertLess(names.index(prerequisite), names.index('military-2'))
        self.assertTrue(plan['production_triggers'])
        # Military 2 alone needs twenty 15-second research units, not 900 seconds each.
        only = research_plan(['military-2'], completed=['military', 'steel-processing',
                                                       'logistic-science-pack'])
        self.assertEqual(only['lab_seconds_at_speed_1'], 300)
        self.assertEqual(only['production_triggers'], [])

    def test_completed_target_does_not_budget_it_again(self):
        plan = research_plan(['military-2'], completed=['military-2'])
        self.assertEqual(plan['steps'], [])
        self.assertEqual(plan['science'], {})

    def test_defense_is_budgeted_and_oil_is_not_silently_treated_as_raw_stock(self):
        materials = solid_budget({'automation-science-pack': 220,
                                  'logistic-science-pack': 20,
                                  'gun-turret': 2, 'firearm-magazine': 40})
        self.assertEqual(materials['missing_base'], {'iron-plate': 790, 'copper-plate': 270})
        with self.assertRaisesRegex(ValueError, 'Fluid planning required'):
            solid_budget({'chemical-science-pack': 1})

    def test_bad_catalog_dependencies_fail_instead_of_underbudgeting(self):
        with self.assertRaisesRegex(ValueError, 'Unknown technology'):
            research_plan(['not-a-technology'])
        catalog = {'factorio_version': 'test', 'technologies': {
            'a': {'prerequisites': ['b'], 'count': 1, 'energy': 60, 'ingredients': []},
            'b': {'prerequisites': ['a'], 'count': 1, 'energy': 60, 'ingredients': []}}}
        with self.assertRaisesRegex(ValueError, 'cycle'):
            research_plan(['a'], catalog=catalog)
        catalog['technologies']['b']['prerequisites'] = []
        catalog['technologies']['b']['count'] = None
        with self.assertRaisesRegex(ValueError, 'Finite research count'):
            research_plan(['a'], catalog=catalog)


if __name__ == '__main__':
    unittest.main()
