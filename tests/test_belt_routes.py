import unittest

from client.belt_routes import belt_route, nearby_belt_batch


class BeltRouteTests(unittest.TestCase):
    def test_underground_crossing_preserves_direction_and_native_span(self):
        from client.belt_routes import underground_pair
        r=underground_pair((.5,2.5),(.5,-.5),5)
        self.assertEqual([s['direction'] for s in r['sites']],['north','north'])
        self.assertEqual([s['belt_type'] for s in r['sites']],['input','output'])
        with self.assertRaises(ValueError):underground_pair((.5,.5),(.5,6.5),5)
        with self.assertRaises(ValueError):underground_pair((.5,.5),(1.5,1.5),5)

    def test_corner_points_toward_next_tile_and_keeps_final_output(self):
        r = belt_route([(0.5, 0.5), (3.5, 0.5), (3.5, -1.5)], 'west')
        self.assertEqual([s['direction'] for s in r['sites']],
                         ['east', 'east', 'east', 'north', 'north', 'west'])
        self.assertEqual(r['materials']['transport-belt'], 6)

    def test_rejects_crossings_diagonal_and_unbounded_paths(self):
        for points in [[(.5,.5),(1.5,1.5)],[(.5,.5),(.5,.5)],
                       [(.5,.5),(2.5,.5),(.5,.5)],[(.5,.5),(10001.5,.5)],
                       [(0,0),(2,0)]]:
            with self.assertRaises(ValueError): belt_route(points, 'north')

    def test_batch_respects_stock_radius_existing_sites_and_unlocks(self):
        sites = {s['id']:s for s in belt_route([(.5,.5),(10.5,.5)], 'east')['sites']}
        first = dict(type='place', entity='transport-belt', x=.5,y=.5,direction='east')
        choice = dict(key='build:belt-0', actions=[first])
        o = dict(position={'x':.5,'y':.5},inventory=[{'name':'transport-belt','count':3}])
        sites['belt-2']['requires']=['logistics-2']
        actual = nearby_belt_batch(choice, sites, {'belt-1':{'name':'transport-belt'}}, o, [])
        self.assertEqual([a['x'] for a in actual['actions']], [.5,3.5,4.5])
        o['inventory'][0]['count']=100
        actual = nearby_belt_batch(choice, sites, {}, o, ['logistics-2'])
        self.assertEqual(len(actual['actions']),6)
        self.assertEqual(choice['actions'],[first])

    def test_never_batches_transfers_or_travel(self):
        for kind in ['walk','take']:
            choice = dict(actions=[dict(type=kind)])
            self.assertIs(nearby_belt_batch(choice, {}, {}, {}, []), choice)


if __name__ == '__main__': unittest.main()
