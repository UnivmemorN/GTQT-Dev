"""Build the GTQT/Pollution working tree against the active gtqt19 organization dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


WORKSPACE_LOCK = Path(__file__).resolve().parents[2] / "workspace.lock.json"


def verify_inputs(source, lock):
    repo = lock["repositories"]["pollution"]["repo"].casefold()
    urls = {
        f"https://github.com/{repo}", f"git@github.com:{repo}", f"ssh://git@github.com/{repo}",
    }
    remotes = subprocess.check_output(["git", "-C", source, "remote", "-v"], text=True)
    fetch_urls = {line.split()[1].casefold().rstrip("/").removesuffix(".git")
                  for line in remotes.splitlines() if line.endswith("(fetch)")}
    if not urls.intersection(fetch_urls):
        raise ValueError(f"Expected a checkout with a GitHub remote for {repo} at {source}")

    # Pollution's Gradle project declares each local dependency as files("libs/<name>.jar").
    script = (source / "build.gradle").read_text(encoding="utf-8")
    local_jar = r"""\bfiles\(\s*["']libs/([^/"'\n]+\.jar)["']\s*\)"""
    names = set(re.findall(local_jar, script))
    if not names:
        raise ValueError(f"No declared local Pollution dependencies found in {source / 'build.gradle'}")
    runtime = lock["profiles"]["gtqt19"]["runtime"]["server"]
    for name in sorted(names):
        expected = runtime.get(name)
        if not expected:
            raise ValueError(f"Pollution declares {name}, which has no gtqt19 server digest")
        file = source / "libs" / name
        if not file.is_file():
            raise ValueError(f"Prepare {file} from the gtqt19 server inputs (SHA-256 {expected})")
        with file.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"{file}: expected gtqt19 SHA-256 {expected}, found {actual}")
    print(f"Verified {len(names)} local Pollution build inputs against gtqt19.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="organization checkout with matching JARs in libs/")
    parser.add_argument("--steam-env", type=Path, required=True, help="prepared Forge 1.12.2 toolchain checkout")
    parser.add_argument("--state", type=Path, required=True, help="directory containing the Pollution Gradle cache")
    parser.add_argument("--offline", action="store_true", help="reuse prepared Gradle inputs")
    parser.add_argument("--clean", action="store_true", help="run Gradle clean before the selected task")
    parser.add_argument("task", nargs="?", choices=["compileJava", "assemble", "build"], default="build")
    args = parser.parse_args()
    source, legacy, state = (p.resolve() for p in (args.source, args.steam_env, args.state))
    try:
        verify_inputs(source, json.loads(WORKSPACE_LOCK.read_text(encoding="utf-8-sig")))
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")

    helpers = legacy / "dev/legacy"
    deps = legacy / ".legacy-dev/deps"
    if not (deps / "maven").is_dir():
        parser.exit(1, f"Prepare the Forge 1.12.2 build tooling in {deps} first\n")
    gradle = state / "gradle"
    if not args.offline:
        subprocess.run([sys.executable, "-B", helpers / "prepare_minecraft_cache.py",
                        "--gradle-home", gradle], check=True)
    jdk_root = legacy / ".legacy-dev/jdks"
    jdks = [Path(os.environ.get(f"GTSTEAM_JAVA{v}") or jdk_root / f"java{v}").resolve() for v in (8, 16, 17)]
    env = dict(os.environ, GRADLE_USER_HOME=str(gradle), JAVA_HOME=str(jdks[-1]))
    wrapper = source / ("gradlew.bat" if os.name == "nt" else "gradlew")
    command = [wrapper, "--console=plain", "-I", helpers / "repositories.gradle",
               f"-Dgtsteam.dev.maven={deps / 'maven'}", "-Porg.gradle.java.installations.paths=" + ",".join(map(str, jdks)),
               "-Porg.gradle.java.installations.auto-download=false", "--max-workers=3",
               "-x", "downloadFernflower", "-x", "downloadAssetManifest", "-x", "downloadVanillaAssets"]
    if args.offline:
        command.append("--offline")
    if args.clean:
        command.append("clean")
    result = subprocess.run(command + [args.task], cwd=source, env=env)
    if result.returncode == 0 and args.task in ("assemble", "build"):
        jar = source / "build/libs/Pollution-1.9.0.jar"
        with zipfile.ZipFile(jar) as archive:
            mods = {(entry["modid"], entry["version"]) for entry in json.loads(archive.read("mcmod.info"))}
            header = archive.read("meowmel/pollution/Pollution.class")[:8]
            java8 = header[:4] == b"\xca\xfe\xba\xbe" and int.from_bytes(header[6:], "big") == 52
            if archive.testzip() or mods != {("pollution", "1.9.0")} or not java8:
                sys.exit(f"Unexpected or damaged Java 8 Pollution 1.9.0 artifact at {jar}")
        with jar.open("rb") as stream:
            print(f"{jar}  SHA-256 {hashlib.file_digest(stream, 'sha256').hexdigest()}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
