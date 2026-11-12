"""Exercise an assembled Forge candidate on loopback, including a real client and the same world after restart."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import runpy
import shutil
import socket
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4
import inputs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from acceptance import isolated_server, server_directory
from pollution.compat_server import saved_identity

world_mods = runpy.run_path(str(HERE.parent / "drtech/server.py"))["world_mods"]
PLAYER = "Pack19Probe"
WORLD = "pack19-candidate"
OFFLINE_ID = UUID(bytes=hashlib.md5(("OfflinePlayer:" + PLAYER).encode()).digest(), version=3)
REQUIRED = {"gregtech", "gtqtcore", "gtsteam", "pollution", "drtech"}
INPUT_DIRS = ("mods", "config", "scripts", "groovy", "resources")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage(source, destination):
    if not (source / "mods").is_dir():
        raise ValueError(f"Missing mods at {source}")
    for name in INPUT_DIRS:
        if (source / name).is_dir():
            shutil.copytree(source / name, destination / name)


def jar_hashes(instance):
    mods = instance / "mods"
    return {p.relative_to(mods).as_posix(): digest(p) for p in sorted(mods.rglob("*.jar"))}


def run_phase(java, forge, rig, results, phase, marker, client, steam, boot_only, cache, lock_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (rig / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={port}\nlevel-name={WORLD}\nonline-mode=false\n"
        "white-list=false\nmax-players=1\nenable-rcon=false\nenable-query=false\n"
        "view-distance=4\nspawn-protection=0\nmax-tick-time=-1\n", encoding="ascii")
    console = results / (phase + ".log")
    lines = queue.Queue()
    args = [str(java), "-Xms768m", "-Xmx5g", "-Dfile.encoding=UTF-8", "-jar", str(forge),
            "nogui", "--universe", str(results / "worlds"), "--world", WORLD]
    with console.open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(args, cwd=rig, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

        def pump():
            try:
                for line in proc.stdout:
                    out.write(line)
                    out.flush()
                    lines.put(line)
            finally:
                lines.put(None)

        def command(value):
            proc.stdin.write(value + "\n")
            proc.stdin.flush()

        def wait_for(predicate, seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    line = lines.get(timeout=1)
                except queue.Empty:
                    continue
                if line is None:
                    break
                if "Encountered an unexpected exception" in line or "This crash report has been saved to" in line:
                    raise RuntimeError(f"Forge crashed in {phase}; inspect {console}")
                if predicate(line):
                    return
            raise RuntimeError(f"Forge stopped or timed out in {phase}; inspect {console}")

        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        try:
            wait_for(lambda s: "Done (" in s and "For help" in s, 900)
            if not boot_only:
                if phase == "create":
                    command("gamerule pack19Receipt " + marker)
                else:
                    command("gamerule pack19Receipt")
                    wait_for(lambda s: "pack19Receipt" in s and marker in s, 30)
                subprocess.run([sys.executable, "-B", str(HERE / "client.py"), "--instance", str(client),
                                "--port", str(port), "--phase", phase, "--result", str(results / ("client-" + phase)),
                                "--steam-env", str(steam), "--cache", str(cache), "--lock", str(lock_path)],
                               check=True, timeout=1000)
                wait_for(lambda s: PLAYER + "[/" in s and "logged in with entity id" in s, 30)
            command("save-all flush")
            wait_for(lambda s: "[minecraft/DedicatedServer]: Saved the world" in s, 120)
            command("stop")
            if proc.wait(timeout=150) != 0:
                raise RuntimeError(f"Abnormal Forge shutdown; inspect {console}")
        finally:
            if proc.poll() is None:
                try:
                    command("stop")
                    proc.wait(timeout=25)
                except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                    proc.kill()
                    proc.wait()
            thread.join()
            proc.stdin.close()
            proc.stdout.close()

    world = results / "worlds" / WORLD
    level = world / "level.dat"
    mods = world_mods(level)
    server_log = console.read_text(encoding="utf-8")
    if not REQUIRED.issubset(mods) or "Unloading dimension 0" not in server_log:
        raise RuntimeError(f"Core mods or normal shutdown missing in {phase}")
    row = {"phase": phase, "world": saved_identity(level), "mods": mods, "levelSha256": digest(level),
           "logSha256": digest(console)}
    if not boot_only:
        saves = results / ("saved-" + phase)
        saves.mkdir()
        shutil.copyfile(level, saves / "level.dat")
        shutil.copyfile(world / "data/visualores.dat", saves / "visualores.dat")
        for filename in ("crafttweaker.log", "logs/groovy_server.log"):
            log = saves / filename
            log.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rig / filename, log)
        player = world / "playerdata" / (str(OFFLINE_ID) + ".dat")
        if not player.is_file():
            raise RuntimeError("Player data missing after real client login")
        shutil.copyfile(player, saves / player.name)
        client_result = json.loads((results / ("client-" + phase) / "client-result.json").read_bytes())
        if client_result["username"] != PLAYER or client_result["phase"] != phase or client_result["exitCode"] != 0:
            raise RuntimeError("Client receipt does not match this connection")
        if "Undefined discriminator for message type" in server_log:
            raise RuntimeError(f"Mod packet could not be encoded on {phase}; inspect {console}")
        client_log = (results / ("client-" + phase) / "client-console.log").read_text(encoding="utf-8", errors="replace")
        if any("Found a missing id from the world gregtech:" + prefix in client_log
               for prefix in ("forestry_pf", "extratrees_pf")):
            raise RuntimeError("Client and saved world disagree about the Forestry or Extra Trees wood recipe IDs")
        row.update(player=PLAYER, playerId=str(OFFLINE_ID), playerSha256=digest(player), client=client_result)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True, help="assembled server input, read only")
    parser.add_argument("--client-instance", type=Path, help="assembled client input, read only")
    parser.add_argument("--steam-env", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--server-dir", type=Path)
    parser.add_argument("--client-cache", type=Path, help="share verified launcher libraries across client runs")
    parser.add_argument("--lock", type=Path, help="candidate lock (defaults to dev/pack/candidate.json for a full run)")
    parser.add_argument("--boot-only", action="store_true", help="diagnostic single boot without a client")
    args = parser.parse_args()
    if not args.boot_only and not args.client_instance:
        parser.error("full verification needs --client-instance")
    steam = args.steam_env.resolve(strict=True)
    source = args.instance.resolve(strict=True)
    runtime = steam / ".legacy-dev"
    root = args.state.resolve()
    client_source = args.client_instance.resolve(strict=True) if args.client_instance else source
    for inp in (source, client_source):
        if inp == root or inp in root.parents:
            parser.error("results must be outside the instance")
    rig = server_directory(args.server_dir, runtime, [steam, source, client_source, root])
    sys.path.insert(0, str(steam / "dev/legacy"))
    import smoke_server as smoke
    java = Path(os.environ.get("GTSTEAM_JAVA8") or runtime / "jdks/java8") / "bin" / ("java.exe" if os.name == "nt" else "java")
    forge = smoke.prepare(str(java), runtime / "forge-server", runtime / "server-dependencies")
    results = root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    results.mkdir(parents=True)
    print(f"Evidence directory: {results}", flush=True)
    cache = (args.client_cache or root / "client-cache").resolve()
    record = {"forge": smoke.FORGE, "serverFiles": jar_hashes(source), "phases": [], "fullVerification": False}
    if not args.boot_only:
        record["clientFiles"] = jar_hashes(client_source)
    try:
        lock_path = args.lock.resolve(strict=True) if args.lock else (HERE / "candidate.json" if not args.boot_only else None)
        lock = json.loads(lock_path.read_bytes()) if lock_path else None
        if lock:
            server_inputs = inputs.inspect(source)
            inputs.locked(server_inputs, lock, "server")
            record["beforeLaunch"] = {"lockSha256": digest(lock_path), "serverSource": inputs.summary(server_inputs)}
            if not args.boot_only:
                client_inputs = inputs.inspect(client_source)
                inputs.locked(client_inputs, lock, "client")
                record["beforeLaunch"]["clientSource"] = inputs.summary(client_inputs)
        with isolated_server(rig, results, record, smoke):
            stage(source, rig)
            if lock:
                staged = inputs.inspect(rig)
                inputs.locked(staged, lock, "server")
                record["beforeLaunch"]["serverCreateStaging"] = inputs.summary(staged)
            marker = uuid4().hex
            for phase in (["create"] if args.boot_only else ["create", "reload"]):
                if phase == "reload":
                    before_reload = inputs.inspect(rig)
                    if before_reload != after_create:
                        raise ValueError("Actual server pack inputs changed while the first JVM was stopped")
                    record["beforeLaunch"]["serverReloadStaging"] = inputs.after_launch(before_reload, server_inputs, "server")
                record["phases"].append(run_phase(java, forge, rig, results, phase, marker, client_source,
                                                  steam, args.boot_only, cache, lock_path))
                if phase == "create" and not args.boot_only:
                    after_create = inputs.inspect(rig)
            if not args.boot_only:
                first, second = record["phases"]
                if first["world"] != second["world"] or first["mods"] != second["mods"]:
                    raise RuntimeError("Saved world or registered mod set changed across the two JVMs")
                if jar_hashes(client_source) != record["clientFiles"]:
                    raise RuntimeError("Client inputs changed between runs")
                record["fullVerification"] = True
    except Exception as exc:
        record["failure"] = str(exc)
        raise
    finally:
        (results / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if not record.get("originalsRestored"):
        raise RuntimeError("Original server fixture was not restored")
    print(f"PASS: {results / 'result.json'}", flush=True)


if __name__ == "__main__":
    main()
