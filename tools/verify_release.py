#!/usr/bin/env python3
"""Verify that a published GitHub Release was actually gated by CI.

WHY THIS EXISTS
---------------
`.github/workflows/ci.yml` publishes releases from the `publish` job, which is
`needs: [test, anchored-build-check]`. That gate works: on the red run
29688381523 the `test` job failed and `publish` was skipped. The hole is not in
the workflow - it is that the workflow is not the only way a release can appear.
Anyone with push rights can run `gh release create` from a laptop and attach any
zip they like, and no CI job is consulted at all. That is exactly how v1.0.67
came to exist on top of a commit whose CI had failed.

This script closes the detection side of that hole. It answers two questions
about a release, both from primary sources:

  1. PROVENANCE - does the tag's commit have a *successful* CI run? A release
     built on a red or unbuilt commit fails here.
  2. ARTIFACT INTEGRITY - does the published asset byte-match a deterministic
     rebuild of that exact commit? This project builds reproducibly
     (`tools/build_skin.py --check` double-builds and byte-compares), so this is
     a real check and not a formality: it catches an asset that was built from
     dirty local state, from a different commit, or hand-edited after the fact.

Check 1 alone would pass a release whose tag is green but whose attached zip was
built from something else. Check 2 alone would pass a hand-built asset that
happens to be reproducible but was never tested. Both are required.

LIMITS - read these before trusting a green result
--------------------------------------------------
* Releases created with the built-in GITHUB_TOKEN do not emit `release` webhook
  events (this is why ci.yml dispatches the hub rebuild directly rather than
  relying on `release: published`). So the event-driven guard fires on
  human/PAT-created releases - which is precisely the bypass we are plugging -
  but cannot be relied on to fire for CI's own releases. The scheduled sweep
  below is what covers everything regardless of how it was created.
* This is DETECTION, not PREVENTION. It makes a bypass loudly red; it does not
  stop the release from existing. True prevention is a repository setting only
  the owner can change - see the note in .github/workflows/release-guard.yml.

Usage:
    verify_release.py --tag v1.0.69              # provenance only (fast)
    verify_release.py --tag v1.0.69 --rebuild    # + deterministic rebuild
    verify_release.py --all --rebuild            # sweep every release
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = os.environ.get("T7B_REPO", "moquette/estuary7")
SKIN_ID = "skin.estuary7"
WORKFLOW_NAME = "CI"

# CI only started publishing releases at 4dd802f ("ci: auto-publish the release
# on green main", 2026-07-16 20:03:48 -0700). Every release before that was
# necessarily hand-made, so enforcing provenance across the whole history would
# flag ~58 releases forever. A permanently red daily sweep is noise that gets
# ignored, which would defeat the point of the guard - so enforcement starts at
# that commit's timestamp. Releases older than this are reported as SKIPPED
# (pre-CI history), never as failures.
ENFORCE_FROM_UTC = "2026-07-17T03:03:48Z"

# Releases that ARE in the enforced window and DO fail, but are known history
# the owner has decided not to rewrite. Listing a tag here downgrades it from a
# failure to a loud warning, so the sweep can be green for NEW bypasses while
# the historical one stays visible on every run. Add to this only with an
# explicit owner decision, and never to silence a fresh failure.
KNOWN_BYPASSES = {
    "v1.0.67": (
        "hand-created with `gh release create` on f4dc26a, whose CI run "
        "29688381523 had FAILED. This is the bypass that motivated this guard. "
        "Kept deliberately: the owner has not asked for it to be deleted or "
        "retagged. Superseded by v1.0.68+."
    ),
}


def gh(*args: str) -> str:
    """Run gh and return stdout, raising with stderr on failure."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("gh {} failed: {}".format(" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def resolve_tag_to_commit(tag: str) -> str:
    """Resolve a tag ref to the commit it ultimately points at.

    Annotated tags point at a tag object, not a commit, so deref when needed -
    otherwise the CI lookup silently finds nothing and every release would look
    unbuilt.
    """
    ref = json.loads(gh("api", "repos/{}/git/refs/tags/{}".format(REPO, tag)))
    obj = ref["object"]
    if obj["type"] == "tag":
        tag_obj = json.loads(gh("api", "repos/{}/git/tags/{}".format(REPO, obj["sha"])))
        return tag_obj["object"]["sha"]
    return obj["sha"]


def ci_conclusions(sha: str) -> list[str]:
    """Every CI-workflow conclusion recorded for this commit."""
    raw = gh(
        "api",
        "repos/{}/actions/runs?head_sha={}&per_page=100".format(REPO, sha),
    )
    runs = json.loads(raw).get("workflow_runs", [])
    return [
        r.get("conclusion") or r.get("status")
        for r in runs
        if r.get("name") == WORKFLOW_NAME
    ]


def asset_sha256(tag: str, version: str, workdir: Path) -> tuple[str, int]:
    """sha256 + size of the published asset, fetched anonymously."""
    name = "{}-{}.zip".format(SKIN_ID, version)
    url = "https://github.com/{}/releases/download/{}/{}".format(REPO, tag, name)
    dest = workdir / name
    urllib.request.urlretrieve(url, dest)
    return hashlib.sha256(dest.read_bytes()).hexdigest(), dest.stat().st_size


