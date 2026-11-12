"""Prepare the two derived Forge runtime JARs for the current Pollution / July Core profile."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from acceptance import check_head


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="built compatibility checkout")
    parser.add_argument("--steam-env", type=Path, required=True, help="prepared SteamTech tool checkout")
    parser.add_argument("--gradle-home", type=Path, required=True, help="Gradle 8.5 cache after a legacy build")
    parser.add_argument("--output", type=Path, required=True, help="directory for derived production JARs")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    legacy = args.steam_env.resolve(strict=True)
    gradle = args.gradle_home.resolve(strict=True)
    destination = args.output.resolve()
    lock = json.loads((ROOT / "workspace.lock.json").read_text(encoding="utf-8"))
    profile = lock["profiles"]["pollutionJulyCompat"]
    check_head(source, profile["sourceRev"])
    check_head(legacy, lock["repositories"]["steamRunner"]["rev"])
    helpers = legacy / "dev/legacy"
    sys.path.insert(0, str(helpers))
    import remap_runtime as mapper

    state = legacy / ".legacy-dev"
    java = Path(os.environ.get("GTSTEAM_JAVA17") or state / "jdks/java17")
    suffix = ".exe" if os.name == "nt" else ""
    gt = lock["artifacts"]["gtOctober"]
    core = lock["artifacts"]["coreJuly"]
    upstream_gt = mapper.checked(source / "libs" / gt["filename"], gt["sha256"])
    upstream_core = mapper.checked(source / "libs" / core["filename"], core["sha256"])
    distribution = next(gradle.glob("wrapper/dists/gradle-8.5-bin/*/gradle-8.5/lib"), None)
    if not distribution:
        parser.error("Run the legacy build first to populate the Gradle 8.5 cache")
    asm = [mapper.checked(distribution / name, sha) for name, sha in mapper.ASM_LIBS.items()]
    classpath = os.pathsep.join(map(str, asm))
    mappings = [mapper.checked(gradle / "caches" / name, sha, name.endswith(".srg"))
                for name, sha in mapper.MAPPING_INPUTS.items()]
    forge = mapper.checked(state / "forge-server/forge-1.12.2-14.23.5.2860.jar", mapper.FORGE_HASH)
    mods = [mapper.checked(state / "server-dependencies" / name, sha) for name, sha in mapper.MOD_LIBS.items()]
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination) as temporary:
        stage = Path(temporary)
        gt_out = stage / "gregtech-1.9.0-october-srg.jar"
        core_out = stage / "gtqtcore-1.9.0-july-compat.jar"
        subprocess.run([java / "bin" / ("javac" + suffix), "--release", "17", "-encoding", "UTF-8",
                        "-cp", classpath, "-d", stage, helpers / "ProductionNames.java"], check=True)
        subprocess.run([java / "bin" / ("java" + suffix), "-Xmx2G", "-cp", str(stage) + os.pathsep + classpath,
                        "ProductionNames", *mappings, forge, upstream_gt, gt_out, stage / "mappings.tsv", *mods],
                       check=True)
        subprocess.run([sys.executable, "-B", HERE / "compat/patch_core.py", "--input", upstream_core,
                        "--output", core_out, "--java-home", java, "--gradle-cache", gradle], check=True)
        for path, mod_id in ((gt_out, "gregtech"), (core_out, "gtqtcore")):
            mapper.checked(path, profile["runtimeSha256"][mod_id])
        for path in (gt_out, core_out):
            path.replace(destination / path.name)
            print(destination / path.name)


if __name__ == "__main__":
    main()
