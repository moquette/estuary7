"""Menu-refresh trigger graph: resetMenu key hygiene + the customizeMenu wrapper.

Executes the REAL `_RESET_MENU_ACTION` and `_CUSTOMIZE_MENU_ACTION` payloads
(tools/skin_transforms.py) via exec() against the two-layer tvOS-accurate fake
(fake_kodi_storage.py), like test_syncmenu_tvos.py does for syncMenu.

WHY (4-agent panel, 2026-07-17):

resetMenu wiped POSIX and copied defaults but never touched the NSUserDefaults
key layer. os.remove cannot reach keys, and on tvOS xbmcvfs.delete on a vectored
userdata *.xml drops ONLY the key (TVOSFile.cpp: the POSIX fallback in Delete is
unreachable for dispatched files). So stale keys survived every reset: a Caches
purge then resurrected the PRE-RESET menu through the surviving key, and until
the next Home-load reconcile every xbmcvfs consumer (including an EZM++ backup)
captured the old custom menu as durable truth. The keydrop closes both.

customizeMenu exists because the power-menu "Customize Main Menu" entry
(1.0.47) launched the skinshortcuts editor as a dialog OVER a still-loaded
Home: closing a dialog never re-fires Home's <onload> - the only rebuild
trigger - so a saved edit sat un-rendered until the user happened to leave Home
(the "menu doesn't refresh" bug; four consumer-side fix releases missed this
missing PRODUCER). The wrapper waits for the editor to close (the engine stamps
Window(10000).Property(skinshortcuts) exactly once after doModal() returns, on
save AND cancel) and fires the rebuild itself, flag-driven, never hash-driven.
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skin_transforms  # noqa: E402  (tools/ is on sys.path via conftest.py)
from fake_kodi_storage import FakeKodiStorage, make_modules  # noqa: E402

_SS = "script.skinshortcuts"
_SP = "special://profile/addon_data/script.skinshortcuts/"
_MENU = "mainmenu.DATA.xml"

_CUSTOM = (
    b"<shortcuts>\n    <shortcut><label>Owner custom</label></shortcut>\n</shortcuts>\n"
)
_DEFAULT = b"<shortcuts>\n    <shortcut><label>Stock default</label></shortcut>\n</shortcuts>\n"


class _Window:
    _store: dict = {}

    def __init__(self, _id):
        self._id = _id

    def getProperty(self, key):
        return self._store.get(key, "")

    def setProperty(self, key, value):
        self._store[key] = value

    def clearProperty(self, key):
        self._store.pop(key, None)


class _Dialog:
    def yesno(self, *a, **k):
        return True


class _XbmcGui:
    Window = _Window
    Dialog = _Dialog


def _make_box(tmp_path, platform="tvos"):
    home = tmp_path / "home"
    ssdir = home / "userdata" / "addon_data" / _SS
    ssdir.mkdir(parents=True)
    defaults = home / "addons" / "skin.estuary7" / "shortcuts"
    defaults.mkdir(parents=True)
    store = FakeKodiStorage(home, platform=platform)
    return store, ssdir, defaults


def _key_for(store, name=_MENU):
    return store._key(store.translate(_SP + name))


def _exec_payload(store, payload_attr, action, extra_ns=None):
    import xml.etree.ElementTree as ET

    xbmc_mod, xbmcvfs_mod, xbmcaddon_mod = make_modules(store)
    store.log.clear()
    src = textwrap.dedent(getattr(skin_transforms, payload_attr))
    src = src.replace(
        "elif sys.argv[1] == '%s':" % action, "if sys.argv[1] == '%s':" % action, 1
    )
    fake_sys = type("S", (), {"argv": ["helpers.py", action]})()
    ns = {
        "xbmc": xbmc_mod,
        "xbmcvfs": xbmcvfs_mod,
        "xbmcaddon": xbmcaddon_mod,
        "xbmcgui": _XbmcGui,
        "os": os,
        "ET": ET,
        "sys": fake_sys,
    }
    if extra_ns:
        ns.update(extra_ns)
    exec(compile(src, "<%s>" % payload_attr, "exec"), ns)
    return xbmc_mod, ns


# ---------------------------------------------------------------------------
# resetMenu: the stale-key drop (tvOS)
# ---------------------------------------------------------------------------


def test_resetmenu_drops_stale_keys_and_restores_defaults(tmp_path):
    store, ssdir, defaults = _make_box(tmp_path)
    (defaults / _MENU).write_bytes(_DEFAULT)
    (ssdir / _MENU).write_bytes(_CUSTOM)
    store.keys[_key_for(store)] = _CUSTOM  # durable key holds the custom menu

    _exec_payload(store, "_RESET_MENU_ACTION", "resetMenu")

    assert (ssdir / _MENU).read_bytes() == _DEFAULT, "POSIX must hold the defaults"
    assert _key_for(store) not in store.keys, (
        "the stale NSUserDefaults key must be dropped: a Caches purge must not "
        "be able to resurrect the pre-reset menu through a surviving key"
    )
    assert _Window._store.get("skinshortcuts-reloadmainmenu") == "True"
    assert any("type=buildxml" in m for m in store.log), "reset must chain a build"
    assert any("keydrop=1" in m for m in store.log), "keydrop must be reported"


def test_resetmenu_purge_after_reset_yields_defaults_not_old_menu(tmp_path):
    """The exact resurrection scenario: reset, then a Caches purge. With the key
    dropped, every reader falls through to the shipped skin defaults - the
    reset's intended end state - instead of the pre-reset custom menu."""
    store, ssdir, defaults = _make_box(tmp_path)
    (defaults / _MENU).write_bytes(_DEFAULT)
    (ssdir / _MENU).write_bytes(_CUSTOM)
    store.keys[_key_for(store)] = _CUSTOM

    _exec_payload(store, "_RESET_MENU_ACTION", "resetMenu")
    os.remove(ssdir / _MENU)  # simulate the purge of the fresh POSIX defaults

    assert bytes(store.read_bytes(_SP + _MENU)) == b"", (
        "after reset+purge neither layer may hold the old custom menu; readers "
        "fall through to the skin's shipped shortcuts/ defaults"
    )


