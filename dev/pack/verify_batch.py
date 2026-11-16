"""Exercise one cumulative GTQT 1.9 modpack batch with two server and two client JVMs."""
import argparse
from datetime import datetime
import gzip
import json
from pathlib import Path
import queue
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
from uuid import uuid4

import client
import inputs
import verify

ROOT = Path(__file__).resolve().parents[2]
WORLD = "gtqt19-batch"
CORE_MODS = {"gregtech", "gtsteam", "gtqtcore", "pollution", "quantumhue"}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_side(instance, accepted, expected, side):
    snapshot = inputs.inspect(instance)
    actual = snapshot["mods"]
    if any(actual.get(name) != sha for name, sha in accepted.items()):
        raise ValueError(f"{side}: baseline JAR missing or changed")
    if expected is not None and actual != expected:
        raise ValueError(f"{side}: staged production mod files differ from the batch lock")
    return snapshot


def pump_log(proc, out, events):
    for line in proc.stdout:
        out.write(line)
        out.flush()
        events.put(line)
    events.put(None)


def wait_line(events, text, timeout):
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            line = events.get(timeout=min(2, max(0.01, deadline - time.monotonic())))
        except queue.Empty:
            continue
        if line is None:
            raise RuntimeError(f"Forge exited waiting for {text!r}. Last line: {last.strip()}")
        last = line
        if "[minecraft/MinecraftServer]: This crash report has been saved to:" in line:
            raise RuntimeError(line.strip())
        if text in line:
            return line.strip()
    raise TimeoutError(f"Forge timed out waiting for {text!r}. Last line: {last.strip()}")


def console(proc, command):
    proc.stdin.write(command + "\n")
    proc.stdin.flush()


