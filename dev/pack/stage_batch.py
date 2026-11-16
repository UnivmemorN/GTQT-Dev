"""Stage a fresh two-sided pack from the accepted organization baseline and selected additions."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

from assemble import digest, extract_overrides, overrides_digest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from workspace import check_mods, safe_name, unique_object, validate


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object)


def stage(args):
    lock = read(ROOT / "workspace.lock.json")
    validate(lock)
    profile = lock["defaultProfile"]
    runtime = lock["profiles"][profile]["runtime"]
    base = args.base.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"Choose a new output directory: {output}")
    for side, entries in runtime.items():
        check_mods(base / side / "mods", entries)
    by_side = {side: {name: (base / side / "mods" / name, sha) for name, sha in entries.items()}
               for side, entries in runtime.items()}
    if bool(args.overrides) != bool(args.overrides_tree):
        raise ValueError("Specify both --overrides and --overrides-tree")
    if args.overrides and overrides_digest(args.overrides) != args.overrides_tree:
        raise ValueError("Upstream overrides paths or contents differ from the selected file tree")

    for rows in args.rows:
        for row in read(rows):
            name = row["filename"]
            if not safe_name(name) or not name.lower().endswith(".jar") or row["side"] not in ("server", "client", "both"):
                raise ValueError(f"Invalid mod entry: {name}")
            options = [cache / name for cache in args.cache]
            if "fileID" in row and safe_name(str(row["fileID"])):
                options.extend(cache / str(row["fileID"]) / name for cache in args.cache)
            if "src" in row:
                options.insert(0, Path(row["src"]))
            source = next((p for p in options if p.is_file() and digest(p) == row["sha256"]), None)
            if not source:
                raise ValueError(f"No source matching {name} ({row['sha256']})")
            for side, entries in by_side.items():
                if row["side"] in (side, "both"):
                    if any(n.casefold() == name.casefold() or sha == row["sha256"] for n, (_, sha) in entries.items()):
                        raise ValueError(f"{side}: addition duplicates a selected JAR: {name}")
                    entries[name] = source, row["sha256"]

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".stage-") as temp:
        staged = Path(temp).resolve() / "batch"
        expected = {}
        for side, entries in by_side.items():
            instance = staged / side
            mods = instance / "mods"
            mods.mkdir(parents=True)
            if args.overrides:
                extract_overrides(args.overrides, instance)
            for name, (source, _) in entries.items():
                shutil.copyfile(source, mods / name)
            expected[side] = {name: sha for name, (_, sha) in sorted(entries.items())}
            check_mods(mods, expected[side])
        (staged / "runtime-lock.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8", newline="\n")
        staged.rename(output)
    return {side: len(entries) for side, entries in by_side.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="original verified server/ and client/ mod sets")
    parser.add_argument("--rows", type=Path, action="append", default=[], help="cumulative JSON additions, repeatable")
    parser.add_argument("--cache", type=Path, action="append", default=[],
                        help="flat JAR directory or cache organized by file ID, repeatable")
    parser.add_argument("--overrides", type=Path, help="upstream git archive containing overrides/")
    parser.add_argument("--overrides-tree", help="expected SHA-256 over sorted upstream paths and file contents")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(stage(args)))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
