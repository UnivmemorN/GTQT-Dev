"""Start, save and restart the July-Core/current-Pollution profile in two dedicated Forge JVMs."""
import argparse
from datetime import datetime
import gzip
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from acceptance import check_head, isolated_server, server_directory


PROCESSING_RECIPES = {
    "thaumcraft:elementalsword", "thaumcraft:voidrobehelm", "thaumcraft:voidrobechest",
    "thaumcraft:voidrobelegs", "thaumcraft:primalcrusher", "thaumcraft:causalitycollapser",
    "thaumcraft:voidsiphon", "pollution:magic_circuit_board_iv", "pollution:magic_fusion_reactor",
}


def build_probe(destination, javac, source, gt_compile, mods, forge):
    classes = destination / "probe-classes"
    classes.mkdir()
    minecraft = source / "build/rfg/recompiled_minecraft-1.12.2.jar"
    if not minecraft.is_file():
        raise ValueError(f"Run the full Pollution build first; missing {minecraft}")
    # Named Minecraft and GT compile APIs take priority over the production dependencies.
    classpath = [minecraft, gt_compile, *mods, forge.parent / "minecraft_server.1.12.2.jar",
                 *sorted((forge.parent / "libraries").rglob("*.jar"))]
    sources = [HERE / "probe" / name for name in (
        "SunnariumProbe.java", "InfusionCases.java", "ProcessingProbe.java", "ImportGuardProbe.java",
        "LegacyInfusionProbe.java", "ReactorAltarProbe.java")]
    subprocess.run([str(javac), "-proc:none", "-encoding", "UTF-8", "-cp", os.pathsep.join(map(str, classpath)),
                    "-d", str(classes), *sources], check=True)
    jar = destination / "gtqt-compat-probe.jar"
    with ZipFile(jar, "w") as out:
        for p in sorted(classes.rglob("*.class")):
            entry = ZipInfo(p.relative_to(classes).as_posix())
            out.writestr(entry, p.read_bytes(), compress_type=ZIP_DEFLATED)
    return jar


def single_marker(lines, prefix, phase):
    messages = [line[line.index(prefix):] for line in lines if prefix in line]
    if len(messages) != 1:
        raise ValueError(f"{phase}.log: expected one {prefix}, found {len(messages)}")
    return messages[0]