def fingerprint(directory):
    return {p.relative_to(directory).as_posix(): inputs.digest(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def crash_reports(result):
    reports = {}
    for directory in [result / "server-files", *(result / ("client-" + p) / "client-game"
                                                 for p in ("create", "reload"))]:
        for file in sorted((directory / "crash-reports").glob("crash-*.txt")):
            lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            reports[file.relative_to(result).as_posix()] = {
                "sha256": inputs.digest(file),
                "description": next((s for s in lines if s.startswith("Description: ")), ""),
                "causes": [s for s in lines if s.startswith("Caused by: ")],
            }
    return reports


def save_script_logs(rig, result, phase):
    found = {}
    for log in sorted([rig / "crafttweaker.log", *(rig / "logs").glob("groovy*.log")]):
        if log.is_file():
            relative = log.relative_to(rig)
            target = result / ("saved-" + phase) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(log, target)
            found[relative.as_posix()] = inputs.digest(target)
    return found


def run_phase(args, forge, java, rig, result, phase, port, marker, snapshots):
    start = time.monotonic()
    log = result / (phase + ".log")
    events = queue.Queue()
    command = [str(java), "-Xms512m", "-Xmx5g", "-Dfile.encoding=UTF-8", "-jar", str(forge), "nogui"]
    with log.open("w", encoding="utf-8") as output:
        proc = subprocess.Popen(command, cwd=rig, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        reader = threading.Thread(target=pump_log, args=(proc, output, events), daemon=True)
        reader.start()
        try:
            wait_line(events, "For help, type", args.timeout)
            if phase == "create":
                console(proc, "scoreboard objectives add batchworld dummy")
                wait_line(events, "batchworld", 30)
                console(proc, f"scoreboard players set WorldMarker batchworld {marker}")
                wait_line(events, str(marker), 30)
            console(proc, f"scoreboard players test WorldMarker batchworld {marker} {marker}")
            wait_line(events, f"Score {marker} is in range", 30)
            client_dir = result / ("client-" + phase)
            # client.py checks the actual staged production files immediately before adding its observer.
            files = snapshots["client"]
            client_lock = result / "client-launch-inputs.json"
            write_json(client_lock, {
                "overrides": {"files": files["overrides"]["files"], "treeSha256": files["overrides"]["sha256"]},
                "files": [{"side": "client", "filename": n, "sha256": v} for n, v in files["mods"].items()],
            })
            subprocess.run([sys.executable, "-B", str(client.__file__), "--join-only", "--phase", phase,
                            "--instance", str(args.instance / "client"), "--port", str(port), "--result",
                            str(client_dir), "--steam-env", str(args.steam_env), "--cache", str(args.client_cache),
                            "--timeout", str(args.timeout), "--lock", str(client_lock)], check=True)
            joined = wait_line(events, client.USER + " joined the game", 60)
            wait_line(events, client.USER + " left the game", 60)
            console(proc, "save-all flush")
            flush_line = wait_line(events, "Saved the world", 180)
            console(proc, "stop")
            if proc.wait(timeout=180):
                raise RuntimeError("Nonzero exit during dedicated server shutdown")
        finally:
            if proc.poll() is None:
                try:
                    console(proc, "stop")
                    proc.wait(timeout=30)
                except (OSError, subprocess.TimeoutExpired):
                    proc.kill()
                    proc.wait()
            reader.join()
            proc.stdout.close()
            try:
                proc.stdin.close()
            except OSError:
                pass
    world = rig / WORLD
    level = world / "level.dat"
    save_directory = result / ("saved-" + phase)
    save_directory.mkdir(exist_ok=True)
    shutil.copyfile(level, save_directory / "level.dat")
    player = world / "playerdata" / (str(client.OFFLINE_ID) + ".dat")
    mod_ids = verify.world_mods(level)
    if not CORE_MODS.issubset(mod_ids) or not set(args.expect_mod).issubset(mod_ids):
        raise RuntimeError("Missing expected mod IDs in saved level.dat")
    scoreboard = gzip.decompress((world / "data/scoreboard.dat").read_bytes())
    if (b"WorldMarker" not in scoreboard or b"\x03\x00\x05Score" + struct.pack(">i", marker) not in scoreboard or
            len(gzip.decompress(player.read_bytes())) <= 1024 or not any((world / "region").glob("*.mca"))):
        raise RuntimeError("Missing saved world marker, player NBT or generated overworld terrain")
    observer = json.loads((client_dir / "client-result.json").read_bytes())
    if not observer["cleanMenuExit"] or observer["phase"] != phase or "chunk=" not in observer["join"]:
        raise RuntimeError("Missing client world/terrain and clean-exit receipt")
    return {"phase": phase, "elapsedSeconds": round(time.monotonic() - start, 1),
            "serverPid": proc.pid, "serverExit": proc.returncode, "world": verify.saved_identity(level),
            "levelSha256": inputs.digest(level), "registeredMods": mod_ids, "marker": marker,
            "playerSha256": inputs.digest(player), "joined": joined, "flushed": flush_line, "client": observer,
            "scriptLogSha256": save_script_logs(rig, result, phase), "logSha256": inputs.digest(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, type=Path, help="root containing server/mods and client/mods")
    parser.add_argument("--label", required=True, help="batch label for the resulting evidence directory")
    parser.add_argument("--runtime-lock", type=Path, help="JSON mapping server and client to filename/SHA-256 pairs")
    parser.add_argument("--steam-env", type=Path, default=Path("D:/GTSteam-1.12.2"))
    parser.add_argument("--client-cache", type=Path, default=ROOT / "work/pack19-client/runtime")
    parser.add_argument("--results", type=Path, default=ROOT / "work/gtqt19-pack-new/runs")
    parser.add_argument("--server-dir", type=Path, help="dedicated test fixture with an accepted eula.txt")
    parser.add_argument("--expect-mod", action="append", default=[], help="additional required saved FML mod ID")
    parser.add_argument("--timeout", type=int, default=720, help="seconds for each Forge startup or client run")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", args.label):
        parser.error("Use a simple batch label")
    args.instance = args.instance.resolve(strict=True)
    runtime = args.steam_env.resolve(strict=True) / ".legacy-dev"
    lock_path = ROOT / "workspace.lock.json"
    lock = json.loads(lock_path.read_bytes())
    base = lock["profiles"][lock["defaultProfile"]]["runtime"]
    expected = json.loads(args.runtime_lock.read_bytes()) if args.runtime_lock else None
    snapshots = {side: verify_side(args.instance / side, base[side], expected[side] if expected else None, side)
                 for side in ("server", "client")}
    result = args.results.resolve() / (args.label + "-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    result.mkdir(parents=True)
    sys.path.insert(0, str(args.steam_env / "dev/legacy"))
    import smoke_server as smoke
    java = runtime / "jdks/java8/bin/java.exe"
    forge = runtime / "forge-server" / (client.FORGE + ".jar")
    rig = verify.server_directory(args.server_dir, runtime, [args.instance, args.results])
    record = {"label": args.label, "forge": client.FORGE, "gameJarSha256": inputs.digest(forge),
              "baselineLockSha256": inputs.digest(lock_path), "batchLockSha256": inputs.digest(args.runtime_lock)
              if args.runtime_lock else None, "inputs": snapshots, "phases": [], "passed": False}
    print("EVIDENCE", result, flush=True)
    try:
        with verify.isolated_server(rig, result, record, smoke):
            verify.stage(args.instance / "server", rig)
            if inputs.inspect(rig) != snapshots["server"]:
                raise RuntimeError("Dedicated server staging differs from its source instance")
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            (rig / "server.properties").write_text(
                f"server-ip=127.0.0.1\nserver-port={port}\nlevel-name={WORLD}\nlevel-seed=6385109\n"
                "online-mode=false\nwhite-list=true\nmax-players=1\nview-distance=3\nmax-tick-time=-1\n"
                "enable-query=false\nenable-rcon=false\n", encoding="ascii")
            write_json(rig / "whitelist.json", [{"name": client.USER, "uuid": str(client.OFFLINE_ID)}])
            marker = uuid4().int % 80000000 + 10000000
            for phase in ("create", "reload"):
                if phase == "reload":
                    if fingerprint(rig / WORLD) != world_after_create or inputs.inspect(rig) != after_create:
                        raise RuntimeError("Staged server or saved world changed between JVMs")
                    record["worldFilesVerifiedBeforeRestart"] = len(world_after_create)
                report = run_phase(args, forge, java, rig, result, phase, port, marker, snapshots)
                record["phases"].append(report)
                write_json(result / "result.json", record)
                if phase == "create":
                    world_after_create = fingerprint(rig / WORLD)
                    after_create = inputs.inspect(rig)
                    write_json(result / "world-before-reload.json", world_after_create)
            before, after = record["phases"]
            if before["world"] != after["world"] or before["registeredMods"] != after["registeredMods"]:
                raise RuntimeError("Saved identity or FML mod set changed between the create and reload phases")
            for side in snapshots:
                if inputs.inspect(args.instance / side) != snapshots[side]:
                    raise RuntimeError(f"Source {side} inputs changed during acceptance")
        if not record["originalsRestored"]:
            raise RuntimeError("Dedicated test fixture was not restored")
        record["passed"] = True
    except Exception as error:
        record["failure"] = str(error)
        record["crashReports"] = crash_reports(result)
        raise
    finally:
        write_json(result / "result.json", record)
    print("PASS", result / "result.json", flush=True)


if __name__ == "__main__":
    main()
