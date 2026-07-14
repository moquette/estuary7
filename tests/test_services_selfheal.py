"""Adversarial regression coverage for the skinshortcuts self-heal boot seed.

Executes the REAL _SERVICES_SEED payload (tools/skin_transforms.py, ~1306-1535)
via exec() against a two-layer tvOS-accurate fake (fake_kodi_storage.py) - not
a substring check on the source text. A substring test is what let the "hash
dropped on every boot" bug ship in 1.0.36/1.0.37 in the first place.

The bug: the boot service deleted script.skinshortcuts' <skinid>.hash file on
EVERY boot whenever the owner had ANY menu of their own (`_usermenu` true),
not just when it had actually re-materialized orphaned DATA (`_healed` true).
Dropping the hash forces skinshortcuts to rebuild + ReloadSkin every single
boot, forever, because it just writes a fresh hash which we then delete again
next time. The fix narrows the drop to `if _healed:` only, with a separate
`elif _usermenu:` branch that touches nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skin_transforms  # noqa: E402  (tools/ is on sys.path via conftest.py)
from fake_kodi_storage import FakeKodiStorage, make_modules  # noqa: E402

_SKINDIR = "skin.estuary7"  # matches fake_kodi_storage._Xbmc.getSkinDir()
PLATFORMS = ("tvos", "android")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _exec_seed(modules):
    """Run ONE boot of the real payload against a given (xbmc, xbmcvfs,
    xbmcaddon) module set, and return the exec namespace so tests can inspect
    the payload's own locals (_healed, _usermenu, _needseed, _purged, ...).

    Reusing the SAME `modules` tuple (and therefore the same FakeKodiStorage
    and the same addon-settings dict) across two calls models two boots of
    the SAME box; calling make_modules() again models a different box.
    """
    xbmc_mod, xbmcvfs_mod, xbmcaddon_mod = modules
    code = compile(
        textwrap.dedent(skin_transforms._SERVICES_SEED), "<_SERVICES_SEED>", "exec"
    )
    ns = {
        "xbmc": xbmc_mod,
        "xbmcvfs": xbmcvfs_mod,
        "xbmcaddon": xbmcaddon_mod,
        "os": os,
        "json": json,
        "hashlib": hashlib,
        "ET": ET,
    }
    exec(code, ns)
    return ns


def _make_box(tmp_path, platform):
    """A fresh box: the skinshortcuts addon_data dir, the skin's generated
    includes.xml, and a single-profile profiles.xml.

    profiles.xml is written so the seed path's profile-listing branch always
    takes the ET.parse() route and never falls through to
    xbmc.getInfoLabel('System.ProfileName') - a method the fake intentionally
    does not implement (out of scope per its own docstring: "multiple
    profiles" territory). This keeps every test exercising the REAL payload
    logic instead of a workaround.
    """
    home = tmp_path / "home"
    ssdir = home / "userdata" / "addon_data" / "script.skinshortcuts"
    ssdir.mkdir(parents=True)
    skin_xml = home / "addons" / _SKINDIR / "xml"
    skin_xml.mkdir(parents=True)
    (skin_xml / "script-skinshortcuts-includes.xml").write_text("<includes/>\n")
    (home / "userdata" / "profiles.xml").write_text(
        "<profiles><profile><name>Master user</name>"
        "<directory>special://masterprofile/</directory></profile></profiles>\n"
    )
    store = FakeKodiStorage(home, platform=platform)
    return store, ssdir


def _hash_path(ssdir):
    return ssdir / ("%s.hash" % _SKINDIR)


def _write_owner_menu(ssdir, name="mainmenu.DATA.xml", content="<owner-shortcuts/>\n"):
    (ssdir / name).write_text(content)


def _write_hash(ssdir, entries):
    _hash_path(ssdir).write_text(json.dumps(entries, indent=4))


# ---------------------------------------------------------------------------
# (a) THE REGRESSION TEST - healthy box, owner has a menu, hash present.
#     MUST FAIL against the pre-fix `if _healed or _usermenu:` guard.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_healthy_box_with_owner_menu_hash_survives(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform)
    _write_owner_menu(ssdir)
    _write_hash(ssdir, [["::SKINVER::", "1.0.30"], ["::SCRIPTVER::", "2.0.3"]])
    before = _hash_path(ssdir).read_bytes()

    ns = _exec_seed(make_modules(store))

    assert _hash_path(ssdir).exists(), (
        "the owner's hash was deleted on a healthy boot - this forces "
        "skinshortcuts to rebuild + ReloadSkin every single boot, forever"
    )
    assert _hash_path(ssdir).read_bytes() == before, "hash content was rewritten"
    assert ns["_usermenu"] is True
    assert ns["_healed"] == 0
    assert ns["_needseed"] is False
    assert not any("dropped stale skinshortcuts hash" in m for m in store.log)
    assert not any("seeded skinshortcuts hash" in m for m in store.log)


# ---------------------------------------------------------------------------
# (b) + (c) orphaned box (tvOS-only - Android has no NSUserDefaults key layer,
#     so this state cannot occur there; fake_kodi_storage.listdir() never
#     surfaces keys when platform != "tvos", matching real CTVOSDirectory vs
#     CPosixDirectory dispatch).
# ---------------------------------------------------------------------------


def test_orphaned_box_heals_once_then_hash_survives_next_boot(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    _write_owner_menu(ssdir, "mainmenu.DATA.xml", "<owner-shortcuts/>\n")
    # Stale: built while the owner's DATA was invisible behind the NSUserDefaults key.
    _write_hash(ssdir, [["::SKINVER::", "1.0.30"]])

    # Reproduce the actual incident: vector the owner's file into NSUserDefaults,
    # delete the POSIX copy - the bytes still exist, only the disk copy is gone.
    store.orphan(str(ssdir / "mainmenu.DATA.xml"))
    assert not (ssdir / "mainmenu.DATA.xml").exists()

    modules = make_modules(store)
    ns = _exec_seed(modules)

    # (b) re-materialized to disk, through the API skinshortcuts actually reads with...
    restored = ssdir / "mainmenu.DATA.xml"
    assert restored.exists()
    assert restored.read_bytes() == b"<owner-shortcuts/>\n"
    assert ns["_healed"] == 1
    # ...and the hash dropped exactly once (forces the one rebuild that reads it back).
    assert not _hash_path(ssdir).exists()
    assert any("re-materialized 1 skinshortcuts DATA file" in m for m in store.log)
    assert any("dropped stale skinshortcuts hash" in m for m in store.log)
    # Bonus (not asked for, but real): the SAME boot's purge block cleans up the
    # now-redundant key left behind by the heal (POSIX + key both present after
    # heal writes the file back, without deleting the key) - one boot, fully clean.
    assert ns["_purged"] == 1

    # (c) the boot IMMEDIATELY AFTER: nothing left orphaned or duplicated ->
    # _healed must be 0 -> the hash (written fresh by skinshortcuts' own
    # rebuild, simulated here) must now SURVIVE. Proves this is self-limiting,
    # not a loop.
    _write_hash(ssdir, [["::SKINVER::", "1.0.38"]])
    before2 = _hash_path(ssdir).read_bytes()
    store.log.clear()
    ns2 = _exec_seed(modules)

    assert ns2["_healed"] == 0
    assert ns2["_purged"] == 0
    assert _hash_path(ssdir).exists()
    assert _hash_path(ssdir).read_bytes() == before2
    assert not any("dropped stale skinshortcuts hash" in m for m in store.log)


# ---------------------------------------------------------------------------
# (d) VIRGIN box - no DATA.xml at all. The original first-launch seed path
#     must be unaffected by this fix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_virgin_box_still_seeds_hash(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform)
    # no DATA.xml, no hash: a truly virgin box.

    ns = _exec_seed(make_modules(store))

    assert ns["_usermenu"] is False
    assert ns["_healed"] == 0
    assert ns["_needseed"] is True
    assert _hash_path(ssdir).exists()
    payload = json.loads(_hash_path(ssdir).read_text())
    assert any(e and e[0] == "::SKINVER::" for e in payload)
    assert any("seeded skinshortcuts hash" in m for m in store.log)


# ---------------------------------------------------------------------------
# (e) Skin VERSION BUMP with a custom menu - the owner's hash must survive
#     because OUR payload never inspects ::SKINVER:: on the usermenu path;
#     skinshortcuts' OWN shouldwerun() is what detects the bump and rebuilds
#     from the owner's DATA. That claim is checked against the real vendored
#     source in test_skinshortcuts_skinver_rebuild_reads_owner_data_first.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_skin_version_bump_with_owner_menu_leaves_hash_alone(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform)
    _write_owner_menu(ssdir)
    # A hash written under a PRIOR skin version - the exact state right after
    # a skin upgrade, before skinshortcuts' own shouldwerun() has run again.
    _write_hash(ssdir, [["::SKINVER::", "1.0.30"], ["::SCRIPTVER::", "2.0.3"]])
    before = _hash_path(ssdir).read_bytes()

    ns = _exec_seed(make_modules(store))

    assert _hash_path(ssdir).read_bytes() == before
    assert ns["_usermenu"] is True
    assert ns["_needseed"] is False


_REAL_SKINSHORTCUTS_CANDIDATES = [
    Path.home() / "Library/Application Support/Kodi/addons/script.skinshortcuts",
]


def _find_real_skinshortcuts():
    for base in _REAL_SKINSHORTCUTS_CANDIDATES:
        xf = base / "resources/lib/skinshorcuts/xmlfunctions.py"
        df = base / "resources/lib/skinshorcuts/datafunctions.py"
        if xf.is_file() and df.is_file():
            return xf, df
    return None


def test_skinshortcuts_skinver_rebuild_reads_owner_data_first():
    """Best-effort, local-only source citation for the fix's core claim
    (tools/skin_transforms.py, comment above the `if _healed:` guard): a skin
    version bump does not need our help because skinshortcuts compares
    ::SKINVER:: in ITS OWN hash and rebuilds from the owner's DATA when it
    changes.

    script.skinshortcuts is not vendored in this repo (it is a separate Kodi
    addon, installed at runtime on the fleet), so this is skipped when it
    is not present on the machine running the test - a confirmation aid for
    local development, not a CI portability requirement. It is NOT a
    substitute for the behavioral tests above, which exercise OUR payload
    directly.
    """
    found = _find_real_skinshortcuts()
    if not found:
        pytest.skip("script.skinshortcuts source not vendored on this machine")
    xf_path, df_path = found
    xf = xf_path.read_text(encoding="utf-8")
    df = df_path.read_text(encoding="utf-8")

    # shouldwerun(): a SKINVER mismatch unconditionally returns True (rebuild) -
    # no branch on whether the on-disk DATA belongs to the owner or the
    # shipped default. (xmlfunctions.py Skinshortcuts.shouldwerun)
    marker = 'elif hashed_item == "::SKINVER::":'
    assert marker in xf, (
        "shouldwerun() no longer checks ::SKINVER:: - the fix's core claim "
        "(a skin version bump self-corrects without our help) is now FALSE"
    )
    snippet = xf[xf.index(marker) : xf.index(marker) + 400]
    assert "if skin_version != hashed_value:" in snippet
    assert "return True" in snippet

    # A missing/corrupt hash file (e.g. post-reset) also unconditionally
    # forces a rebuild - so never seeding one is equally safe there.
    assert "if not hashes:" in xf

    # writexml() reads the OWNER's DATA before the skin/shipped-default
    # fallback, so ANY rebuild - version-bump or otherwise - regenerates the
    # owner's actual menu instead of reverting to the shipped default.
    # (datafunctions.py DataFunctions.get_shortcuts)
    assert "paths = [user_shortcuts, skin_shortcuts, default_shortcuts]" in df


# ---------------------------------------------------------------------------
# (f) The PURGE block - a file in BOTH layers (listed twice) drops the key,
#     the POSIX file survives untouched.
# ---------------------------------------------------------------------------


def test_purge_drops_duplicate_key_keeps_posix_file(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    _write_owner_menu(ssdir, "mainmenu.DATA.xml", "<owner-shortcuts/>\n")
    # Simulate "listed twice": inject a key for the SAME name WITHOUT touching
    # the POSIX copy (store.orphan() would delete the POSIX file - that is
    # the opposite state, covered by the heal test above).
    real = store.translate(str(ssdir / "mainmenu.DATA.xml"))
    store.keys[store._key(real)] = b"<owner-shortcuts/>\n"

    _, files = store.listdir(str(ssdir))
    assert files.count("mainmenu.DATA.xml") == 2, (
        "test setup didn't reproduce the double-listing"
    )

    ns = _exec_seed(make_modules(store))

    assert ns["_purged"] == 1
    assert store._key(real) not in store.keys, "the redundant key must be dropped"
    posix_file = ssdir / "mainmenu.DATA.xml"
    assert posix_file.exists(), "the POSIX copy must survive the purge"
    assert posix_file.read_bytes() == b"<owner-shortcuts/>\n"
    _, files2 = store.listdir(str(ssdir))
    assert files2.count("mainmenu.DATA.xml") == 1
