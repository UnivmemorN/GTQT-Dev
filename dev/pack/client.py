"""Run the 1.12.2 Forge client against an isolated loopback pack server (Windows, JDK 8, pywin32)."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import msvcrt
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import inputs

FORGE = "forge-1.12.2-14.23.5.2860"
PROBE = Path(__file__).resolve().parent / "client/ClientProbe.java"
USER = "Pack19Probe"
OFFLINE_ID = UUID(bytes=hashlib.md5(("OfflinePlayer:" + USER).encode()).digest(), version=3)


def valid(path, record):
    return (path.is_file() and path.stat().st_size == record["size"]
            and hashlib.sha1(path.read_bytes()).hexdigest() == record["sha1"])


def materialize(target, record, candidates=()):
    if valid(target, record):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        for source in candidates:
            if valid(source, record):
                shutil.copyfile(source, temp)
                break
        else:
            url = record["url"]
            if not url.startswith("https://"):
                raise ValueError(f"Missing HTTPS source for {target.name}")
            for attempt in range(3):
                try:
                    with urlopen(url, timeout=30) as remote, temp.open("wb") as dest:
                        shutil.copyfileobj(remote, dest)
                    if not valid(temp, record):
                        raise ValueError(f"Bad SHA-1 or size for {target.name}")
                    break
                except OSError:
                    if attempt == 2:
                        raise
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def windows_library(lib):
    allowed = not lib.get("rules")
    for rule in lib.get("rules", []):
        if rule.get("os", {}).get("name", "windows") == "windows":
            allowed = rule["action"] == "allow"
    return allowed


def prepare(runtime, cache, resource_dirs):
    vanilla_dir = runtime / "gradle/caches/retro_futura_gradle/mc-vanilla"
    vanilla = json.loads((vanilla_dir / "manifest_1.12.2.json").read_bytes())
    installer = runtime / "forge-server" / (FORGE + "-installer.jar")
    with ZipFile(installer) as zipfile:
        forge = json.loads(zipfile.read("version.json"))
    gradle = runtime / "gradle/caches/modules-2/files-2.1"
    forge_dir = runtime / "forge-server"
    native_archives = []
    classpath = []
    seen = set()
    for lib in forge["libraries"] + vanilla["libraries"]:
        if not windows_library(lib):
            continue
        group, artifact, version = lib["name"].split(":")
        entries = []
        downloads = lib["downloads"]
        if "artifact" in downloads:
            entries.append((False, downloads["artifact"]))
        native = lib.get("natives", {}).get("windows")
        if native:
            entries.append((True, downloads["classifiers"][native]))
        for is_native, record in entries:
            key = (group, artifact, is_native)
            if key in seen:
                continue
            seen.add(key)
            name = Path(record["path"]).name
            sources = [forge_dir / "libraries" / record["path"],
                       gradle / group / artifact / version / record["sha1"] / name]
            if group == "net.minecraftforge" and artifact == "forge":
                sources.insert(0, forge_dir / (FORGE + ".jar"))
            sources.extend(d / "libraries" / record["path"] for d in resource_dirs)
            path = materialize(cache / "libraries" / record["path"], record, sources)
            (native_archives if is_native else classpath).append(path)
    classpath.append(materialize(cache / "vanilla-1.12.2.jar", vanilla["downloads"]["client"],
                                 [vanilla_dir / "1.12.2/client.jar"]))
    index = materialize(cache / "assets/indexes/1.12.json", vanilla["assetIndex"],
                        [d / "assets/indexes/1.12.json" for d in resource_dirs])
    objects = json.loads(index.read_bytes())["objects"].values()

    def asset(entry):
        sha = entry["hash"]
        path = f"{sha[:2]}/{sha}"
        record = {"sha1": sha, "size": entry["size"], "url": "https://resources.download.minecraft.net/" + path}
        materialize(cache / "assets/objects" / path, record, [d / "assets/objects" / path for d in resource_dirs])

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(asset, {entry["hash"]: entry for entry in objects}.values()))
    return classpath, native_archives


def build_probe(classes, mods, jdk, classpath):
    classes.mkdir()
    subprocess.run([jdk / "bin/javac.exe", "-proc:none", "-encoding", "UTF-8", "-cp",
                    os.pathsep.join(map(str, classpath)), "-d", classes, PROBE], check=True)
    with ZipFile(mods / "gtqt-pack-client-acceptance.jar", "x") as zipfile:
        for file in sorted(classes.rglob("*.class")):
            info = ZipInfo(file.relative_to(classes).as_posix())
            zipfile.writestr(info, file.read_bytes(), compress_type=ZIP_DEFLATED)


def hidden_client(command, game, log, timeout):
    # A private, never-switched desktop permits an actual LWJGL2 display without taking input or focus.
    import win32con
    import win32event
    import win32process
    import win32service
    import pywintypes
    name = "GTQTPackClient" + uuid4().hex
    desktop = win32service.CreateDesktop(name, 0, win32con.GENERIC_ALL, None)
    try:
        with log.open("wb") as output, open(os.devnull, "rb") as stdin:
            out_handle = msvcrt.get_osfhandle(output.fileno())
            in_handle = msvcrt.get_osfhandle(stdin.fileno())
            os.set_handle_inheritable(out_handle, True)
            os.set_handle_inheritable(in_handle, True)
            startup = win32process.STARTUPINFO()
            startup.lpDesktop = name
            startup.dwFlags = win32con.STARTF_USESTDHANDLES
            startup.hStdInput, startup.hStdOutput, startup.hStdError = in_handle, out_handle, out_handle
            process, thread, _, _ = win32process.CreateProcess(str(command[0]), subprocess.list2cmdline(command),
                    None, None, True, win32con.CREATE_NO_WINDOW, None, str(game), startup)
            thread.Close()
            try:
                deadline = time.monotonic() + timeout
                while win32event.WaitForSingleObject(process, 1000) == win32event.WAIT_TIMEOUT:
                    # LoliASM and other crash handlers can leave a live GUI instead of exiting.
                    report = next((game / "crash-reports").glob("crash-*-client.txt"), None)
                    if report:
                        raise RuntimeError(f"Client crashed; see {report}")
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Forge client did not join and exit in {timeout}s; see {log}")
                return win32process.GetExitCodeProcess(process)
            finally:
                if win32event.WaitForSingleObject(process, 0) == win32event.WAIT_TIMEOUT:
                    try:
                        win32process.TerminateProcess(process, 1)
                    except pywintypes.error as error:
                        if error.winerror != 5 or win32event.WaitForSingleObject(process, 1000) != win32event.WAIT_OBJECT_0:
                            raise
                    win32event.WaitForSingleObject(process, 10000)
                process.Close()
    finally:
        desktop.CloseDesktop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("instance", "result", "steam-env"):
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("create", "reload"))
    parser.add_argument("--port", required=True, type=int, choices=range(1, 65536), metavar="PORT")
    parser.add_argument("--timeout", default=480, type=int)
    parser.add_argument("--cache", type=Path, help="shared verified libraries and asset objects")
    parser.add_argument("--lock", type=Path, help="verify the actual player-mod and override staging before JVM startup")
    parser.add_argument("--resource-dir", type=Path, action="append", default=[], help="optional read-only .minecraft resource cache")
    args = parser.parse_args()
    result, instance = args.result.resolve(), args.instance.resolve(strict=True)
    if result == instance or result.is_relative_to(instance):
        parser.error("The client result must be separate from the staged client instance")
    game = result / "client-game"
    if game.exists() or not (instance / "mods").is_dir():
        parser.error("Supply a staged instance with mods/ and an unused per-phase result directory")
    result.mkdir(parents=True, exist_ok=True)
    runtime = args.steam_env.resolve(strict=True) / ".legacy-dev"
    jdk = Path(os.environ.get("GTSTEAM_JAVA8") or runtime / "jdks/java8")
    cache = (args.cache or result.parent / "client-cache").resolve()
    classpath, natives = prepare(runtime, cache, args.resource_dir)
    game.mkdir()
    for name in ("mods", "config", "scripts", "groovy", "resources"):
        source = instance / name
        if source.is_dir():
            shutil.copytree(source, game / name)
    staged = None
    if args.lock:
        staged = inputs.inspect(game)
        inputs.locked(staged, json.loads(args.lock.read_bytes()), "client")
    build_probe(result / "client-probe-classes", game / "mods", jdk, classpath)
    native_dir = result / "client-natives"
    native_dir.mkdir()
    for path in natives:
        with ZipFile(path) as zipfile:
            for entry in zipfile.infolist():
                if entry.filename.lower().endswith(".dll"):
                    (native_dir / Path(entry.filename).name).write_bytes(zipfile.read(entry))
    command = [str(jdk / "bin/java.exe"), "-Xms512m", "-Xmx6g", "-Dfile.encoding=UTF-8",
               "-Dlog4j2.formatMsgNoLookups=true", "-Djava.library.path=" + str(native_dir),
               "-Dorg.lwjgl.librarypath=" + str(native_dir), "-Dnet.java.games.input.librarypath=" + str(native_dir),
               "-Dgtqt.probe.phase=" + args.phase, "-Dgtqt.probe.port=" + str(args.port),
               "-cp", os.pathsep.join(map(str, classpath)), "net.minecraft.launchwrapper.Launch",
               "--username", USER, "--version", FORGE, "--gameDir", str(game), "--assetsDir", str(cache / "assets"),
               "--assetIndex", "1.12", "--accessToken", "offline", "--uuid", OFFLINE_ID.hex,
               "--userType", "legacy", "--userProperties", "{}", "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker",
               "--server", "127.0.0.1", "--port", str(args.port), "--width", "480", "--height", "270"]
    log = result / "client-console.log"
    print(f"Forge client console: {log}", flush=True)
    code = hidden_client(command, game, log, args.timeout)
    report = next((game / "crash-reports").glob("crash-*-client.txt"), None)
    if report:
        raise RuntimeError(f"Client produced a crash report: {report}")
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    prefix = f"GTQT_PACK_CLIENT_OK phase={args.phase} user={USER} "
    markers = [line[line.index(prefix):] for line in lines if prefix in line]
    graceful = sum("GTQT_PACK_CLIENT_EXIT_OK unloadedWorld=true menuTicks=5" in line for line in lines)
    if code or len(markers) != 1 or graceful != 1:
        raise RuntimeError(f"Client exit {code}, successful joins {len(markers)}; see {log}")
    print(markers[0])
    record = {"phase": args.phase, "username": USER, "exitCode": code, "join": markers[0], "cleanMenuExit": True}
    missing = Counter()
    for line in lines:
        match = re.search(r"Registry ([^:\r\n]+): Found a missing id from the world (\S+)", line)
        if match:
            missing[" ".join(match.groups())] += 1
    record["missingWorldIds"] = dict(sorted(missing.items()))
    if staged is not None:
        record["beforeProbeAndJvm"] = inputs.summary(staged)
    for line in lines:
        if "GTQT_BOP_WOOD_OK " in line:
            record["biomesOPlentyWood"] = line[line.index("GTQT_BOP_WOOD_OK "):]
    (result / "client-result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
