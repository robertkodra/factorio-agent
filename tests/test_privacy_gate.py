"""Exercise actual Git hooks and publication failures in isolated repositories."""
import json
import base64
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.privacy_gate import outgoing

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / 'scripts/privacy_gate.py'
INSTALL = ROOT / 'scripts/install_privacy_hooks.py'
SCANNER = ROOT / '.tools/gitleaks'


class PrivacyGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git('init','-b','fixture')
        self.git('config','user.name','Fixture')
        self.git('config','user.email','fixture@users.noreply.github.com')
        self.git('config','commit.gpgsign','false')
        (self.root/'.gitignore').write_text('runtime/\n.tools/\n')
        (self.root/'README.md').write_text('Public fixture\n')
        self.git('add','.')
        self.git('commit','-m','Public fixture')

    def command(self, *args):
        return subprocess.run(args,cwd=self.root,capture_output=True,text=True)

    def git(self,*args):
        result = self.command('git',*args)
        if result.returncode:
            self.fail('Fixture Git operation failed; output withheld')
        return result.stdout.strip()

    def gate(self,mode):
        return self.command(sys.executable,str(GATE),mode)

    def use_scanner(self):
        scanner = str(SCANNER) if SCANNER.exists() else shutil.which('gitleaks')
        if not scanner:
            self.skipTest('Optional Gitleaks executable unavailable')
        self.git('config','privacy.gitleaksPath',scanner)

    def test_outgoing_references_are_validated(self):
        oid='a'*40; zero='0'*40
        self.assertEqual(outgoing(f'HEAD {oid} refs/heads/fixture {zero}',()),[oid])
        self.assertEqual(outgoing(f'(delete) {zero} refs/heads/fixture {oid}',()),[])
        for data in ['bad-input',f'HEAD --all refs/heads/fixture {zero}']:
            with self.assertRaises(ValueError): outgoing(data,())
        with self.assertRaises(ValueError):
            outgoing(f'HEAD {oid} refs/heads/private-fixture {zero}',(b'private-fixture',))

    def test_missing_scanner_blocks_without_private_output(self):
        self.git('config','privacy.gitleaksPath',str(self.root/'missing-private-path'))
        result=self.gate('ci')
        self.assertEqual(result.returncode,2)
        self.assertNotIn(str(self.root),result.stdout+result.stderr)
        self.assertNotIn('Traceback',result.stdout+result.stderr)

    def test_scanner_failure_output_stays_private(self):
        runtime=self.root/'runtime'; runtime.mkdir()
        scanner=runtime/'fake-scanner'
        marker='private-diagnostic-fixture'
        scanner.write_text('#!/bin/sh\nprintf '+marker+'\nexit 2\n'); scanner.chmod(0o700)
        self.git('config','privacy.gitleaksPath',str(scanner))
        result=self.gate('ci')
        self.assertEqual(result.returncode,1)
        self.assertNotIn(marker,result.stdout+result.stderr)
        logs=list(runtime.glob('privacy-gate-*/*.log'))
        self.assertTrue(logs)
        self.assertTrue(any(marker in p.read_text() for p in logs))
        self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in logs))

    def test_unignored_reports_are_rejected(self):
        (self.root/'.gitignore').write_text('')
        result=self.gate('ci')
        self.assertEqual(result.returncode,2)
        self.assertFalse(list((self.root/'runtime').glob('privacy-gate-*')))

    def test_markers_remain_local_and_block_staged_values(self):
        runtime=self.root/'runtime';runtime.mkdir()
        marker='private-identifier-fixture'
        (runtime/'privacy-private-markers.json').write_text(json.dumps([marker]))
        (self.root/'README.md').write_text(marker)
        self.git('add','README.md')
        result=self.gate('staged')
        self.assertEqual(result.returncode,1)
        self.assertIn('private-local-value',result.stdout)
        self.assertNotIn(marker,result.stdout+result.stderr)

    def test_exact_staged_snapshot_is_scanned(self):
        self.use_scanner()
        secret='gh'+'p_'+'AbcDef0123456789'*3
        (self.root/'README.md').write_text(secret)
        self.git('add','README.md')
        (self.root/'README.md').write_text('Clean unstaged distraction')
        self.assertEqual(self.gate('staged').returncode,1)
        self.git('add','README.md')
        (self.root/'README.md').write_text(secret)
        self.assertEqual(self.gate('staged').returncode,0)

    def test_generic_secret_scanner_blocks_without_echoing(self):
        self.use_scanner()
        secret=base64.b64encode(hashlib.sha256(b'synthetic privacy fixture').digest()).decode()
        (self.root/'README.md').write_text('api_key = "'+secret+'"\n')
        self.git('add','README.md')
        result=self.gate('staged')
        self.assertEqual(result.returncode,1)
        self.assertNotIn(secret,result.stdout+result.stderr)

    def test_public_text_draft_is_scanned(self):
        self.use_scanner()
        runtime=self.root/'runtime';runtime.mkdir()
        draft=runtime/'draft.md';draft.write_text('/'+'Users/'+'fixture')
        result=self.command(sys.executable,str(GATE),'text','--text-file',str(draft))
        self.assertEqual(result.returncode,1)
        draft.write_text('Aggregate findings only.')
        self.assertEqual(self.command(sys.executable,str(GATE),'text','--text-file',str(draft)).returncode,0)

    def test_nested_unreferenced_tag_metadata_is_scanned(self):
        private='/'+'Users/'+'fixture'
        self.git('tag','-a','inner','-m',private)
        self.git('tag','-a','outer','inner','-m','Public outer annotation')
        oid=self.git('rev-parse','outer')
        self.git('tag','-d','inner','outer')
        result=subprocess.run([sys.executable,str(GATE),'push'],cwd=self.root,
            input=f'HEAD {oid} refs/tags/fixture '+('0'*40)+'\n',capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('personal-path',result.stdout)
        self.assertNotIn(private,result.stdout+result.stderr)

    def test_installed_hooks_survive_branch_switch_and_block_removed_history(self):
        self.use_scanner()
        result=self.command(sys.executable,str(INSTALL))
        self.assertEqual(result.returncode,0)
        hooks=Path(self.git('config','core.hooksPath'))
        self.assertTrue((hooks/'pre-commit').is_file())
        self.assertTrue((hooks/'pre-push').is_file())
        self.git('checkout','-b','other-branch')
        # No project scripts exist in this fixture checkout; installed copies run.
        (self.root/'README.md').write_text('Allowed update')
        self.git('add','README.md')
        self.git('commit','-m','Allowed update')
        private='/'+'Users/'+'fixture/private'
        (self.root/'README.md').write_text(private)
        self.git('add','README.md')
        blocked=self.command('git','commit','-m','Must be blocked')
        self.assertNotEqual(blocked.returncode,0)
        self.assertNotIn(private,blocked.stdout+blocked.stderr)
        # Deliberately simulate a locally bypassed commit, then remove the value.
        self.git('-c','core.hooksPath=/dev/null','commit','-m','Synthetic rejected fixture')
        (self.root/'README.md').write_text('Clean again')
        self.git('add','README.md')
        self.git('commit','-m','Clean visible tree')
        remote=self.root/'runtime/remote.git'
        self.git('init','--bare',str(remote))
        blocked=self.command('git','push',str(remote),'HEAD:refs/heads/fixture')
        self.assertNotEqual(blocked.returncode,0)
        self.assertIn('personal-path',blocked.stdout+blocked.stderr)
        self.assertEqual(subprocess.check_output(['git','--git-dir',str(remote),'for-each-ref']),b'')

    def test_installer_preserves_existing_hooks(self):
        self.use_scanner()
        hook=self.root/'.git/hooks/pre-push';hook.write_text('existing hook')
        result=self.command(sys.executable,str(INSTALL))
        self.assertEqual(result.returncode,2)
        self.assertEqual(hook.read_text(),'existing hook')
        self.assertEqual(self.command('git','config','--get','core.hooksPath').returncode,1)

    def test_outgoing_unreferenced_commit_is_scanned(self):
        (self.root/'README.md').write_text('/'+'home/'+'fixture/private')
        self.git('add','README.md')
        tree=self.git('write-tree')
        oid=self.git('commit-tree',tree,'-m','Synthetic unreferenced fixture')
        self.git('reset','--hard','HEAD')
        result=subprocess.run([sys.executable,str(GATE),'push'],cwd=self.root,
            input=f'HEAD {oid} refs/heads/fixture '+('0'*40)+'\n',capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('personal-path',result.stdout)


if __name__ == '__main__':
    unittest.main()
