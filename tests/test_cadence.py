import unittest
from client.cadence import summarize


def row(job_id,start,end,status='complete'):
    return dict(kind='job_reconciled',data=dict(skill={'key':'approach:site'},
        result=dict(id=job_id,started_tick=start,finished_tick=end,status=status)))


class CadenceTests(unittest.TestCase):
    def test_recovery_gap_and_failed_work_are_not_hidden_by_deduplication(self):
        a=row('a',0,600);b=row('b',2400,2460,'failed')
        result=summarize([a,a,b])
        self.assertEqual(result['jobs'],2)
        self.assertEqual(result['execution']['total_seconds'],11)
        self.assertEqual(result['between_jobs']['maximum_seconds'],30)
        self.assertEqual(result['outcomes']['failed'],1)

    def test_mixed_world_timeline_is_rejected(self):
        with self.assertRaises(ValueError):summarize([row('a',0,100),row('b',50,200)])
        with self.assertRaises(ValueError):summarize([row('a',100,0)])
