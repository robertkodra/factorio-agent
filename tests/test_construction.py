import unittest
from client.construction import clear_tree_for_belt


class ConstructionTests(unittest.TestCase):
    def test_only_an_observed_neutral_tree_on_the_planned_belt_is_mined(self):
        action=dict(type='place',entity='transport-belt',x=.5,y=.5)
        observation={'position':{'x':3,'y':.5}}
        tree=dict(type='tree',force='neutral',name='tree-01',x=.5,y=.5)
        proto={'tree-01':{'collision_box':{'left_top':{'x':-.4,'y':-.4},'right_bottom':{'x':.4,'y':.4}}}}
        def check(entity):
            return clear_tree_for_belt(action,observation,{'entities':[]},{'entities':[entity]},proto)
        result=check(tree)
        self.assertEqual([a['type'] for a in result['actions']],['walk','mine'])
        self.assertEqual(result['actions'][1]['item'],'wood')
        self.assertIsNone(check(dict(tree,force='player')))
        self.assertIsNone(check(dict(tree,type='container')))
        self.assertIsNone(check(dict(tree,x=5)))
