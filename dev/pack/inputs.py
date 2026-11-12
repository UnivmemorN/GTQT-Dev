"""Content receipts for the locked Forge pack, including configurations, scripts, quests and resources."""
import hashlib
from pathlib import Path

OVERRIDE_DIRS = ("config", "groovy", "resources", "scripts")
CLIENT_PROBE = "gtqt-pack-client-acceptance.jar"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree(files):
    """Match assemble.overrides_digest: slash-separated, case-sensitive UTF-8 paths and raw SHA-256 bytes."""
    result = hashlib.sha256()
    for path in sorted(files):
        result.update(path.encode("utf-8") + b"\0")
        result.update(bytes.fromhex(files[path]))
    return {"files": len(files), "sha256": result.hexdigest()}


def immutable(path):
    return (path.startswith(("overrides/scripts/", "overrides/groovy/", "overrides/resources/",
                             "overrides/config/ftbquests/", "overrides/config/betterquesting/"))
            or path == "overrides/config/imported_quests.nbt")


def inspect(instance):
    instance = Path(instance)
    mods = instance / "mods"
    if not mods.is_dir():
        raise ValueError(f"Missing mods at {instance}")
    files = {"overrides/" + p.relative_to(instance).as_posix(): digest(p)
             for name in OVERRIDE_DIRS for p in (instance / name).rglob("*") if p.is_file()}
    # Hash every file, including any non-JAR or nested additions a Forge launch could load.
    mod_files = {p.relative_to(mods).as_posix(): digest(p) for p in mods.rglob("*") if p.is_file()}
    return {"overrides": tree(files), "scriptsQuestsResources": tree({k: v for k, v in files.items() if immutable(k)}),
            "mods": mod_files}


def expected_mods(lock, side):
    return {r["filename"]: r["sha256"] for r in lock["files"] if r["side"] in ("both", side)}


def locked(snapshot, lock, side):
    target = {"files": lock["overrides"]["files"], "sha256": lock["overrides"]["treeSha256"]}
    if snapshot["overrides"] != target:
        raise ValueError(f"{side} config, scripts, quests or resources differ from the candidate lock: {snapshot['overrides']}")
    if snapshot["mods"] != expected_mods(lock, side):
        raise ValueError(f"{side} production mod files differ from the candidate lock")


def after_launch(snapshot, source, side, probe=False):
    if snapshot["scriptsQuestsResources"] != source["scriptsQuestsResources"]:
        raise ValueError(f"{side} scripts, quest definitions or resources differ from the input tree")
    mods = dict(snapshot["mods"])
    for name, sha in source["mods"].items():
        if mods.pop(name, None) != sha:
            raise ValueError(f"{side} staged production file changed or disappeared: {name}")
    probe_hash = mods.pop(CLIENT_PROBE, None) if probe else None
    if probe and not probe_hash:
        raise ValueError("Missing client probe in actual game staging")
    if any("/" not in name for name in mods):
        raise ValueError(f"{side} has unexpected top-level production files: {sorted(mods)}")
    return {"overridesAfterLaunch": snapshot["overrides"], "scriptsQuestsResources": snapshot["scriptsQuestsResources"],
            "productionMods": tree(source["mods"]), "generatedFilesUnderMods": mods,
            **({"clientProbeSha256": probe_hash} if probe else {})}


def summary(snapshot):
    return {"overrides": snapshot["overrides"], "scriptsQuestsResources": snapshot["scriptsQuestsResources"],
            "productionMods": tree(snapshot["mods"])}
