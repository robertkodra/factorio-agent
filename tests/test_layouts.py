import unittest

from client.layouts import assembly_cell


class LayoutTests(unittest.TestCase):
    def test_opposing_furnace_rows_share_one_output_without_duplicate_placements(self):
        from client.layouts import smelting_block
        for n in (12,24):
            b=smelting_block('iron-plate',n,(10,20))
            self.assertEqual(b['materials']['stone-furnace'],2*n)
            positions=[(s['position']['x'],s['position']['y']) for s in b['sites']]
            self.assertEqual(len(positions),len(set(positions)))
            outputs=[s for s in b['sites'] if s['entity']=='transport-belt' and s['position']['y']==22.5]
            self.assertEqual(len(outputs),3*(n-1)+1)
            top=[s for s in b['sites'] if s['entity']=='inserter' and s['position']['y']==21.5]
            bottom=[s for s in b['sites'] if s['entity']=='inserter' and s['position']['y']==23.5]
            self.assertTrue(all(s['direction']=='north' for s in top))
            self.assertTrue(all(s['direction']=='south' for s in bottom))

    def test_smelting_row_has_separate_inputs_outputs_and_pole_coverage(self):
        from client.layouts import smelting_row
        row = smelting_row('iron-plate', 8)
        self.assertEqual(row['materials']['stone-furnace'], 8)
        self.assertEqual(row['materials']['inserter'], 16)
        sites = {s['id']:s for s in row['sites']}
        for i in range(8):
            f = sites[f'row-{i}-furnace']['position']
            p = sites[f'row-{i}-pole']['position']
            for label, offset in [('input-arm',-1.5),('output-arm',1.5)]:
                a=sites[f'row-{i}-{label}']['position']
                self.assertEqual(a['y']-f['y'],offset)
                self.assertLessEqual(abs(a['x']-p['x']),2.5)
                self.assertLessEqual(abs(a['y']-p['y']),2.5)
            self.assertGreater(p['x'],f['x']+1)
            self.assertLess(p['x'],f['x']+2)
        self.assertEqual(row['ports']['mixed_input'],{'x':21.5,'y':-2.5})

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
