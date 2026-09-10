import unittest
from client.fluid_routes import pipe_route


class FluidRouteTests(unittest.TestCase):
    def test_routes_around_obstacle_with_adjacent_tiles_and_real_pipe_cost(self):
        tiles={(x,y) for x in range(9) for y in range(7)}
        blocked={(4,y) for y in range(5)}
        r=pipe_route('water',(1,1),(7,1),tiles,blocked)
        self.assertFalse(set(r['path']) & blocked)
        self.assertEqual(r['materials']['pipe'],len(r['path']))
        for a,b in zip(r['path'],r['path'][1:]):
            self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),1)
        self.assertTrue(all(s['entity']=='pipe' and s['build'] for s in r['sites']))

    def test_cannot_mix_fluids_or_escape_the_surveyed_region(self):
        tiles={(x,y) for x in range(7) for y in range(5)}
        crossing={(3,y):'crude-oil' for y in range(5)}
        with self.assertRaisesRegex(ValueError,'No separated'):
            pipe_route('water',(1,2),(5,2),tiles,existing=crossing)
        with self.assertRaisesRegex(ValueError,'Endpoints'):
            pipe_route('water',(2,2),(5,2),tiles,existing=crossing)
        with self.assertRaisesRegex(ValueError,'Endpoints'):
            pipe_route('water',(-1,2),(5,2),tiles)

    def test_reuses_matching_pipe_and_keeps_construction_access_clear(self):
        tiles={(x,y) for x in range(7) for y in range(5)}
        r=pipe_route('water',(1,2),(5,2),tiles,existing={(3,2):'water'})
        self.assertEqual(r['materials']['pipe'],4)
        for s in r['sites']:
            access=(s['stand']['x']-.5,s['stand']['y']-.5)
            self.assertNotIn(access,r['path'])