def test_resetmenu_keydrop_preserves_settings_key(tmp_path):
    store, ssdir, defaults = _make_box(tmp_path)
    (defaults / _MENU).write_bytes(_DEFAULT)
    (ssdir / _MENU).write_bytes(_CUSTOM)
    store.keys[_key_for(store)] = _CUSTOM
    settings_key = store._key(store.translate(_SP + "settings.xml"))
    store.keys[settings_key] = b"<settings/>"

    _exec_payload(store, "_RESET_MENU_ACTION", "resetMenu")

    assert store.keys.get(settings_key) == b"<settings/>", (
        "settings.xml's key is the addon settings' durable copy, not menu data"
    )


def test_resetmenu_no_keydrop_off_tvos(tmp_path):
    store, ssdir, defaults = _make_box(tmp_path, platform="android")
    (defaults / _MENU).write_bytes(_DEFAULT)
    (ssdir / _MENU).write_bytes(_CUSTOM)

    _exec_payload(store, "_RESET_MENU_ACTION", "resetMenu")

    assert not any("keydrop" in m for m in store.log)
    assert (ssdir / _MENU).read_bytes() == _DEFAULT


def test_resetmenu_source_still_wipes_posix_with_os_remove():
    """The keydrop must be ADDITIVE: the POSIX wipe stays plain os.remove
    (xbmcvfs.delete cannot delete a vectored POSIX file), and the payload never
    verifies the drop with xbmcvfs.exists (it falls back to the fresh POSIX
    defaults and proves nothing about the key)."""
    src = skin_transforms._RESET_MENU_ACTION
    code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    assert "os.remove(os.path.join(base, name))" in code
    assert "xbmcvfs.delete" in code
    assert "xbmcvfs.exists" not in code


# ---------------------------------------------------------------------------
# customizeMenu: the power-menu editor wrapper
# ---------------------------------------------------------------------------


def _run_customize(store, on_manage=None):
    """Run the wrapper with an executebuiltin interceptor standing in for the
    engine: `on_manage` mutates window properties the way the real manage
    dialog would (stamp on close; reloadmainmenu on save)."""
    xbmc_mod, _, _ = make_modules(store)
    _Window._store = {}

    class _Monitor:
        def abortRequested(self):
            return False

        def waitForAbort(self, _secs):
            return False

    calls = []

    class _XbmcWrap(xbmc_mod):
        Monitor = _Monitor

        @staticmethod
        def executebuiltin(cmd):
            calls.append(cmd)
            if "type=manage" in cmd and on_manage:
                on_manage(_Window._store)

    _exec_payload(
        store,
        "_CUSTOMIZE_MENU_ACTION",
        "customizeMenu",
        extra_ns={"xbmc": _XbmcWrap},
    )
    return calls


