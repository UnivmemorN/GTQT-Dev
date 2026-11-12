"""Summarize a verified create/reload run, its actual staged inputs and independent script diagnostics."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

import inputs
from inputs import digest

PLAYER = "Pack19Probe"
PLAYER_ID = str(UUID(bytes=hashlib.md5(("OfflinePlayer:" + PLAYER).encode()).digest(), version=3))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def script_diagnostics(archive, server_log):
    files = {"craftTweaker": archive / "crafttweaker.log", "groovy": archive / "logs/groovy_server.log"}
    ct = files["craftTweaker"].read_text(encoding="utf-8", errors="replace").splitlines()
    errors = [line for line in ct if "[ERROR]" in line]
    by_file = Counter()
    failed = set()
    for line in errors:
        match = re.search(r"(?:\[ERROR\] |\]: )([^{}:\[\]]+\.zs)(?:[:}])", line, re.I)
        if match:
            name = match.group(1).strip().replace("\\", "/")
            by_file[name] += 1
            if "Error executing" in line:
                failed.add(name)
    groovy = files["groovy"].read_text(encoding="utf-8", errors="replace")
    conflicts = Counter(re.findall(r"Recipe duplicate or conflict found in RecipeMap (\w+)", groovy))
    rejected = Counter(re.findall(r"\[GregTech\]: Invalid recipe for recipe map (\w+)", server_log))
    return {"craftTweakerErrorLines": len(errors), "craftTweakerErrorsByFile": dict(sorted(by_file.items())),
            "craftTweakerUnattributedErrorLines": len(errors) - sum(by_file.values()),
            "craftTweakerExecutionFailures": sorted(failed), "groovyRecipeConflicts": sum(conflicts.values()),
            "groovyRecipeConflictsByMap": dict(sorted(conflicts.items())),
            "gregTechRejectedRecipesByMap": dict(sorted(rejected.items())),
            "groovyErrorLines": sum("[SERVER/ERROR]" in line for line in groovy.splitlines()),
            "logSha256": {name: digest(path) for name, path in files.items()}}


def check_published_lock(published, tested, lock):
    tested_bytes = tested.read_bytes()
    tested_sha = hashlib.sha256(tested_bytes).hexdigest()
    if tested_bytes == published.read_bytes():
        return tested_sha, []
    original = json.loads(tested_bytes)
    reconstruction = copy.deepcopy(lock)
    differences = []
    require(len(original["files"]) == len(reconstruction["files"]), "Candidate file count changed after acceptance")
    for old, new in zip(original["files"], reconstruction["files"]):
        require(old["filename"] == new["filename"], "Candidate file order or name changed after acceptance")
        if old["url"] != new["url"]:
            mirror = old["source"] == old["url"] and new["source"] == new["url"]
            differences.append({"filename": old["filename"], "urlAtTest": old["url"], "urlPublished": new["url"],
                                "mirrorSourceUrl": mirror})
            if mirror:
                new["source"] = old["source"]
            new["url"] = old["url"]
    require(differences and original == reconstruction, "Only corrected URLs and exact source URL mirrors are permitted")
    # Publishing uses UTF-8, two-space JSON and a trailing LF; ensure the advertised differences
    # reproduce the byte-for-byte preflight lock, including original key and list ordering.
    canonical = (json.dumps(reconstruction, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    require(canonical == tested_bytes, "URL corrections do not reproduce the exact tested lock bytes")
    return tested_sha, differences


def input_evidence(tested_sha, receipt, lock):
    sources = {}
    preflight = receipt["beforeLaunch"]
    require(preflight["lockSha256"] == tested_sha, "Pre-launch lock digest differs from the tested lock")
    for side in ("server", "client"):
        summary = preflight[side + "Source"]
        sources[side] = dict(summary, mods=inputs.expected_mods(lock, side))
        inputs.locked(sources[side], lock, side)
        require(summary == inputs.summary(sources[side]), "Invalid pre-launch source receipt")
    require(preflight["serverCreateStaging"] == preflight["serverSource"], "Server preflight mismatch")
    reload_stage = preflight["serverReloadStaging"]
    require(reload_stage["productionMods"] == preflight["serverSource"]["productionMods"] and
            reload_stage["scriptsQuestsResources"] == preflight["serverSource"]["scriptsQuestsResources"],
            "Server restart staging differs from the locked immutable content")
    return sources, {"method": "pre-launch", **preflight}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--tested-lock", type=Path, help="original preflight lock when publication corrects download URLs only")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    base = args.result.resolve(strict=True)
    receipt, lock = read(base / "result.json"), read(args.lock)
    require(receipt.get("fullVerification") and receipt.get("originalsRestored") and not receipt.get("failure"),
            "Requires a successful two-phase run and original server restoration")
    tested_sha, corrections = check_published_lock(args.lock, args.tested_lock or args.lock, lock)
    sources, evidence = input_evidence(tested_sha, receipt, lock)
    for side in ("server", "client"):
        require(inputs.expected_mods(lock, side) == receipt[side + "Files"], f"{side} JARs differ from lock")
    require([r["phase"] for r in receipt["phases"]] == ["create", "reload"], "Missing original or restarted JVM")
    first, second = receipt["phases"]
    require(first["mods"] == second["mods"] and first["world"] == second["world"], "Saved world changed")
    phases = []
    markers = []
    for row in receipt["phases"]:
        phase = row["phase"]
        client_dir = base / ("client-" + phase)
        client_receipt = read(client_dir / "client-result.json")
        server_log = base / (phase + ".log")
        require(digest(server_log) == row["logSha256"] and row["client"] == client_receipt, f"{phase} receipts differ")
        log = server_log.read_text(encoding="utf-8", errors="replace")
        game = base / "worlds" / row["world"]["name"]
        port = re.findall(r"Starting Minecraft server on 127\.0\.0\.1:(\d+)", log)
        require(len(port) == 1 and len(re.findall(r"Pack19Probe\[/127\.0\.0\.1:\d+\] logged in with entity id", log)) == 1
                and "Unloading dimension 0" in log, f"{phase}: missing unique loopback login or shutdown")
        saved_marker = re.search(r"\[Server thread/INFO\] \[minecraft/DedicatedServer\]: Saved the world\s*$", log, re.M)
        stopping = log.find("[minecraft/DedicatedServer]: Stopping the server")
        require(saved_marker is not None and saved_marker.start() < stopping, f"{phase}: save-all did not finish before stop")
        rule = "Game rule pack19Receipt has been updated to " if phase == "create" else "pack19Receipt = "
        matched = re.findall(rule + r"([0-9a-f]{32})", log)
        require(len(matched) == 1, f"{phase}: missing world gamerule")
        markers.append(matched[0])
        console = (client_dir / "client-console.log").read_text(encoding="utf-8", errors="replace")
        expected = rf"GTQT_PACK_CLIENT_OK phase={phase} user={PLAYER} uuid={PLAYER_ID} port={port[0]} dimension=-?\d+ chunk=-?\d+,-?\d+"
        require(re.findall(expected, console) == [client_receipt["join"]] and client_receipt["exitCode"] == 0 and
                client_receipt["phase"] == phase and row["player"] == client_receipt["username"] == PLAYER and
                row["playerId"] == PLAYER_ID, f"{phase}: invalid real remote client receipt")
        loaded = re.findall(r"Forge Mod Loader has successfully loaded (\d+) mods", console)
        wood = re.findall(r"GTQT_BOP_WOOD_OK species=\d+ registeredStacks=\d+", console)
        require(len(loaded) == 1 and wood == ["GTQT_BOP_WOOD_OK species=16 registeredStacks=128"],
                "Expected complete client startup and verification of all 128 wood stacks")
        require(client_receipt["beforeProbeAndJvm"] == inputs.summary(sources["client"]),
                f"{phase}: actual client staging differs from lock")
        require(client_receipt["cleanMenuExit"] and console.count("GTQT_PACK_CLIENT_EXIT_OK unloadedWorld=true menuTicks=5") == 1
                and not list((client_dir / "client-game/crash-reports").glob("crash-*-client.txt")),
                f"{phase}: unsuccessful client teardown")
        missing = Counter(re.findall(r"Registry ([^:\r\n]+): Found a missing id from the world ([^\s]+)", console))
        missing_ids = {registry + " " + key: count for (registry, key), count in sorted(missing.items())}
        require(client_receipt["missingWorldIds"] == missing_ids, f"{phase}: missing mapping receipt differs")
        actual = inputs.after_launch(inputs.inspect(client_dir / "client-game"), sources["client"], "client", probe=True)
        saved = base / ("saved-" + phase)
        player_file = PLAYER_ID + ".dat"
        require(digest(saved / "level.dat") == row["levelSha256"] and digest(saved / player_file) == row["playerSha256"],
                f"{phase}: saved snapshot differs")
        if phase == "reload":
            require(digest(game / "level.dat") == row["levelSha256"] and
                    digest(game / "playerdata" / player_file) == row["playerSha256"], "World archive differs from final save")
        phases.append({k: row[k] for k in ("phase", "world", "levelSha256", "logSha256", "player", "playerId",
                                          "playerSha256", "client")} |
                      {"saveAllCompletedBeforeStop": True, "clientLogSha256": digest(client_dir / "client-console.log"), "clientLoadedWithProbe": int(loaded[0]),
                       "bopWood": wood[0], "missingWorldIds": missing_ids, "actualClientAfterLaunch": actual,
                       "diagnostics": script_diagnostics(saved, log)})
    require(markers[0] == markers[1], "Server did not read back the create phase gamerule")
    evidence["serverAfterReload"] = inputs.after_launch(inputs.inspect(base / "server-files"), sources["server"], "server")
    clients = [phase["actualClientAfterLaunch"] for phase in phases]
    require(clients[0]["clientProbeSha256"] == clients[1]["clientProbeSha256"], "Client probe changed between boots")
    generated = [{name: sha for name, sha in stage["generatedFilesUnderMods"].items() if name.lower().endswith(".jar")}
                 for stage in (evidence["serverReloadStaging"], evidence["serverAfterReload"], *clients)]
    require(generated[0] == generated[1] and generated[2] == generated[3],
            "Auto-extracted libraries changed between boots")
    for name in generated[0].keys() & generated[2].keys():
        require(generated[0][name] == generated[2][name], f"Auto-extracted client and server libraries disagree: {name}")
    data = {"forge": receipt["forge"], "world": first["world"], "dedicatedServerRestartAndClientRejoin": True,
            "serverRestored": True, "inputs": evidence, "resultSha256": digest(base / "result.json"),
            "lockSha256": digest(args.lock), "testedLockSha256": tested_sha, "sourceUrlCorrections": corrections,
            "serverJars": len(receipt["serverFiles"]), "clientJars": len(receipt["clientFiles"]),
            "savedModIds": first["mods"], "phases": phases, "lastBootDiagnostics": phases[-1]["diagnostics"]}
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