def saved_identity(level):
    """Read the two unique vanilla seed/name tags from a 1.12.2 level.dat."""
    raw = gzip.decompress(level.read_bytes())
    seed_tag = b"\x04\x00\x0aRandomSeed"
    name_tag = b"\x08\x00\x09LevelName"
    if raw.count(seed_tag) != 1 or raw.count(name_tag) != 1:
        raise ValueError("Missing or ambiguous vanilla world identity in level.dat")
    seed_bytes = raw.partition(seed_tag)[2][:8]
    name_bytes = raw.partition(name_tag)[2]
    name_size = int.from_bytes(name_bytes[:2], "big")
    name = name_bytes[2:2 + name_size].decode("utf-8")
    return {"seed": int.from_bytes(seed_bytes, "big", signed=True), "name": name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "steam-env", "state", "core", "gregtech"):
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--support-cache", type=Path, help="optional cache of the pinned magic support JARs")
    parser.add_argument("--server-dir", type=Path, help="isolated idle server with an already accepted EULA")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--supplier", action="store_true", help="inject a distinguishable registered Sunnarium in this test world")
    modes.add_argument("--core-field", action="store_true", help="use a test-only Core with a real public Sunnarium field")
    modes.add_argument("--runtime-only", action="store_true", help="use only the production JARs; verify the saved seed and mod list")
    modes.add_argument("--processing", action="store_true", help="process all affected infusions in the industrial matrix before and after restart")
    modes.add_argument("--reactor-altar", action="store_true", help="craft the magic fusion reactor on a Thaumcraft infusion altar before and after restart")
    modes.add_argument("--legacy-infusion", action="store_true", help="reload an already-paid infusion from an older scheduler save")
    parser.add_argument("--candidate", action="store_true", help="test new hashes and source commit before promotion to the lock")
    args = parser.parse_args()
    lock = json.loads((HERE.parents[1] / "workspace.lock.json").read_text(encoding="utf-8"))
    legacy, source = args.steam_env.resolve(strict=True), args.source.resolve(strict=True)
    state = args.state.resolve()
    support = (args.support_cache or state / "support").resolve()
    core, gt = args.core.resolve(strict=True), args.gregtech.resolve(strict=True)
    runtime = legacy / ".legacy-dev"
    directory = server_directory(args.server_dir, runtime, [source, legacy, state, core, gt, support])
    state.mkdir(parents=True, exist_ok=True)
    check_head(legacy, lock["repositories"]["steamRunner"]["rev"])
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    expected_rev = revision if args.candidate else lock["repositories"]["pollutionCompat"]["rev"]
    check_head(source, expected_rev)
    sys.path.insert(0, str(legacy / "dev/legacy"))
    import smoke_server as smoke
    world_mods = runpy.run_path(str(HERE.parent / "drtech/server.py"))["world_mods"]
    jdk = Path(os.environ.get("GTSTEAM_JAVA8") or runtime / "jdks/java8")
    java = str(jdk / "bin" / ("java.exe" if os.name == "nt" else "java"))
    javac = jdk / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    hashes = {"gtqtcore": smoke.digest(core), "gregtech": smoke.digest(gt)}
    if not args.candidate and hashes != lock["profiles"]["pollutionJulyCompat"]["runtimeSha256"]:
        parser.error(f"Generated runtime files differ from the profile lock: {hashes}")
    base = runtime / "server-dependencies"
    forge = smoke.prepare(java, runtime / "forge-server", base)
    result = state / "server-checks" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    result.mkdir(parents=True)
    pollution = source / "build/libs/Pollution-1.9.0.jar"
    if not args.candidate:
        profile = lock["profiles"]["pollutionJulyCompat"]
        inputs = {key: lock["artifacts"][key]["sha256"] for key in profile["artifacts"]}
        receipt = json.loads((source / "build/pollution-compat.json").read_text(encoding="utf-8"))
        if receipt != {"source": revision, "profile": "pollutionJulyCompat",
                       "jarSha256": smoke.digest(pollution), "inputs": inputs}:
            parser.error("The selected Pollution JAR does not match the locked build receipt")
        gt_compile = lock["artifacts"]["gtOctober"]
        if smoke.digest(source / "libs" / gt_compile["filename"]) != gt_compile["sha256"]:
            parser.error("The GregTech API JAR for the acceptance probe differs from the build lock")
    staged_core = core
    if args.core_field:
        from probe.core_field_fixture import make_fixture
        jdk17 = Path(os.environ.get("GTSTEAM_JAVA17") or runtime / "jdks/java17")
        gradle_cache = Path(os.environ.get("GTSTEAM_GRADLE_CACHE") or runtime / "gradle")
        staged_core = make_fixture(core, result, jdk17, gradle_cache)
    files = [gt, staged_core, pollution]
    records = {key: lock["artifacts"][key] for key in ("gtfoJuly", "steamJuly", "model100", "astralJuly")}
    for record in records.values():
        path = support / record["filename"]
        smoke.fetch(path, record["url"], record["sha256"])
        files.append(path)
    files.extend(base / name for name in smoke.DEPENDENCIES)
    for item in json.loads((HERE / "server-support.json").read_text(encoding="utf-8")):
        path = support / item["name"]
        smoke.fetch(path, item["url"], item["sha256"])
        files.append(path)
    gt_compile = source / "libs" / lock["artifacts"]["gtOctober"]["filename"]
    if not args.runtime_only:
        files.append(build_probe(result, javac, source, gt_compile, files, forge))
    if len({f.name.lower() for f in files}) != len(files):
        parser.error("Duplicate filenames in candidate runtime")
    marker = uuid4().hex
    mode = "fallback"
    if args.runtime_only:
        mode = "runtime-only"
    elif args.core_field:
        mode = "core-field"
    elif args.supplier:
        mode = "supplier"
    test_mode = mode
    if args.processing:
        test_mode = "processing"
    elif args.reactor_altar:
        test_mode = "reactor-altar"
    elif args.legacy_infusion:
        test_mode = "legacy-infusion"
    record = {"source": revision, "forge": smoke.FORGE, "mode": test_mode,
              "productionRuntimeSha256": hashes,
              "sha256": {p.name: smoke.digest(p) for p in [forge, *files]},
              "restartVerified": False, "runs": []}
    print(f"Evidence directory: {result}", flush=True)
    try:
        with isolated_server(directory, result, record, smoke):
            mods = directory / "mods"
            mods.mkdir()
            for path in files:
                shutil.copyfile(path, mods / path.name)
            level = result / "worlds" / smoke.WORLD / "level.dat"
            for phase in ("create", "reload"):
                if level.exists() != (phase == "reload"):
                    raise ValueError(f"Unexpected level.dat state before {phase}")
                if not args.runtime_only:
                    (directory / "gtqt-probe.properties").write_text(
                        f"phase={phase}\nmarker={marker}\nmode={mode}\nprocessing={str(args.processing).lower()}\n"
                        f"legacyInfusion={str(args.legacy_infusion).lower()}\nreactorAltar={str(args.reactor_altar).lower()}\n",
                        encoding="ascii")
                try:
                    smoke.boot(java, forge, directory, result, timeout=360)
                finally:
                    if (result / "console.log").exists():
                        (result / "console.log").rename(result / (phase + ".log"))
                lines = (result / (phase + ".log")).read_text(encoding="utf-8").splitlines()
                fatal_recipes = ("FluidStack cannot be null", "Invalid recipe for recipe map industrial_infusion_recipes",
                                 "Skipping industrial infusion pollution:magic_fusion_reactor:")
                if any(message in line for message in fatal_recipes for line in lines):
                    raise ValueError(f"Recipe registration errors in {phase}.log")
                expected_probe = f"GTQT_PROBE_OK phase={phase} marker={marker} "
                matches = [line[line.index(expected_probe):] for line in lines if expected_probe in line]
                if len(matches) != (0 if args.runtime_only else 1) or not any("Saved the world" in line for line in lines):
                    failures = [line for line in lines if line.startswith("Caused by: ")]
                    detail = failures[-1] if failures else "missing saved-world or probe marker"
                    raise ValueError(f"{phase}.log: {detail}")
                registered = world_mods(level)
                required = {"pollution", "gtqtcore", "gregtech", "gtsteam", "gregtechfoodoption", "modelloader"}
                if ("gtqtcompatprobe" in registered) == args.runtime_only:
                    raise ValueError(f"{phase}: unexpected probe presence for {mode}")
                if missing := required - registered.keys():
                    raise ValueError(f"{phase}: saved world is missing {sorted(missing)}")
                if phase == "reload" and registered != record["runs"][0]["mods"]:
                    raise ValueError("Registered mods changed on restart")
                identity = saved_identity(level)
                if identity["name"] != smoke.WORLD or (phase == "reload" and identity != record["runs"][0]["world"]):
                    raise ValueError(f"Different saved-world identity during {phase}: {identity}")
                run = {"phase": phase, "world": identity, "mods": registered, "levelSha256": smoke.digest(level)}
                if matches:
                    run["probe"] = matches[0]
                if args.reactor_altar:
                    run["altar"] = single_marker(lines, f"GTQT_REACTOR_ALTAR_OK phase={phase} ", phase)
                if args.legacy_infusion:
                    run["legacyInfusion"] = single_marker(lines, f"GTQT_LEGACY_INFUSION_OK phase={phase} ", phase)
                if args.processing:
                    run["importGuard"] = single_marker(lines, "GTQT_IMPORT_GUARD_OK ", phase)
                    run["parallel"] = single_marker(lines, f"GTQT_INFUSION_BATCH_OK phase={phase} ", phase)
                    marker_text = f"GTQT_PROCESS_OK phase={phase} recipe="
                    processed = [line[line.index(marker_text):] for line in lines if marker_text in line]
                    keys = [re.search(r" recipe=(\S+)", line)[1] for line in processed]
                    if len(keys) != len(PROCESSING_RECIPES) or set(keys) != PROCESSING_RECIPES:
                        raise ValueError(f"Incomplete industrial infusion processing in {phase}.log: {keys}")
                    run["processing"] = processed
                record["runs"].append(run)
            record["restartVerified"] = True
    except Exception as error:
        record["failure"] = str(error)
        reports = sorted((result / "server-files/crash-reports").glob("crash-*-server.txt"))
        if reports:
            lines = reports[-1].read_text(encoding="utf-8", errors="replace").splitlines()
            record["causes"] = [line for line in lines if line.startswith("Caused by: ")]
        raise
    finally:
        (result / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if record.get("originalsRestored") is False:
            raise RuntimeError(f"Isolated server restoration failed; inspect {result}")
    print(f"PASS: {result / 'result.json'}")


if __name__ == "__main__":
    main()
