"""Generate a test-only Core with a real public static Material Sunnarium field."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import subprocess
from zipfile import ZipFile


HOLDER = "meowmel/gtqtcore/api/unification/material/GTQTMaterials.class"
ASM_SHA = "b62e84b5980729751b0458c534cf1366f727542bb8d158621335682a460f0353"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def make_fixture(core, directory, java_home, gradle_cache):
    """Use a distinct test-only filename and keep the certified production Core intact."""
    core = core.resolve(strict=True)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory.resolve() / "TEST-ONLY-gtqtcore-field.jar"
    if target == core or (target.exists() and target.samefile(core)):
        raise ValueError("Test fixture must use a separate destination")
    asm = next(gradle_cache.glob("wrapper/dists/gradle-8.5-bin/*/gradle-8.5/lib/asm-9.5.jar"), None)
    if not asm or digest(asm) != ASM_SHA:
        raise ValueError("Expected ASM 9.5 from the locked Gradle distribution")
    java = java_home / "bin" / ("java.exe" if os.name == "nt" else "java")
    with tempfile.TemporaryDirectory(dir=directory) as scratch:
        stage = Path(scratch)
        with ZipFile(core) as source:
            before, after = stage / "before.class", stage / "after.class"
            before.write_bytes(source.read(HOLDER))
            subprocess.run([java, "-cp", asm, Path(__file__).with_name("AddTestSunnariumField.java"),
                            before, after], check=True)
            fixture = stage / "fixture.jar"
            with ZipFile(fixture, "w") as archive:
                for item in source.infolist():
                    data = after.read_bytes() if item.filename == HOLDER else source.read(item)
                    archive.writestr(item, data)
        os.replace(fixture, target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("core", "destination", "java-home", "gradle-cache"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    path = make_fixture(args.core, args.destination, args.java_home, args.gradle_cache)
    print(f"{digest(path)}  {path}")
