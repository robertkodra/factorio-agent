import copy
import unittest
from client.production_audit import compare

class AuditTests(unittest.TestCase):
    def test_craft_rates_exclude_new_or_reconfigured_machines(self):
        before=dict(tick=100,entities=[dict(id=1,name='assembling-machine-1',recipe='copper-cable',products_finished=5)],produced={'iron-plate':20})
        after=dict(tick=3700,entities=[dict(id=1,name='assembling-machine-1',recipe='copper-cable',products_finished=15),dict(id=2,name='stone-furnace',products_finished=8)],produced={'iron-plate':30})
        report=compare(before,after)
        self.assertEqual(report['machines'][0]['crafts_per_game_minute'],10)
        self.assertNotIn('completed_crafts',report['machines'][1])
        self.assertEqual(report['item_production_delta']['iron-plate'],10)
        after['entities'][0]['recipe']='iron-gear-wheel'
        self.assertNotIn('completed_crafts',compare(before,after)['machines'][0])

    def test_regressed_ticks_and_counters_are_rejected(self):
        before=dict(tick=100,entities=[],produced={'iron-plate':20})
        with self.assertRaises(ValueError):compare(before,before)
        after=copy.deepcopy(before);after.update(tick=200,produced={'iron-plate':19})
        with self.assertRaises(ValueError):compare(before,after)
