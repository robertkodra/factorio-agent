import unittest
from client.routes import corridor, service_stances


class RouteTests(unittest.TestCase):
    def test_explicit_corridor_detours_and_keeps_steps_short(self):
        network={'nodes':{'a':{'x':0,'y':0},'b':{'x':0,'y':60},'c':{'x':60,'y':60}},
                 'edges':[['a','b'],['b','c']]}
        route=corridor({'x':0,'y':0},{'x':60,'y':60},network)
        self.assertIn({'x':0,'y':60},route)
        self.assertNotIn({'x':30,'y':30},route)
        previous={'x':0,'y':0}
        for p in route:
            self.assertLessEqual(((p['x']-previous['x'])**2+(p['y']-previous['y'])**2)**.5,24)
            previous=p
        network['edges']=[]
        with self.assertRaises(ValueError):corridor({'x':0,'y':0},{'x':60,'y':60},network)

    def test_stance_inside_a_new_lab_is_replaced(self):
        site={'position':{'x':0,'y':0},'stand':{'x':2,'y':0}}
        entities=[{'type':'lab','box':{'left_top':{'x':1,'y':-1},'right_bottom':{'x':3,'y':1}}}]
        stances=service_stances(site,entities)
        self.assertNotIn(site['stand'],stances)
        self.assertTrue(stances)
