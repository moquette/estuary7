"""reconcileMenu coverage: the tvOS main-menu PERSISTENCE fix.

Executes the REAL _RECONCILE_MENU_ACTION payload (tools/skin_transforms.py) via
exec() against the two-layer, tvOS-accurate fake (fake_kodi_storage.py) - not a
substring check on the source text.

THE BUG IT FIXES
----------------
On Apple TV a userdata *.xml is "vectored": Kodi shadows the on-disk POSIX file
with an NSUserDefaults KEY, and that key is the durable store (the POSIX copy
lives in purgeable Library/Caches). xbmcvfs reads/writes the KEY (POSIX fallback
only when NO key exists). skinshortcuts SAVES the edited menu with ElementTree =
POSIX only, so the durable key never sees the edit - the two layers diverge and
the menu reverts (in-session and/or after a cache purge).

reconcileMenu, fired from Home's onload while an edit is pending, copies the
just-saved POSIX bytes of every *.DATA.xml back through xbmcvfs so the durable
key holds the SAME bytes, then re-asserts them on POSIX. After it runs
key == POSIX == the user's edit, so no read path can revert.

Invariants asserted here:
  - tvOS + pending: the durable key is created/updated to the fresh POSIX bytes
    (persists a simulated Caches purge).
  - a STALE key is overwritten with the fresh edit (no revert).
  - byte-preserving: identical bytes are written back (no re-serialize, so the
    content hash cannot churn); idempotent across repeated runs.
  - NEVER deletes; empty / unparseable files are skipped, not propagated.
  - strict no-op on Fire TV / desktop and when no edit is pending.
  - the build is always (re)fired, serialized after the sync.
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

_SS = "script.skinshortcuts"
_SP = "special://profile/addon_data/%s/" % _SS
_NAME = "skin.estuary7-mainmenu.DATA.xml"
_FRESH = b"<shortcuts>\n\t<shortcut>EDIT</shortcut>\n</shortcuts>\n"
_STALE = b"<shortcuts>\n\t<shortcut>STOCK</shortcut>\n</shortcuts>\n"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _Window:
    """Minimal xbmcgui.Window(10000): a persistent Property bag."""

    def __init__(self):
        self.props = {}

    def getProperty(self, key):
        return self.props.get(key, "")

    def setProperty(self, key, value):
        self.props[key] = value

    def clearProperty(self, key):
        self.props.pop(key, None)


def _make_xbmcgui(window):
    class _XbmcGui:
        @staticmethod
        def Window(_id):
            return window

    return _XbmcGui


def _reconcile_code():
    """Turn the injected `elif sys.argv[1] == 'reconcileMenu':` clause into a
    standalone runnable block (dedent, elif -> if)."""
    action = textwrap.dedent(skin_transforms._RECONCILE_MENU_ACTION)
    action = action.replace("elif sys.argv[1]", "if sys.argv[1]", 1)
    return compile(action, "<_RECONCILE_MENU_ACTION>", "exec")


def _run_reconcile(store, window):
    xbmc_mod, xbmcvfs_mod, xbmcaddon_mod = make_modules(store)
    ns = {
        "xbmc": xbmc_mod,
        "xbmcvfs": xbmcvfs_mod,
        "xbmcgui": _make_xbmcgui(window),
        "xbmcaddon": xbmcaddon_mod,
        "os": os,
        "sys": type("S", (), {"argv": ["helpers.py", "reconcileMenu"]}),
    }
    exec(_reconcile_code(), ns)
    return store, window


def _make_box(tmp_path, platform="tvos"):
    home = tmp_path / "home"
    ssdir = home / "userdata" / "addon_data" / _SS
    ssdir.mkdir(parents=True)
    return FakeKodiStorage(home, platform=platform), ssdir


def _key(store):
    return store._key(store.translate(_SP + _NAME))


def _built(store):
    return any("type=buildxml" in m for m in store.log)


# ---------------------------------------------------------------------------
# (a) tvOS + pending: the durable key is created and equals the fresh POSIX
#     bytes, and it SURVIVES a simulated Caches purge (the whole point).
# ---------------------------------------------------------------------------


def test_tvos_pending_registers_durable_key_that_survives_purge(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    (ssdir / _NAME).write_bytes(_FRESH)  # skinshortcuts' POSIX-only save
    assert _key(store) not in store.keys  # no durable key yet
    win = _Window()
    win.setProperty("skinshortcuts-reloadmainmenu", "True")

    _run_reconcile(store, win)

    # The durable key now holds the user's freshest bytes.
    assert store.keys.get(_key(store)) == _FRESH
    # POSIX still holds them too: both layers agree.
    assert (ssdir / _NAME).read_bytes() == _FRESH
    # Simulate tvOS purging Library/Caches: drop the POSIX copy. The durable
    # key must still serve the edit (key-first read + exists).
    (ssdir / _NAME).unlink()
    assert store.exists(_SP + _NAME) is True
    assert bytes(store.read_bytes(_SP + _NAME)) == _FRESH
    # The rebuild was fired, and the pending flag re-asserted for shouldwerun.
    assert _built(store)
    assert win.getProperty("skinshortcuts-reloadmainmenu") == "True"


# ---------------------------------------------------------------------------
# (b) A STALE durable key (pre-edit bytes shadowing a fresh POSIX save) is
#     overwritten with the edit - the exact "menu reverts" divergence.
# ---------------------------------------------------------------------------


def test_stale_key_is_replaced_with_fresh_edit(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    (ssdir / _NAME).write_bytes(_FRESH)
    store.keys[_key(store)] = _STALE  # durable key shadows pre-edit bytes
    win = _Window()
    win.setProperty("skinshortcuts-reloadmainmenu", "True")

    _run_reconcile(store, win)

    assert store.keys[_key(store)] == _FRESH, "stale key must be overwritten"
    assert bytes(store.read_bytes(_SP + _NAME)) == _FRESH


# ---------------------------------------------------------------------------
# (c) Byte-preserving + idempotent: identical bytes are written back (no
#     re-serialize), so a second run changes nothing (no hash churn).
# ---------------------------------------------------------------------------


def test_idempotent_and_byte_preserving(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    (ssdir / _NAME).write_bytes(_FRESH)
    win = _Window()
    win.setProperty("skinshortcuts-reloadmainmenu", "True")

    _run_reconcile(store, win)
    first_key = store.keys[_key(store)]
    first_posix = (ssdir / _NAME).read_bytes()

    win.setProperty("skinshortcuts-reloadmainmenu", "True")
    _run_reconcile(store, win)

    assert store.keys[_key(store)] == first_key == _FRESH
    assert (ssdir / _NAME).read_bytes() == first_posix == _FRESH


# ---------------------------------------------------------------------------
# (d) NEVER deletes; empty and unparseable DATA files are skipped, not
#     propagated into the durable key, and never removed from disk.
# ---------------------------------------------------------------------------


def test_empty_and_unparseable_files_are_skipped_never_deleted(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    good = ssdir / _NAME
    good.write_bytes(_FRESH)
    empty = ssdir / "skin.estuary7-empty.DATA.xml"
    empty.write_bytes(b"")
    junk = ssdir / "skin.estuary7-junk.DATA.xml"
    junk.write_bytes(b"<not-closed>")
    win = _Window()
    win.setProperty("skinshortcuts-reloadmainmenu", "True")

    _run_reconcile(store, win)

    # Good file synced.
    assert store.keys.get(_key(store)) == _FRESH
    # Empty / unparseable were NOT vectored (no durable key created)...
    assert (
        store._key(store.translate(_SP + "skin.estuary7-empty.DATA.xml"))
        not in store.keys
    )
    assert (
        store._key(store.translate(_SP + "skin.estuary7-junk.DATA.xml"))
        not in store.keys
    )
    # ...and NOT deleted from disk (never destroy the user's bytes).
    assert good.exists() and empty.exists() and junk.exists()


def test_action_source_never_deletes():
    """Belt-and-suspenders: the payload text contains no delete/remove call.
    reconcileMenu must only ever ADD/refresh a copy, never destroy one."""
    src = skin_transforms._RECONCILE_MENU_ACTION
    for token in ("os.remove", "os.unlink", "xbmcvfs.delete", "shutil.rmtree"):
        assert token not in src, "reconcileMenu must never delete (%s)" % token


# ---------------------------------------------------------------------------
# (e) Strict no-op off the hot path: Fire TV / desktop, and no pending edit.
#     In every case the durable key is left untouched, and the build still
#     fires (the action replaces the plain buildxml onload on its branch).
# ---------------------------------------------------------------------------


def test_no_edit_pending_is_a_noop(tmp_path):
    store, ssdir = _make_box(tmp_path, "tvos")
    (ssdir / _NAME).write_bytes(_FRESH)
    win = _Window()  # reloadmainmenu NOT set

    _run_reconcile(store, win)

    assert _key(store) not in store.keys, "no sync when no edit is pending"
    assert _built(store), "build is still (re)fired"


def test_non_tvos_is_a_noop(tmp_path):
    store, ssdir = _make_box(tmp_path, "android")
    (ssdir / _NAME).write_bytes(_FRESH)
    win = _Window()
    win.setProperty("skinshortcuts-reloadmainmenu", "True")

    _run_reconcile(store, win)

    assert store.keys == {}, "Fire TV / desktop must never touch the key store"
    assert _built(store)


# ---------------------------------------------------------------------------
# (f) The onload wiring: exactly one build path fires per Home load, and the
#     tvOS reconcile branch is gated on BOTH the platform and a pending edit.
# ---------------------------------------------------------------------------


def test_onload_wires_reconcile_only_on_tvos_with_pending_edit():
    home = skin_transforms._edit_home  # noqa: F841  (referenced for context)
    # Render the real transform against upstream Home.xml and inspect onloads.
    sha = "8d9b2c7c304c6f0226cd40e24819061c6165a6ec"
    up = (
        Path(__file__).resolve().parent.parent
        / "upstream-cache"
        / sha
        / "xml"
        / "Home.xml"
    )
    if not up.is_file():
        pytest.skip("upstream cache not present")
    out = skin_transforms._edit_home(up.read_text(encoding="utf-8"), "xml/Home.xml")
    assert "helpers.py,reconcileMenu" in out
    # reconcile branch requires tvOS AND a pending edit.
    assert (
        "System.Platform.TVOS + "
        '!String.IsEmpty(Window(10000).Property(skinshortcuts-reloadmainmenu))">'
        "RunScript(special://skin/scripts/helpers.py,reconcileMenu)" in out
    )
    # the plain buildxml branch is the mutually-exclusive complement.
    assert (
        "[!System.Platform.TVOS | "
        'String.IsEmpty(Window(10000).Property(skinshortcuts-reloadmainmenu))]">'
        "RunScript(script.skinshortcuts,type=buildxml" in out
    )
    # exactly one reconcile onload, and the first-boot defer is untouched.
    assert out.count("helpers.py,reconcileMenu") == 1
    assert "AlarmClock(t7bbuild" in out
