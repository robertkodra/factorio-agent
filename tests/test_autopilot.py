import copy
import json
from pathlib import Path
import tempfile
import unittest

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
        action=p.maintenance()['actions'][0]
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
