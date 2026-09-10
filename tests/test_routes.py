import unittest
from client.routes import corridor, service_stances


class RouteTests(unittest.TestCase):
    def test_new_drill_cannot_become_an_interpolated_walk_destination(self):
        network={'nodes':{'a':{'x':40,'y':0},'b':{'x':0,'y':0}},'edges':[['a','b']]}
        obstacle={'type':'mining-drill','box':{'left_top':{'x':19,'y':-1},'right_bottom':{'x':21,'y':1}}}
        route=corridor({'x':40,'y':0},{'x':0,'y':0},network,[obstacle])
        self.assertNotIn({'x':20,'y':0},route)
        for p in route:
            self.assertFalse(18.75<p['x']<21.25 and -1.25<p['y']<1.25)

    def test_inserter_center_is_not_a_service_stance(self):
        p={'x':0,'y':0}
        e={'type':'inserter','box':{'left_top':{'x':-.15,'y':-.15},'right_bottom':{'x':.15,'y':.15}}}
        self.assertNotEqual(service_stances({'position':p,'stand':p},[e])[0],p)

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

    def test_natural_gather_stances_leave_margin_for_shorter_reach(self):
        from client.routes import service_stances,distance
        p={'x':0,'y':0}
        options=service_stances({'position':p,'stand':{'x':3,'y':0},'gather':'wood'},[])
        self.assertEqual(options[0],{'x':2.,'y':0.})
        self.assertTrue(all(distance(p,s)<=2.01 for s in options))
