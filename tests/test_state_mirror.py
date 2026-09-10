from copy import deepcopy
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest

from client.agent import AgentRejected, ROOT
from client.mirror_log import MirrorLog, Reconstructor
from client.mirror_observer import BlockObserver, EmergencyPump, domains_for
from client.state_mirror import ENTITY_FIELDS, InvalidState, StateMirror

IDENTITY = dict(episode='fixture', save_sha256='a'*64, mod_sha256='b'*64,
                controller='0.8.1', base='2.0.77', actor=7, surface=1)
TARGETS = [dict(id=10,x=2,y=3)]


def player(tick=60):
    return dict(tick=tick,actor_unit=7,surface=1,version='0.8.1',mods={'base':'2.0.77'},
                position=dict(x=0,y=0),inventory=[dict(name='iron-plate',count=5)],
                health=250,paused=False,speed=1,guard=dict(enabled=True),job=dict(status='idle'))


def entities(tick=60, eid=10):
    return dict(tick=tick,version='0.8.1',actor_unit=7,surface=1,
                scope='owned_charted_requested_entities',missing=[],entities=[dict(
                    id=eid,name='stone-furnace',type='furnace',position=dict(x=2,y=3),direction=0,
                    health=200,status='working',energy=100,fuel=[dict(name='coal',count=2)],
                    input=[dict(name='iron-ore',count=1)],output=[],products_finished=3,crafting=True)])


def event(seq=1,kind='factory_damaged',eid=10,tick=61):
    return dict(seq=seq,tick=tick,kind=kind,detail=dict(id=eid,health=180,position=dict(x=2,y=3)))


def status(seq=0,tick=60,events=()):
    return dict(tick=tick,sequence=seq,events=list(events))


def ready():
    m=StateMirror(IDENTITY)
    m.player(player(),1.)
    m.entities(entities(),1.,[10])
    m.research(dict(tick=60,researched=['automation'],enabled_recipes=['iron-plate'],progress=0),1.)
    m.reconcile(IDENTITY,0,60,1.,domains_for(TARGETS))
    return m


class FakeGame:
    def __init__(self):
        self.calls=[];self.page=status();self.jobs={};self.fail=False;self.p=player()
    def request(self,op,**kwargs):
        self.calls.append((op,deepcopy(kwargs)))
        if self.fail:raise ConnectionError('offline')
        if op=='hello':return dict(version='0.8.1',observation_contract='smelting-block-v1')
        if op=='observe':return deepcopy(self.p)
        if op=='observe_entities':return entities(self.p['tick'])
        if op=='research_state':return dict(tick=self.p['tick'],researched=[],enabled_recipes=[],progress=0)
        if op=='status' and 'id' in kwargs:
            if kwargs['id'] not in self.jobs:raise AgentRejected('unknown_job_id')
            return deepcopy(self.jobs[kwargs['id']])
        if op=='status':return deepcopy(self.page)
        raise AssertionError('Unexpected mutation: '+op)


