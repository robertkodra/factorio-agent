import json
from pathlib import Path
import tempfile
import unittest

from client.run_metrics import summarize


def record(name, start, end, status='complete'):
    return dict(kind='job_reconciled', data=dict(skill=dict(key='approach:private-site'),
        result=dict(id=name, started_tick=start, finished_tick=end, status=status)))


class RunMetricsTests(unittest.TestCase):
    def summarize(self, rows):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'events.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in rows))
            return summarize(path)

    def test_duplicate_failed_receipts_and_native_gaps(self):
        first = record('a', 100, 160)
        report = self.summarize([dict(kind='observation', data={}), first, first,
                                 record('b', 190, 250, 'failed')])
        self.assertEqual(report['jobs'], 2)
        self.assertEqual(report['statuses'], dict(complete=1, failed=1))
        self.assertEqual(report['span_game_seconds'], 2.5)
        self.assertEqual(report['gap_game_seconds']['median'], .5)
        self.assertNotIn('private-site', json.dumps(report))

    def test_conflict_and_overlapping_worlds_rejected(self):
        for rows in ([record('a', 10, 20), record('a', 10, 30)],
                     [record('a', 10, 30), record('b', 20, 40)]):
            with self.assertRaises(ValueError):
                self.summarize(rows)

    def test_empty_journal_has_no_invented_zero_latency(self):
        report = self.summarize([])
        self.assertEqual(report['jobs'], 0)
        self.assertIsNone(report['gap_game_seconds']['p95'])
