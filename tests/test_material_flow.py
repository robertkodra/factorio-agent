from copy import deepcopy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import unittest

from client.material_flow import (acceptance,buffer_room,build_flow,classify_rate,
                                 diagnose,lane,observed_craft_rates,replay_flow,route_capacity)
from client.mirror_log import MirrorLog
from client.production_graph import build_graph
from tests.test_production_graph import block,mirrored
from tests.test_state_mirror import temporary_runtime


def belt(eid,x=0,y=0,**fields):
    return dict(id=eid,name='transport-belt',type='transport-belt',direction=0,
                position=dict(x=x,y=y),box=dict(left_top=dict(x=x-.5,y=y-.5),
                right_bottom=dict(x=x+.5,y=y+.5)),lines=[[],[]],**fields)


def flow(rows):
    return build_flow(build_graph(mirrored(rows),[r['id'] for r in rows],1.))


def links(index,*targets):
    return dict(index=index,complete=True,outputs=[dict(entity=e,lane=l) for e,l in targets])


class MaterialFlowTests(unittest.TestCase):
    def test_rate_interval_boundaries_and_invalid_values(self):
        self.assertEqual(classify_rate(2,2,5)['status'],'feasible')
        self.assertEqual(classify_rate(5,2,5)['status'],'unknown')
        r=classify_rate(6,2,5,limiting=dict(node='fixture'))
        self.assertEqual(r['status'],'infeasible');self.assertEqual(r['requested_per_second'],6)
        self.assertEqual(classify_rate(1,0,None,needed=['missing'])['observations_needed'],['missing'])
        for args in [(1,3,2),(float('nan'),0,2),(-1,0,2),(True,0,2),(1,0,float('inf'))]:
            with self.assertRaises(ValueError):classify_rate(*args)
        with self.assertRaises(ValueError):classify_rate(3,0,2)

    def test_turn_relations_preserve_lanes_without_union(self):
        a=belt(11);b=belt(22,1,0);b['direction']=4;b['belt_shape']='left'
        a['transport_lines']=[links(1,(22,1)),links(2,(22,2))]
        g=flow([b,a]);pairs={(e['source'],e['target']) for e in g['edges']}
        self.assertEqual(pairs,{(lane('entity:11',i),lane('entity:22',i)) for i in (1,2)})

    def test_side_loading_merges_only_into_observed_destination_lane(self):
        a=belt(1);b=belt(2,1,0);b['direction']=4
        a['transport_lines']=[links(1,(2,1)),links(2,(2,1))]
        g=flow([a,b]);self.assertEqual({e['target'] for e in g['edges']},{'entity:2:lane:1'})

    def test_underground_internal_and_endpoint_lines_remain_distinct(self):
        a=belt(1);b=belt(2,0,-5)
        for r in (a,b):r.update(type='underground-belt',name='underground-belt')
        a['transport_lines']=[links(1,(1,3)),links(2,(1,4)),links(3,(2,3)),links(4,(2,4))]
        b['transport_lines']=[links(3,(2,1)),links(4,(2,2))]
        g=flow([a,b]);self.assertEqual(len(g['edges']),6)
        self.assertNotIn(('entity:1:lane:1','entity:2:lane:2'),{(e['source'],e['target']) for e in g['edges']})

    def test_absent_links_unknown_and_out_of_scope_links_not_invented(self):
        g=flow([belt(1),belt(2,0,-1)])
        result=route_capacity(g,['entity:1:lane:1','entity:2:lane:1'],'coal',1)
        self.assertEqual(result['status'],'unknown');self.assertEqual(result['capacity']['lower_per_second'],0)
        a=belt(1,transport_lines=[links(1,(99,1))]);g=flow([a])
        self.assertEqual(g['edges'],[]);self.assertTrue(any(x['code']=='unobserved_endpoint' for x in g['missing']))

    def test_lane_upper_and_explicit_closed_link_report_limiter(self):
        a=belt(1,transport_lines=[links(1,(2,1))]);b=belt(2,0,-1)
        g=flow([a,b]);route=['entity:1:lane:1','entity:2:lane:1']
        r=route_capacity(g,route,'coal',8)
        self.assertEqual(r['status'],'infeasible');self.assertEqual(r['capacity']['upper_per_second'],7.5)
        self.assertEqual(r['limiting']['reason'],'base_unstacked_lane_upper')
        a['transport_lines']=[links(1)];r=route_capacity(flow([a,b]),route,'coal',1)
        self.assertEqual(r['capacity']['upper_per_second'],0);self.assertEqual(r['status'],'infeasible')

    def test_inserter_pickup_lanes_are_distinct_and_drop_on_far_side(self):
        source=belt(1,0,1);target=belt(2,0,-1,belt_shape='straight')
        arm=dict(id=3,name='inserter',type='inserter',position=dict(x=0,y=0),
                 pickup=dict(x=0,y=1),drop=dict(x=0,y=-1))
        g=flow([source,target,arm])
        pickups=[e for e in g['edges'] if e['target']=='entity:3:hand']
        drops=[e for e in g['edges'] if e['source']=='entity:3:hand']
        self.assertEqual({e['source'] for e in pickups},{'entity:1:lane:1','entity:1:lane:2'})
        self.assertEqual([e['target'] for e in drops],['entity:2:lane:2'])
        target['belt_shape']='left';g=flow([source,target,arm])
        self.assertFalse(any(e['source']=='entity:3:hand' for e in g['edges']))
        self.assertTrue(any(i['code']=='drop_lane_unobserved' for i in g['missing']))

    def test_explicit_inserter_curve_and_underground_lane_ports(self):
        arm=dict(id=3,name='inserter',type='inserter',position=dict(x=0,y=0),
            inserter_ports=dict(pickup=[dict(entity=1,lane=2)],drop=dict(entity=2,lane=1)))
        g=flow([belt(1),belt(2,0,-1),arm]);self.assertEqual(
            {(e['source'],e['target']) for e in g['edges']},
            {('entity:1:lane:2','entity:3:hand'),('entity:3:hand','entity:2:lane:1')})

    def test_pickup_preference_and_far_drop_rotate_with_the_belt(self):
        for direction,(dx,dy) in {0:(0,-1),4:(1,0),8:(0,1),12:(-1,0)}.items():
            for sign,near,far in [(1,2,2),(-1,1,1)]:
                x,y=-dy*sign,dx*sign
                source=belt(1,belt_shape='straight');source['direction']=direction
                target=belt(2,2*x,2*y,belt_shape='straight');target['direction']=direction
                arm=dict(id=3,name='inserter',type='inserter',position=dict(x=x,y=y),
                         pickup=dict(x=0,y=0),drop=dict(x=2*x,y=2*y))
                g=flow([source,target,arm])
                pick=next(e for e in g['edges'] if e.get('pickup_priority')==0)
                self.assertEqual(pick['source'],lane('entity:1',near))
                drop=next(e for e in g['edges'] if e['source']=='entity:3:hand')
                self.assertEqual(drop['target'],lane('entity:2',far))

    def test_recipe_and_fuel_are_separate_material_constraints(self):
        rows=block();rows[3]['name']='stone-furnace';g=flow(rows);f=g['entities']['entity:4']
        self.assertTrue(acceptance(f,'coal','fuel',g['base']))
        self.assertFalse(acceptance(f,'coal','input',g['base']))
        self.assertTrue(acceptance(f,'iron-ore','input',g['base']))
        self.assertFalse(acceptance(f,'iron-ore','fuel',g['base']))
        self.assertIsNone(acceptance(f,'iron-ore','input','other-version'))
        del f['facts']['production']['recipe'];self.assertIsNone(acceptance(f,'iron-ore','input',g['base']))

    def test_mixed_buffer_capacity_needs_slots_and_stack_sizes(self):
        rows=block();g=flow(rows);box=g['entities']['entity:2'];self.assertIsNone(buffer_room(box,'copper-cable')['upper'])
        inv=box['facts']['inventory'];inv.update(stack_sizes={'iron-ore':50,'copper-cable':200},
            chest=[dict(name='iron-ore',count=100)],chest_slots=2)
        self.assertEqual(buffer_room(box,'copper-cable')['upper'],0)
        inv['inventory_slots']=[dict(name='iron-ore',count=50,filter=None),dict(count=0,filter='iron-ore')]
        self.assertEqual(buffer_room(box,'copper-cable')['upper'],0)
        inv['inventory_slots'][1]['filter']=None;self.assertEqual(buffer_room(box,'copper-cable')['lower'],200)
        inv['inventory_slots'][0]['count']=999;self.assertIsNone(buffer_room(box,'copper-cable')['upper'])

    def test_mixed_buffer_diagnosis_has_no_site_ids(self):
        rows=block();rows[1].update(chest=[dict(name='iron-plate',count=200)],chest_slots=2,
            stack_sizes={'iron-plate':100,'copper-cable':200})
        rows[3].update(type='assembling-machine',name='assembling-machine-1',recipe='electronic-circuit')
        for offset in (0,1000):
            copied=deepcopy(rows)
            for row in copied:row['id']+=offset
            findings=diagnose(flow(copied));matches=[f for f in findings if f.get('diagnosis')=='buffer_cannot_accept_required_item']
            self.assertEqual(len(matches),1);self.assertEqual(matches[0]['item'],'copper-cable')

    def test_coal_symptom_does_not_invent_upstream_cause_or_empty_burning_fuel(self):
        rows=block();rows[3].update(name='stone-furnace',fuel=[],status_name='no_fuel')
        f=next(f for f in diagnose(flow(rows)) if f['case']=='coal_feed')
        self.assertEqual(f['status'],'unknown')
        rows[3]['burner']={'remaining_burning_fuel':0}
        f=next(f for f in diagnose(flow(rows)) if f['case']=='coal_feed')
        self.assertEqual(f['status'],'supported_symptom');self.assertEqual(f['cause'],'unknown')

    def test_science_mixture_does_not_prove_stall_and_separate_lanes_do_not_merge(self):
        red=dict(name='automation-science-pack',count=4);green=dict(name='logistic-science-pack',count=3)
        a=belt(1);a['lines']=[[red,green],[]]
        f=next(f for f in diagnose(flow([a])) if f['case']=='science_lane')
        self.assertEqual(f['status'],'unknown');self.assertIn('ordered_lane_items',f['observations_needed'])
        a['lines']=[[red],[green]]
        self.assertFalse(any(f.get('observed')=='red_and_green_share_one_lane' for f in diagnose(flow([a]))))

    def test_recipe_upper_is_distinct_from_observed_operating_rate(self):
        rows=block();rows[3].update(name='stone-furnace',crafting_speed=1,productivity_bonus=0)
        g=flow(rows);route=['entity:4:output','entity:5:hand','entity:6:storage']
        r=route_capacity(g,route,'iron-plate',1)
        self.assertEqual(r['capacity']['upper_per_second'],1/3.2);self.assertEqual(r['status'],'infeasible')
        later=deepcopy(g);later['tick']+=600;later['entities']['entity:4']['facts']['production']['products_finished']+=2
        rates=observed_craft_rates(g,later);self.assertEqual(rates[0]['crafts_per_second'],.2)
        self.assertFalse(rates[0]['capacity_guarantee']);self.assertIsNone(rates[0]['item_delivery_rate'])
        self.assertEqual(route_capacity(later,route,'iron-plate',.2)['status'],'unknown')

    def test_corrupt_or_cross_episode_rates_are_rejected(self):
        g=flow(block());after=deepcopy(g);after['tick']+=60;after['identity']['episode']='other'
        with self.assertRaises(ValueError):observed_craft_rates(g,after)
        after['identity']=deepcopy(g['identity']);after['entities']['entity:4']['facts']['production']['products_finished']=0
        with self.assertRaises(ValueError):observed_craft_rates(g,after)

    def test_replay_preserves_evidence_and_reports_unknown_for_missing_history(self):
        with temporary_runtime() as directory:
            source=Path(directory)/'mirror.jsonl';log=MirrorLog(source);log.append(mirrored(block(),legacy=True));log.close()
            original=hashlib.sha256(source.read_bytes()).hexdigest();output=Path(directory)/'flow'
            report=replay_flow(source,output)
            self.assertEqual(report['source_sha256'],original);self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)
            self.assertEqual(report['live_calls'],0)
            diagnoses=report['frames'][0]['diagnoses'];self.assertEqual({d['case'] for d in diagnoses},{'coal_feed','mixed_buffer','science_lane'})
            self.assertTrue(all(d['status']=='unknown' for d in diagnoses))
            cli=subprocess.run([sys.executable,'-m','client.material_flow',str(source),
                                '--output',str(Path(directory)/'cli')],capture_output=True,text=True)
            self.assertEqual(cli.returncode,0)
            self.assertEqual(json.loads(cli.stdout)['live_calls'],0)
            with self.assertRaises(FileExistsError):replay_flow(source,output)
            bad=json.loads(source.read_text());bad['after']='0'*64;source.write_text(json.dumps(bad)+'\n')
            with self.assertRaises(ValueError):replay_flow(source,Path(directory)/'corrupt')
