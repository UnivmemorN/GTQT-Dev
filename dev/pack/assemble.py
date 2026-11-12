"""Assemble both sides of the locked 1.12.2 candidate from verified JARs and the upstream overrides ZIP."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
OVERRIDES = {"config", "scripts", "groovy", "resources"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def overrides_digest(path):
    tree = hashlib.sha256()
    with ZipFile(path) as bundle:
        for entry in sorted(bundle.infolist(), key=lambda item: item.filename):
            if entry.is_dir():
                continue
            tree.update(entry.filename.encode("utf-8") + b"\0")
            with bundle.open(entry) as data:
                tree.update(hashlib.file_digest(data, "sha256").digest())
    return tree.hexdigest()


def resolve_jars(entries, caches):
    by_size = defaultdict(dict)
    needed = {entry["bytes"] for entry in entries}
    for directory in caches:
        if not directory.is_dir():
            raise ValueError(f"Missing cache: {directory}")
        for file in directory.rglob("*.jar"):
            size = file.stat().st_size
            if size in needed:
                by_size[size][file.resolve()] = file.name
    seen = {}
    resolved = {}
    for entry in entries:
        options = by_size[entry["bytes"]]
        for path in sorted(options, key=lambda p: options[p] != entry["filename"]):
            if path not in seen:
                seen[path] = digest(path)
            if seen[path] == entry["sha256"]:
                resolved[entry["filename"]] = path
                break
        else:
            raise ValueError(f"Missing {entry['filename']} with digest {entry['sha256']} ({entry['source']})")
    return resolved


def extract_overrides(archive, instance):
    with ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if len(parts) < 3 or parts[0] != "overrides" or parts[1] not in OVERRIDES or ".." in parts:
                raise ValueError(f"Unexpected overrides path: {info.filename}")
            target = instance.joinpath(*parts[1:]).resolve()
            if not target.is_relative_to(instance):
                raise ValueError(f"Escaped overrides directory: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lock", type=Path, default=HERE / "candidate.json")
    p.add_argument("--cache", type=Path, action="append", required=True, help="JAR directory, repeat as needed")
    p.add_argument("--overrides", type=Path, required=True, help="pinned overrides.pinned.zip")
    p.add_argument("--output", type=Path, required=True, help="new directory for server/ and client/")
    args = p.parse_args()
    lock = json.loads(args.lock.read_bytes())
    output = args.output.resolve()
    if output.exists():
        p.error("Choose a new output directory")
    if (digest(args.overrides) != lock["overrides"]["sha256"] and
            overrides_digest(args.overrides) != lock["overrides"].get("treeSha256")):
        p.error("Overrides archive differs from lock")
    files = lock["files"]
    if (len({entry["filename"].casefold() for entry in files}) != len(files)
            or any(Path(entry["filename"]).name != entry["filename"] or entry["side"] not in
                   {"both", "server", "client"} for entry in files)):
        p.error("Invalid or duplicate filename/side in lock")
    resolved = resolve_jars(files, args.cache)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        staged = Path(tmp).resolve() / "candidate"
        for side in ("server", "client"):
            instance = staged / side
            (instance / "mods").mkdir(parents=True)
            extract_overrides(args.overrides, instance)
            for entry in files:
                if entry["side"] in (side, "both"):
                    filename = entry["filename"]
                    shutil.copyfile(resolved[filename], instance / "mods" / filename)
        staged.rename(output)
    print(f"Assembled server and client at {output}")


if __name__ == "__main__":
    main()
