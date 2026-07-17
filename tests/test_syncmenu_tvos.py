"""tvOS main-menu DATA durability reconcile (1.0.65) - the syncMenu helper.

Executes the REAL `_SYNC_MENU_ACTION` payload (tools/skin_transforms.py) via
exec() against the two-layer, tvOS-accurate fake (fake_kodi_storage.py). This is
NOT a substring check on the source: the payload runs against a key store AND a
real POSIX tree, so every claim below is proven against the same storage model
Kodi's TVOSFile.cpp implements.

THE BUG (v1.0.64, script.skinshortcuts 2.0.3, Apple TV): a Customize Main Menu
edit is written by skinshortcuts with ElementTree.write (plain POSIX) and read
back with ETree.parse (plain POSIX) behind an `xbmcvfs.exists` guard. On tvOS a
*.xml under userdata is ALSO shadowed by an NSUserDefaults key: xbmcvfs
read/exists are key-first, xbmcvfs write is key-only, and the POSIX copy lives in
a purgeable cache. So (1) a stale key shadows the fresh POSIX edit for xbmcvfs
consumers, and (2) after a cache purge only the key survives and skinshortcuts (a
POSIX reader) reverts to the shipped default. syncMenu reconciles the two layers
in the direction that preserves the user's freshest edit (POSIX wins when
present), re-materializes POSIX from the durable key when the cache was purged,
NEVER deletes a copy, and is a strict no-op on Fire TV / desktop and on a
consistent box with no pending edit.

THE LINCHPIN, made explicit: the fake's `exists()` is key-first with a POSIX
fallback WHEN NO KEY EXISTS (fake_kodi_storage.py:147-152). That is why a fresh
keyless POSIX write passes the datafunctions.py:178 guard, and why the state
"key absent, POSIX present" is undetectable by content compare. It IS detectable
structurally: listdir merges POSIX and key names WITHOUT dedupe
(TVOSDirectory.cpp), so a name listed once alongside a present POSIX file has no
key. syncMenu registers the key from that signal - flag-free, because the old
gate on skinshortcuts-reloadmainmenu raced the builder's read-and-clear of the
same property and could skip the durability push forever.

THE ORDERING CONTRACT (the 4-agent panel's race findings, 2026-07-17): Home's
tvOS onload no longer fires a buildxml in parallel with syncMenu. It SETS
t7b_chainbuild (later loads only, synchronous builtin) before the spawn; syncMenu
fires the ONE build strictly after reconciling, and sets
skinshortcuts-reloadmainmenu whenever it changed the bytes skinshortcuts reads
(the POSIX layer) so the build can never be skipped by the hash - 2.0.3's
writexml drops hash entries for files absent at build time, making a
re-materialized DATA invisible to the hash check.
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skin_transforms  # noqa: E402  (tools/ is on sys.path via conftest.py)
from fake_kodi_storage import FakeKodiStorage, make_modules  # noqa: E402

_SKINDIR = "skin.estuary7"
_SS = "script.skinshortcuts"
_MENU = "%s-mainmenu.DATA.xml" % _SKINDIR  # skinshortcuts' user-menu naming
_SP = "special://profile/addon_data/script.skinshortcuts/"

_FRESH = (
    b"<shortcuts>\n    <shortcut><label>Owner edit</label></shortcut>\n</shortcuts>\n"
)
_STALE = (
    b"<shortcuts>\n    <shortcut><label>Old default</label></shortcut>\n</shortcuts>\n"
)
_CORRUPT = b"<shortcuts><shortcut>truncated..."


# ---------------------------------------------------------------------------
# Harness: run the REAL elif payload as a standalone script.
# ---------------------------------------------------------------------------


class _Window:
    """Minimal xbmcgui.Window(10000): a property bag on window 10000."""

    _store: dict = {}

    def __init__(self, _id):
        self._id = _id

    def getProperty(self, key):
        return self._store.get(key, "")

    def setProperty(self, key, value):
        self._store[key] = value

    def clearProperty(self, key):
        self._store.pop(key, None)


class _XbmcGui:
    Window = _Window


def _run_syncmenu(store, pending=False, chainbuild=False, sabotage_vfs_file=False):
    """Execute the real syncMenu payload once. Returns the xbmc module (for its
    log/builtin trace)."""
    import xml.etree.ElementTree as ET

    xbmc_mod, xbmcvfs_mod, _ = make_modules(store)
    store.log.clear()  # scope the returned trace to THIS invocation
    _Window._store = {}
    if pending:
        # Legacy flag: the payload must IGNORE it now (flag-free reconcile).
        _Window._store["skinshortcuts-reloadmainmenu"] = "True"
    if chainbuild:
        _Window._store["t7b_chainbuild"] = "1"
    if sabotage_vfs_file:
        # Crash the reconcile mid-flight: the chained build must still fire.
        class _Boom:
            def __init__(self, *a, **k):
                raise RuntimeError("sabotaged xbmcvfs.File")

        xbmcvfs_mod.File = _Boom

    # The payload is an `elif` fragment indented for the helpers.py dispatch.
    # Dedent it and turn the leading `elif` into `if` so it stands alone.
    src = textwrap.dedent(skin_transforms._SYNC_MENU_ACTION)
    src = src.replace(
        "elif sys.argv[1] == 'syncMenu':", "if sys.argv[1] == 'syncMenu':", 1
    )
    fake_sys = type("S", (), {"argv": ["helpers.py", "syncMenu"]})()
    ns = {
        "xbmc": xbmc_mod,
        "xbmcvfs": xbmcvfs_mod,
        "xbmcgui": _XbmcGui,
        "os": os,
        "ET": ET,
        "sys": fake_sys,
    }
    exec(compile(src, "<_SYNC_MENU_ACTION>", "exec"), ns)
    return store.log


def _make_box(tmp_path, platform="tvos"):
    home = tmp_path / "home"
    ssdir = home / "userdata" / "addon_data" / _SS
    ssdir.mkdir(parents=True)
    store = FakeKodiStorage(home, platform=platform)
    return store, ssdir


def _key_for(store, name=_MENU):
    return store._key(store.translate(_SP + name))


def _set_posix(ssdir, data, name=_MENU):
    (ssdir / name).write_bytes(data)


def _set_key(store, data, name=_MENU):
    store.keys[_key_for(store, name)] = bytes(data)


def _get_key(store, name=_MENU):
    return store.keys.get(_key_for(store, name))


def _built(log):
    return any(
        "builtin: RunScript(script.skinshortcuts,type=buildxml" in m for m in log
    )


# ---------------------------------------------------------------------------
# (1) Stale shadow: a leftover key holds the old menu while POSIX has the fresh
#     edit. syncMenu pushes POSIX onto the key so every xbmcvfs consumer sees the
#     edit - and leaves the user's fresh POSIX copy exactly as it was.
# ---------------------------------------------------------------------------


def test_stale_shadow_deshadowed_posix_preserved(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _STALE)

    xbmc_mod = _run_syncmenu(store, pending=False)

    assert _get_key(store) == _FRESH, (
        "durable key must be de-shadowed onto the fresh edit"
    )
    assert (ssdir / _MENU).read_bytes() == _FRESH, (
        "POSIX (the freshest copy) must be untouched"
    )
    # A key-layer-only change does not alter what skinshortcuts READS, so no
    # build fires without the chainbuild marker and no rebuild flag is set -
    # the on-screen menu already matches POSIX.
    assert not _built(xbmc_mod)
    assert _Window._store.get("skinshortcuts-reloadmainmenu") != "True"
    # byte-preserving: exact bytes, no ETree re-serialize / whitespace churn.
    assert _get_key(store) == (ssdir / _MENU).read_bytes()


# ---------------------------------------------------------------------------
# (2) Fresh edit, no prior key: content compares equal (reads fall back to
#     POSIX), so bytes cannot detect it - yet the durable key MUST be registered
#     or the edit dies at the next cache purge. Detected structurally via the
#     listdir dup-count, FLAG-FREE: the old skinshortcuts-reloadmainmenu gate
#     raced the builder's read-and-clear of the same property (panel finding
#     2026-07-17) and could skip this push forever.
# ---------------------------------------------------------------------------


def test_keyless_posix_registers_durable_key_flag_free(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    assert _get_key(store) is None  # virgin: no durable key yet

    xbmc_mod = _run_syncmenu(store, pending=False)  # NO flag - must still push

    assert _get_key(store) == _FRESH, (
        "a keyless POSIX menu must register the durable NSUserDefaults key so "
        "the edit survives a purge of the POSIX cache - without any pending flag"
    )
    assert (ssdir / _MENU).read_bytes() == _FRESH
    # Registration is not a visible content change: no rebuild is forced.
    assert not _built(xbmc_mod)
    assert _Window._store.get("skinshortcuts-reloadmainmenu") != "True"


def test_legacy_pending_flag_is_ignored_and_survives(tmp_path):
    """The payload must not consume or depend on skinshortcuts-reloadmainmenu:
    that property belongs to the builder (shouldwerun reads-and-clears it)."""
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _FRESH)  # consistent box

    xbmc_mod = _run_syncmenu(store, pending=True)

    assert _Window._store.get("skinshortcuts-reloadmainmenu") == "True", (
        "a pending edit flag must be left for the builder, never consumed here"
    )
    assert not _built(xbmc_mod)


# ---------------------------------------------------------------------------
# (3) Cache purge: POSIX gone, only the durable key survives. syncMenu
#     re-materializes POSIX so skinshortcuts (a POSIX reader) can load it, keeps
#     the key, and sets the rebuild flag: 2.0.3's writexml drops hash entries
#     for files absent at build time, so a re-materialized DATA is INVISIBLE to
#     the hash check - without the flag the next build would no-op and the menu
#     would stay on the shipped default forever (panel finding F1/B4c).
# ---------------------------------------------------------------------------


def test_cache_purge_rematerializes_posix_and_flags_rebuild(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_key(store, _FRESH)  # POSIX absent (purged), durable key holds the edit
    assert not (ssdir / _MENU).exists()

    xbmc_mod = _run_syncmenu(store, pending=False)

    assert (ssdir / _MENU).read_bytes() == _FRESH, (
        "POSIX must be rebuilt from the durable key"
    )
    assert _get_key(store) == _FRESH, "the durable key must be preserved, never deleted"
    assert _Window._store.get("skinshortcuts-reloadmainmenu") == "True", (
        "a POSIX-layer change must set the rebuild flag: the hash cannot see a "
        "re-materialized file, the flag is the only reliable trigger"
    )
    # First-boot load (no chainbuild marker): no build fires here - the deferred
    # AlarmClock build owns it and will honor the flag. Later loads chain it.
    assert not _built(xbmc_mod)


# ---------------------------------------------------------------------------
# (3b) The ordered build chain. Home's tvOS onload sets t7b_chainbuild (later
#      loads only) BEFORE spawning syncMenu and fires no parallel buildxml;
#      syncMenu fires the ONE build strictly after the reconcile. The marker is
#      consumed, the stuck-guard is cleared, and the fire happens even when the
#      reconcile crashes (a crash must not strand the upstream-parity build).
# ---------------------------------------------------------------------------


def test_chainbuild_fires_one_build_after_reconcile(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_key(store, _FRESH)  # purge case: reconcile has real work to do
    _Window._store = {}

    log = _run_syncmenu(store, chainbuild=True)

    builds = [
        m for m in log if "builtin: RunScript(script.skinshortcuts,type=buildxml" in m
    ]
    assert len(builds) == 1, "exactly ONE chained build"
    # Ordering: the reconcile's own log line precedes the build fire.
    sync_idx = next(i for i, m in enumerate(log) if "syncMenu key=" in m)
    build_idx = next(i for i, m in enumerate(log) if "type=buildxml" in m)
    assert sync_idx < build_idx, "the build must fire AFTER the reconcile"
    assert "t7b_chainbuild" not in _Window._store, "marker must be consumed"
    assert "skinshortcuts-isrunning" not in _Window._store
    assert _Window._store.get("skinshortcuts-reloadmainmenu") == "True"


def test_chainbuild_fires_even_on_consistent_box(tmp_path):
    """Upstream parity: the later-load build always runs (shouldwerun decides
    whether anything is actually rebuilt), even when the reconcile no-ops."""
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _FRESH)

    log = _run_syncmenu(store, chainbuild=True)

    assert _built(log)
    assert "t7b_chainbuild" not in _Window._store


def test_chainbuild_fires_despite_reconcile_crash(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _STALE)  # forces the reconcile into the sabotaged File call

    log = _run_syncmenu(store, chainbuild=True, sabotage_vfs_file=True)

    assert any("syncMenu failed" in m for m in log), "crash must be logged"
    assert _built(log), "a reconcile crash must not strand the chained build"
    assert "t7b_chainbuild" not in _Window._store


def test_no_build_without_chainbuild_marker(tmp_path):
    """First load per boot (or a customizeMenu-spawned reconcile): no marker,
    no build - the AlarmClock (or the wrapper) owns that build."""
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _STALE)

    log = _run_syncmenu(store, chainbuild=False)

    assert not _built(log)


# ---------------------------------------------------------------------------
# (4) Strict no-op when the two layers already agree and no edit is pending -
#     the overwhelmingly common Home load. Nothing is written, nothing rebuilds.
# ---------------------------------------------------------------------------


def test_noop_when_layers_agree(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _FRESH)

    xbmc_mod = _run_syncmenu(store, pending=False)

    assert _get_key(store) == _FRESH
    assert (ssdir / _MENU).read_bytes() == _FRESH
    assert not _built(xbmc_mod), "a consistent box must not rebuild"
    assert not any("syncMenu" in m for m in xbmc_mod), (
        "a strict no-op must not even log"
    )


def test_idempotent_second_run(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _STALE)

    _run_syncmenu(store, pending=False)  # heals
    xbmc_mod = _run_syncmenu(store, pending=False)  # now consistent

    assert not _built(xbmc_mod), "second run over a healed box must be a no-op"


# ---------------------------------------------------------------------------
# (5) Fire TV / desktop: strict no-op. The tvOS gate must fully short-circuit.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", ("android",))
def test_strict_noop_off_tvos(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform=platform)
    _set_posix(ssdir, _FRESH)
    keys_before = dict(store.keys)

    xbmc_mod = _run_syncmenu(store, pending=True)  # even with a pending flag

    assert store.keys == keys_before, "no key writes off tvOS"
    assert (ssdir / _MENU).read_bytes() == _FRESH, "POSIX untouched off tvOS"
    assert not _built(xbmc_mod), "no rebuild off tvOS"


# ---------------------------------------------------------------------------
# (6) Corruption is never propagated, and the only good copy is never destroyed:
#     a truncated/unparseable POSIX edit must NOT overwrite a good durable key,
#     even with a pending flag.
# ---------------------------------------------------------------------------


def test_corrupt_posix_never_overwrites_good_key(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _CORRUPT)
    _set_key(store, _STALE)  # a good, parseable prior menu

    xbmc_mod = _run_syncmenu(store, pending=True)

    assert _get_key(store) == _STALE, (
        "a corrupt POSIX edit must not clobber the good durable key"
    )
    assert (ssdir / _MENU).read_bytes() == _CORRUPT, (
        "syncMenu must not touch POSIX in this case"
    )
    assert not _built(xbmc_mod)


def test_corrupt_key_never_overwrites_posix_on_purge(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_key(store, _CORRUPT)  # durable key is garbage, POSIX purged
    assert not (ssdir / _MENU).exists()

    xbmc_mod = _run_syncmenu(store, pending=False)

    assert not (ssdir / _MENU).exists(), (
        "a corrupt key must not be written back to POSIX"
    )
    assert not _built(xbmc_mod)


# ---------------------------------------------------------------------------
# (7) Never deletes: after any heal, BOTH layers still exist.
# ---------------------------------------------------------------------------


def test_never_deletes_either_layer(tmp_path):
    store, ssdir = _make_box(tmp_path)
    _set_posix(ssdir, _FRESH)
    _set_key(store, _STALE)

    _run_syncmenu(store, pending=False)

    assert (ssdir / _MENU).exists(), "POSIX copy must survive"
    assert _get_key(store) is not None, "durable key must survive"


def test_source_has_no_delete_calls():
    """Belt-and-suspenders: the payload never deletes a menu copy."""
    src = skin_transforms._SYNC_MENU_ACTION
    assert "os.remove" not in src
    assert "xbmcvfs.delete" not in src
