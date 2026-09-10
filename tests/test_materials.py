"""Early-game material budgets checked against the observed 2.0.77 recipes."""
import unittest

from client.materials import budget, craft_budget


class MaterialsTests(unittest.TestCase):
    def test_new_lab_craft_is_not_satisfied_by_an_existing_lab(self):
        result = craft_budget([('lab', 1)], {'lab': 1})
        self.assertEqual(result['missing_base'], {'iron-plate': 36, 'copper-plate': 15})
        self.assertEqual(result['leftovers']['lab'], 2)

    def test_ordered_crafts_share_the_intermediate_they_actually_produce(self):
        result = craft_budget([('iron-gear-wheel', 1), ('transport-belt', 1)],
                              {'iron-plate': 3})
        self.assertEqual(result['missing_base'], {})
        self.assertEqual(result['recipe_batches'], {'iron-gear-wheel': 1, 'transport-belt': 1})
        self.assertEqual(result['leftovers'], {'transport-belt': 2})

    def test_hand_crafting_does_not_expand_missing_steel_through_a_furnace(self):
        result = craft_budget([('piercing-rounds-magazine', 1)],
                              {'firearm-magazine': 1, 'copper-plate': 5, 'iron-plate': 5})
        self.assertEqual(result['missing_base'], {'steel-plate': 1})
        with self.assertRaisesRegex(ValueError, 'not supported for hand crafting'):
            craft_budget([('steel-plate', 1)], {'iron-plate': 5})

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
