"""Build GTMaid or VisualOres against the locked October GT using the verified Forge 1.12 toolchain."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(target, url, expected):
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response, target.open("xb") as stream:
            shutil.copyfileobj(response, stream)
    if sha(target) != expected:
        raise ValueError(f"SHA-256 differs from the lock: {target}")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addon", choices=("gtmaid", "visualores"))
    parser.add_argument("--work", type=Path, required=True, help="new, empty build directory")
    parser.add_argument("--cache", type=Path, required=True, help="cache for pinned source and build scaffolding")
    parser.add_argument("--mods", type=Path, required=True, help="original 1.8.8 flat mods directory")
    parser.add_argument("--steam-env", type=Path, required=True, help="prepared SteamTech 1.12.2 development environment")
    parser.add_argument("--rfg-maven", type=Path, required=True, help="1.4.0 plugin cache prepared by dev/drtech/build.py")
    parser.add_argument("--prepare-only", action="store_true", help="verify inputs and apply the patch without running Gradle")
    args = parser.parse_args()
    lock = json.loads((HERE / "manifest-addon-sources.json").read_bytes())
    addon = lock["addons"][args.addon]
    project = args.work.resolve()
    project.mkdir(parents=True, exist_ok=True)
    if any(project.iterdir()):
        parser.error(f"Build directory must be empty: {project}")
    cache = args.cache.resolve()
    repo, revision = addon["repo"], addon["rev"]
    bundle = fetch(cache / f"{repo.split('/')[-1]}.zip", f"https://codeload.github.com/{repo}/zip/{revision}",
                   addon["sourceZipSha256"])
    with ZipFile(bundle) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            relative = member.filename.partition("/")[2]
            dest = (project / relative).resolve()
            if not relative or not dest.is_relative_to(project):
                raise ValueError(f"Unsafe archive entry {member.filename}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, dest.open("xb") as output:
                shutil.copyfileobj(source, output)
    for name, expected in addon["templates"].items():
        template = fetch(cache / addon["templateRev"] / name,
                         f"https://raw.githubusercontent.com/{addon['templateRepo']}/{addon['templateRev']}/{name}", expected)
        shutil.copyfile(template, project / name)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "apply", str(HERE / f"manifest-{args.addon}.patch")], cwd=project, check=True)
    lines = ["dependencies {"]
    for key in addon["inputs"]:
        artifact = lock["inputs"][key]
        if "embeddedInSource" in artifact:
            path = project / artifact["embeddedInSource"]
        elif "curseProject" in artifact:
            path = args.mods.resolve() / artifact["filename"]
        else:
            path = fetch(cache / artifact["filename"], artifact["url"], artifact["sha256"])
        if sha(path) != artifact["sha256"]:
            raise ValueError(f"Build input checksum mismatch: {path}")
        # Work with names relative to this isolated checkout, including when an external path contains quotes.
        dest = project / "candidate-inputs" / artifact["filename"]
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, dest)
        lines.append(f"    implementation rfg.deobf(files('candidate-inputs/{dest.name}'))")
    legacy = args.steam_env.resolve()
    runtime = legacy / ".legacy-dev"
    gradle = runtime / "gradle"
    mui = lock["modularUiCompile"]
    candidates = (gradle / "caches/modules-2/files-2.1/com.cleanroommc/modularui/3.1.5").glob("*/" + mui["filename"])
    if not any(sha(path) == mui["sha256"] for path in candidates):
        raise ValueError("Missing verified ModularUI 3.1.5 development JAR in the SteamTech Gradle cache")
    lines.extend(['    api("com.cleanroommc:modularui:3.1.5") { transitive = false }', "}", ""])
    (project / addon["dependenciesFile"]).write_text("\n".join(lines), encoding="utf-8")
    if args.prepare_only:
        return
    java = runtime / "jdks"
    env = dict(os.environ, JAVA_HOME=str(java / "java17"), GRADLE_USER_HOME=str(gradle))
    wrapper = legacy / ("gradlew.bat" if os.name == "nt" else "gradlew")
    subprocess.run([str(wrapper), "--offline", "--no-daemon", "--console=plain", "--max-workers=2",
                    "-I", str(HERE.parent / "drtech/rfg.gradle"), f"-Ddrtech.rfg.maven={args.rfg_maven.resolve()}",
                    "-I", str(legacy / "dev/legacy/repositories.gradle"), f"-Dgtsteam.dev.maven={runtime / 'deps/maven'}",
                    "-Porg.gradle.java.installations.paths=" + ",".join(str(java / v) for v in ("java8", "java16", "java17")),
                    "-Porg.gradle.java.installations.auto-download=false", "-x", "downloadFernflower", "build"],
                   env=env, cwd=project, check=True)
    jar = next(path for path in (project / "build/libs").glob("*.jar") if not path.name.endswith(("-dev.jar", "-sources.jar")))
    print(f"{jar}: {sha(jar)}")


if __name__ == "__main__":
    main()
