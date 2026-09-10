import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from client.agent import ROOT
from client.autopilot import Journal, Planner, Runner


def observation():
    return dict(tick=100, actor_unit=1, health=250, max_health=250, paused=False, speed=1,
                version='0.6.0', mods={'base':'2.0.77'}, position={'x':0,'y':0}, inventory=[],
                crafting={}, guard={'enabled':True,'active':False}, job={'status':'idle'},
                guns={'slots':[{'ammo':'firearm-magazine','magazines':20,'rounds':10}]})


def site(name='iron'):
    return dict(id=name,entity='stone-furnace',position={'x':3,'y':0},stand={'x':1,'y':0})


class MemoryJournal:
    def __init__(self):
        self.state={'pending':None,'serial':0}; self.events=[]; self.directory=Path('test-run')
    def save(self):pass
    def emit(self,kind,data):self.events.append((kind,copy.deepcopy(data)))


class FakeGame:
    def __init__(self):
        self.o=observation();self.calls=[];self.pending=None;self.drop=False
        self.f={'researched':['steam-power','electronics','automation-science-pack','military',
                              'automation','gun-turret'], 'entities':[], 'launches':[]}
    def request(self,op,**kw):
        self.calls.append((op,kw))
        if op=='status':
            if 'id' in kw:return self.pending
            return {'sequence':0,'events':[]}
        if op=='observe':return self.o
        if op=='scan':return {'entities':[],'truncated':False}
        if op=='factory':return self.f
        if op=='research_state':return {'enabled_recipes':[]}
        if op=='submit':
            self.pending=dict(id=kw['id'],status='running')
            self.o['job']=self.pending
            if self.drop:raise ConnectionError('lost reply')
            return self.pending
        raise AssertionError(op)


