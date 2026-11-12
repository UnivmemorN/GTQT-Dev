"""Probe the July Pollution and Core binaries on the existing isolated Forge server."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import zipfile

from build import BASELINE, ENVIRONMENT, LOCK, check_head
from acceptance import isolated_server, server_directory


HERE = Path(__file__).resolve().parent
EXPECTED_MODS = {"pollution", "gtqtcore", "gtsteam", "gregtech", "gregtechfoodoption",
                 "bloodmagic", "botania", "extrabotany", "thaumcraft", "astralsorcery"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "steam-env", "state"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--august-gt", action="store_true", help="use SteamTech's verified August GregTech production JAR")
    parser.add_argument("--server-dir", type=Path, help="isolated server directory with an already accepted eula.txt")
    args = parser.parse_args()
    legacy, source, state = (p.resolve(strict=True) for p in (args.steam_env, args.source, args.state))
    check_head(source, BASELINE)
    check_head(legacy, ENVIRONMENT)
    sys.path.insert(0, str(legacy / "dev/legacy"))
    import smoke_server as smoke
    from smoke_server import DEPENDENCIES, WORLD, boot, digest, fetch, prepare
    from remap_runtime import OUTPUT_HASH
    read_world = runpy.run_path(str(HERE.parent / "drtech/server.py"))["world_mods"]

    runtime = legacy / ".legacy-dev"
    directory = server_directory(args.server_dir, runtime, [legacy, source, state])
    jdk8 = Path(os.environ.get("GTSTEAM_JAVA8") or runtime / "jdks/java8")
    java = str(jdk8 / "bin" / ("java.exe" if os.name == "nt" else "java"))
    base = runtime / "server-dependencies"
    forge = prepare(java, runtime / "forge-server", base)
    files = [base / name for name in DEPENDENCIES]
    libs = source / "libs"
    for artifact_id in LOCK["profiles"]["pollutionJuly"]["artifacts"]:
        if artifact_id == "gtJuly" and args.august_gt:
            # The verified August production JAR is remapped from the locked upstream build input.
            path = runtime / "runtime" / LOCK["artifacts"]["gtAugust"]["filename"]
            if digest(path) != OUTPUT_HASH:
                parser.error(f"Unexpected remapped GregTech binary at {path}")
            files.append(path)
            continue
        artifact = LOCK["artifacts"][artifact_id]
        path = libs / artifact["filename"]
        if artifact_id == "model100":
            path = state / "support" / artifact["filename"]
            fetch(path, artifact["url"], artifact["sha256"])
        if path.stat().st_size != artifact["size"] or digest(path) != artifact["sha256"]:
            parser.error(f"Unexpected binary at {path}")
        files.append(path)
    pollution = source / "build/libs/Pollution-1.9.0.jar"
    with zipfile.ZipFile(pollution) as jar:
        if json.loads(jar.read("mcmod.info"))[0]["modid"] != "pollution":
            parser.error("Build the July Pollution source before running its server probe")
    files.append(pollution)
    for entry in json.loads((HERE / "server-support.json").read_text(encoding="utf-8")):
        path = state / "support" / entry["name"]
        fetch(path, entry["url"], entry["sha256"])
        files.append(path)
    if len({path.name.casefold() for path in files}) != len(files):
        parser.error("Duplicate filenames in the server profile")
    result = state / "server-checks" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    result.mkdir(parents=True, exist_ok=False)
    record = {"readyAndSaved": False, "source": BASELINE, "sha256": {p.name: digest(p) for p in [forge, *files]}}
    print(f"Evidence directory: {result}", flush=True)
    try:
        with isolated_server(directory, result, record, smoke):
            mods = directory / "mods"
            mods.mkdir()
            for path in files:
                shutil.copyfile(path, mods / path.name)
            boot(java, forge, directory, result, timeout=300)
            registered = read_world(result / "worlds" / WORLD / "level.dat")
            missing = EXPECTED_MODS - registered.keys()
            if missing:
                raise RuntimeError(f"Missing from the saved FML ModList: {sorted(missing)}")
            record.update(readyAndSaved=True, modVersions=registered)
    except Exception as error:
        # Forge's crash report retains the Java error even when the closed console pipe raises an OS error.
        reports = sorted((result / "server-files/crash-reports").glob("crash-*-server.txt"))
        if reports:
            lines = reports[-1].read_text(encoding="utf-8", errors="replace").splitlines()
            start = next((i for i, line in enumerate(lines) if line.startswith("Description: ")), None)
            if start is not None:
                trace = [line.strip() for line in lines[start + 1:] if line.strip()]
                record["crashExcerpt"] = trace[:3] + [line for line in trace if line.startswith("Caused by: ")]
                if trace:
                    record["failure"] = trace[0]
                    raise RuntimeError(f"{trace[0]} (see {reports[-1]})") from error
        record["failure"] = str(error)
        raise
    finally:
        (result / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if record.get("originalsRestored") is False:
            raise RuntimeError(f"Original rig verification failed. Inspect {result}")


if __name__ == "__main__":
    main()
