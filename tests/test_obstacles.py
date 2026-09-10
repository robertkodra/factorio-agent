import unittest
from client.obstacles import neutral_bounds
from client.routes import service_stances

class ObstacleTests(unittest.TestCase):
    def test_observed_wreck_excludes_stance_even_without_owned_factory_entry(self):
        scan={'entities':[{'name':'wreck','type':'container','force':'neutral','x':3,'y':0}]}
        prototype={'wreck':{'collision_box':{'left_top':{'x':-1,'y':-.5},'right_bottom':{'x':1,'y':.5}}}}
        bounds=neutral_bounds(scan,prototype)
        options=service_stances({'position':{'x':0,'y':0},'stand':{'x':3,'y':0}},bounds)
        self.assertNotIn({'x':3,'y':0},options)
        self.assertEqual(neutral_bounds({'entities':[]},prototype),[])

    def test_resources_and_non_neutral_entities_do_not_become_neutral_solids(self):
        scan={'entities':[{'name':'ore','type':'resource','force':'neutral','x':0,'y':0},
                          {'name':'tank','type':'car','force':'enemy','x':1,'y':0}]}
        self.assertEqual(neutral_bounds(scan,{}),[])
