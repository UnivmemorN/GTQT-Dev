"""Build the pinned Pollution checkout with independently verified author dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acceptance import check_head

LOCK = json.loads((Path(__file__).resolve().parents[2] / "workspace.lock.json").read_text(encoding="utf-8-sig"))
BASELINE = LOCK["repositories"]["pollutionJuly"]["rev"]
CURRENT = LOCK["repositories"]["pollutionCurrent"]["rev"]
ENVIRONMENT = LOCK["repositories"]["steamRunner"]["rev"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--steam-env", type=Path, required=True, help="prepared legacy SteamTech checkout")
    parser.add_argument("--state", type=Path, required=True, help="private Pollution state directory")
    parser.add_argument("--offline", action="store_true", help="reuse previously prepared inputs only")
    parser.add_argument("--clean", action="store_true", help="run Gradle clean before the selected task")
    parser.add_argument("task", nargs="?", choices=["compileJava", "build"], default="build")
    args = parser.parse_args()
    source, legacy, state = (p.resolve() for p in (args.source, args.steam_env, args.state))
    revision = check_head(source, CURRENT, BASELINE)
    check_head(legacy, ENVIRONMENT)
    helpers = legacy / "dev/legacy"
    sys.path.insert(0, str(helpers))
    from prepare_dependencies import fetch_verified, matches

    profile = "pollutionJuly" if revision == BASELINE else "pollutionCurrent"
    for artifact_id in LOCK["profiles"][profile]["artifacts"]:
        # This July Core dependency is needed at runtime only; July Pollution compiles without it.
        if profile == "pollutionJuly" and artifact_id == "model100":
            continue
        artifact = LOCK["artifacts"][artifact_id]
        target = source / "libs" / artifact["filename"]
        entry = dict(size=artifact["size"], sha256=artifact["sha256"], urls=[artifact["url"]])
        if not matches(target, entry) and (target.exists() or args.offline):
            sys.exit(f"Expected SHA-256 {artifact['sha256']} at {target}; use a clean checkout and prepare online first")
        fetch_verified(entry, target)
    deps = legacy / ".legacy-dev/deps"
    if not (deps / "maven").is_dir():
        sys.exit(f"Prepare the SteamTech legacy tooling in {deps} first")
    gradle = state / "gradle"
    if not args.offline:
        subprocess.run([sys.executable, "-B", helpers / "prepare_minecraft_cache.py",
                        "--gradle-home", gradle], check=True)
    jdk_root = legacy / ".legacy-dev/jdks"
    java8, java16, java17 = (Path(os.environ.get(f"GTSTEAM_JAVA{v}") or jdk_root / f"java{v}").resolve()
                             for v in (8, 16, 17))
    env = dict(os.environ, GRADLE_USER_HOME=str(gradle), JAVA_HOME=str(java17))
    wrapper = source / ("gradlew.bat" if os.name == "nt" else "gradlew")
    command = [wrapper, "--no-daemon", "--console=plain", "-I", helpers / "repositories.gradle",
               f"-Dgtsteam.dev.maven={deps / 'maven'}", f"-Porg.gradle.java.installations.paths={java8},{java16}",
               "-Porg.gradle.java.installations.auto-download=false", "--max-workers=3", "-x", "downloadFernflower"]
    if args.offline:
        command.append("--offline")
    if args.clean:
        command.append("clean")
    result = subprocess.run(command + [args.task], cwd=source, env=env)
    if result.returncode == 0 and args.task == "build":
        jar = source / "build/libs/Pollution-1.9.0.jar"
        with zipfile.ZipFile(jar) as archive:
            mods = {(entry["modid"], entry["version"]) for entry in json.loads(archive.read("mcmod.info"))}
            header = archive.read("meowmel/pollution/Pollution.class")[:8]
            java8 = header[:4] == b"\xca\xfe\xba\xbe" and int.from_bytes(header[6:], "big") == 52
            if archive.testzip() or mods != {("pollution", "1.9.0")} or not java8:
                sys.exit(f"Unexpected or damaged Java 8 Pollution 1.9.0 artifact at {jar}")
        print(f"{jar}  SHA-256 {hashlib.sha256(jar.read_bytes()).hexdigest()}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