class MirrorTests(unittest.TestCase):
    def test_explicit_identity_required_and_changed_world_actor_or_controller_rejected(self):
        with self.assertRaises(ValueError):StateMirror(dict(actor=7))
        for field in IDENTITY:
            m=ready();identity=dict(IDENTITY);identity[field]='changed'
            with self.assertRaises(InvalidState):m.verify_identity(identity)
            self.assertFalse(m.state['connected'])
        m=ready();o=player();o['actor_unit']=8
        with self.assertRaises(InvalidState):m.player(o,1.)

    def test_immediate_snapshot_is_usable_and_scoped(self):
        m=ready();v=m.require(['player','inventory','entity:10:inventory','entity:10:power'],1.)
        self.assertEqual(v['entity:10:inventory']['fuel'][0]['count'],2)
        self.assertEqual(m.state['domains']['entity:10:structure']['scope'],'owned_charted_requested_entities')
        invalid=entities();invalid['scope']='all_world'
        with self.assertRaises(InvalidState):m.entities(invalid,1.,[10])

    def test_pages_never_jump_to_head_and_duplicates_are_idempotent(self):
        m=ready();first=event()
        m.status(status(3,61,[first]),1.01)
        self.assertEqual(m.state['cursor'],1)
        with self.assertRaises(InvalidState):m.require(['player'],1.01)
        safety=m.state['safety_revision']
        m.status(status(3,61,[first,event(2,'unrelated')]),1.01)
        self.assertEqual(m.state['cursor'],2)
        self.assertEqual(m.state['safety_revision'],safety)
        m.status(status(3,61,[event(3,'unrelated')]),1.01)
        self.assertEqual(m.state['cursor'],3)
        m.require(['player'],1.01)

    def test_out_of_order_and_gap_invalidate_without_partial_page_application(self):
        for events in ([event(2),event(1)], [event(1),event(3)]):
            m=ready();m.status(status(3,61,events),1.01)
            self.assertEqual(m.state['cursor'],0)
            self.assertFalse(m.state['event_valid'])
            self.assertEqual(m.state['domains']['entity:10:structure']['data']['health'],200)
        m=ready();m.status(dict(status(10),events_lost=True),1.)
        self.assertFalse(m.state['event_valid'])
        self.assertEqual(m.state['cursor'],0)

    def test_duplicates_inside_one_page_apply_once(self):
        m=ready();first=event();second=event(2,'unrelated')
        fresh=m.status(status(2,61,[first,deepcopy(first),second]),1.01)
        self.assertEqual([e['seq'] for e in fresh],[1,2])
        self.assertTrue(m.state['event_valid'])

    def test_guard_sample_clock_alone_does_not_invalidate_player_plan(self):
        m=ready();o=player();o['guard']=dict(enabled=True,observation=dict(tick=60,entities=[]))
        m.player(o,1.);token=m.plan_token(['player'],1.)
        o['tick']=61;o['guard']['observation']['tick']=61
        m.player(o,1.01);m.status(status(0,61),1.01)
        self.assertTrue(m.validate_plan(token,1.01))

    def test_conflicting_duplicate_or_empty_missing_page_is_not_silently_accepted(self):
        m=ready();m.status(status(1,61,[event()]),1.01)
        conflict=event();conflict['detail']['health']=1
        m.status(status(1,61,[conflict]),1.02)
        self.assertFalse(m.state['event_valid'])
        m=ready();m.status(status(1),1.)
        self.assertFalse(m.state['event_valid'])

    def test_gap_needs_complete_new_observations_and_explicit_reconciliation(self):
        m=ready();m.status(status(2,61,[event(2)]),1.01)
        with self.assertRaises(InvalidState):m.reconcile(IDENTITY,2,61,1.01,domains_for(TARGETS))
        m.player(player(62),1.02);m.entities(entities(62),1.02,[10])
        m.research(dict(tick=62,researched=[],enabled_recipes=[],progress=0),1.02)
        m.reconcile(IDENTITY,2,61,1.01,domains_for(TARGETS))
        m.status(status(2,62),1.02)
        m.require(['entity:10:inventory'],1.02)
        self.assertIsNone(m.state['last_consumed_event_sequence'])
        self.assertEqual(m.state['reconciled_fence'],2)
        self.assertEqual(m.state['reconciliations'][-1]['reason'],'event_sequence_gap')
        m.status(status(3,63,[event(3,'unrelated',tick=63)]),1.03)
        self.assertEqual(m.state['last_consumed_event_sequence'],3)

    def test_reconciliation_cannot_hide_safety_change_during_reads(self):
        m=ready();rev=m.state['safety_revision']
        m.status(status(1,61,[event()]),1.01)
        m.player(player(62),1.02);m.entities(entities(62),1.02,[10])
        m.research(dict(tick=62,researched=[],enabled_recipes=[],progress=0),1.02)
        with self.assertRaises(InvalidState):
            m.reconcile(IDENTITY,1,61,1.01,domains_for(TARGETS),safety_revision=rev)

    def test_destroyed_entity_is_not_resurrected_by_old_snapshot_and_replacement_has_new_id(self):
        m=ready();m.status(status(1,61,[event(kind='factory_destroyed')]),1.01)
        m.entities(entities(),1.02,[10])
        with self.assertRaises(InvalidState):m.require(['entity:10:production'],1.02)
        m.entities(entities(62,11),1.03,[11])
        self.assertEqual(m.require(['entity:11:production'],1.03)['entity:11:production']['products_finished'],3)
        self.assertIn('10',m.state['tombstones'])
        restored=StateMirror.restore(m.checkpoint())
        self.assertEqual(restored.checkpoint(),m.checkpoint())

    def test_missing_entity_is_absence_not_invented_destruction(self):
        m=ready();o=entities(61);o.update(entities=[],missing=[10]);m.entities(o,1.01,[10])
        self.assertEqual(m.require(['entity:10:structure'],1.01)['entity:10:structure']['presence'],'missing')
        self.assertEqual(m.state['tombstones'],{})
        with self.assertRaises(InvalidState):m.require(['entity:10:inventory'],1.01)

    def test_out_of_order_observation_does_not_refresh_data_or_age(self):
        m=ready();o=entities(59);o['entities'][0]['fuel']=[]
        m.entities(o,1.1,[10])
        d=m.state['domains']['entity:10:inventory']
        self.assertEqual(d['tick'],60);self.assertEqual(d['at'],1.)
        self.assertEqual(d['data']['fuel'][0]['count'],2)

    def test_per_domain_wall_and_tick_freshness_expire_independently(self):
        for key,elapsed in [('inventory',1.01),('entity:10:power',.51),('entity:10:production',1.01)]:
            m=ready();m.status(status(0,60),1.+elapsed)
            with self.assertRaisesRegex(InvalidState,'domain'):m.require([key],1.+elapsed)
        m=ready();m.status(status(0,91),1.01)
        with self.assertRaises(InvalidState):m.require(['entity:10:power'],1.01)

    def test_fresh_other_observations_cannot_mask_stale_event_poll(self):
        m=ready();m.player(player(61),2.)
        with self.assertRaisesRegex(InvalidState,'Event observation'):m.require(['player'],2.)

    def test_plan_token_rejects_changed_facts_but_accepts_unchanged_resampling(self):
        m=ready();token=m.plan_token(['inventory','entity:10:power'],1.)
        m.player(player(61),1.01);m.status(status(0,61),1.01)
        self.assertTrue(m.validate_plan(token,1.01))
        changed=entities(61);changed['entities'][0]['energy']=0;m.entities(changed,1.01,[10])
        with self.assertRaises(InvalidState):m.validate_plan(token,1.01)

    def test_damage_invalidates_plan_even_if_health_recovers_before_sample(self):
        m=ready();token=m.plan_token(['entity:10:structure'],1.)
        m.status(status(1,61,[event()]),1.01)
        m.entities(entities(62),1.02,[10])
        with self.assertRaises(InvalidState):m.validate_plan(token,1.02)

    def test_unknown_submission_and_terminal_receipt_conflicts(self):
        m=ready();m.submitted('job-1',60,1.)
        with self.assertRaises(InvalidState):m.require(['inventory'],1.)
        receipt=dict(id='job-1',status='complete',started_tick=60,finished_tick=61)
        m.receipt(receipt,61,1.01);m.require(['inventory'],1.01)
        with self.assertRaises(InvalidState):m.receipt(dict(receipt,status='failed'),61,1.01)

    def test_reconstruct_checkpoint_plus_deltas_and_resume_events(self):
        m=ready();reader=Reconstructor()
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as d:
            log=MirrorLog(Path(d)/'mirror.jsonl',checkpoint_seconds=.02)
            records=[log.append(m)]
            m.status(status(1,61,[event()]),1.01);records.append(log.append(m))
            m.entities(entities(62),1.03,[10]);records.append(log.append(m));log.close()
            for record in records:reader.apply(json.loads(json.dumps(record)))
            self.assertEqual(reader.state,m.checkpoint())
            self.assertEqual([r['kind'] for r in records],['checkpoint','delta','checkpoint'])
            tail=Reconstructor();tail.apply(records[-1]);restored=tail.mirror()
            restored.status(status(2,63,[event(2,kind='factory_destroyed')]),1.04)
            m.status(status(2,63,[event(2,kind='factory_destroyed')]),1.04)
            self.assertEqual(restored.checkpoint(),m.checkpoint())
            broken=deepcopy(records[1]);broken['before']='0'*64
            other=Reconstructor();other.apply(records[0])
            with self.assertRaises(ValueError):other.apply(broken)

    def test_logs_refuse_public_paths_and_overwrite(self):
        with self.assertRaises(ValueError):MirrorLog(ROOT/'should-not-exist.jsonl')
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as d:
            p=Path(d)/'mirror.jsonl';log=MirrorLog(p);log.close()
            with self.assertRaises(FileExistsError):MirrorLog(p)

    def test_legacy_replay_scope_never_becomes_live_charting_proof(self):
        m=ready();o=entities();o['scope']='owned_factory_replay';m.entities(o,1.,[10])
        with self.assertRaises(InvalidState):m.require(['entity:10:structure'],1.)


