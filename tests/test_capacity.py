import unittest

from client.capacity import coal_reserve, science_capacity


class CapacityTests(unittest.TestCase):
    def test_bootstrap_red_leaves_construction_headroom(self):
        result = science_capacity()
        self.assertEqual(result['nominal_science_per_minute']['automation-science-pack'], 12)
        self.assertEqual(result['required_plates_per_minute'], {'iron-plate': 24, 'copper-plate': 12})
        self.assertEqual(result['plate_headroom_per_minute'], {'iron-plate': 21, 'copper-plate': 3})
        self.assertEqual(result['proportional_supply_fraction'], 1)

    def test_green_intermediates_expose_copper_bottleneck(self):
        result = science_capacity(red=4, green=2)
        self.assertEqual(result['required_plates_per_minute'], {'iron-plate': 103, 'copper-plate': 39})
        self.assertEqual(result['minimum_direct_burner_lines'], {'iron-plate': 7, 'copper-plate': 3})
        self.assertAlmostEqual(result['proportional_supply_fraction'], 15 / 39)

    def test_no_supply_or_no_demand(self):
        self.assertEqual(science_capacity(iron_per_minute=0)['proportional_supply_fraction'], 0)
        result = science_capacity(red=0, green=0, iron_per_minute=0, copper_per_minute=0)
        self.assertEqual(sum(result['supply_limited_science_per_minute'].values()), 0)

    def test_fuel_rounds_each_machine_and_includes_margin(self):
        self.assertEqual(coal_reserve(150, 180), 9)
        self.assertEqual(coal_reserve(90, 180), 6)
        self.assertEqual(coal_reserve(150, 180, margin=0), 7)
        self.assertEqual(coal_reserve(150, 0), 0)

    def test_invalid_configuration_is_not_reported_as_capacity(self):
        for bad in [True, -1, float('nan'), float('inf')]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    science_capacity(iron_per_minute=bad)
                with self.assertRaises(ValueError):
                    coal_reserve(150, bad)
        for bad in [True, -1, 1.5]:
            with self.assertRaises(ValueError):
                science_capacity(red=bad)
