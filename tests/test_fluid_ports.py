import unittest
from client.fluid_ports import recipe_ports,connected_segment


class FluidPortTests(unittest.TestCase):
    def prototype(self):
        boxes=[]
        for index,kind in enumerate(['input','input','output','output','output'],1):
            boxes.append(dict(index=index,production_type=kind,connections=[dict(type='normal',
                direction=8 if kind=='input' else 0,
                positions=[{'x':index,'y':2},{'x':-2,'y':index},{'x':-index,'y':-2},{'x':2,'y':-index}])]))
        return {'fluid_boxes':boxes}
    def recipe(self):
        return {'ingredients':[{'type':'fluid','name':'crude-oil','fluidbox_index':2}],
                'products':[{'type':'fluid','name':'petroleum-gas','fluidbox_index':3}]}
    def test_explicit_indices_are_relative_to_input_or_output_slots(self):
        ports=recipe_ports(self.prototype(),self.recipe(),{'x':10,'y':20})
        self.assertEqual([p['box'] for p in ports],[2,5])
        self.assertEqual(ports[0]['target'],{'x':12,'y':23})
    def test_rotated_connection_uses_rotated_port_and_outward_direction(self):
        p=recipe_ports(self.prototype(),self.recipe(),{'x':10,'y':20},'east')[0]
        self.assertEqual(p['target'],{'x':7,'y':22})
        with self.assertRaises(ValueError):recipe_ports(self.prototype(),self.recipe(),{'x':0,'y':0},'northeast')
    def test_segment_identity_requires_both_endpoints_and_compatible_fluid(self):
        a={'fluid_boxes':[{'index':1,'segment_id':12,'locked_fluid':'water'}]}
        b={'fluid_boxes':[{'index':2,'segment_id':12}]}
        self.assertTrue(connected_segment(a,1,b,2,'water'))
        self.assertFalse(connected_segment(a,1,b,2,'crude-oil'))
        self.assertFalse(connected_segment(a,1,{},2,'water'))
        b['fluid_boxes'][0]['segment_id']=13
        self.assertFalse(connected_segment(a,1,b,2,'water'))

    def test_output_only_boxes_without_segments_use_directed_reciprocal_ports(self):
        from client.fluid_ports import fluid_path
        factory={'entities':[{'id':1,'fluid_boxes':[{'index':2,'locked_fluid':'steam',
            'connections':[{'target_id':2,'target_box':1,'flow':'output'}]}]},
            {'id':2,'fluid_boxes':[{'index':1,'segment_id':4,'locked_fluid':'steam',
            'connections':[{'target_id':1,'target_box':2,'flow':'input-output'}]}]}]}
        self.assertEqual(fluid_path(factory,(1,2),(2,1),'steam'),[(1,2),(2,1)])
        self.assertEqual(fluid_path(factory,(2,1),(1,2),'steam'),[])
        self.assertEqual(fluid_path(factory,(1,2),(2,1),'water'),[])
        factory['entities'][1]['fluid_boxes'][0]['connections']=[]
        self.assertEqual(fluid_path(factory,(1,2),(2,1),'steam'),[])

    def test_unlocked_pipe_with_another_fluid_is_not_accepted(self):
        from client.fluid_ports import fluid_path
        f={'entities':[{'id':1,'fluid_boxes':[{'index':1}],
                       'fluids':[{'index':1,'name':'petroleum-gas'}]}]}
        self.assertEqual(fluid_path(f,(1,1),(1,1),'water'),[])
