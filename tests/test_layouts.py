import unittest

from client.layouts import assembly_cell


class LayoutTests(unittest.TestCase):
    def test_cell_costs_and_ports_translate_together(self):
        a=assembly_cell('automation-science-pack')
        b=assembly_cell('automation-science-pack',(24,-16))
        self.assertEqual(a['materials'],{'small-electric-pole':2,'wooden-chest':2,
            'inserter':2,'assembling-machine-1':1})
        for left,right in zip(a['sites'],b['sites']):
            for k in ('position','stand'):
                self.assertEqual(right[k]['x']-left[k]['x'],24)
                self.assertEqual(right[k]['y']-left[k]['y'],-16)
        sites={s['id']:s for s in a['sites']}
        machine=sites['cell-machine']
        self.assertEqual(machine['input_site'],'cell-input')
        self.assertEqual(machine['output_site'],'cell-output')
        for label in ('inserter-in','inserter-out'):
            inserter=sites['cell-'+label]
            self.assertEqual(inserter['direction'],'west')
            self.assertLessEqual(abs(inserter['position']['x']-sites['cell-power']['position']['x']),2.5)

    def test_fluid_recipe_cannot_be_silently_placed_as_an_unconnected_solid_cell(self):
        with self.assertRaisesRegex(ValueError,'route fluids'):
            assembly_cell('processing-unit')
        with self.assertRaises(ValueError):assembly_cell('automation-science-pack',(.5,0))

    def test_buffered_smelting_geometry_has_a_complete_native_item_path(self):
        from client.layouts import smelting_cell
        cell=smelting_cell('iron-plate',(10,10),'iron')
        sites={s['id']:s for s in cell['sites']}
        drill=sites['iron-drill']['position'];feed=sites['iron-input']['position']
        self.assertEqual((drill['x'],drill['y']+2),(feed['x'],feed['y']))
        arm=sites['iron-inserter-in']['position']
        self.assertEqual((arm['x'],arm['y']-1),(feed['x'],feed['y']))
        self.assertTrue(sites['iron-furnace']['external_inputs'])
        self.assertEqual(cell['materials']['inserter'],2)

    def test_pole_chain_respects_wire_distance_after_quantization(self):
        import math
        from client.layouts import pole_line
        for end in ((100.5,33.5),(-70.5,100.5),(.5,.5)):
            line=pole_line((.5,.5),end)
            path=[(.5,.5)]+[(s['position']['x'],s['position']['y']) for s in line['sites']]+[end]
            self.assertTrue(all(math.dist(a,b)<=7.5 for a,b in zip(path,path[1:])))
        with self.assertRaises(ValueError):pole_line((0,0),(10.5,10.5))
        with self.assertRaises(ValueError):pole_line((.5,.5),(10.5,10.5),wire_distance=2)
