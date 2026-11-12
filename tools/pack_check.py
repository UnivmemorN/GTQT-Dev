"""Find duplicate mod IDs declared in a Forge 1.12.2 mods directory."""

import argparse
from collections import defaultdict
import json
from lzma import LZMAError
from pathlib import Path
import re
import sys
from zipfile import BadZipFile, ZipFile
import zlib


def ids_in_metadata(data):
    entries = data.get("modList") if isinstance(data, dict) else data
    if not isinstance(entries, list) or not entries:
        return set(), ["unrecognized or empty mod list"]
    ids, warnings = set(), []
    for number, entry in enumerate(entries, 1):
        mod_id = entry.get("modid") if isinstance(entry, dict) else None
        # Some legacy descriptors use uppercase or a pipe. Keep the original ID.
        if not isinstance(mod_id, str) or not re.fullmatch(r"[A-Za-z0-9_.|-]+", mod_id):
            warnings.append(f"entry {number} has no literal modid")
        elif mod_id in ids:
            warnings.append(f"entry {number} repeats {mod_id} within this descriptor")
        else:
            ids.add(mod_id)
    return ids, warnings


def inspect_jar(path):
    with ZipFile(path) as jar:
        try:
            raw = jar.read("mcmod.info")
        except KeyError:
            return set(), ["no root mcmod.info"]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return set(), [f"nonstandard mcmod.info encoding: {error}"]
    try:
        metadata = json.loads(text)
    except json.JSONDecodeError as error:
        # Some published 1.12 descriptors contain literal newlines in description strings.
        try:
            metadata = json.loads(text, strict=False)
        except json.JSONDecodeError:
            return set(), [f"nonstandard mcmod.info: {error}"]
        ids, warnings = ids_in_metadata(metadata)
        warnings.append("nonstandard mcmod.info: accepted literal control characters in strings")
        return ids, warnings
    return ids_in_metadata(metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mods", type=Path, help="instance mods directory, including its 1.12.2 subdirectory")
    mods = parser.parse_args().mods
    try:
        directories = [mods]
        version_dir = mods / "1.12.2"
        if version_dir.is_dir():
            directories.append(version_dir)
        jars = sorted(
            path for directory in directories for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".jar"
        )
    except OSError as error:
        parser.exit(2, f"Cannot scan mods directory: {error}\n")
    if not jars:
        parser.exit(2, f"No JAR files in {mods} or {version_dir}\n")

    owners = defaultdict(list)
    partial = failures = 0
    for path in jars:
        name = path.relative_to(mods).as_posix()
        try:
            ids, warnings = inspect_jar(path)
        except (BadZipFile, OSError, RuntimeError, EOFError, zlib.error, LZMAError) as error:
            failures += 1
            print(f"UNREADABLE {name}: {error}")
            continue
        if warnings:
            partial += 1
            print(f"INCOMPLETE {name}: {'; '.join(warnings)}")
        for mod_id in ids:
            owners[mod_id].append(name)

    duplicates = {mod_id: files for mod_id, files in owners.items() if len(files) > 1}
    for mod_id in sorted(duplicates):
        print(f"DUPLICATE {mod_id}: {', '.join(duplicates[mod_id])}")
    print(f"Scanned {len(jars)} JARs: {len(duplicates)} duplicate declared IDs, "
          f"{partial} incomplete descriptors, {failures} unreadable JARs.")
    if duplicates:
        return 1
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
