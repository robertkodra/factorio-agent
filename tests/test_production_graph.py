from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from client.mirror_log import MirrorLog
from client.production_graph import analyze_journal, build_graph, upstream
from client.state_mirror import InvalidState, digest
from tests.test_state_mirror import ROOT, entities, ready, temporary_runtime


def block():
    def row(eid, kind, x, y, width=1, **kw):
        return dict(id=eid,name=kind,type=kind,position=dict(x=x,y=y),direction=0,
                    box=dict(left_top=dict(x=x-width/2,y=y-width/2),
                             right_bottom=dict(x=x+width/2,y=y+width/2)), **kw)
    return [
        row(1,'mining-drill',0,-5,3,drop=dict(x=0,y=-3),
            mining_target=dict(name='iron-ore',amount=100,position=dict(x=0,y=-5))),
        row(2,'container',0,-3,chest=[dict(name='coal',count=1),dict(name='iron-ore',count=10)]),
        row(3,'inserter',0,-1.5,pickup=dict(x=0,y=-3),drop=dict(x=0,y=0)),
        row(4,'furnace',0,0,2,recipe='iron-plate',input=[],output=[],products_finished=5),
        row(5,'inserter',0,1.5,pickup=dict(x=0,y=0),drop=dict(x=0,y=3)),
        row(6,'container',0,3,chest=[])]


def mirrored(rows, *, legacy=False):
    m=ready();m.state['domains']={k:v for k,v in m.state['domains'].items() if not k.startswith('entity:')}
    sample=entities();sample['entities']=deepcopy(rows)
    if legacy:sample['scope']='owned_factory_replay'
    m.entities(sample,1.,[r['id'] for r in rows])
    return m