class ObserverTests(unittest.TestCase):
    def test_bounded_refresh_never_queries_full_factory_or_mutates(self):
        m=StateMirror(IDENTITY);g=FakeGame();o=BlockObserver(m,g,TARGETS,clock=lambda:1.)
        o.refresh(IDENTITY);m.require(['entity:10:inventory'],1.)
        self.assertNotIn('factory',[op for op,_ in g.calls])
        self.assertEqual(next(k for op,k in g.calls if op=='observe_entities')['targets'],TARGETS)

    def test_observer_writes_reconstructable_checkpoint_and_event_delta(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as d:
            m=StateMirror(IDENTITY);g=FakeGame();p=Path(d)/'observer.jsonl';log=MirrorLog(p)
            observer=BlockObserver(m,g,TARGETS,clock=lambda:1.,journal=log)
            observer.refresh(IDENTITY);g.page=status(1,61,[event()]);observer.poll_events();log.close()
            rebuilt=Reconstructor();records=[json.loads(line) for line in p.read_text().splitlines()]
            for record in records:rebuilt.apply(record)
            self.assertEqual(rebuilt.state,m.checkpoint())
            self.assertEqual(records[-1]['events'][0]['kind'],'factory_damaged')

    def test_disconnect_reconnect_and_unknown_job_outcome_use_same_id(self):
        m=ready();g=FakeGame();o=BlockObserver(m,g,TARGETS,clock=lambda:1.)
        m.submitted('uncertain',60,1.);g.fail=True
        with self.assertRaises(ConnectionError):o.reconcile_jobs()
        self.assertFalse(m.state['connected']);g.fail=False
        g.jobs['uncertain']=dict(id='uncertain',status='complete',tick=60,started_tick=59,finished_tick=60)
        o.refresh(IDENTITY)
        self.assertEqual(m.unknown_jobs(),[])
        self.assertTrue(any(op=='status' and kw.get('id')=='uncertain' for op,kw in g.calls))
        self.assertFalse(any(op in ('submit','bind','pause') for op,_ in g.calls))
        m.require(['inventory'],1.)

    def test_missing_receipt_does_not_authorize_retry(self):
        m=ready();g=FakeGame();o=BlockObserver(m,g,TARGETS,clock=lambda:1.)
        m.submitted('uncertain',60,1.);o.reconcile_jobs()
        self.assertEqual(m.unknown_jobs(),['uncertain'])
        with self.assertRaises(InvalidState):m.plan_token(['inventory'],1.)

    def test_current_job_observation_does_not_skip_unknown_id_reconciliation(self):
        m=ready();g=FakeGame();o=BlockObserver(m,g,TARGETS,clock=lambda:1.)
        m.submitted('uncertain',60,1.)
        g.p['job']=dict(id='uncertain',status='complete',started_tick=59,finished_tick=60)
        m.player(g.p,1.)
        self.assertEqual(m.unknown_jobs(),['uncertain'])
        g.jobs['uncertain']=dict(g.p['job'],tick=60);o.reconcile_jobs()
        self.assertEqual(m.unknown_jobs(),[])

    def test_reconnect_to_changed_actor_or_earlier_world_is_rejected(self):
        for actor,tick in [(8,60),(7,59)]:
            m=ready();m.invalidate('lost',disconnected=True)
            g=FakeGame();g.p.update(actor_unit=actor,tick=tick);g.page['tick']=tick
            with self.assertRaises(InvalidState):BlockObserver(m,g,TARGETS,clock=lambda:1.).refresh(IDENTITY)
            self.assertFalse(m.state['connected'])

    def test_emergency_polling_continues_while_model_is_stalled(self):
        m=ready();g=FakeGame();g.page=status(1,61,[event()])
        observer=BlockObserver(m,g,TARGETS,clock=lambda:1.01)
        model_started=threading.Event();release_model=threading.Event()
        def slow_model():
            m.require(['player','inventory'],1.)
            model_started.set();release_model.wait(2)
        model=threading.Thread(target=slow_model);model.start();self.assertTrue(model_started.wait(1))
        pump=EmergencyPump(observer,interval=.005)
        try:
            pump.start();received=pump.events.get(timeout=1)
            self.assertEqual(received['kind'],'factory_damaged')
            self.assertTrue(model.is_alive())
            self.assertGreaterEqual(sum(op=='status' for op,_ in g.calls),1)
            self.assertTrue(pump.errors.empty())
        finally:
            pump.close();release_model.set();model.join(1)
