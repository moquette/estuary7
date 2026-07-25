#!/usr/bin/env python3
"""Catch source that changed at an ALREADY-RELEASED version.

The hole this closes, found by the 2026-07-25 pipeline audit: the publish job is
idempotent by tag. If the tag for the current version already exists it prints
"nothing to publish" and exits 0. So a real fix committed without bumping
`our_version` in skin_build.lock builds, tests green, publishes nothing, reaches
zero boxes, and NOTHING GOES RED ANYWHERE.

This repo is the more exposed of the two, because unlike the add-on it has NO
separate release script to fail closed: CI on push to main is the only path that
ever cuts a release, so this warning is the only thing standing between a
forgotten bump and a fix that silently never ships.

    tools/check_unreleased_changes.py            warn, always exit 0
    tools/check_unreleased_changes.py --strict   exit 1 if there are unreleased changes

The signal is `git diff <tag> HEAD -- <build inputs>`: no network, no build, and
it asks about source rather than build output. Only paths that actually shape the
zip count, so a docs or CI edit at a released version is correctly ignored.

Exit codes: 0 ok (or warning), 1 unreleased changes under --strict, 2 the check
could not run (which is never treated as a pass).
"""

import argparse
import json
import os
import subprocess
import sys

# Only what build_skin.py actually reads into the zip: the upstream pin and our
# version (skin_build.lock), the transform code (tools/), and the overlaid art
# and resources (assets/). docs/, tests/ and CLAUDE.md cannot change the artifact.
SOURCE_PATHS = ("skin_build.lock", "tools", "assets")


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args, cwd=None):
    """Run git, returning (exit_code, stdout). Never raises on a non-zero exit."""
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root(),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip()


def read_version(lock_path=None):
    """our_version out of skin_build.lock, the single source of truth for the skin."""
    path = lock_path or os.path.join(repo_root(), "skin_build.lock")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("our_version")


def tag_exists(tag):
    code, out = git("tag", "--list", tag)
    return code == 0 and out != ""


def changed_since(tag, paths=SOURCE_PATHS):
    """Files under `paths` that differ between `tag` and HEAD."""
    code, out = git("diff", "--name-only", tag, "HEAD", "--", *paths)
    if code != 0:
        return None
    return [line for line in out.splitlines() if line.strip()]


def classify(version, has_tag, changed):
    """Pure decision, so the states are testable without a git repo.

    Returns (state, message) where state is one of: unreleased, clean, dirty.
    """
    tag = "v" + version
    if not has_tag:
        return (
            "unreleased",
            f"{version} has no {tag} tag yet: the next push to main publishes it.",
        )
    if not changed:
        return (
            "clean",
            f"{version} is released and no build input changed since {tag}.",
        )
    listed = "\n".join(f"      {f}" for f in changed[:20])
    more = f"\n      ... and {len(changed) - 20} more" if len(changed) > 20 else ""
    return (
        "dirty",
        f"{len(changed)} build input(s) changed since {tag}, but our_version is\n"
        f"    still {version}. Kodi upgrades by version number only, so these\n"
        f"    changes reach NO box until skin_build.lock is bumped, and the publish\n"
        f"    job will report success while doing nothing.\n{listed}{more}",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on unreleased changes instead of warning",
    )
    args = parser.parse_args(argv)

    version = read_version()
    if not version:
        print(
            "check-unreleased: FATAL: no our_version in skin_build.lock",
            file=sys.stderr,
        )
        return 2

    has_tag = tag_exists("v" + version)
    changed = changed_since("v" + version) if has_tag else []
    if changed is None:
        # The tag exists but is not reachable, usually a shallow clone. Refuse to
        # call that a pass: an unverifiable gate is not a green one.
        print(
            f"check-unreleased: FATAL: cannot diff against v{version}.\n"
            "    Fetch tags and full history (actions/checkout needs fetch-depth: 0).",
            file=sys.stderr,
        )
        return 2

    state, message = classify(version, has_tag, changed)
    if state == "dirty":
        label = "FAIL" if args.strict else "WARNING"
        print(f"check-unreleased: {label}: {message}")
        return 1 if args.strict else 0

    print(f"check-unreleased: OK: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