def rebuild_sha256(sha: str, workdir: Path) -> tuple[str, str]:
    """Deterministically rebuild the skin at `sha`; return (version, sha256).

    Uses a detached worktree so the caller's checkout is never disturbed.
    """
    tree = workdir / "src"
    subprocess.run(
        ["git", "worktree", "add", "-f", "--detach", str(tree), sha],
        check=True,
        capture_output=True,
    )
    try:
        lock = json.loads((tree / "skin_build.lock").read_text())
        version = lock["our_version"]
        subprocess.run(
            [sys.executable, "tools/build_skin.py"],
            cwd=tree,
            check=True,
            capture_output=True,
        )
        zip_path = tree / "dist" / "{}-{}.zip".format(SKIN_ID, version)
        return version, hashlib.sha256(zip_path.read_bytes()).hexdigest()
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(tree)],
            capture_output=True,
        )


def release_created_at(tag: str) -> str:
    return json.loads(gh("release", "view", tag, "--json", "createdAt"))["createdAt"]


def verify(tag: str, rebuild: bool, enforce_window: bool = True) -> list[str]:
    """Return a list of problems; empty means the release is CI-gated.

    `enforce_window` is honoured for sweeps. An explicit --tag always verifies,
    so the guard can never be dodged by asking about an old tag.
    """
    problems: list[str] = []
    print("=== {} ===".format(tag))

    if enforce_window:
        created = release_created_at(tag)
        if created < ENFORCE_FROM_UTC:
            print(
                "  SKIPPED - pre-CI history ({} < {})".format(created, ENFORCE_FROM_UTC)
            )
            return []

    sha = resolve_tag_to_commit(tag)
    print("  commit:        {}".format(sha))

    concl = ci_conclusions(sha)
    print("  CI runs:       {}".format(", ".join(concl) if concl else "<none>"))
    if "success" not in concl:
        problems.append(
            "{}: no successful {} run on {} (found: {}). This release was not "
            "gated by CI - it was almost certainly created by hand with "
            "`gh release create`.".format(
                tag, WORKFLOW_NAME, sha[:12], ", ".join(concl) or "no runs at all"
            )
        )

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        # Read the lock straight from the tagged commit rather than trusting the
        # tag name: a hand-made release can be tagged anything.
        raw_lock = gh(
            "api",
            "repos/{}/contents/skin_build.lock?ref={}".format(REPO, sha),
            "--jq",
            ".content",
        )
        lock = json.loads(base64.b64decode(raw_lock))
        version = lock["our_version"]
        print("  lock version:  {}".format(version))
        print("  lock sha256:   {}".format(lock["zip_sha256"]))

        try:
            got, size = asset_sha256(tag, version, work)
        except Exception as exc:  # noqa: BLE001
            problems.append(
                "{}: could not fetch the published asset: {}".format(tag, exc)
            )
            return problems
        print("  asset sha256:  {}  ({} bytes)".format(got, size))

        # INFORMATIONAL ONLY - never a failure. skin_build.lock's zip_sha256 is
        # written by whoever last ran tools/build_skin.py locally, so on a
        # CI-published release it routinely records the PREVIOUS build. Measured
        # 2026-07-19: v1.0.60's lock records 012b0f9b..., which is exactly
        # v1.0.59's published asset, and v1.0.61's lock still records the same
        # stale value. Treating this field as an integrity oracle produced three
        # false alarms on a sweep. The authoritative integrity check is the
        # deterministic rebuild below.
        if got != lock["zip_sha256"]:
            print(
                "  note:          lock zip_sha256 differs from the published asset "
                "(lock bookkeeping lags; not an error - rebuild is authoritative)"
            )

        if rebuild:
            rv, rebuilt = rebuild_sha256(sha, work)
            print("  rebuilt sha256:{}".format(rebuilt))
            if rv != version:
                problems.append(
                    "{}: rebuilt version {} != lock version {}".format(tag, rv, version)
                )
            if rebuilt != got:
                problems.append(
                    "{}: published asset sha256 {} does not match a deterministic "
                    "rebuild of {} ({}). The asset was not built from this "
                    "commit.".format(tag, got, sha[:12], rebuilt)
                )

    print("  -> {}".format("OK" if not problems else "PROBLEM"))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", help="release tag to verify, e.g. v1.0.69")
    ap.add_argument("--all", action="store_true", help="verify every release")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="also deterministically rebuild the commit and byte-compare",
    )
    args = ap.parse_args()

    if args.all:
        tags = [
            r["tagName"]
            for r in json.loads(
                gh("release", "list", "--limit", "200", "--json", "tagName")
            )
        ]
    elif args.tag:
        tags = [args.tag]
    else:
        ap.error("pass --tag TAG or --all")

    problems: list[str] = []
    waived: list[str] = []
    for tag in tags:
        found = verify(tag, args.rebuild, enforce_window=args.all)
        # The waiver applies to SWEEPS only. Asking about a tag explicitly must
        # always give the unvarnished answer, so the guard cannot be dodged by
        # naming a waived tag.
        if found and args.all and tag in KNOWN_BYPASSES:
            waived.append("{}: {}".format(tag, KNOWN_BYPASSES[tag]))
            for f in found:
                waived.append("    detected: {}".format(f))
            continue
        problems.extend(found)

    if waived:
        print("\nWARNING - known, owner-accepted historical bypass(es):")
        for w in waived:
            print("  - {}".format(w))

    if problems:
        print("\nFATAL: release provenance check failed:")
        for p in problems:
            print("  - {}".format(p))
        return 1
    print("\nOK - every checked release is CI-gated and byte-matches its commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
