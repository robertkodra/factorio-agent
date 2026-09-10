"""Review-only trusted launch lifecycle. No automatic installation or attachment.

Only an owned child process, private copied inputs, a fresh RCON credential and
validated controller/actor/surface can yield an episode identity. No game is
started by importing this module. Existing server.py is deliberately unchanged.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import uuid
import zipfile

from .agent import Agent, ROOT
from .state_mirror import digest


class ProvenanceError(RuntimeError):
    pass


def file_hash(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ProvenanceError('regular_file_required')
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def tree_hash(path):
    path=Path(path)
    if path.is_symlink() or not path.is_dir():raise ProvenanceError('regular_directory_required')
    entries={}
    for child in sorted(path.rglob('*')):
        if child.is_symlink():raise ProvenanceError('symlink_in_input_tree')
        if child.is_file():entries[child.relative_to(path).as_posix()]=file_hash(child)
        elif not child.is_dir():raise ProvenanceError('special_file_in_input_tree')
    if not entries:raise ProvenanceError('empty_input_tree')
    return digest(entries)


def copy_file(source,target):
    before=file_hash(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    with Path(source).open('rb') as src, target.open('xb') as dst:shutil.copyfileobj(src,dst)
    target.chmod(0o600)
    if before!=file_hash(source) or before!=file_hash(target):
        raise ProvenanceError('input_changed_during_copy')
    return before


def copy_tree(source,target):
    before=tree_hash(source)
    shutil.copytree(source,target,symlinks=True)
    if before!=tree_hash(source) or before!=tree_hash(target):
        raise ProvenanceError('input_tree_changed_during_copy')
    return before


def write_private(path,value):
    with path.open('x') as stream:
        path.chmod(0o600)
        json.dump(value,stream,indent=2,sort_keys=True)


@dataclass(frozen=True)
class Expectations:
    save_sha256: str
    controller_sha256: str
    controller_version: str
    base_version: str
    actor: int
    surface: int
    player: int=1

    def validate(self):
        for value in (self.save_sha256,self.controller_sha256):
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ProvenanceError('reviewed_input_hash_required')
        if any(type(v) is not int or v<=0 for v in (self.actor,self.surface,self.player)):
            raise ProvenanceError('explicit_actor_surface_player_required')
        if any(not isinstance(v,str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',v)
               for v in (self.controller_version,self.base_version)):
            raise ProvenanceError('explicit_versions_required')


class ProcessBackend:
    """Small POSIX adapter. Real Factorio use still requires platform review."""
    def spawn(self,argv,cwd,environment,log):
        return subprocess.Popen(argv,cwd=cwd,env=environment,stdout=log,
                                stderr=subprocess.STDOUT,start_new_session=True)

    def fingerprint(self,process):
        if process.poll() is not None:raise ProvenanceError('owned_process_exited')
        def read(field):
            return subprocess.check_output(['ps','-ww','-p',str(process.pid),'-o',field+'='],
                                           stderr=subprocess.PIPE,text=True).strip()
        if sys.platform.startswith('linux'):
            proc=Path('/proc')/str(process.pid)
            executable=str((proc/'exe').resolve(strict=True))
            command=' '.join(v.decode() for v in (proc/'cmdline').read_bytes().split(b'\0') if v)
        else:
            executable=read('comm');command=read('command')
        return dict(pid=process.pid,executable=executable,started=read('lstart'),command=command)

    def listeners(self,port,protocol):
        command=['lsof','-nP','-t','-i'+protocol+':'+str(port)]
        if protocol=='TCP':command.append('-sTCP:LISTEN')
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode not in (0,1) or result.stderr.strip():
            raise ProvenanceError('listener_ownership_unavailable')
        return sorted({int(v) for v in result.stdout.split()})


class TrustedLaunch:
    """One-way prepared -> started -> validated lifecycle, never attach/adopt."""
    def __init__(self):
        raise ProvenanceError('use_prepare_with_reviewed_inputs')

    @classmethod
    def attach(cls,*args,**kwargs):
        raise ProvenanceError('unowned_process_attachment_refused')

    @classmethod
    def prepare(cls,*,save,controller,data,executable,output,expected,game_port,rcon_port,backend=None):
        expected.validate()
        if (any(type(p) is not int or not 1024<=p<=65535 for p in (game_port,rcon_port))
                or game_port==rcon_port):raise ProvenanceError('distinct_unprivileged_ports_required')
        output=Path(output).resolve()
        if ROOT/'runtime' not in output.parents:raise ProvenanceError('private_runtime_output_required')
        output.mkdir(parents=True,exist_ok=False,mode=0o700)
        obj=object.__new__(cls)
        obj.directory=output;obj.expected=expected;obj.backend=backend or ProcessBackend()
        obj.process=None;obj.fingerprint=None;obj.episode=None;obj.failed=False;obj.log=None
        obj.game_port=game_port;obj.rcon_port=rcon_port
        try:
            executable=Path(executable)
            if executable.is_symlink():raise ProvenanceError('direct_executable_required')
            obj.executable=executable.resolve();engine_hash=file_hash(obj.executable)
            if not os.access(obj.executable,os.X_OK):raise ProvenanceError('executable_permission_required')
            obj.inputs=output/'inputs';obj.inputs.mkdir(mode=0o700)
            obj.save=obj.inputs/'save.zip';save_hash=copy_file(save,obj.save)
            with zipfile.ZipFile(obj.save) as archive:
                if archive.testzip() is not None:raise ProvenanceError('save_integrity_failed')
            if save_hash!=expected.save_sha256:raise ProvenanceError('save_hash_mismatch')
            info=json.loads((Path(controller)/'info.json').read_text())
            if info.get('name')!='codex-controller' or info.get('version')!=expected.controller_version:
                raise ProvenanceError('controller_metadata_mismatch')
            obj.mods=obj.inputs/'mods';obj.mods.mkdir()
            obj.controller=obj.mods/('codex-controller_'+expected.controller_version)
            controller_hash=copy_tree(controller,obj.controller)
            if controller_hash!=expected.controller_sha256:raise ProvenanceError('controller_hash_mismatch')
            obj.data=obj.inputs/'data';obj.data.mkdir()
            for name in ('base','core'):copy_tree(Path(data)/name,obj.data/name)
            base_info=json.loads((obj.data/'base/info.json').read_text())
            if base_info.get('version')!=expected.base_version:raise ProvenanceError('base_version_mismatch')
            write_private(obj.mods/'mod-list.json',{'mods':[{'name':name,'enabled':enabled} for name,enabled in
                [('base',True),('codex-controller',True),('space-age',False),('quality',False),('elevated-rails',False)]]})
            for name in ('write-data','home','tmp'):(output/name).mkdir(mode=0o700)
            obj.password=output/'rcon-password';obj.password.write_text(secrets.token_urlsafe(32));obj.password.chmod(0o600)
            obj.config=obj.inputs/'config.ini'
            obj.config.write_text('[path]\nread-data='+str(obj.data)+'\nwrite-data='+str(output/'write-data')+'\n\n[general]\nlocale=en\n')
            obj.settings=obj.inputs/'server-settings.json'
            write_private(obj.settings,dict(name='Private reviewed controller run',visibility=dict(public=False,lan=False),
                require_user_verification=False,allow_commands='false',autosave_interval=0,auto_pause=True,
                only_admins_can_pause_the_game=True))
            obj.environment={'HOME':str(output/'home'),'TMPDIR':str(output/'tmp'),'PATH':os.defpath,'LANG':'C'}
            obj.argv=[str(obj.executable),'--config',str(obj.config),'--mod-directory',str(obj.mods),
                '--start-server',str(obj.save),'--server-settings',str(obj.settings),
                '--bind','127.0.0.1:'+str(game_port),'--rcon-bind','127.0.0.1:'+str(rcon_port),
                '--rcon-password',obj.password.read_text()]
            obj.hashes=obj.current_hashes()
            if obj.hashes['engine']!=engine_hash:raise ProvenanceError('engine_changed_during_prepare')
            # This is a launch-attempt record, deliberately not an episode identity.
            write_private(output/'prepared.json',dict(schema=1,state='prepared',hashes=obj.hashes,
                argv_sha256=digest(obj.argv),environment_sha256=digest(obj.environment),
                expected=expected.__dict__,game_port=game_port,rcon_port=rcon_port))
            obj.argv_hash=digest(obj.argv);obj.environment_hash=digest(obj.environment)
            return obj
        except BaseException as exc:
            obj.fail(exc)
            raise

    def current_hashes(self):
        return dict(save=file_hash(self.save),controller=tree_hash(self.controller),
            base=tree_hash(self.data/'base'),core=tree_hash(self.data/'core'),
            mods_tree=tree_hash(self.mods),data_tree=tree_hash(self.data),
            mod_list=file_hash(self.mods/'mod-list.json'),config=file_hash(self.config),
            settings=file_hash(self.settings),engine=file_hash(self.executable),password=file_hash(self.password))

    def verify_inputs(self):
        if self.failed or self.current_hashes()!=self.hashes:
            raise ProvenanceError('launch_input_changed')
        if digest(self.argv)!=self.argv_hash or digest(self.environment)!=self.environment_hash:
            raise ProvenanceError('launch_configuration_changed')

    def verify_process(self):
        if self.process is None:raise ProvenanceError('no_owned_process')
        current=self.backend.fingerprint(self.process)
        if current!=self.fingerprint:raise ProvenanceError('process_identity_changed')
        if current['executable']!=str(self.executable) or current['command']!=' '.join(self.argv):
            raise ProvenanceError('process_launch_binding_mismatch')

    def start(self):
        if self.process is not None or self.episode is not None or self.failed:
            raise ProvenanceError('launch_attempt_not_reusable')
        try:
            self.verify_inputs()
            if self.backend.listeners(self.rcon_port,'TCP') or self.backend.listeners(self.game_port,'UDP'):
                raise ProvenanceError('existing_listener_not_adopted')
            self.log=(self.directory/'process.log').open('x');os.chmod(self.directory/'process.log',0o600)
            self.process=self.backend.spawn(self.argv,self.directory,self.environment,self.log)
            self.fingerprint=self.backend.fingerprint(self.process)
            self.verify_process();self.verify_inputs()
            write_private(self.directory/'started.json',dict(state='started',process=self.fingerprint,
                hashes=self.hashes,argv_sha256=self.argv_hash,environment_sha256=self.environment_hash))
            return self
        except BaseException as exc:
            self.fail(exc);raise

    def validate_observation(self,observation):
        expected=self.expected
        if (observation.get('version')!=expected.controller_version or
                observation.get('mods')!={'base':expected.base_version,'codex-controller':expected.controller_version}):
            raise ProvenanceError('controller_or_mod_set_mismatch')
        if any(type(observation.get(key)) is not int or observation[key]!=value
               for key,value in [('actor_unit',expected.actor),('surface',expected.surface)]):
            raise ProvenanceError('actor_or_surface_mismatch')
        if (observation.get('policy')!='no-console-lua-v1' or observation.get('speed')!=1
                or type(observation.get('speed')) is bool or type(observation.get('paused')) is not bool):
            raise ProvenanceError('normal_mechanics_contract_mismatch')
        if type(observation.get('tick')) is not int or observation['tick']<0:
            raise ProvenanceError('invalid_observation_tick')
        if observation.get('job',{}).get('status') in ('running','unknown'):
            raise ProvenanceError('unreconciled_work_on_launch')

    def mint_episode(self,*,agent_factory=Agent):
        """Call after the owned server is ready and its expected player joined.

        The injectable transport is for offline fixtures. Live integration has
        no transport supplied by another process and never reconnects by PID.
        """
        if self.episode is not None or self.failed:raise ProvenanceError('launch_attempt_not_reusable')
        try:
            self.verify_inputs();self.verify_process()
            for port,protocol in [(self.rcon_port,'TCP'),(self.game_port,'UDP')]:
                if self.backend.listeners(port,protocol)!=[self.process.pid]:
                    raise ProvenanceError('listener_is_not_owned_child')
            with agent_factory(host='127.0.0.1',port=self.rcon_port,password_file=self.password,timeout=5) as agent:
                hello=agent.request('hello')
                if (hello.get('version')!=self.expected.controller_version
                        or hello.get('observation_contract')!='smelting-block-v1'):
                    raise ProvenanceError('controller_handshake_mismatch')
                bound=agent.request('bind',player=self.expected.player)
                self.validate_observation(bound)
                observation=agent.request('observe');self.validate_observation(observation)
                if observation['tick']<bound['tick']:raise ProvenanceError('observation_tick_regressed')
            self.verify_process();self.verify_inputs()
            # No episode UUID is generated until every provenance check above passes.
            identity=dict(episode=str(uuid.uuid4()),save_sha256=self.hashes['save'],
                mod_sha256=digest({k:self.hashes[k] for k in ('mods_tree','data_tree')}),
                controller=self.expected.controller_version,base=self.expected.base_version,
                actor=self.expected.actor,surface=self.expected.surface)
            write_private(self.directory/'episode.json',dict(schema=1,identity=identity,
                launched_process=self.fingerprint,hashes=self.hashes,argv_sha256=self.argv_hash,
                environment_sha256=self.environment_hash,validated_tick=observation['tick'],
                startup_paused=observation['paused'],observation_sha256=digest(observation)))
            self.episode=identity
            return dict(identity)
        except BaseException as exc:
            self.fail(exc);raise

    def fail(self,error):
        self.failed=True
        path=self.directory/'failure.json'
        if not path.exists():write_private(path,dict(state='failed',error_type=type(error).__name__,
            code=str(error) if isinstance(error,ProvenanceError) else 'adapter_or_input_failure'))
        self.close()

    def close(self):
        # Only the Popen object created by this attempt can be signalled.
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if not (self.directory/'shutdown-pending.json').exists():
                    write_private(self.directory/'shutdown-pending.json',dict(state='graceful_shutdown_pending'))
        if self.log is not None:self.log.close();self.log=None
