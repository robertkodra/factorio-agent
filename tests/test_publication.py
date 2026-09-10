"""Exercise publication boundaries using isolated Git repositories."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.check_publication import content_issues

GUARD = Path(__file__).resolve().parents[1] / 'scripts/check_publication.py'


class PublicationTests(unittest.TestCase):
    def test_github_service_and_user_noreply_addresses_pass(self):
        metadata=b'author Fixture <fixture@users.noreply.github.com>\ncommitter GitHub <noreply@github.com>\n'
        self.assertEqual(content_issues(metadata),set())

    def test_service_exception_does_not_allow_other_addresses_or_lookalikes(self):
        addresses=[b'person'+b'@github.com', b'other+noreply'+b'@github.com',
                   b'noreply'+b'@github.com.example.invalid', b'person'+b'@example.invalid']
        for address in addresses:
            self.assertIn('non-noreply-email',content_issues(b'committer Fixture <'+address+b'>'))

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
