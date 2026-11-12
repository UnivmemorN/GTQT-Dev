"""Run the August DrTech/SteamTech dedicated Forge probe in an existing isolated loopback rig."""
import argparse
from datetime import datetime
import gzip
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acceptance import check_head, isolated_server, server_directory

SUPPORT = {
    "forestry-59751-2684780": "812260f39b7a17c856d30ba97bbe36578635a2f3b9413fc4dc98ccbf7b0d9884",
    "BdLib-70496-4675629": "b385f1a6f3f908673324ef03ed15b6bb5f588ce2e36443acc7273a6263cca045",
    "gendustry-70492-2516215": "21952b5b2f4a89a3b80029042ec7b07d99835e56683d2c17e130a1144922b38d",
    "Binnie's Mods-223525-2916129": "2ead1181ab49131241862d98a78d72f4b171f102d2774c730b0f67677fcfd03f",
}


def world_mods(level):
    data = gzip.decompress(level.read_bytes())
    marker = b"\x09\x00\x07ModList\x0a"
    if data.count(marker) != 1:
        raise ValueError("Expected exactly one FML ModList compound list in level.dat")
    nbt = BytesIO(data.split(marker, 1)[1])

    def read_string():
        length = int.from_bytes(nbt.read(2), "big")
        return nbt.read(length).decode("utf-8")

    mods = {}
    for _ in range(int.from_bytes(nbt.read(4), "big")):
        fields = {}
        while (tag := nbt.read(1)) != b"\x00":
            if tag != b"\x08":
                raise ValueError("Unexpected entry type in FML ModList")
            key = read_string()
            fields[key] = read_string()
        mod_id = fields["ModId"]
        if mod_id in mods:
            raise ValueError(f"Duplicate id {mod_id} in FML ModList")
        mods[mod_id] = fields["ModVersion"]
    return mods


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("steam-env", "drtech", "drtech-source", "results-root"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--support-cache", type=Path, required=True, help="download/cache for the four pinned support JARs")
    parser.add_argument("--server-dir", type=Path, help="isolated server directory with an already accepted eula.txt")
    args = parser.parse_args()
    legacy = args.steam_env.resolve(strict=True)
    state = legacy / ".legacy-dev"
    from build import build_receipt, workspace_lock
    lock = workspace_lock()
    profile = "steamDrtechAugust"
    check_head(legacy, lock["repositories"]["steamRunner"]["rev"])
    baseline = state / "baseline"
    check_head(baseline, lock["profiles"]["steamBaseline"]["sourceRev"])
    source = args.drtech_source.resolve(strict=True)
    check_head(source, lock["repositories"]["drtech"]["rev"])
    directory = server_directory(args.server_dir, state, [legacy, source, args.drtech, args.support_cache, args.results_root])
    sys.path.insert(0, str(legacy / "dev/legacy"))
    import smoke_server as smoke
    from smoke_server import boot, prepare, digest, fetch, DEPENDENCIES, WORLD
    from remap_runtime import OUTPUT_HASH
    from prepare_dependencies import matches

    java8 = Path(os.environ.get("GTSTEAM_JAVA8") or state / "jdks/java8") / "bin" / ("java.exe" if os.name == "nt" else "java")
    deps = state / "server-dependencies"
    addons = []
    for key in lock["profiles"][profile]["artifacts"]:
        entry = lock["artifacts"][key]
        path = source / "libs" / entry["filename"]
        if not matches(path, entry):
            parser.error(f"Unexpected {profile} compile input at {path}")
        if key != "gtAugust":
            addons.append(path)
    core = state / "runtime" / lock["artifacts"]["gtAugust"]["filename"]
    if digest(core) != OUTPUT_HASH:
        parser.error(f"Expected the pinned SRG GregTech runtime at {core}")
    drtech = source / "build/libs/drtech-1.8.9.jar"
    receipt = source / "build/drtech-profile.json"
    if not drtech.is_file() or not receipt.is_file():
        parser.error("Run dev/drtech/build.py with --steam-gregtech build for this checkout first")
    actual = digest(drtech)
    if (json.loads(receipt.read_text(encoding="utf-8")) != build_receipt(lock, profile, actual) or
            digest(args.drtech.resolve(strict=True)) != actual):
        parser.error("--drtech must match this checkout's verified August build output")
    files = [core, baseline / "build/libs/gtsteam-1.9.0.jar", drtech, *addons]
    forge = prepare(str(java8), state / "forge-server", deps)
    files.extend(deps / name for name in DEPENDENCIES)
    support = args.support_cache.resolve()
    results = args.results_root.resolve() / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for stem, sha in SUPPORT.items():
        artifact, file_id = stem.rsplit("-", 1)
        filename = stem + ".jar"
        url = f"https://cursemaven.com/curse/maven/{quote(artifact)}/{file_id}/{quote(filename)}"
        path = support / filename
        fetch(path, url, sha)
        files.append(path)
    if len({path.name.casefold() for path in files}) != len(files):
        parser.error("Duplicate JAR filenames in the combined server profile")
    results.mkdir(parents=True, exist_ok=False)
    record = {"readyAndSaved": False, "sha256": {path.name: digest(path) for path in [forge, *files]}}
    print(f"Evidence directory: {results}", flush=True)
    try:
        with isolated_server(directory, results, record, smoke):
            mods = directory / "mods"
            mods.mkdir()
            for path in files:
                shutil.copyfile(path, mods / path.name)
            boot(str(java8), forge, directory, results, timeout=300)
            mods = world_mods(results / "worlds" / WORLD / "level.dat")
            expected = {"gregtech": "1.9.0", "gtsteam": "0.0.1-beta", "drtech": "1.8.9",
                        "futuremc": "1.0.0", "gregtechfoodoption": "1.9.0", "modelloader": "1.0.0"}
            for mod_id, version in expected.items():
                if mods.get(mod_id) != version:
                    raise RuntimeError(f"Expected {mod_id} {version} in FML ModList, found {mods.get(mod_id)}")
            console = (results / "console.log").read_text(encoding="utf-8")
            record.update(readyAndSaved=True, modVersions=mods, extractorRejected="Invalid recipe for recipe map extractor" in console,
                          cropSeedReflectionFailures=console.count("NoSuchMethodException: net.minecraft.block.BlockCrops.getSeed()"))
    except Exception as exc:
        record["failure"] = str(exc)
        raise
    finally:
        (results / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if record.get("originalsRestored") is False:
            raise RuntimeError(f"Original rig verification failed. Inspect {results}")
    print(f"PASS: {results / 'result.json'}")


if __name__ == "__main__":
    main()
