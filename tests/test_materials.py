"""Early-game material budgets checked against the observed 2.0.77 recipes."""
import unittest

from client.materials import budget


class MaterialsTests(unittest.TestCase):
    def test_science_expansion_cost_includes_five_gears_per_assembler(self):
        result = budget({'assembling-machine-1': 2, 'inserter': 2,
                         'automation-science-pack': 40})
        self.assertEqual(result['missing_base'], {'iron-plate': 132, 'copper-plate': 52})

    def test_shared_cable_batch_and_existing_inventory(self):
        result = budget({'electronic-circuit': 2}, {'copper-cable': 1, 'iron-plate': 1})
        self.assertEqual(result['missing_base'], {'iron-plate': 1, 'copper-plate': 3})
        self.assertEqual(result['leftovers'], {'copper-cable': 1})

    def test_twenty_green_packs_with_two_machines_and_output_inserters(self):
        result = budget({'assembling-machine-1': 2, 'inserter': 2,
                         'logistic-science-pack': 20})
        self.assertEqual(result['missing_base'], {'iron-plate': 162, 'copper-plate': 42})


if __name__ == '__main__':
    unittest.main()
