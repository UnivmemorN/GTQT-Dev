"""Build the narrowly scoped Future MC barrel compatibility patch for BogoSorter 1.6.2 and 1.6.4."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile, ZipInfo

SOURCE = Path(__file__).with_name("PatchBogoBarrel.java")
CLASS = "com/cleanroommc/bogosorter/compat/DefaultCompat.class"
INPUTS = {"7e8edc3137e96f04d8e46a44e66737ec159a503c9e61894b3b3425fbddab12d1",
          "08286ce5971766c02e7ae522357b5ef4aa35b15bf9ee226053932c34582a8a53"}
ASM = "b62e84b5980729751b0458c534cf1366f727542bb8d158621335682a460f0353"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--java-home", required=True, type=Path, help="JDK 17")
    parser.add_argument("--gradle-cache", required=True, type=Path, help="Prepared Gradle 8.5 cache")
    args = parser.parse_args()
    source, output = args.input.resolve(), args.output.resolve()
    if source == output or digest(source) not in INPUTS:
        parser.error("Supply a pinned original BogoSorter JAR and a separate output path")
    asm = next((p for p in args.gradle_cache.glob("wrapper/dists/gradle-8.5-*/**/lib/asm-9.5.jar")
                if digest(p) == ASM), None)
    if asm is None:
        parser.error("Missing Gradle 8.5 ASM 9.5 JAR with the pinned digest")
    java = args.java_home.resolve() / "bin"
    ext = ".exe" if os.name == "nt" else ""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp)
        with ZipFile(source) as original:
            before, after = stage / "before.class", stage / "after.class"
            before.write_bytes(original.read(CLASS))
            subprocess.run([java / ("javac" + ext), "--release", "17", "-cp", asm, "-d", stage, SOURCE], check=True)
            subprocess.run([java / ("java" + ext), "-cp", os.pathsep.join(map(str, (stage, asm))),
                            "PatchBogoBarrel", before, after], check=True)
            jar = stage / "patched.jar"
            with ZipFile(jar, "w") as target:
                for member in original.infolist():
                    info = ZipInfo(member.filename)
                    info.create_system = 0
                    info.external_attr = 16 if member.is_dir() else 32
                    target.writestr(info, after.read_bytes() if member.filename == CLASS else original.read(member))
        os.replace(jar, output)
    print(f"{digest(output)}  {output}")


if __name__ == "__main__":
    main()
