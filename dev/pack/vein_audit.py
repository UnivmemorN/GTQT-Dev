"""Verify two stopped server snapshots of VisualOres' overworld index (nbtlib==2.0.4)."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import nbtlib


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_index(path):
    data = nbtlib.load(path)["data"]
    rows = set()
    for grid, entries in data.items():
        grid_x, grid_z = map(int, grid.split(","))
        for vein in entries:
            name = str(vein["name"])
            x, z = int(vein["x"]), int(vein["z"])
            row = (grid_x, grid_z, x, z, name)
            if (x // 48, z // 48) != (grid_x, grid_z) or not name or row in rows:
                raise ValueError(f"Invalid or duplicate vein in {path}: {row}")
            rows.add(row)
    if not rows:
        raise ValueError(f"No overworld veins persisted in {path}")
    encoded = json.dumps(sorted(rows), separators=(",", ":")).encode("utf-8")
    counts = Counter(row[4] for row in rows)
    return rows, {
        "sha256": digest(path),
        "sortedRecordsSha256": hashlib.sha256(encoded).hexdigest(),
        "bytes": path.stat().st_size,
        "grids": len(data),
        "veins": len(rows),
        "deposits": dict(sorted(counts.items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="completed verify.py result directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observations", type=Path,
                        help="older run's independently captured create.dat, reload.dat and comparison.json")
    args = parser.parse_args()
    result_path = args.run / "result.json"
    result = json.loads(result_path.read_bytes())
    if not result["fullVerification"] or not result["originalsRestored"] or "failure" in result:
        raise ValueError("Whole-pack verification did not pass")
    phases = result["phases"]
    if [phase["phase"] for phase in phases] != ["create", "reload"] or phases[0]["world"] != phases[1]["world"]:
        raise ValueError("Expected one world created and reloaded by two server JVMs")
    report = {"run": args.run.name, "resultSha256": digest(result_path),
              "worldStorage": "data/visualores.dat", "phases": {}}
    observations = None
    if args.observations:
        observations = json.loads((args.observations / "comparison.json").read_bytes())
        if observations["run"] != args.run.name:
            raise ValueError("External observations are from a different run")
    indexes = []
    for phase in phases:
        key = phase["phase"]
        checkpoint = args.run / ("saved-" + key)
        if digest(checkpoint / "level.dat") != phase["levelSha256"]:
            raise ValueError(f"{key} level.dat does not match its verifier receipt")
        path = checkpoint / "visualores.dat"
        if not path.is_file() and observations:
            path = args.observations / (key + ".dat")
            receipt = observations["phases"][key]
            if digest(path) != receipt["sha256"] or receipt["levelSha256"] != phase["levelSha256"]:
                raise ValueError(f"{key} external observation does not match the shutdown snapshot")
        rows, stats = read_index(path)
        indexes.append(rows)
        report["phases"][key] = {"levelSha256": phase["levelSha256"], **stats}
    created, reloaded = indexes
    missing = created - reloaded
    if missing:
        raise ValueError(f"{len(missing)} veins lost across restart, including {min(missing)}")
    report["preserved"] = len(created)
    report["additional"] = len(reloaded - created)
    report["sample"] = [
        {"grid": [gx, gz], "x": x, "z": z, "name": name}
        for gx, gz, x, z, name in sorted(created)[:5]
    ]
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