def test_customizemenu_save_arms_ordered_chain_on_tvos(tmp_path):
    """tvOS save path: the wrapper must NOT fire buildxml itself in parallel
    with a syncMenu spawn - that would recreate the exact reconcile-vs-build
    race the onload redesign removed (a mid-session purge makes syncMenu WRITE
    POSIX while the build reads it). It reuses the ordered chain instead: arm
    t7b_chainbuild, spawn ONLY syncMenu, which fires the one build after
    reconciling."""
    store, ssdir, _ = _make_box(tmp_path)

    def _save(props):
        props["skinshortcuts"] = "1752770000"  # doModal returned (stamp)
        props["skinshortcuts-reloadmainmenu"] = "True"  # user SAVED

    calls = _run_customize(store, on_manage=_save)

    assert not any("type=buildxml" in c for c in calls), (
        "the wrapper must never fire a build in parallel with syncMenu on tvOS"
    )
    manage_idx = next(i for i, c in enumerate(calls) if "type=manage" in c)
    sync_idx = next(i for i, c in enumerate(calls) if "helpers.py,syncMenu" in c)
    assert manage_idx < sync_idx, "chain is armed after the editor closes"
    assert _Window._store.get("t7b_chainbuild") == "1", (
        "the marker is what makes the chained syncMenu fire the one build"
    )


def test_customizemenu_chain_end_to_end_fires_exactly_one_build(tmp_path):
    """Full tvOS chain: wrapper (save) -> real syncMenu payload -> exactly one
    build, marker consumed, stuck guard cleared, save flag left for the
    builder."""
    store, ssdir, _ = _make_box(tmp_path)
    (ssdir / _MENU).write_bytes(_CUSTOM)  # the fresh save on POSIX

    def _save(props):
        props["skinshortcuts"] = "1752770003"
        props["skinshortcuts-reloadmainmenu"] = "True"
        props["skinshortcuts-isrunning"] = "True"  # a stuck guard on top

    _run_customize(store, on_manage=_save)
    assert _Window._store.get("t7b_chainbuild") == "1"

    # Now the spawned syncMenu runs (same window store, real payload).
    store.log.clear()
    _exec_payload(store, "_SYNC_MENU_ACTION", "syncMenu")

    builds = [m for m in store.log if "type=buildxml" in m]
    assert len(builds) == 1, "exactly ONE build for the whole save flow"
    assert "t7b_chainbuild" not in _Window._store, "marker consumed"
    assert "skinshortcuts-isrunning" not in _Window._store, (
        "the stuck guard must be cleared before the build or it silently no-ops"
    )
    assert _Window._store.get("skinshortcuts-reloadmainmenu") == "True", (
        "the save flag is the builder's to consume, so the build rebuilds "
        "flag-driven even if the hash cannot see the change"
    )
    assert store.keys.get(_key_for(store)) == _CUSTOM, (
        "the durable key registers immediately, not at the next Home load"
    )


def test_customizemenu_cancel_fires_no_build(tmp_path):
    store, ssdir, _ = _make_box(tmp_path)

    def _cancel(props):
        props["skinshortcuts"] = "1752770001"  # closed WITHOUT saving

    calls = _run_customize(store, on_manage=_cancel)

    assert not any("type=buildxml" in c for c in calls)
    assert not any("helpers.py,syncMenu" in c for c in calls)
    assert "t7b_chainbuild" not in _Window._store


def test_customizemenu_direct_build_off_tvos(tmp_path):
    store, ssdir, _ = _make_box(tmp_path, platform="android")

    def _save(props):
        props["skinshortcuts"] = "1752770002"
        props["skinshortcuts-reloadmainmenu"] = "True"
        props["skinshortcuts-isrunning"] = "True"

    calls = _run_customize(store, on_manage=_save)

    assert any("type=buildxml" in c for c in calls), "the rebuild is cross-platform"
    assert not any("helpers.py,syncMenu" in c for c in calls), (
        "no key layer off tvOS - nothing to reconcile"
    )
    assert "t7b_chainbuild" not in _Window._store, "no chain off tvOS"
    assert "skinshortcuts-isrunning" not in _Window._store