class AutopilotTests(unittest.TestCase):
    def test_first_defense_sample_is_immediate_with_near_zero_clock_and_on_resume(self):
        g=FakeGame();j=MemoryJournal();g.f['tick']=100
        station=dict(id='station',entity='gun-turret',position=dict(x=100,y=0),stand=dict(x=98,y=0))
        plan=dict(target='defense',sites=[station],defense_stations=['station'])
        g.pending=dict(id='production-1',status='running');g.o['job']=g.pending
        j.state['pending']=dict(id='production-1',key='approach:work',actions=[])
        with patch('client.autopilot.time.monotonic',return_value=0.0) as clock:
            r=Runner(g,Planner(plan),j)
            self.assertFalse(r.poll())
            self.assertEqual(sum(op=='factory' for op,_ in g.calls),1)
            clock.return_value=.499
            self.assertFalse(r.poll())
            self.assertEqual(sum(op=='factory' for op,_ in g.calls),1)
            clock.return_value=.5
            self.assertFalse(r.poll())
            self.assertEqual(sum(op=='factory' for op,_ in g.calls),2)
            clock.return_value=.501
            r=Runner(g,Planner(plan),j)
            self.assertFalse(r.poll())
            self.assertEqual(sum(op=='factory' for op,_ in g.calls),3)

    def test_blocked_construction_keeps_defense_alive_across_resume(self):
        g=FakeGame();j=MemoryJournal();g.f['tick']=100
        station=dict(id='station',entity='gun-turret',position=dict(x=100,y=0),stand=dict(x=98,y=0))
        build=dict(id='pole',entity='small-electric-pole',position=dict(x=1,y=0),stand=dict(x=0,y=0),build=True)
        g.o['inventory']=[dict(name='small-electric-pole',count=1)]
        turret=dict(id=1,name='gun-turret',type='ammo-turret',position=station['position'],health=400,
                    ammo=[dict(name='firearm-magazine',count=20)])
        g.f['entities']=[turret]
        original=g.request
        def request(op,**kw):
            if op=='placement':
                g.calls.append((op,kw));return dict(can_place=False)
            return original(op,**kw)
        g.request=request
        plan=dict(target='infrastructure',sites=[build,station],defense_stations=['station'])
        r=Runner(g,Planner(plan),j)
        self.assertFalse(r.poll())
        self.assertEqual(j.state['production_suspended']['action']['entity'],'small-electric-pole')
        self.assertIsNone(j.state['pending'])
        self.assertFalse(any(op=='submit' for op,_ in g.calls))
        # Resuming the same plan must not retry the rejected footprint.
        r=Runner(g,Planner(plan),j)
        self.assertFalse(r.poll())
        self.assertEqual(sum(op=='placement' for op,_ in g.calls),1)
        g.o['tick']=200;g.f['tick']=200;turret['health']=390;r.defense_poll_wall=None
        self.assertFalse(r.poll())
        self.assertTrue(j.state['pending']['key'].startswith('factory-defense:'))
        self.assertTrue(g.o['guard']['enabled'])

    def test_completed_target_keeps_factory_watch_alive(self):
        g=FakeGame();j=MemoryJournal();g.f['researched'].append('military-2');g.f['tick']=100
        s=dict(id='station',entity='gun-turret',position=dict(x=3,y=0),stand=dict(x=1,y=0))
        g.f['entities']=[dict(id=1,name='gun-turret',type='ammo-turret',position=s['position'],
            health=400,ammo=[dict(name='firearm-magazine',count=20)])]
        p=Planner(dict(target='military-2',sites=[s],defense_stations=['station'],watch_after_target=True))
        r=Runner(g,p,j);self.assertFalse(r.poll());self.assertTrue(j.state['target_verified'])
        g.o['tick']=130;g.f['tick']=130;g.f['entities'][0]['health']=399;r.defense_poll_wall=None
        self.assertFalse(r.poll());self.assertIsNotNone(r.factory_defense.state['alarm'])
        self.assertEqual(sum(k=='target_verified' for k,_ in j.events),1)
        s.update(ammo_min=10,ammo_target=20)
        g.o.update(tick=800,position=s['stand']);g.f['tick']=800
        g.f['entities'][0]['ammo'][0]['count']=5;r.defense_poll_wall=None
        self.assertFalse(r.poll())
        self.assertEqual(j.state['pending']['key'],'maintain:ammo:station')

    def test_remote_damage_preempts_running_work_and_restores_local_guard(self):
        g=FakeGame();j=MemoryJournal()
        station=dict(id='station',entity='gun-turret',position=dict(x=100,y=0),stand=dict(x=98,y=0))
        p=Planner(dict(target='defense',sites=[station],defense_stations=['station']))
        g.f.update(tick=130,entities=[dict(id=1,name='transport-belt',type='transport-belt',
            position=dict(x=102,y=0),health=80),dict(id=2,name='gun-turret',type='ammo-turret',
            position=station['position'],health=400,ammo=[dict(name='firearm-magazine',count=20)])])
        g.o['tick']=130;g.pending=dict(id='production-1',status='running');g.o['job']=g.pending
        j.state['pending']=dict(id='production-1',key='approach:work',actions=[dict(type='walk',x=200,y=0)])
        j.state['factory_defense']=dict(tick=100,health={'1':100,'2':400},alarm=None)
        original=g.request
        def request(op,**kw):
            if op=='cancel':
                g.calls.append((op,kw));self.assertEqual(kw['id'],'production-1')
                g.pending.update(status='cancelled',started_tick=100,finished_tick=130)
                g.o['guard']['enabled']=False
                return g.pending
            if op=='guard':
                g.calls.append((op,kw));g.o['guard']['enabled']=kw['enabled'];return g.o['guard']
            return original(op,**kw)
        g.request=request;r=Runner(g,p,j)
        self.assertFalse(r.poll());self.assertTrue(g.o['guard']['enabled'])
        self.assertEqual([op for op,_ in g.calls if op in ('cancel','guard','submit')],['cancel','guard'])
        self.assertTrue(j.state['pending']['factory_defense_cancelled'])
        self.assertFalse(r.poll());self.assertEqual(dict(r.failures),{})
        self.assertFalse(r.poll());self.assertTrue(j.state['pending']['key'].startswith('factory-defense:'))

    def test_construction_precedes_optional_buffer_refill(self):
        building=dict(id='pole',entity='small-electric-pole',build=True,
            position={'x':2,'y':0},stand={'x':0,'y':0})
        buffer=dict(id='buffer',entity='wooden-chest',position={'x':3,'y':0},stand={'x':0,'y':0},
            stock_min={'copper-plate':30},stock_target={'copper-plate':100})
        p=Planner(dict(target='infrastructure',sites=[building,buffer]))
        o=observation();o['inventory']=[{'name':'small-electric-pole','count':1},{'name':'copper-plate','count':50}]
        f=dict(researched=[],entities=[dict(name='wooden-chest',position=buffer['position'],chest=[])])
        self.assertEqual(p.choose(o,f,{'enabled_recipes':[]})['actions'][0]['type'],'place')
        o['inventory']=[{'name':'copper-plate','count':50}]
        self.assertEqual(p.choose(o,f,{'enabled_recipes':[]})['actions'][0]['type'],'put')

    def test_nearby_transfer_skips_walk_but_failure_restores_service_stance(self):
        p=Planner(dict(target='military-2',sites=[site()],local_transfer_radius=3))
        o=observation()
        f=dict(entities=[dict(name='stone-furnace',position=site()['position'])])
        p.refresh(o,f,{'enabled_recipes':[]})
        action=dict(type='take',item='iron-plate',count=1,inventory='output')
        self.assertEqual(p.at('iron',action,'collect')['actions'][0]['type'],'take')
        p.stance_attempts['iron']=1
        self.assertEqual(p.at('iron',action,'collect')['actions'][0]['type'],'walk')
        p.stance_attempts.clear();o['position']={'x':-1,'y':0}
        self.assertEqual(p.at('iron',action,'collect')['actions'][0]['type'],'walk')

    def test_lab_colour_shortage_is_served_before_topping_up_abundant_colour(self):
        s=dict(id='lab',entity='lab',position={'x':3,'y':0},stand={'x':1,'y':0})
        p=Planner(dict(target='military-2',sites=[s]))
        o=observation();o['position']=s['stand'];o['inventory']=[
            {'name':'automation-science-pack','count':20},{'name':'logistic-science-pack','count':20}]
        f=dict(researched=[],research='military-2',progress=0,entities=[dict(
            name='lab',type='lab',position=s['position'],input=[{'name':'automation-science-pack','count':9}])])
        choice=p.choose(o,f,{'enabled_recipes':[]})
        self.assertEqual(choice['actions'][0]['item'],'logistic-science-pack')

    def test_construction_walks_while_crafting_but_never_places_missing_item(self):
        s=dict(id='belt',entity='transport-belt',build=True,
               position={'x':10.5,'y':.5},stand={'x':10.5,'y':.5})
        second=dict(s,id='next-belt',position={'x':11.5,'y':.5},stand={'x':11.5,'y':.5})
        p=Planner(dict(target='infrastructure',sites=[s,second]))
        o=observation();o['crafting']=[{'recipe':'transport-belt','count':10}]
        f={'entities':[],'researched':[]};r={'enabled_recipes':['transport-belt']}
        self.assertEqual(p.choose(o,f,r)['actions'][0]['type'],'walk')
        o['position']=s['stand']
        self.assertIsNone(p.choose(o,f,r))
        o['inventory']=[{'name':'transport-belt','count':2}]
        self.assertEqual(p.choose(o,f,r)['actions'][0]['type'],'place')

    def test_infrastructure_target_requires_every_belt_and_correct_direction(self):
        g = FakeGame(); j = MemoryJournal()
        s = dict(id='belt',entity='transport-belt',position={'x':.5,'y':.5},
                 stand={'x':.5,'y':.5},build=True,direction='east')
        p = Planner(dict(target='infrastructure',sites=[s]))
        g.f['entities']=[dict(name='transport-belt',type='transport-belt',
                              position=s['position'],direction=0)]
        self.assertFalse(Runner(g,p,j).poll())
        self.assertFalse(any(k=='target_verified' for k,_ in j.events))
        g.f['entities'][0]['direction']=4
        self.assertTrue(Runner(g,p,j).poll())

    def test_belt_batch_preflights_every_tile_before_any_submission(self):
        g = FakeGame(); j = MemoryJournal()
        from client.belt_routes import belt_route
        sites = belt_route([(.5,.5),(2.5,.5)], 'east')['sites']
        p = Planner(dict(target='infrastructure',sites=sites))
        g.o['position']={'x':.5,'y':.5}
        g.o['inventory']=[{'name':'transport-belt','count':3}]
        original = g.request
        checks=[]
        def request(op,**kw):
            if op=='placement':
                checks.append(kw)
                return {'can_place':kw['x']!=1.5}
            return original(op,**kw)
        g.request=request
        with self.assertRaisesRegex(RuntimeError,'footprint is blocked'):
            Runner(g,p,j).poll()
        self.assertEqual([q['x'] for q in checks],[.5,1.5])
        self.assertFalse(any(op=='submit' for op,_ in g.calls))
        self.assertIsNone(j.state['pending'])

    def test_transfer_is_replanned_after_travel_not_batched_with_stale_count(self):
        p=Planner({'target':'military-2','sites':[site()],
            'sources':[{'site':'iron','item':'iron-plate','inventory':'output'}]})
        o=observation();f={'entities':[dict(name='stone-furnace',position={'x':3,'y':0},
            output=[{'name':'iron-plate','count':20}])], 'researched':[]}
        p.refresh(o,f,{'enabled_recipes':[]})
        choice=p.ensure('iron-plate',20)
        self.assertEqual(choice['actions'],[{'type':'walk','x':1,'y':0,'timeout':3600}])
        o['position']={'x':1,'y':0}; f['entities'][0]['output'][0]['count']=3
        p.refresh(o,f,{'enabled_recipes':[]})
        self.assertEqual(p.ensure('iron-plate',20)['actions'][0]['count'],3)

    def test_reserves_and_health_override_science(self):
        p=Planner({'target':'military-2','sites':[site()], 'sources':[
            {'site':'iron','item':'coal','inventory':'fuel','reserve':5}]})
        o=observation();f={'entities':[dict(name='stone-furnace',position={'x':3,'y':0},
            fuel=[{'name':'coal','count':5}])], 'researched':[]}
        p.refresh(o,f,{'enabled_recipes':[]})
        self.assertIsNone(p.ensure('coal',10))
        o['health']=20
        self.assertIsNone(p.choose(o,f,{'enabled_recipes':[]}))

    def test_arrival_finishes_original_trip_with_fresh_source_amount(self):
        p=Planner({'target':'military-2','sites':[site()], 'sources':[
            {'site':'iron','item':'coal','inventory':'fuel','reserve':5}]})
        o=observation();f={'entities':[dict(name='stone-furnace',position={'x':3,'y':0},
            type='furnace',fuel=[{'name':'coal','count':25}])], 'researched':[]}
        p.refresh(o,f,{'enabled_recipes':[]})
        self.assertEqual(p.ensure('coal',20)['key'],'approach:iron')
        o['position']={'x':1,'y':0};f['entities'][0]['fuel'][0]['count']=8
        action=p.choose(o,f,{'enabled_recipes':[]})['actions'][0]
        self.assertEqual(action['type'],'take');self.assertEqual(action['count'],3)
        self.assertIsNone(p.service_intent)

    def test_buffered_remote_burners_do_not_starve_local_construction(self):
        furnace=dict(site(),position={'x':100,'y':0},stand={'x':103,'y':0},fuel_min=2,fuel_target=30)
        p=Planner({'target':'military-2','sites':[furnace], 'sources':[
            {'site':'iron','item':'iron-plate','inventory':'output'}]})
        o=observation();o['inventory']=[{'name':'coal','count':30}]
        f={'entities':[dict(name='stone-furnace',type='furnace',position={'x':100,'y':0},
            fuel=[],output=[{'name':'iron-plate','count':30}])], 'researched':[]}
        p.refresh(o,f,{'enabled_recipes':[]});self.assertIsNone(p.maintenance())
        f['entities'][0]['output']=[]
        p.refresh(o,f,{'enabled_recipes':[]})
        self.assertEqual(p.maintenance()['key'],'approach:iron')

    def test_parallel_starved_cell_is_fed_before_tiny_output_pickup(self):
        sites=[dict(site('red-a'),entity='assembling-machine-1',recipe='automation-science-pack'),
               dict(site('red-b'),entity='assembling-machine-1',recipe='automation-science-pack',
                    position={'x':10,'y':0},stand={'x':13,'y':0})]
        p=Planner({'target':'military-2','sites':sites});o=observation()
        o['inventory']=[{'name':'copper-plate','count':20},{'name':'iron-gear-wheel','count':20}]
        f={'entities':[dict(name=s['entity'],type='assembling-machine',position=s['position'],
            recipe=s['recipe'],input=([{'name':'copper-plate','count':10},{'name':'iron-gear-wheel','count':10}]
                if s['id']=='red-a' else []),output=[{'name':'automation-science-pack','count':1 if s['id']=='red-a' else 0}]) for s in sites]}
        p.refresh(o,f,{'enabled_recipes':['automation-science-pack']})
        choice=p.ensure('automation-science-pack',20)
        self.assertEqual(choice['key'],'approach:red-b')
        self.assertEqual(p.service_intent['action']['type'],'put')

    def test_buffer_inventory_refill_uses_chest_and_actual_stock(self):
        chest=dict(site('buffer'),entity='wooden-chest',stock_min={'coal':5},stock_target={'coal':30})
        p=Planner({'target':'military-2','sites':[chest]});o=observation()
        o['position']={'x':1,'y':0};o['inventory']=[{'name':'coal','count':12}]
        f={'entities':[dict(name='wooden-chest',type='container',position=chest['position'],chest=[])]}
        p.refresh(o,f,{'enabled_recipes':[]})
        action=p.maintain_buffers()['actions'][0]
        self.assertEqual((action['type'],action['inventory'],action['count']),('put','chest',12))

    def test_existing_output_satisfies_demand_before_expanding_production(self):
        sites=[dict(site('a'),entity='assembling-machine-1',recipe='automation-science-pack'),
               dict(site('b'),entity='assembling-machine-1',recipe='automation-science-pack',
                    position={'x':10,'y':0},stand={'x':13,'y':0})]
        p=Planner({'target':'military-2','sites':sites});o=observation();o['position']={'x':1,'y':0}
        f={'entities':[dict(name=s['entity'],type='assembling-machine',position=s['position'],
             recipe=s['recipe'],input=[],output=[{'name':'automation-science-pack','count':10}] if s['id']=='a' else []) for s in sites]}
        p.refresh(o,f,{'enabled_recipes':['automation-science-pack']})
        self.assertEqual(p.ensure('automation-science-pack',5)['actions'][0]['type'],'take')

    def test_unknown_submission_is_journalled_and_never_replayed(self):
        game=FakeGame();game.drop=True;journal=MemoryJournal()
        runner=Runner(game,Planner({'target':'military-2','sites':[]}),journal)
        with self.assertRaises(ConnectionError):runner.poll()
        self.assertIsNotNone(journal.state['pending'])
        self.assertEqual(sum(op=='submit' for op,_ in game.calls),1)
        game.drop=False
        resumed=Runner(game,runner.planner,journal)
        resumed.poll()
        self.assertEqual(sum(op=='submit' for op,_ in game.calls),1)

    def test_defense_interrupt_discards_batch_and_waits_for_guard(self):
        game=FakeGame();j=MemoryJournal();r=Runner(game,Planner({'target':'military-2','sites':[]}),j)
        r.poll();game.pending['status']='cancelled';game.pending['error']='defense_interrupt'
        game.o['guard']['active']=True;r.poll();r.poll()
        self.assertIsNone(j.state['pending'])
        self.assertEqual(sum(op=='submit' for op,_ in game.calls),1)

    def test_stop_button_pause_and_character_change_are_not_overridden(self):
        for field,value in [('paused',True),('guard',{'enabled':False}),('speed',2)]:
            g=FakeGame();g.o[field]=value
            with self.assertRaises(RuntimeError):Runner(g,Planner({'target':'military-2','sites':[]}),MemoryJournal()).poll()
            self.assertFalse(any(op=='submit' for op,_ in g.calls))
        g=FakeGame();r=Runner(g,Planner({'target':'military-2','sites':[]}),MemoryJournal());r.poll()
        g.o['actor_unit']=2
        with self.assertRaisesRegex(RuntimeError,'Character'):r.poll()

    def test_rocket_requires_new_actual_launch_event(self):
        g=FakeGame();g.f['launches']=[{'tick':99}];r=Runner(g,Planner({'target':'rocket','sites':[]}),MemoryJournal())
        self.assertFalse(r.poll())
        g.pending['status']='complete';g.o['job']=g.pending;g.f['launches'].append({'tick':101});g.o['tick']=102
        self.assertTrue(r.poll())

    def test_fluid_dependency_builds_real_upstream_without_fluid_transfer(self):
        acid=dict(site('acid'), entity='chemical-plant',recipe='sulfuric-acid',build=True)
        sulfur=dict(site('sulfur'),entity='chemical-plant',position={'x':10,'y':0},
                    stand={'x':13,'y':0},recipe='sulfur',build=True)
        p=Planner({'target':'rocket','sites':[acid,sulfur]})
        o=observation();o['inventory']=[{'name':'chemical-plant','count':1}]
        f={'entities':[], 'researched':[]};p.refresh(o,f,{'enabled_recipes':['sulfuric-acid','sulfur']})
        choice=p.supply_fluid('sulfuric-acid',())
        self.assertEqual(choice['key'],'approach:acid')
        self.assertEqual(p.service_intent['action']['type'],'place')
        self.assertFalse(any(a['type']=='put' for a in choice['actions']))

    def test_silo_is_built_before_waiting_for_rocket_parts(self):
        silo=dict(site('silo'),entity='rocket-silo',recipe='rocket-part',build=True)
        p=Planner({'target':'rocket','sites':[silo]});o=observation()
        o['inventory']=[{'name':'rocket-silo','count':1}]
        f={'entities':[], 'researched':list(p.catalog['technologies'])}
        choice=p.choose(o,f,{'enabled_recipes':['rocket-part','rocket-silo']})
        self.assertEqual(choice['key'],'approach:silo')
        self.assertEqual(p.service_intent['action']['type'],'place')

    def test_blocked_placement_is_preflighted_without_spending_an_item(self):
        g=FakeGame();j=MemoryJournal();p=Planner({'target':'military-2','sites':[]})
        p.choose=lambda *args:dict(key='build:test',actions=[dict(type='place',entity='lab',x=1,y=1,direction='north')])
        original=g.request
        def request(op,**kw):
            if op=='placement':return {'can_place':False}
            return original(op,**kw)
        g.request=request
        with self.assertRaisesRegex(RuntimeError,'footprint is blocked'):Runner(g,p,j).poll()
        self.assertFalse(any(op=='submit' for op,_ in g.calls))

    def test_failure_limit_survives_restart(self):
        j=MemoryJournal();j.state['failures']={'build:test':3}
        with self.assertRaisesRegex(RuntimeError,'corrected plan'):
            Runner(FakeGame(),Planner({'target':'rocket','sites':[]}),j)

    def test_durable_resume_requires_identical_plan_and_preserves_intent(self):
        (ROOT/'runtime').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as d:
            directory=Path(d)/'run';plan={'target':'rocket','sites':[]}
            j=Journal(directory,plan);j.state['pending']={'id':'uncertain'};j.save();j.stream.close()
            resumed=Journal(directory,plan,resume=True)
            self.assertEqual(resumed.state['pending'],{'id':'uncertain'});resumed.stream.close()
            with self.assertRaisesRegex(ValueError,'exact recorded plan'):
                Journal(directory,dict(plan,target='military-2'),resume=True)

    def test_missing_inserter_bootstraps_through_normal_machine_inventory(self):
        from client.layouts import assembly_cell
        sites=assembly_cell('iron-gear-wheel')['sites']
        p=Planner({'target':'military-2','sites':sites})
        machine=next(s for s in sites if s.get('recipe'))
        o=observation();o['position']=machine['stand'];o['inventory']=[{'name':'iron-plate','count':100}]
        f={'entities':[dict(name=machine['entity'],position=machine['position'],type='assembling-machine',
             recipe=machine['recipe'],input=[],output=[])]}
        p.refresh(o,f,{'enabled_recipes':['iron-gear-wheel']})
        a=p.supply_cell(machine['id'],10,())['actions'][0]
        self.assertEqual((a['type'],a['inventory']),('put','input'))
        self.assertEqual(p.output_location(machine['id']),machine['id'])

    def test_gather_trip_is_not_discarded_for_neutral_entity_absent_from_factory(self):
        tree=dict(site('tree'),entity='tree-01',gather='wood')
        p=Planner({'target':'military-2','sites':[tree]});o=observation()
        p.refresh(o,{'entities':[]},{'enabled_recipes':[]})
        self.assertEqual(p.ensure('wood',5)['key'],'approach:tree')
        o['position']=tree['stand'];p.refresh(o,{'entities':[]},{'enabled_recipes':[]})
        self.assertEqual(p.finish_service()['actions'][0]['type'],'mine')
        p.consumed_gather.add('tree');self.assertIsNone(p.ensure('wood',5))

    def test_construction_batches_only_unbuilt_unlocked_matching_structures(self):
        sites=[dict(site('pole-'+str(i)),entity='small-electric-pole',build=True,
                    position={'x':3+i*5,'y':0},stand={'x':1+i*5,'y':0}) for i in range(4)]
        sites[3]['requires']=['not-yet-unlocked']
        p=Planner({'target':'military-2','construction_batch_size':10,'sites':sites})
        o=observation();o['inventory']=[{'name':'wood','count':20},{'name':'copper-plate','count':20}]
        f={'entities':[], 'researched':[]}
        choice=p.choose(o,f,{'enabled_recipes':['small-electric-pole']})
        self.assertEqual(choice['key'],'craft:small-electric-pole')
        # Each ordinary craft yields two poles; three missing poles need two crafts.
        self.assertEqual(choice['actions'][0]['count'],2)

    def test_power_is_built_before_inserter_production_can_bootstrap(self):
        arm=dict(site('arm'),entity='inserter',build=True)
        pole=dict(site('pole'),entity='small-electric-pole',build=True)
        p=Planner({'target':'military-2','sites':[arm,pole]})
        o=observation();o['position']=pole['stand'];o['inventory']=[{'name':'small-electric-pole','count':1}]
        choice=p.choose(o,{'entities':[],'researched':[]},{'enabled_recipes':[]})
        self.assertEqual(choice['key'],'build:pole')

    def test_collection_uses_full_neighbor_instead_of_repeated_tiny_nearest_pickups(self):
        sites=[dict(site('near'),position={'x':100,'y':0},stand={'x':103,'y':0}),
               dict(site('full'),position={'x':103,'y':0},stand={'x':106,'y':0})]
        p=Planner({'target':'military-2','sites':sites,'sources':[
            {'site':s['id'],'inventory':'output','item':'iron-plate'} for s in sites]})
        f={'entities':[dict(name=s['entity'],position=s['position'],output=[{'name':'iron-plate','count':n}])
                       for s,n in zip(sites,(8,100))]}
        p.refresh(observation(),f,{'enabled_recipes':[]})
        self.assertEqual(p.ensure('iron-plate',20)['key'],'approach:full')

    def test_starved_recipe_does_not_top_up_every_other_nearly_full_ingredient(self):
        s=dict(site('inserter-cell'),entity='assembling-machine-1',recipe='inserter',batch_size=50)
        p=Planner({'target':'military-2','sites':[s]});o=observation();o['position']=s['stand']
        o['inventory']=[{'name':'iron-plate','count':100},{'name':'iron-gear-wheel','count':100},
                        {'name':'electronic-circuit','count':50}]
        f={'entities':[dict(name=s['entity'],position=s['position'],type='assembling-machine',recipe='inserter',
            input=[{'name':'iron-plate','count':49},{'name':'iron-gear-wheel','count':49}],output=[])]}
        p.refresh(o,f,{'enabled_recipes':['inserter']})
        choice=p.supply_cell(s['id'],10,())
        self.assertEqual(choice['actions'][0]['item'],'electronic-circuit')
        self.assertEqual(choice['actions'][0]['count'],50)

    def test_waits_for_small_growing_machine_output_instead_of_dispatching_a_long_tiny_trip(self):
        s=dict(site('gear'),entity='assembling-machine-1',recipe='iron-gear-wheel',batch_size=50)
        p=Planner({'target':'military-2','sites':[s]})
        e=dict(name=s['entity'],position=s['position'],type='assembling-machine',recipe=s['recipe'],
               input=[{'name':'iron-plate','count':100}],output=[{'name':'iron-gear-wheel','count':1}],crafting=True)
        p.refresh(observation(),{'entities':[e]},{'enabled_recipes':['iron-gear-wheel']})
        self.assertIsNone(p.ensure('iron-gear-wheel',10))
        e['output'][0]['count']=10
        p.refresh(observation(),{'entities':[e]},{'enabled_recipes':['iron-gear-wheel']})
        self.assertEqual(p.ensure('iron-gear-wheel',10)['key'],'approach:gear')

    def test_ready_science_is_delivered_before_funding_another_starved_parallel_cell(self):
        sites=[dict(site('ready'),entity='assembling-machine-1',recipe='logistic-science-pack'),
               dict(site('starved'),entity='assembling-machine-1',recipe='logistic-science-pack',
                    position={'x':10,'y':0},stand={'x':13,'y':0})]
        o=observation();o['inventory']=[{'name':'inserter','count':20},{'name':'transport-belt','count':20}]
        f={'entities':[dict(name=s['entity'],position=s['position'],type='assembling-machine',recipe=s['recipe'],input=[],
                           output=[{'name':'logistic-science-pack','count':4 if s['id']=='ready' else 0}]) for s in sites]}
        p=Planner({'target':'military-2','sites':sites});p.refresh(o,f,{'enabled_recipes':['logistic-science-pack']})
        self.assertEqual(p.ensure('logistic-science-pack',20)['key'],'approach:ready')
        self.assertEqual(p.service_intent['action']['type'],'take')

    def test_one_item_deficit_does_not_send_tiny_remote_pickup(self):
        s=dict(site('gear'),entity='assembling-machine-1',recipe='iron-gear-wheel',batch_size=50)
        p=Planner({'target':'military-2','sites':[s]})
        e=dict(name=s['entity'],position=s['position'],type='assembling-machine',recipe=s['recipe'],
               input=[{'name':'iron-plate','count':100}],output=[{'name':'iron-gear-wheel','count':1}],crafting=True)
        p.refresh(observation(),{'entities':[e]},{'enabled_recipes':['iron-gear-wheel']})
        self.assertIsNone(p.ensure('iron-gear-wheel',1))
        o=observation();o['position']=s['stand']
        p.refresh(o,{'entities':[e]},{'enabled_recipes':['iron-gear-wheel']})
        self.assertEqual(p.ensure('iron-gear-wheel',1)['actions'][0]['type'],'take')

    def test_chest_limit_is_applied_before_optional_production(self):
        s=dict(site('stock'),entity='wooden-chest',chest_slots=2)
        p=Planner(dict(target='defense',sites=[s]))
        o=observation();o['position']=s['stand']
        f=dict(researched=[],entities=[dict(name=s['entity'],position=s['position'],type='container',chest_slots=16)])
        choice=p.choose(o,f,{'enabled_recipes':[]})
        self.assertEqual(choice['actions'][0]['type'],'limit_chest')
        self.assertEqual(choice['actions'][0]['slots'],2)
        f['entities'][0]['chest_slots']=2
        self.assertIsNone(p.choose(o,f,{'enabled_recipes':[]}))

    def test_native_factory_interrupt_reconciles_without_failure_or_guard_reset(self):
        g=FakeGame();j=MemoryJournal();g.o['version']='0.8.0';g.f['tick']=100
        station=dict(id='station',entity='gun-turret',position=dict(x=100,y=0),stand=dict(x=98,y=0))
        g.f['entities']=[dict(id=2,name='gun-turret',type='ammo-turret',position=station['position'],
                             health=400,ammo=[dict(name='firearm-magazine',count=20)])]
        g.pending=dict(id='interrupted',status='cancelled',error='factory_defense_interrupt',started_tick=90,finished_tick=100)
        g.o['job']=g.pending
        j.state['pending']=dict(id='interrupted',key='approach:work',actions=[dict(type='walk',x=200,y=0)])
        original=g.request
        def request(op,**kw):
            if op=='status' and 'id' not in kw:
                return dict(sequence=1,events=[],last_factory_damage=dict(seq=1,tick=100,id=3,
                    entity='transport-belt',position=dict(x=102,y=0),kind='destroyed'))
            return original(op,**kw)
        g.request=request
        r=Runner(g,Planner(dict(target='defense',sites=[station],defense_stations=['station'])),j)
        self.assertFalse(r.poll());self.assertEqual(dict(r.failures),{})
        self.assertFalse(r.poll())
        submits=[kw for op,kw in g.calls if op=='submit']
        self.assertEqual(len(submits),1);self.assertTrue(submits[0]['defense'])
        self.assertFalse(any(op in ('cancel','guard') for op,_ in g.calls))

    def test_damage_summary_cannot_skip_older_paginated_events(self):
        g=FakeGame();j=MemoryJournal();g.o['version']='0.8.0'
        g.pending=dict(id='defense-1',status='running');g.o['job']=g.pending
        j.state.update(event_cursor=0,pending=dict(id='defense-1',key='factory-defense:station'))
        records=[dict(seq=n,tick=100+n,id=n+2,entity='transport-belt',
                      position=dict(x=n,y=0),kind='destroyed') for n in (1,2,3)]
        original=g.request
        def request(op,**kw):
            if op=='status' and 'id' not in kw:
                page=records[kw['after']:kw['after']+1]
                return dict(sequence=3,events=[dict(seq=d['seq'],tick=d['tick'],
                    kind='factory_destroyed',detail=d) for d in page],last_factory_damage=records[-1])
            return original(op,**kw)
        g.request=request
        r=Runner(g,Planner(dict(target='defense',sites=[])),j)
        for expected in (1,2,3):
            self.assertFalse(r.poll())
            self.assertEqual(r.factory_defense.state['event_seq'],expected)
            self.assertEqual(len(r.factory_defense.state['alarm']['damage']),expected)
        self.assertFalse(r.poll())
        self.assertEqual({d['id'] for d in r.factory_defense.state['alarm']['damage']},{3,4,5})

    def test_external_belt_input_services_starved_upstream_cable(self):
        cable=dict(site('cable'),entity='assembling-machine-1',recipe='copper-cable',batch_size=50)
        circuit=dict(site('circuit'),entity='assembling-machine-1',recipe='electronic-circuit',external_inputs=True,
                     position=dict(x=10,y=0),stand=dict(x=9,y=0))
        p=Planner(dict(target='military-2',sites=[cable,circuit]))
        o=observation();o['position']=cable['stand'];o['inventory']=[dict(name='copper-plate',count=100)]
        f=dict(entities=[dict(name=cable['entity'],position=cable['position'],type='assembling-machine',
                             recipe='copper-cable',input=[],output=[]),
                        dict(name=circuit['entity'],position=circuit['position'],type='assembling-machine',
                             recipe='electronic-circuit',input=[dict(name='iron-plate',count=3)],output=[])])
        p.refresh(o,f,dict(enabled_recipes=['copper-cable','electronic-circuit']))
        choice=p.supply_cell('circuit',10,('electronic-circuit',))
        self.assertEqual(choice['key'],'feed:copper-plate:cable')
        self.assertEqual(choice['actions'][0]['count'],50)
        self.assertEqual(choice['actions'][0]['entity'],'assembling-machine-1')

    def test_explicit_handcraft_fallback_breaks_repair_bootstrap_deadlock(self):
        s=dict(site('inserter'),entity='assembling-machine-1',recipe='inserter',external_inputs=True)
        p=Planner(dict(target='military-2',sites=[s],handcraft_fallback=['inserter']))
        o=observation();o['inventory']=[dict(name=item,count=10) for item in ['iron-plate','iron-gear-wheel','electronic-circuit']]
        f=dict(entities=[dict(name=s['entity'],position=s['position'],type='assembling-machine',recipe='inserter',input=[],output=[])])
        p.refresh(o,f,dict(enabled_recipes=['inserter']))
        choice=p.ensure('inserter',1)
        self.assertEqual(choice['actions'],[dict(type='craft',recipe='inserter',count=1)])
        p.plan['handcraft_fallback']=[]
        self.assertIsNone(p.ensure('inserter',1))
