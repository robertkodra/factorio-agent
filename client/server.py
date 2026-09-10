"""Private macOS test server. Explicit setup installs the control-only client mod."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
GAME = Path.home() / "Library/Application Support/Steam/steamapps/common/Factorio/factorio.app/Contents"
USER = Path.home() / "Library/Application Support/factorio"
MOD_VERSION = json.loads((ROOT / "mod/codex-controller/info.json").read_text())["version"]
MOD_DIRECTORY = "codex-controller_" + MOD_VERSION


def controller_mod_list():
    # Bundled expansions can default to enabled when absent from mod-list.json.
    return {"mods": [{"name": name, "enabled": enabled} for name, enabled in (
        ("base", True), ("codex-controller", True),
        ("space-age", False), ("quality", False), ("elevated-rails", False))]}


def setup():
    if not (GAME / "MacOS/factorio").is_file():
        raise SystemExit("Install Factorio through Steam before setup; see HANDOFF.md")
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    RUNTIME.chmod(0o700)
    for name in ("server/saves", "mods", "backups"):
        (RUNTIME / name).mkdir(parents=True, exist_ok=True)
    password = RUNTIME / "rcon-password"
    if not password.exists():
        password.write_text(secrets.token_urlsafe(32))
        password.chmod(0o600)
    config = f"[path]\nread-data={GAME / 'data'}\nwrite-data={RUNTIME / 'server'}\n\n[general]\nlocale=en\n"
    (RUNTIME / "server/config.ini").write_text(config)
    mods = controller_mod_list()
    (RUNTIME / "mods/mod-list.json").write_text(json.dumps(mods, indent=2))
    link = RUNTIME / "mods" / MOD_DIRECTORY
    # Old managed symlinks point at the same source; leaving both after a version
    # bump makes Factorio see duplicate copies of the new version.
    for previous_link in (RUNTIME / "mods").glob("codex-controller_*"):
        if previous_link != link and previous_link.is_symlink() and previous_link.resolve() == ROOT / "mod/codex-controller":
            previous_link.unlink()
    if not link.exists():
        link.symlink_to(ROOT / "mod/codex-controller", target_is_directory=True)
    settings = {"name": "Codex Performance Test", "description": "Local vanilla tick controller benchmark", "max_players": 1, "visibility": {"public": False, "lan": False}, "require_user_verification": False, "allow_commands": "false", "autosave_interval": 0, "auto_pause": True, "auto_pause_when_players_connect": False, "minimum_latency_in_ticks": 0, "max_heartbeats_per_second": 60, "only_admins_can_pause_the_game": True}
    (RUNTIME / "server-settings.json").write_text(json.dumps(settings, indent=2))
    client_mods = USER / "mods"
    client_mods.mkdir(parents=True, exist_ok=True)
    previous = client_mods / "mod-list.json"
    backup = RUNTIME / "backups/client-mod-list.json"
    if not backup.exists() and previous.exists():
        shutil.copy2(previous, backup)
    enabled = json.loads(previous.read_text()) if previous.exists() else {"mods": []}
    found = set()
    for entry in enabled["mods"]:
        entry["enabled"] = entry["name"] in ("base", "codex-controller")
        found.add(entry["name"])
    enabled["mods"].extend(entry for entry in mods["mods"] if entry["name"] not in found)
    previous.write_text(json.dumps(enabled, indent=2))
    link = client_mods / MOD_DIRECTORY
    # The Steam GUI may lack macOS access to Desktop. Keep a real installed copy.
    if link.is_symlink():
        link.unlink()
    shutil.copytree(ROOT / "mod/codex-controller", link, dirs_exist_ok=True)
    print("Installed control mod; enabled base and controller only. Prior client mod list backed up.")


def base_args():
    return [str(GAME / "MacOS/factorio"), "--config", str(RUNTIME / "server/config.ini"), "--mod-directory", str(RUNTIME / "mods")]


def start(save):
    pidfile = RUNTIME / "server.pid"
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text()), 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit("Recorded server is still running; stop it first")
    save_path = RUNTIME / "server/saves" / (save + ".zip")
    if not save_path.is_file():
        raise SystemExit(f"Missing save: {save_path}")
    args = base_args() + ["--start-server", str(save_path), "--server-settings", str(RUNTIME / "server-settings.json"), "--bind", "127.0.0.1:34198", "--rcon-bind", "127.0.0.1:27016", "--rcon-password", (RUNTIME / "rcon-password").read_text().strip()]
    with (RUNTIME / "server-process.log").open("a") as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pidfile.write_text(str(process.pid))
    print(f"Started local server PID {process.pid}; game 127.0.0.1:34198, RCON 127.0.0.1:27016")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("setup", "create", "start", "stop"))
    parser.add_argument("--save", default="performance-fresh")
    args = parser.parse_args()
    if not args.save or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.save):
        parser.error("Save name must be alphanumeric with hyphens or underscores")
    if args.operation == "setup":
        setup()
    elif args.operation == "create":
        target = RUNTIME / "server/saves" / (args.save + ".zip")
        if target.exists():
            raise SystemExit("Refusing to overwrite an existing save")
        with (RUNTIME / "create.log").open("w") as log:
            result = subprocess.run(base_args() + ["--create", str(target), "--map-gen-seed", "20260906"], stdout=log, stderr=subprocess.STDOUT)
        print("Created seed 20260906" if result.returncode == 0 else "Map creation failed; see private runtime/create.log")
        raise SystemExit(result.returncode)
    elif args.operation == "start":
        start(args.save)
    else:
        pidfile = RUNTIME / "server.pid"
        pid = int(pidfile.read_text())
        command = subprocess.check_output(["ps", "-p", str(pid), "-o", "comm="], text=True).strip()
        if not command.endswith("factorio"):
            raise SystemExit("PID no longer identifies Factorio; refusing to signal it")
        os.kill(pid, signal.SIGINT)
        print("Requested graceful server shutdown")
