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
