"""Inspect the GTQT workspace lock, fetch a pinned artifact, or check out a pinned repository."""

import argparse
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, f"Duplicate JSON field: {key}")
        obj[key] = value
    return obj


def safe_name(value):
    return (isinstance(value, str) and bool(value) and value not in {".", ".."}
            and not value.endswith((" ", ".")) and not re.search(r'[<>:"/\\|?*\x00-\x1f]', value)
            and not re.fullmatch(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³]",
                                 value.partition(".")[0].strip().upper()))


def is_hash(value, length):
    return isinstance(value, str) and len(value) == length and re.fullmatch(r"[0-9a-f]+", value)


def check_local_reference(profile_key, field, name):
    require(isinstance(name, str) and bool(name) and not PureWindowsPath(name).anchor
            and not Path(name).is_absolute(), f"{profile_key}: expected a relative {field} path")
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT) and path.is_file(), f"{profile_key}: missing or external {field}: {name}")


def validate(lock):
    require(isinstance(lock, dict), "Expected a JSON object")
    require(type(lock.get("format")) is int and lock["format"] == 1, "Expected workspace lock format 1")
    require(lock.get("minecraft") == "1.12.2", "Expected a Minecraft 1.12.2 workspace lock")
    for group in ("repositories", "artifacts", "profiles"):
        entries = lock.get(group)
        require(isinstance(entries, dict), f"Missing lock section: {group}")
        require(len({key.casefold() for key in entries}) == len(entries), f"Case collision in {group}")
        for key, entry in entries.items():
            require(safe_name(key) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", key), f"Invalid {group} key: {key}")
            require(isinstance(entry, dict), f"{group}.{key} must be an object")

    for key, entry in lock["repositories"].items():
        repo = entry.get("repo")
        require(isinstance(repo, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repo)
                and repo.split("/")[1] not in {".", ".."}, f"{key}: expected a GitHub owner/repo")
        require(is_hash(entry.get("rev"), 40), f"{key}: expected a full commit SHA")
        extras = entry.get("extraRevs", [])
        require(isinstance(extras, list) and all(is_hash(rev, 40) for rev in extras),
                f"{key}: invalid extraRevs")
        require(len(set([entry["rev"], *extras])) == len(extras) + 1, f"{key}: repeated commit")

    for key, entry in lock["artifacts"].items():
        url = entry.get("url")
        require(isinstance(url, str) and not re.search(r"\s", url), f"{key}: invalid artifact URL")
        parsed = urlsplit(url)
        require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
                f"{key}: expected an HTTPS download URL")
        require(safe_name(entry.get("filename")), f"{key}: invalid artifact filename")
        require(type(entry.get("size")) is int and entry["size"] > 0, f"{key}: expected a positive file size")
        require(is_hash(entry.get("sha256"), 64), f"{key}: expected a SHA-256 digest")

    for key, profile in lock["profiles"].items():
        for group in ("repositories", "artifacts"):
            refs = profile.get(group)
            require(isinstance(refs, list) and all(isinstance(ref, str) for ref in refs),
                    f"{key}: expected a {group} list")
            require(len(refs) == len(set(refs)), f"{key}: repeated {group} reference")
            for ref in refs:
                require(ref in lock[group], f"{key}: unknown {group} reference {ref}")
        for field in ("build", "server"):
            require(isinstance(profile.get(field), str) and profile[field].strip(), f"{key}: missing {field} status")
        check_local_reference(key, "guide", profile.get("guide"))
        if "evidence" in profile:
            check_local_reference(key, "evidence", profile["evidence"])
        if "sourceRev" in profile:
            repos = [lock["repositories"][ref] for ref in profile["repositories"]]
            require(is_hash(profile["sourceRev"], 40) and any(profile["sourceRev"] in
                    [repo["rev"], *repo.get("extraRevs", [])] for repo in repos),
                    f"{key}: sourceRev must be pinned by a referenced repository")


def workspace_path(*parts):
    path = ROOT / "work" / Path(*parts)
    require(path.resolve() == path and not path.is_symlink(), f"Refusing redirected workspace path: {path}")
    return path


