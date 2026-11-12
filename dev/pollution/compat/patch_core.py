"""Generate the July Core with client-only renderer registration for the compatibility profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZIP_STORED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
PATCHED_CLASSES = ("meowmel/gtqtcore/common/CommonProxy.class",
                   "meowmel/gtqtcore/common/blocks/BlockWireCoil$Builder$1.class")
ASM_SHA = "b62e84b5980729751b0458c534cf1366f727542bb8d158621335682a460f0353"


def sha256(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="unmodified July GTQT-Core JAR")
    parser.add_argument("--output", type=Path, required=True, help="separate generated JAR")
    parser.add_argument("--java-home", type=Path, required=True, help="JDK 17")
    parser.add_argument("--gradle-cache", type=Path, required=True, help="prepared Gradle 8.5 cache")
    args = parser.parse_args()
    source, output = args.input.resolve(), args.output.resolve()
    if output == source or (output.exists() and output.samefile(source)):
        parser.error("Choose a separate output JAR")
    lock = json.loads((HERE.parents[2] / "workspace.lock.json").read_text(encoding="utf-8"))
    if sha256(source) != lock["artifacts"]["coreJuly"]["sha256"]:
        parser.error(f"Expected the locked July GTQT-Core at {source}")
    asm = next(args.gradle_cache.glob("wrapper/dists/gradle-8.5-bin/*/gradle-8.5/lib/asm-9.5.jar"), None)
    if not asm or sha256(asm) != ASM_SHA:
        parser.error("Expected the Gradle 8.5 distribution with the pinned ASM 9.5 JAR")
    exe = ".exe" if os.name == "nt" else ""
    javac = args.java_home / "bin" / ("javac" + exe)
    java = args.java_home / "bin" / ("java" + exe)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp)
        with ZipFile(source) as original:
            subprocess.run([javac, "--release", "17", "-cp", asm, "-d", stage,
                            HERE / "PatchJulyCore.java"], check=True)
            changes = {}
            for name in PATCHED_CLASSES:
                before, after = stage / "original.class", stage / "patched.class"
                before.write_bytes(original.read(name))
                subprocess.run([java, "-cp", os.pathsep.join((str(stage), str(asm))),
                                "PatchJulyCore", before, after], check=True)
                changes[name] = after.read_bytes()
            jar = stage / "core.jar"
            with ZipFile(jar, "w", ZIP_STORED) as target:
                for entry in original.infolist():
                    info = ZipInfo(entry.filename)
                    info.create_system = 0
                    info.external_attr = 0x10 if entry.is_dir() else 0x20
                    data = changes[entry.filename] if entry.filename in changes else original.read(entry)
                    target.writestr(info, data)
        os.replace(jar, output)
    print(f"{sha256(output)}  {output}")


if __name__ == "__main__":
    main()
