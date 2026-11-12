"""Replay the pinned DrTech build probe with the SteamTech legacy tool bootstrap."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from acceptance import check_head

RFG_URL = "https://github.com/GTNewHorizons/RetroFuturaGradle/releases/download/1.4.0/"
RFG = {
    "retrofuturagradle": (46866219, "49de836a84b0ee5b3e0f9c0fdf25b9e780fb7b69790e1a3e86074d388396eb94"),
    "rfgJavacPlugin": (4946060, "3efe33563d27492c69fee6aeda8c9eb209aa59376153eb8c545197f1d254b29e"),
}


def workspace_lock():
    return json.loads((HERE.parents[1] / "workspace.lock.json").read_text(encoding="utf-8-sig"))


def build_receipt(lock, profile, jar_sha):
    ids = lock["profiles"][profile]["artifacts"]
    return {"profile": profile, "source": lock["repositories"]["drtech"]["rev"], "jarSha256": jar_sha,
            "inputs": {key: lock["artifacts"][key]["sha256"] for key in ids}}


def prepare_october_source(source, revision):
    prefix = "src/main/java/com/drppp/drtech/"
    changeset = {prefix + "common/metaTileEntities/muti/mutipart/MetaTileEntityYotHatch.java":
                 ("Textures.ME_INPUT_BUS.renderSided(", "Textures.FLUID_HATCH_INPUT_OVERLAY.renderSided(")}
    for filename, handler, packet, discriminator in (
        ("common/glider/GliderNetwork", "SyncHandler", "SyncPacket", 1),
        ("common/wings/WingsNetwork", "SyncHandler", "SyncPacket", 1),
        ("hooked/HookNetwork", "SyncHooksHandler", "PacketHookCapSync", 4),
    ):
        register = f"{packet}.class, {discriminator}, Side.CLIENT);"
        before = f"CHANNEL.registerMessage({handler}.class, {register}\n        }}"
        after = (before + " else {\n            // The dedicated sender also needs the discriminator to encode the packet.\n"
                 f"            CHANNEL.registerMessage((message, ctx) -> null, {register}\n        }}")
        changeset[prefix + filename + ".java"] = before, after
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    changes = set(subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=source, text=True).splitlines())
    if head != revision or changes.difference(changeset):
        sys.exit(f"Use an isolated DrTech checkout at {revision} for --october-gregtech")
    pending = {}
    adapted = {}
    for path, (before, after) in changeset.items():
        original = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=source).replace(b"\r\n", b"\n")
        if original.count(before.encode()) != 1:
            sys.exit(f"Pinned DrTech source does not contain the expected code in {path}")
        expected = original.replace(before.encode(), after.encode())
        content = (source / path).read_bytes()
        normalized = content.replace(b"\r\n", b"\n")
        if normalized not in (original, expected):
            sys.exit(f"Unexpected local changes at {source / path}")
        if normalized != expected:
            pending[source / path] = expected.replace(b"\n", b"\r\n") if b"\r\n" in content else expected
        adapted[path] = hashlib.sha256(expected).hexdigest()
    for path, data in pending.items():
        path.write_bytes(data)
    return adapted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="upstream DrTech checkout")
    parser.add_argument("--steam-env", type=Path, required=True, help="pinned SteamTech environment checkout")
    parser.add_argument("--state", type=Path, required=True, help="local DrTech tooling/cache directory")
    parser.add_argument("--gradle-home", type=Path, help="optional existing Gradle 8.5 cache")
    parser.add_argument("--rfg-seed", type=Path, help="optional official release JAR download directory")
    versions = parser.add_mutually_exclusive_group()
    versions.add_argument("--steam-gregtech", action="store_true", help="build with SteamTech's August GregTech pin")
    versions.add_argument("--october-gregtech", action="store_true",
                          help="apply the October YOT overlay and dedicated packet fixes in the supplied isolated checkout")
    parser.add_argument("--offline", action="store_true", help="use only previously prepared inputs and Gradle cache")
    parser.add_argument("--clean", action="store_true", help="run upstream clean before the selected task")
    parser.add_argument("task", nargs="?", choices=["help", "compileJava", "build"], default="build")
    args = parser.parse_args()
    source, legacy, state = [path.resolve() for path in (args.source, args.steam_env, args.state)]
    lock = workspace_lock()
    profile = "steamDrtechAugust" if args.steam_gregtech else "drtechJuly"
    adapted_sources = None
    if args.october_gregtech:
        profile = "drtechOctober"
        adapted_sources = prepare_october_source(source, lock["repositories"]["drtech"]["rev"])
    else:
        check_head(source, lock["repositories"]["drtech"]["rev"])
    check_head(legacy, lock["repositories"]["steamRunner"]["rev"])
    helpers = legacy / "dev/legacy"
    sys.path.insert(0, str(helpers))
    from prepare_dependencies import fetch_verified, matches

    deps = legacy / ".legacy-dev/deps"
    maven = state / "maven"
    jdk_root = legacy / ".legacy-dev/jdks"
    java8 = Path(os.environ.get("GTSTEAM_JAVA8") or jdk_root / "java8").resolve()
    java17 = Path(os.environ.get("GTSTEAM_JAVA17") or jdk_root / "java17").resolve()
    gradle_home = (args.gradle_home or state / "gradle").resolve()
    env = dict(os.environ, JAVA_HOME=str(java17), GRADLE_USER_HOME=str(gradle_home))
    if not args.offline:
        subprocess.run([sys.executable, "-B", helpers / "prepare_dependencies.py", "--output", deps], check=True)
        subprocess.run([sys.executable, "-B", helpers / "prepare_minecraft_cache.py",
                        "--gradle-home", gradle_home], check=True)
    for key, (size, sha) in RFG.items():
        filename = f"{key}-1.4.0.jar"
        dest = maven / "com/gtnewhorizons" / key / "1.4.0" / filename
        entry = dict(size=size, sha256=sha, urls=[RFG_URL + filename])
        if args.offline and not matches(dest, entry):
            sys.exit(f"Prepare {dest} online first")
        fetch_verified(entry, dest, args.rfg_seed / filename if args.rfg_seed else None)
    # The official GitHub release provides the shaded plug-in and javac plug-in.
    # Generate the three POMs using the same coordinates as the locked 1.4.1 layout.
    bootstrap_lock = json.loads((helpers / "dependencies.lock.json").read_text(encoding="utf-8"))
    for entry in bootstrap_lock:
        path = entry["path"]
        if path.startswith("maven/com/gtnewhorizons/") and path.endswith(".pom"):
            pom = state / path.replace("1.4.1", "1.4.0")
            pom.parent.mkdir(parents=True, exist_ok=True)
            pom.write_text(entry["text"].replace("1.4.1", "1.4.0"), encoding="utf-8")
    for key in lock["profiles"][profile]["artifacts"]:
        pin = lock["artifacts"][key]
        dest = source / "libs" / pin["filename"]
        entry = {**pin, "urls": [pin["url"]]}
        cached = deps / "libs" / pin["filename"]
        if dest.exists() and not matches(dest, entry):
            sys.exit(f"Expected SHA-256 {pin['sha256']} at {dest}")
        if args.offline and not matches(dest, entry) and not matches(cached, entry):
            sys.exit(f"Prepare {dest} online first")
        fetch_verified(entry, dest, cached)
    wrapper = source / ("gradlew.bat" if os.name == "nt" else "gradlew")
    args_gradle = [wrapper, "--no-daemon", "--console=plain", "-I", HERE / "rfg.gradle",
                   f"-Ddrtech.rfg.maven={maven}", "-I", helpers / "repositories.gradle",
                   f"-Dgtsteam.dev.maven={deps / 'maven'}", f"-Porg.gradle.java.installations.paths={java8},{java17}",
                   "-Porg.gradle.java.installations.auto-download=false", "--max-workers=4", "-x", "downloadFernflower"]
    if args.offline:
        args_gradle.append("--offline")
    if args.clean:
        args_gradle.append("clean")
    result = subprocess.run([*args_gradle, args.task], cwd=source, env=env)
    if result.returncode == 0 and args.task == "build":
        artifact = source / "build/libs/drtech-1.8.9.jar"
        with zipfile.ZipFile(artifact) as jar:
            mods = {(mod["modid"], mod["version"]) for mod in json.loads(jar.read("mcmod.info"))}
            main_class = jar.read("com/drppp/drtech/DrTechMain.class")
        expected_mods = {("drtech", "1.8.9"), ("futuremc", "1.0.0")}
        java8_header = main_class[:4] == b"\xca\xfe\xba\xbe" and int.from_bytes(main_class[6:8], "big") == 52
        if mods != expected_mods or not java8_header:
            sys.exit(f"Unexpected mod metadata or Java bytecode in {artifact}")
        sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        receipt = source / "build/drtech-profile.json"
        record = build_receipt(lock, profile, sha)
        if adapted_sources:
            record["adaptedSourcesSha256"] = adapted_sources
        receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"{artifact}  SHA-256 {sha}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