def git(directory, *args):
    result = subprocess.run(["git", "-C", str(directory), *args], stdout=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", check=True)
    return result.stdout.strip()


def verify_checkout(path, repo, rev):
    require(path.is_dir() and (path / ".git").exists(), f"Existing destination is not a Git checkout: {path}")
    require(git(path, "rev-parse", "HEAD") == rev, f"{path}: HEAD differs from locked revision {rev}")
    origin = git(path, "config", "--get", "remote.origin.url").lower().removesuffix(".git")
    require(origin in {f"https://github.com/{repo}", f"git@github.com:{repo}", f"ssh://git@github.com/{repo}"},
            f"{path}: origin differs from github.com/{repo}")
    require(not git(path, "status", "--porcelain", "--untracked-files=normal"), f"Existing checkout is dirty: {path}")


def pin_ref(rev):
    return f"{rev}:refs/gtqt-dev/pins/{rev}"


def checkout(key, entry):
    target = workspace_path("src", key)
    repo, rev = entry["repo"], entry["rev"]
    extras = entry.get("extraRevs", [])
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent, prefix=".checkout-") as temp:
            stage = Path(temp) / "repo"
            stage.mkdir()
            git(stage, "init", "--quiet")
            git(stage, "remote", "add", "origin", f"https://github.com/{repo}.git")
            git(stage, "fetch", "--no-tags", "--depth=1", "origin", rev, *map(pin_ref, extras))
            git(stage, "checkout", "--quiet", "--detach", rev)
            verify_checkout(stage, repo.lower(), rev)
            try:
                if not target.exists():
                    stage.rename(target)
            except OSError:
                if not target.exists():
                    raise
                # A concurrent checkout may already have published this revision.
    verify_checkout(target, repo.lower(), rev)
    missing = [extra for extra in extras if subprocess.run(
        ["git", "-C", str(target), "cat-file", "-e", extra + "^{commit}"], stderr=subprocess.DEVNULL,
    ).returncode != 0]
    if missing:
        git(target, "fetch", "--no-tags", "--depth=1", "origin", *map(pin_ref, missing))
    print(target)


def matches(path, entry):
    if not path.is_file() or path.stat().st_size != entry["size"]:
        return False
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest() == entry["sha256"]


def fetch(key, entry, offline):
    target = workspace_path("artifacts", key, entry["filename"])
    if not matches(target, entry):
        require(not offline, f"No verified cached artifact at {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        request = Request(entry["url"], headers={"User-Agent": "GTQT-Dev", "Accept-Encoding": "identity"})
        staged = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as file:
                staged = Path(file.name)
                with urlopen(request, timeout=60) as remote:
                    require(remote.status == 200 and urlsplit(remote.geturl()).scheme == "https",
                            f"{key}: unexpected download response")
                    size = 0
                    for block in iter(lambda: remote.read(1024 * 1024), b""):
                        size += len(block)
                        require(size <= entry["size"], f"{key}: download exceeds locked size")
                        file.write(block)
            require(matches(staged, entry), f"{key}: downloaded size or SHA-256 differs from lock")
            try:
                os.replace(staged, target)
            except OSError:
                if not matches(target, entry):
                    raise
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    print(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list profiles and build/server status")
    commands.add_parser("check", help="validate the lock, referenced files and existing artifact cache offline")
    commands.add_parser("checkout", help="obtain a clean checkout at a locked commit").add_argument("key")
    download = commands.add_parser("fetch", help="obtain a size- and SHA-256-verified artifact")
    download.add_argument("key")
    download.add_argument("--offline", action="store_true", help="verify an already cached file")
    args = parser.parse_args()
    try:
        lock = json.loads((ROOT / "workspace.lock.json").read_text(encoding="utf-8-sig"),
                          object_pairs_hook=unique_object)
        validate(lock)
        if args.command == "list":
            for key, profile in lock["profiles"].items():
                print(f"{key}: build={profile['build']}  server={profile['server']}  {profile['guide']}")
        elif args.command == "check":
            cached = 0
            for key, entry in lock["artifacts"].items():
                path = workspace_path("artifacts", key, entry["filename"])
                if path.exists():
                    require(matches(path, entry), f"{key}: cached artifact differs from lock at {path}")
                    cached += 1
            print(f"Valid lock: {len(lock['profiles'])} profiles, {len(lock['repositories'])} repositories, "
                  f"{len(lock['artifacts'])} artifacts ({cached} cached and verified).")
        elif args.command == "checkout":
            require(args.key in lock["repositories"], f"Unknown repository: {args.key}")
            checkout(args.key, lock["repositories"][args.key])
        else:
            require(args.key in lock["artifacts"], f"Unknown artifact: {args.key}")
            fetch(args.key, lock["artifacts"][args.key], args.offline)
    except (OSError, HTTPException, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
