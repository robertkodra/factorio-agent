"""Exercise publication boundaries using isolated Git repositories."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.check_publication import content_issues, file_issues, load_markers

GUARD = Path(__file__).resolve().parents[1] / 'scripts/check_publication.py'


class PublicationTests(unittest.TestCase):
    def test_encoded_and_root_paths_are_private(self):
        path = '/' + 'Users/' + 'fixture'
        variants = [path, path.replace('/', r'\/'), path.replace('/', '%2F'),
                    path.replace('/', r'\u002f'), path.replace('/', '%252F'),
                    'c:' + path.replace('/', '\\'), '/' + 'home/' + 'fixture']
        for value in variants:
            self.assertIn('personal-path', content_issues(value.encode()))

    def test_nested_environment_and_credential_files_are_private(self):
        for name in ['config/.ENV.production', 'local/credentials.json', '.SSH/config',
                     'copy.sqlite3', 'setup/.netrc', 'config/secrets.yaml']:
            self.assertIn('private-artifact', file_issues(name, '100644', b'fixture'))
        self.assertEqual(file_issues('config/local-planner.json', '100644', b'{}'), set())
        self.assertEqual(content_issues(b'os.environ.get("FACTORIO_RUN_ID")'), set())

    def test_private_markers_detect_non_token_identifiers_and_encoded_forms(self):
        marker = b'unpublished-fixture-identity'
        for data in [marker, b'%75' + marker[1:]]:
            self.assertIn('private-local-value', content_issues(data, (marker,)))
        self.assertIn('private-local-value', file_issues(marker.decode()+'.md', '100644', b'text', (marker,)))

    def test_bad_marker_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'markers.json'
            for value in [{'wrong': 'shape'}, [''], [1], ['x'*4097]]:
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    load_markers(path)

    def test_cli_withholds_sensitive_filenames_and_error_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git','init','-b','fixture'],cwd=root,capture_output=True,check=True)
            name = 'private-person' + '@' + 'example.invalid' + '.md'
            (root/name).write_text('fixture')
            subprocess.run(['git','add',name],cwd=root,capture_output=True,check=True)
            result = subprocess.run([os.sys.executable,str(GUARD)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertNotIn(name,result.stdout+result.stderr)
            result = subprocess.run([os.sys.executable,str(GUARD),'--private-markers',str(root/'missing')],
                                    cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertNotIn(directory,result.stdout+result.stderr)
            self.assertNotIn('Traceback',result.stdout+result.stderr)

    def test_root_license_is_text_checked_without_allowing_other_unreviewed_files(self):
        self.assertEqual(file_issues('LICENSE','100644',b'MIT License\n'),set())
        self.assertIn('unreviewed-file-type',file_issues('unknown','100644',b'text'))
        self.assertIn('unreviewed-file-type',file_issues('other/LICENSE','100644',b'text'))
        self.assertIn('binary-content',file_issues('LICENSE','100644',b'\x00'))
        self.assertIn('non-regular-file',file_issues('LICENSE','120000',b'target'))
        self.assertIn('private-key',file_issues('LICENSE','100644',b'-----BEGIN '+b'PRIVATE KEY-----'))

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
