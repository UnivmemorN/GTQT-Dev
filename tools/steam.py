"""Run the pinned SteamTech baseline build or isolated Forge server check."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def git(checkout, *args):
    return subprocess.run(
        ["git", "-C", str(checkout), *args], check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def check_checkout(directory, expected):
    if not directory.is_dir() or not (directory / ".git").exists():
        raise ValueError(f"Missing Git checkout: {directory}")
    head = git(directory, "rev-parse", "HEAD")
    if head != expected:
        raise ValueError(f"{directory}: expected {expected}, found {head}")
    changes = git(directory, "status", "--porcelain", "--untracked-files=normal")
    if changes:
        raise ValueError(f"Use a clean checkout for this profile: {directory}\n{changes}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    build = sub.add_parser("build", help="build the baseline via its upstream Gradle wrapper")
    verify = sub.add_parser("verify", help="boot the built baseline and check the saved world")
    for command in (build, verify):
        command.add_argument(
            "--checkout", type=Path, default=ROOT / "work" / "src" / "steamRunner",
            help="prepared SteamTech runner checkout (default: work/src/steamRunner)",
        )
    build.add_argument("--offline", action="store_true", help="use Gradle offline mode with a populated cache")
    verify.add_argument(
        "--server-dir", type=Path, required=True,
        help="isolated server directory with an already accepted eula.txt; the runner reads that file",
    )
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    try:
        lock = json.loads((ROOT / "workspace.lock.json").read_text(encoding="utf-8"))
        check_checkout(checkout, lock["repositories"]["steamRunner"]["rev"])
        baseline = checkout / ".legacy-dev" / "baseline"
        baseline_rev = lock["profiles"]["steamBaseline"]["sourceRev"]
        if baseline.exists() or args.action == "verify":
            check_checkout(baseline, baseline_rev)
        script = checkout / "dev" / "legacy" / (args.action + ".py")
        command = [sys.executable, "-B", str(script)]
        if args.action == "build":
            if args.offline:
                command.append("--offline")
            command.append("build")
        else:
            server = args.server_dir.resolve(strict=True)
            if not server.is_dir():
                raise ValueError(f"Expected a dedicated test server directory: {server}")
            command.extend(["--server-dir", str(server)])
        result = subprocess.run(command, cwd=checkout)
        if result.returncode == 0 and args.action == "build":
            check_checkout(baseline, baseline_rev)
        return result.returncode
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
