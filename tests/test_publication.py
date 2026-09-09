"""Exercise publication boundaries using isolated Git repositories."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

GUARD = Path(__file__).resolve().parents[1] / 'scripts/check_publication.py'


class PublicationTests(unittest.TestCase):
    def test_removed_private_file_is_still_rejected_in_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init', '-b', 'test-publication')
            git('config', 'user.name', 'Test fixture')
            git('config', 'user.email', 'fixture@users.noreply.github.com')
            git('config', 'commit.gpgsign', 'false')
            private = root / ('.' + 'env')
            private.write_text('LOCAL_SETTING=synthetic-fixture\n')
            git('add', private.name)
            git('commit', '-m', 'Add synthetic private fixture')
            git('rm', private.name)
            (root / 'README.md').write_text('Clean visible tree\n')
            git('add', 'README.md')
            git('commit', '-m', 'Remove fixture from visible tree')
            staged = subprocess.run([os.sys.executable, str(GUARD)], cwd=root,
                                    capture_output=True, text=True)
            history = subprocess.run([os.sys.executable, str(GUARD), '--history'], cwd=root,
                                     capture_output=True, text=True)
            self.assertEqual(staged.returncode, 0, staged.stdout + staged.stderr)
            self.assertEqual(history.returncode, 1, history.stdout + history.stderr)
            self.assertIn('private-artifact', history.stdout)

    def test_private_values_are_detected_without_echoing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-b', 'test-publication'], cwd=root, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            values = ['/' + 'Users/' + 'synthetic-person/work/',
                      'synthetic-person' + '@' + 'example.invalid',
                      '-----BEGIN ' + 'PRIVATE KEY-----']
            (root / 'notes.md').write_text('\n'.join(values))
            subprocess.run(['git', 'add', 'notes.md'], cwd=root, check=True)
            result = subprocess.run([os.sys.executable, str(GUARD)], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            for category in ['personal-path', 'non-noreply-email', 'private-key']:
                self.assertIn(category, result.stdout)
            for value in values:
                self.assertNotIn(value, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
