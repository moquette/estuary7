"""The 1.0.36 landmine: a user's customised menu must never be reverted.

WHAT WENT WRONG AT 1.0.36
-------------------------
The fork seeded a skinshortcuts `<skin>.hash` file so that the first launch
would skip the rebuild+ReloadSkin. skinshortcuts' `shouldwerun()` reads that
hash, saw it matching, and concluded "menu is up to date" - while being
completely blind to the owner's own edits in
`addon_data/script.skinshortcuts/*.DATA.xml`. The result was a fleet-wide menu
revert: Home main-menu edits never persisted, surviving neither ReloadSkin nor a
restart, because no rebuild was ever run to turn the edited DATA into the
rendered includes. The seed was removed at 1.0.64.

This is the failure that would actually destroy the owner's setup, and it is
strictly worse than the swap-window defect it was introduced to hide: the swap
window is transient and self-heals, a hash-seeded revert is permanent and
silently discards the user's work.

WHAT THESE TESTS PIN
--------------------
Two independent properties, both read off the SHIPPED artifact rather than the
source, so they hold regardless of how the menu pipeline is refactored:

  1. Nothing that reaches skinshortcuts' hash may ship or be written by us. If a
     hash exists before the first real build, `shouldwerun()` can short-circuit
     on stale state.
  2. A rebuild trigger must survive on the later-load path. `shouldwerun()`
     returning True for an edited menu is worthless if nothing ever calls
     buildxml to act on it - that is the same revert by a different route.

Deliberately NOT asserted here: the 15s AlarmClock. Measured on the bench
2026-07-19 (proof/ALARM-MECHANISM-FINDING.txt), `t7b_firstbuild_done` survives a
ReloadSkin, so only the first Home load of a Kodi process is ever deferred and
the alarm contributes 0s to an upgrade. Pinning it here would freeze an
irrelevant implementation detail and block a legitimate fix.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture(scope="module")
def home_xml(built) -> str:
    return (built.tree / "xml" / "Home.xml").read_text(encoding="utf-8")


def _onloads(home: str) -> list[str]:
    return re.findall(r"<onload[^>]*>.*?</onload>", home, re.S)


def test_no_skinshortcuts_hash_is_shipped(built):
    """No `.hash` may ride along in the packaged skin.

    A shipped hash is the 1.0.36 landmine in its most direct form: it is on disk
    before the owner's first build, so shouldwerun() can report "up to date"
    against menu DATA it has never actually read.
    """
    hashes = [
        p.relative_to(built.tree).as_posix()
        for p in built.tree.rglob("*")
        if p.is_file() and p.suffix == ".hash"
    ]
    assert not hashes, (
        "the built skin ships skinshortcuts hash file(s): {}. This is the 1.0.36 "
        "fleet-wide menu revert - shouldwerun() will report the menu up to date "
        "while blind to the owner's addon_data edits.".format(", ".join(hashes))
    )


def test_nothing_in_the_skin_writes_a_skinshortcuts_hash(built):
    """No shipped python may create or write the skinshortcuts hash.

    Covers the indirect form: not shipping a hash, but having the boot service or
    a helper create one at runtime before the first genuine build.

    CREATING a hash is the landmine. DELETING one is the opposite and must stay
    legal: `scripts/helpers.py` removes the hash in the menu-reset path
    precisely so shouldwerun() returns True and the menu rebuilds. Reading and
    `hashlib` are likewise fine.

    The scan is windowed rather than line-scoped. An earlier line-scoped version
    of this test MISSED a two-line writer (path built on one line, `open(p,'w')`
    on the next) during its own mutation check - a line-scoped rule is not
    sufficient here.
    """
    write_re = re.compile(
        r"open\s*\([^)]*['\"][wa]|\.write\s*\(|json\.dump|write_hashes|shutil\.copy"
    )
    remove_re = re.compile(
        r"os\.remove|os\.unlink|\.unlink\s*\(|xbmcvfs\.delete|shutil\.rmtree"
    )
    offenders: list[str] = []

    for py in built.tree.rglob("*.py"):
        lines = py.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if ".hash" not in line:
                continue
            window = "\n".join(lines[i : i + 7])
            if write_re.search(window) and not remove_re.search(window):
                offenders.append(
                    "{}:{}: {}".format(
                        py.relative_to(built.tree).as_posix(), i + 1, line.strip()
                    )
                )

    assert not offenders, (
        "shipped code appears to CREATE a skinshortcuts hash, which re-arms the "
        "1.0.36 menu revert:\n  " + "\n  ".join(offenders)
    )


def test_a_rebuild_trigger_survives_on_the_later_load_path(home_xml):
    """Home must still invoke buildxml on a load that is not the first.

    `shouldwerun()` returns True when the menu has been edited
    (`skinshortcuts-reloadmainmenu`) or when the DATA hash mismatches - but that
    only reverts nothing if buildxml is actually invoked to rebuild. Removing the
    later-load trigger would strand every edit exactly like a seeded hash does.
    """
    onloads = _onloads(home_xml)
    assert onloads, "no <onload> handlers found in the built Home.xml"

    builders = [o for o in onloads if "script.skinshortcuts" in o and "buildxml" in o]
    assert builders, (
        "the built Home.xml invokes buildxml nowhere. Nothing can turn an edited "
        "menu into the rendered includes, so every customisation is stranded."
    )

    # At least one trigger must be reachable on a load where the first-build
    # marker is ALREADY set - i.e. not gated on the marker being empty.
    later = [
        b
        for b in builders
        if "String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))" not in b
        or "!String.IsEmpty" in b
    ]
    assert later, (
        "every buildxml trigger in Home.xml is gated on the FIRST load only "
        "(t7b_firstbuild_done empty). After that marker is set - which survives a "
        "ReloadSkin - an edited menu would never rebuild."
    )
