from dataclasses import replace
import json
from pathlib import Path
import os
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import zipfile

from client.state_mirror import StateMirror
from client.trusted_launcher import Expectations, ProcessBackend, ProvenanceError, TrustedLaunch, file_hash, tree_hash
from tests.test_state_mirror import temporary_runtime


class FakeProcess:
    pid=4321
    def __init__(self):self.code=None;self.signals=[]
    def poll(self):return self.code
    def send_signal(self,value):self.signals.append(value);self.code=0
    def wait(self,timeout):return self.code


class FakeBackend:
    def __init__(self):
        self.process=None;self.foreign=False;self.changed=False;self.spawn_count=0
    def spawn(self,argv,cwd,environment,log):
        self.argv=list(argv);self.environment=dict(environment);self.process=FakeProcess();self.spawn_count+=1
        return self.process
    def fingerprint(self,process):
        if process.poll() is not None:raise ProvenanceError('owned_process_exited')
        return dict(pid=process.pid,executable=self.argv[0],started='other' if self.changed else 'fixture-start',
                    command=' '.join(self.argv))
    def listeners(self,port,protocol):
        return [99] if self.foreign else [self.process.pid] if self.process and self.process.poll() is None else []


class FakeAgent:
    def __init__(self,observations,hello=None,after_observe=None):
        self.observations=observations;self.calls=[];self.connection=None;self.after_observe=after_observe
        self.hello=hello or dict(version='0.8.1',observation_contract='smelting-block-v1')
    def __call__(self,**kwargs):self.connection=kwargs;return self
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def request(self,operation,**kwargs):
        self.calls.append((operation,kwargs))
        if operation=='hello':return self.hello
        if operation=='bind':return dict(self.observations[0])
        if operation=='observe':
            if self.after_observe:self.after_observe()
            return dict(self.observations[1])
        raise AssertionError('Unexpected operation')


def observation(**changes):
    return dict(dict(version='0.8.1',mods={'base':'2.0.77','codex-controller':'0.8.1'},
                actor_unit=17,surface=1,policy='no-console-lua-v1',speed=1,paused=True,tick=60,
                job={'status':'idle'}),**changes)


class TrustedLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary_runtime();self.directory=Path(self.tmp.__enter__())
        self.addCleanup(self.tmp.__exit__,None,None,None)
        self.source=self.directory/'source';self.source.mkdir()
        self.save=self.source/'save.zip'
        with zipfile.ZipFile(self.save,'w') as z:z.writestr('fixture/level.dat',b'fixture-save-bytes')
        self.mod=self.source/'mod';self.mod.mkdir()
        (self.mod/'info.json').write_text(json.dumps(dict(name='codex-controller',version='0.8.1')))
        (self.mod/'control.lua').write_text('-- synthetic controller fixture\n')
        self.data=self.source/'data'
        for name in ('base','core'):
            (self.data/name).mkdir(parents=True)
            (self.data/name/'info.json').write_text(json.dumps(dict(name=name,version='2.0.77')))
        self.engine=self.source/'factorio-fixture';self.engine.write_text('fixture engine bytes');self.engine.chmod(0o700)
        self.expected=Expectations(file_hash(self.save),tree_hash(self.mod),'0.8.1','2.0.77',17,1)
        self.backend=FakeBackend()

    def prepare(self,**changes):
        kwargs=dict(save=self.save,controller=self.mod,data=self.data,executable=self.engine,
                    output=self.directory/'attempt',expected=self.expected,game_port=34198,rcon_port=27016,
                    backend=self.backend)
        kwargs.update(changes)
        launch=TrustedLaunch.prepare(**kwargs);self.addCleanup(launch.close)
        return launch

    def test_preparation_copies_and_hashes_actual_bytes_without_start_or_episode(self):
        launch=self.prepare()
        self.assertEqual(file_hash(launch.save),file_hash(self.save))
        self.assertEqual(tree_hash(launch.controller),tree_hash(self.mod))
        self.assertEqual(self.backend.spawn_count,0);self.assertIsNone(launch.episode)
        self.assertFalse((launch.directory/'episode.json').exists())
        self.assertEqual(launch.directory.stat().st_mode & 0o077,0)
        self.assertEqual(launch.password.stat().st_mode & 0o077,0)
        self.assertNotIn('episode',json.loads((launch.directory/'prepared.json').read_text()))

    def test_source_changes_cannot_change_the_private_launch_copy(self):
        launch=self.prepare();(self.mod/'control.lua').write_text('changed original')
        self.save.write_bytes(b'changed original')
        launch.start()
        self.assertEqual(self.backend.spawn_count,1)
        self.assertEqual(file_hash(launch.save),self.expected.save_sha256)

    def test_input_hash_mismatch_refuses_before_spawn(self):
        for expected in [replace(self.expected,save_sha256='0'*64),replace(self.expected,controller_sha256='0'*64)]:
            with self.assertRaises(ProvenanceError):self.prepare(expected=expected,output=self.directory/expected.save_sha256)
        self.assertEqual(self.backend.spawn_count,0)

    def test_symlink_mod_and_special_version_refused(self):
        (self.mod/'escape.lua').symlink_to(self.engine)
        with self.assertRaises(ProvenanceError):self.prepare()
        with self.assertRaises(ProvenanceError):
            replace(self.expected,controller_version='../unreviewed').validate()

    def test_no_reuse_no_public_output_no_implicit_identity(self):
        self.prepare()
        with self.assertRaises(FileExistsError):self.prepare()
        with self.assertRaises(ProvenanceError):self.prepare(output=self.source.parent.parent.parent/'public-launch')
        for field,value in [('actor',True),('surface',0),('player',0)]:
            with self.assertRaises(ProvenanceError):replace(self.expected,**{field:value}).validate()

    def test_existing_listener_and_attachment_are_refused_without_signalling_it(self):
        launch=self.prepare();self.backend.foreign=True
        with self.assertRaises(ProvenanceError):launch.start()
        with self.assertRaises(ProvenanceError):TrustedLaunch.attach(pid=99)
        self.assertEqual(self.backend.spawn_count,0);self.assertIsNone(launch.process)

    def test_changed_staged_save_mod_config_engine_or_extra_mod_refused(self):
        for i,kind in enumerate(['save','controller','config','settings','engine','extra_mod','core']):
            # Each case needs its own source engine after the deliberate mutation.
            self.engine.write_text('fixture engine bytes')
            launch=self.prepare(output=self.directory/('attempt-'+str(i)))
            target={'save':launch.save,'controller':launch.controller/'control.lua','config':launch.config,
                    'settings':launch.settings,'engine':launch.executable,'extra_mod':launch.mods/'unlisted.lua',
                    'core':launch.data/'core/info.json'}[kind]
            target.write_text('changed bytes')
            with self.assertRaises(ProvenanceError):launch.start()
            self.assertIsNone(launch.process);self.assertFalse((launch.directory/'episode.json').exists())

    def test_process_argv_and_fresh_password_are_bound_before_episode(self):
        launch=self.prepare();launch.start()
        agent=FakeAgent([observation(),observation(tick=61)])
        identity=launch.mint_episode(agent_factory=agent)
        self.assertEqual(identity['save_sha256'],self.expected.save_sha256)
        self.assertEqual(identity['actor'],17);self.assertEqual(identity['surface'],1)
        StateMirror(identity)
        self.assertEqual([call[0] for call in agent.calls],['hello','bind','observe'])
        self.assertEqual(agent.calls[1][1],{'player':1})
        self.assertEqual(agent.connection['password_file'],launch.password)
        manifest=json.loads((launch.directory/'episode.json').read_text())
        self.assertEqual(manifest['hashes'],launch.hashes)
        self.assertEqual(manifest['launched_process'],launch.fingerprint)
        self.assertEqual(manifest['identity'],identity)
        self.assertEqual(set(self.backend.environment),{'HOME','TMPDIR','PATH','LANG'})
        with self.assertRaises(ProvenanceError):launch.mint_episode(agent_factory=agent)

    def test_wrong_controller_actor_surface_mods_or_policy_never_mints(self):
        variants=[dict(version='0.8.0'),dict(actor_unit=18),dict(surface=2),dict(actor_unit=True),
                  dict(mods={'base':'2.0.77','other':'1'}),dict(speed=2),dict(speed=True),
                  dict(paused='false'),dict(policy='other'),dict(job={'status':'running'})]
        for i,variant in enumerate(variants):
            launch=self.prepare(output=self.directory/('mismatch-'+str(i)));launch.start()
            agent=FakeAgent([observation(**variant),observation()])
            with patch('client.trusted_launcher.uuid.uuid4') as uuid_call:
                with self.assertRaises(ProvenanceError):launch.mint_episode(agent_factory=agent)
                uuid_call.assert_not_called()
            self.assertFalse((launch.directory/'episode.json').exists())
            self.assertEqual(launch.process.signals,[signal.SIGINT])

    def test_changed_process_or_foreign_listener_refused(self):
        for i,kind in enumerate(['process','listener','exited']):
            self.backend=FakeBackend();launch=self.prepare(output=self.directory/('ownership-'+str(i)));launch.start()
            if kind=='process':self.backend.changed=True
            elif kind=='listener':self.backend.foreign=True
            else:launch.process.code=0
            agent=FakeAgent([observation(),observation()])
            with self.assertRaises(ProvenanceError):launch.mint_episode(agent_factory=agent)
            self.assertEqual(agent.calls,[]);self.assertFalse((launch.directory/'episode.json').exists())

    def test_post_bind_mutation_and_identity_drift_are_rechecked(self):
        for i,mode in enumerate(['file','actor','tick','process']):
            self.backend=FakeBackend();launch=self.prepare(output=self.directory/('late-'+str(i)));launch.start()
            def mutate():
                if mode=='file':(launch.data/'base/info.json').write_text('changed')
                if mode=='process':self.backend.changed=True
            after=observation(actor_unit=18) if mode=='actor' else observation(tick=59) if mode=='tick' else observation()
            agent=FakeAgent([observation(),after],after_observe=mutate)
            with self.assertRaises(ProvenanceError):launch.mint_episode(agent_factory=agent)
            self.assertFalse((launch.directory/'episode.json').exists())

    def test_controller_handshake_is_validated_before_binding(self):
        launch=self.prepare();launch.start()
        agent=FakeAgent([observation(),observation()],hello={'version':'0.8.0'})
        with self.assertRaises(ProvenanceError):launch.mint_episode(agent_factory=agent)
        self.assertEqual([c[0] for c in agent.calls],['hello'])

    def test_configuration_mutation_rejected_before_spawn(self):
        launch=self.prepare();launch.argv[1]='--changed-configuration'
        with self.assertRaises(ProvenanceError):launch.start()
        self.assertEqual(self.backend.spawn_count,0)

    @unittest.skipUnless(shutil.which('lsof'),'Optional OS listener inspection unavailable')
    def test_real_owned_fixture_process_fingerprint_and_listener_identity(self):
        backend=ProcessBackend();ready=self.directory/'fixture-ready.json'
        code=('import json,socket,sys,time;'
              'a=socket.socket();a.bind(("127.0.0.1",0));a.listen();'
              'b=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);b.bind(("127.0.0.1",0));'
              'open(sys.argv[1],"w").write(json.dumps([a.getsockname()[1],b.getsockname()[1]]));'
              'time.sleep(20)')
        # Apple's system python command is a launcher for a different app image.
        # Exercise a direct image; do not weaken the launcher's wrapper rejection.
        if sys.platform=='darwin':
            executable=subprocess.check_output(['ps','-ww','-p',str(os.getpid()),'-o','comm='],text=True).strip()
        else:
            executable=str(Path(sys.executable).resolve())
        argv=[executable,'-c',code,str(ready)]
        with (self.directory/'fixture-process.log').open('w') as log:
            process=backend.spawn(argv,self.directory,{'HOME':str(self.directory),'PATH':os.defpath},log)
            try:
                for _ in range(100):
                    if ready.exists() and ready.stat().st_size:break
                    if process.poll() is not None:self.fail('Fixture process exited')
                    time.sleep(.02)
                ports=json.loads(ready.read_text())
                identity=backend.fingerprint(process)
                self.assertEqual(identity['pid'],process.pid)
                self.assertEqual(identity['executable'],executable)
                self.assertEqual(identity['command'],' '.join(argv))
                self.assertEqual(backend.listeners(ports[0],'TCP'),[process.pid])
                self.assertEqual(backend.listeners(ports[1],'UDP'),[process.pid])
            finally:
                process.send_signal(signal.SIGINT);process.wait(timeout=5)
            with self.assertRaises(ProvenanceError):backend.fingerprint(process)
