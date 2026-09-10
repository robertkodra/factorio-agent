import hashlib
import json
from pathlib import Path
import unittest

from client.agent import ROOT
from client.replay_mirror import replay
from tests.test_state_mirror import IDENTITY, entities, event, player, temporary_runtime


class ReplayMirrorTests(unittest.TestCase):
    def test_same_retained_observations_reconstruct_without_changing_source(self):
        with temporary_runtime() as d:
            d=Path(d);source=d/'original.jsonl'
            factory=entities();factory.update(researched=['automation'],research=None,progress=0)
            changed=entities(62);changed['entities'][0]['health']=180
            changed.update(researched=['automation'],research=None,progress=0)
            rows=[dict(kind='observation',data=player(),wall_epoch=1.),
                  dict(kind='factory',data=factory,wall_epoch=1.),
                  dict(kind='game_event',data=event(),wall_epoch=1.01),
                  dict(kind='factory',data=changed,wall_epoch=1.02),
                  dict(kind='job_reconciled',data=dict(result=dict(id='retained-failure',status='failed',
                       started_tick=60,finished_tick=62,error='insufficient_items')),wall_epoch=1.03)]
            source.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            before=source.read_bytes();report=replay(source,d/'replayed',IDENTITY,[10])
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(report['source_sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(report['reconstruction_mismatches'],0)
            self.assertEqual(report['retained_projection_checks'],10)
            self.assertEqual(report['observation_rcon']['live_calls'],0)
            self.assertIsNone(report['observation_rcon']['latency_seconds'])
            self.assertIsNone(report['first_defensive_input_latency_seconds'])
            self.assertEqual(report['native_damage_to_preemption_ticks']['samples'],0)
            self.assertEqual(report['mirror_bytes'],(d/'replayed/mirror.jsonl').stat().st_size)
            with self.assertRaises(FileExistsError):replay(source,d/'replayed',IDENTITY,[10])

    def test_failed_replay_leaves_original_and_failure_evidence(self):
        with temporary_runtime() as d:
            d=Path(d);source=d/'bad.jsonl';source.write_text('invalid json\n')
            with self.assertRaises(json.JSONDecodeError):replay(source,d/'failed',IDENTITY,[10])
            self.assertEqual(source.read_text(),'invalid json\n')
            self.assertTrue((d/'failed/failure.json').is_file())