class ProductionGraphTests(unittest.TestCase):
    def test_journal_analysis_retains_inputs_and_rejects_corruption_and_public_output(self):
        with temporary_runtime() as d:
            source=Path(d)/'mirror.jsonl';log=MirrorLog(source)
            log.append(mirrored(block()));log.close()
            original=hashlib.sha256(source.read_bytes()).hexdigest()
            output=Path(d)/'analysis'
            report=analyze_journal(source,output,list(range(1,7)))
            self.assertEqual(report['source_sha256'],original)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)
            self.assertEqual(report['graph_sha256'],digest(json.loads((output/'graph.json').read_text())))
            self.assertEqual(report['live_calls'],0);self.assertIsNone(report['throughput'])
            with self.assertRaises(FileExistsError):analyze_journal(source,output,[1])
            with self.assertRaises(ValueError):analyze_journal(source,ROOT/'public-graph',[1])
            corrupt=json.loads(source.read_text());corrupt['after']='0'*64
            bad=Path(d)/'corrupt.jsonl';bad.write_text(json.dumps(corrupt)+'\n')
            with self.assertRaises(ValueError):analyze_journal(bad,Path(d)/'failed',[1])
            self.assertTrue((Path(d)/'failed/failure.json').exists())

    def test_direct_feed_chain_uses_observed_ports_and_does_not_mutate_mirror(self):
        m=mirrored(block());before=m.checkpoint()
        g=build_graph(m,list(range(1,7)),1.)
        self.assertEqual({(e['source'],e['target']) for e in g['edges']},
                         {('entity:%d'%i,'entity:%d'%(i+1)) for i in range(1,6)} |
                         {('entity:1:resource','entity:1')})
        self.assertEqual(set(upstream(g,'entity:6')),
                         {'entity:%d'%i for i in range(1,6)}|{'entity:1:resource'})
        self.assertTrue(g['offline_only'])
        self.assertEqual(m.checkpoint(),before)

    def test_translation_rotation_and_new_ids_preserve_chain_without_site_edits(self):
        rows=block()
        def transform(p):return dict(x=50-p['y'],y=-20+p['x'])
        for r in rows:
            r['id']+=100;r['position']=transform(r['position'])
            for field in ('pickup','drop'):
                if field in r:r[field]=transform(r[field])
            a,b=map(transform,r['box'].values())
            r['box']=dict(left_top={k:min(a[k],b[k]) for k in a},
                          right_bottom={k:max(a[k],b[k]) for k in a})
            if 'mining_target' in r:r['mining_target']['position']=transform(r['mining_target']['position'])
        g=build_graph(mirrored(rows),[r['id'] for r in reversed(rows)],1.)
        self.assertEqual(len(g['edges']),6)
        self.assertEqual(len(upstream(g,'entity:106')),6)
        self.assertEqual(g,build_graph(mirrored(list(reversed(rows))),[r['id'] for r in rows],1.))

    def test_disconnected_port_is_unresolved_not_invented_supply_or_hidden_entity(self):
        rows=block();rows[2]['pickup']=dict(x=8,y=8)
        g=build_graph(mirrored(rows),list(range(1,7)),1.)
        issue=next(i for i in g['issues'] if i['code']=='endpoint_unresolved')
        self.assertEqual(issue['entity'],'entity:3')
        self.assertEqual(issue['evidence']['candidates'],[])
        self.assertNotIn('entity:2',upstream(g,'entity:6'))
        # A partial sample also yields unknown, never an assertion of destruction.
        g=build_graph(mirrored(block()),[3,4,5,6],1.)
        self.assertTrue(any(i['code']=='endpoint_unresolved' for i in g['issues']))
        self.assertNotIn('entity:2',{n['key'] for n in g['nodes']})

    def test_ambiguous_geometry_does_not_choose_an_arbitrary_target(self):
        rows=block();extra=deepcopy(rows[1]);extra['id']=7;rows.append(extra)
        g=build_graph(mirrored(rows),list(range(1,8)),1.)
        self.assertTrue(any(i['code']=='endpoint_ambiguous' for i in g['issues']))
        self.assertNotIn('entity:2',upstream(g,'entity:6'))

    def test_belt_lanes_remain_separate_without_guessed_transfer(self):
        rows=block();rows[1].update(type='transport-belt',name='transport-belt',
            lines=[[dict(name='iron-ore',count=5)],[dict(name='coal',count=1)]])
        g=build_graph(mirrored(rows),list(range(1,7)),1.)
        lanes={n['lane']:n for n in g['nodes'] if n['kind']=='transport-lane'}
        self.assertEqual(lanes[1]['contents'][0]['name'],'iron-ore')
        self.assertEqual(lanes[2]['contents'][0]['name'],'coal')
        self.assertTrue(any(i['code']=='lane_mapping_unresolved' for i in g['issues']))
        self.assertNotIn('entity:2',upstream(g,'entity:6'))

    def test_mixed_stock_is_not_called_full_and_native_status_is_not_sustained_rate(self):
        rows=block();rows[0]['status_name']='waiting_for_space_in_destination'
        g=build_graph(mirrored(rows),list(range(1,7)),1.)
        mixed=next(i for i in g['issues'] if i['code']=='mixed_buffer_contents')
        self.assertEqual(mixed['evidence']['capacity'],'unknown')
        self.assertTrue(any(i['code']=='native_status_observed' for i in g['issues']))
        self.assertNotIn('promised_throughput',g)

    def test_stale_structure_or_untrusted_event_stream_blocks_normal_projection(self):
        for change in ('stale','disconnect','gap'):
            m=mirrored(block())
            if change=='stale':m.state['domains']['entity:2:structure']['at']=-10.
            elif change=='disconnect':m.invalidate('protocol_error',disconnected=True)
            else:m.state['head']=1
            with self.assertRaises(InvalidState):build_graph(m,list(range(1,7)),1.)

    def test_stale_dynamic_fact_is_unknown_and_not_reported_as_current(self):
        m=mirrored(block());m.state['domains']['entity:2:inventory']['at']=-10.
        g=build_graph(m,list(range(1,7)),1.)
        self.assertFalse(any(i['code']=='mixed_buffer_contents' for i in g['issues']))
        self.assertTrue(any(i['code']=='domain_unavailable' for i in g['issues']))
        self.assertEqual(len(g['edges']),6)

    def test_legacy_replay_requires_explicit_mode_and_preserves_scope_and_validity(self):
        m=mirrored(block(),legacy=True)
        with self.assertRaises(InvalidState):build_graph(m,list(range(1,7)),1.)
        g=build_graph(m,list(range(1,7)),1.,historical=True)
        self.assertTrue(g['historical_only']);self.assertTrue(g['offline_only'])
        sample=g['nodes'][0]['samples']['structure']
        self.assertEqual(sample['scope'],'owned_factory_replay');self.assertFalse(sample['valid'])
        with self.assertRaises(InvalidState):build_graph(mirrored(block()),list(range(1,7)),1.,historical=True)

    def test_destroyed_missing_and_stale_historical_entities_have_no_edges(self):
        for reason in ('destroyed','missing','stale'):
            m=mirrored(block(),legacy=True)
            if reason=='destroyed':m.state['tombstones']['4']=60
            elif reason=='missing':m.state['domains']['entity:4:structure']['data']['presence']='missing'
            else:m.state['domains']['entity:4:structure']['at']=-10.
            g=build_graph(m,list(range(1,7)),1.,historical=True)
            self.assertNotIn('entity:4',{n['key'] for n in g['nodes']})
            self.assertNotIn('entity:1',upstream(g,'entity:6'))

    def test_missing_recipe_and_resource_stay_unknown(self):
        rows=block();del rows[3]['recipe'];del rows[0]['mining_target']
        g=build_graph(mirrored(rows),list(range(1,7)),1.)
        self.assertTrue({'recipe_unobserved','mining_target_unobserved'} <= {i['code'] for i in g['issues']})

    def test_selection_bounds_and_cycle_safe_structural_walk(self):
        for ids in ([],list(range(1,66)),[1,1],[0],[True]):
            with self.assertRaises(ValueError):build_graph(mirrored(block()),ids,1.)
        g=build_graph(mirrored(block()),list(range(1,7)),1.)
        g['edges'].append(dict(source='entity:6',target='entity:1'))
        self.assertEqual(len(upstream(g,'entity:6')),6)
        with self.assertRaises(ValueError):upstream(g,'unobserved')
