import copy
import json
from pathlib import Path
import tempfile
import unittest

from client.agent import ROOT
from client.autopilot import Journal, Planner, Runner


def observation():
    return dict(tick=100, actor_unit=1, health=250, max_health=250, paused=False, speed=1,
                version='0.5.1', mods={'base':'2.0.77'}, position={'x':0,'y':0}, inventory=[],
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
                if s['id']=='red-a' else []),output=[{'name':'automation-science-pack','count':1}]) for s in sites]}
        p.refresh(o,f,{'enabled_recipes':['automation-science-pack']})
        choice=p.ensure('automation-science-pack',20)
        self.assertEqual(choice['key'],'approach:red-b')
        self.assertEqual(p.service_intent['action']['type'],'put')

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
