"""Checkout verification and isolated server staging shared by the legacy profiles."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess


def check_head(path, *allowed):
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    if actual not in allowed:
        raise SystemExit(f"Expected one of {allowed} at {path}, found {actual}")
    tracked = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no",
                                       "--ignore-submodules=none"], cwd=path, text=True).strip()
    if tracked:
        raise SystemExit(f"Tracked files differ from {actual} in {path}:\n{tracked}")
    return actual


def server_directory(explicit, runtime, inputs):
    selected = explicit
    if selected is None:
        settings = runtime / "settings.json"
        if settings.is_file():
            selected = json.loads(settings.read_text(encoding="utf-8-sig")).get("server_dir")
    if not selected:
        raise SystemExit("Supply --server-dir for an isolated, idle server directory with an accepted eula.txt")
    directory = Path(selected).resolve(strict=True)
    if not directory.is_dir():
        raise SystemExit(f"Expected a server directory at {directory}")
    for item in inputs:
        path = item.resolve()
        if directory == path or directory in path.parents or path in directory.parents:
            raise SystemExit(f"Keep the server directory {directory} separate from {path}")
    return directory


def original_state(directory, lock):
    # The upstream cross-process lock is kept between runs, including in a fresh directory.
    names = sorted(item.name for item in directory.iterdir() if item.name != lock)
    hashes = {}
    for name in ("eula.txt", "whitelist.json", "server.properties"):
        path = directory / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"entries": names, "sha256": hashes}


def verify_restored(directory, lock, before, record):
    after = original_state(directory, lock)
    record["serverBefore"] = before
    record["serverAfter"] = after
    record["originalsRestored"] = before == after


def check_idle_port(properties):
    fields = {}
    for line in properties.read_text(encoding="latin-1").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip()
    port = int(fields.get("server-port", 25565))
    address = fields.get("server-ip") or None
    # Probing the configured listener also handles wildcard and IPv6 servers.
    for family, type_, protocol, _, bind_to in socket.getaddrinfo(address, port, type=socket.SOCK_STREAM,
                                                                  flags=socket.AI_PASSIVE):
        with socket.socket(family, type_, protocol) as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(bind_to)


@contextmanager
def isolated_server(directory, results, record, smoke):
    before = original_state(directory, smoke.TEST_LOCK)
    eula = directory / "eula.txt"
    if (not eula.is_file() or eula.is_symlink() or
            "eula=true" not in eula.read_text(encoding="utf-8-sig").splitlines()):
        raise ValueError(f"The selected directory needs an already accepted eula.txt: {directory}")
    if before["entries"] == ["eula.txt"]:
        # This is the original helper's portable path; it creates and leaves its lock file.
        try:
            with smoke.staged_directory(directory, results):
                yield
        finally:
            verify_restored(directory, smoke.TEST_LOCK, before, record)
        return

    # The upstream populated-directory branch only recognizes its author's named fixture.
    # Preserve the same exclusive lock and same-volume backup for any explicitly selected
    # idle server. Worlds and configuration stay in that backup until the JVM has exited.
    with smoke.server_lock(directory):
        before = original_state(directory, smoke.TEST_LOCK)
        backup = directory / smoke.BACKUP
        props = directory / "server.properties"
        if backup.exists():
            raise RuntimeError(f"Interrupted run. Restore the original test server from {backup} before retrying")
        if not props.is_file():
            raise ValueError("Use an EULA-only directory or an existing dedicated test server with server.properties")
        check_idle_port(props)
        archive = results / "server-files"
        archive.mkdir()
        backup.mkdir()
        originals = set(before["entries"]) - {"eula.txt"}
        try:
            for name in sorted(originals):
                (directory / name).rename(backup / name)
            yield
        finally:
            for item in directory.iterdir():
                if item == backup or item.name in {smoke.TEST_LOCK, "eula.txt"}:
                    continue
                if item.name not in originals or (backup / item.name).exists():
                    shutil.move(str(item), str(archive / item.name))
            for original in backup.iterdir():
                original.rename(directory / original.name)
            backup.rmdir()
            verify_restored(directory, smoke.TEST_LOCK, before, record)
