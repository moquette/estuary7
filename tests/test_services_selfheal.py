"""Boot-service seed coverage: donthidepvr only, plus the tvOS Siri keymap.

Executes the REAL _SERVICES_SEED payload (tools/skin_transforms.py) via exec()
against a two-layer tvOS-accurate fake (fake_kodi_storage.py) - not a substring
check on the source text.

The boot service now does exactly two things: seed script.skinshortcuts'
donthidepvr=true (so Live TV/Radio stay always-visible like stock, hardware
verified), and (tvOS only) write the Siri-remote keymap for Fire TV parity. It
seeds NO skinshortcuts .hash.

History (1.0.64 fix): the fork once seeded a .hash so shouldwerun() returned
False and the first-launch rebuild+ReloadSkin was skipped. But that seeded hash
reported "menu up to date" while blind to the owner's addon_data edits, so Home
main-menu edits never persisted - they survived ReloadSkin AND a full restart.
The hash seed was removed, together with the coupled tvOS DATA self-heal/purge
that existed only to protect the seed's assumptions (re-materializing DATA was a
no-op in effect without the coupled hash-drop that forced a rebuild). With no
hash on disk, shouldwerun() rebuilds from the owner's real DATA on first boot,
writes a REAL hash, and every later edit self-heals via a hash mismatch. These
tests assert the seed writes donthidepvr and NEVER a hash.
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

_SKINDIR = "skin.estuary7"  # matches fake_kodi_storage._Xbmc.getSkinDir()
_SS = "script.skinshortcuts"
PLATFORMS = ("tvos", "android")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _exec_seed(modules):
    """Run ONE boot of the real payload against a given (xbmc, xbmcvfs,
    xbmcaddon) module set, and return the exec namespace.

    Reusing the SAME `modules` tuple across two calls models two boots of the
    SAME box (the addon-settings dict persists); calling make_modules() again
    models a different box.
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
    }
    exec(code, ns)
    return ns


def _make_box(tmp_path, platform):
    """A fresh box: the skinshortcuts addon_data dir and the skin's generated
    includes.xml."""
    home = tmp_path / "home"
    ssdir = home / "userdata" / "addon_data" / "script.skinshortcuts"
    ssdir.mkdir(parents=True)
    skin_xml = home / "addons" / _SKINDIR / "xml"
    skin_xml.mkdir(parents=True)
    (skin_xml / "script-skinshortcuts-includes.xml").write_text("<includes/>\n")
    store = FakeKodiStorage(home, platform=platform)
    return store, ssdir


def _hash_path(ssdir):
    return ssdir / ("%s.hash" % _SKINDIR)


def _donthidepvr(modules):
    _, _, xbmcaddon_mod = modules
    return xbmcaddon_mod.Addon(_SS).getSetting("donthidepvr")


def _write_owner_menu(ssdir, name="mainmenu.DATA.xml", content="<owner-shortcuts/>\n"):
    (ssdir / name).write_text(content)


# ---------------------------------------------------------------------------
# (a) donthidepvr is seeded on boot (both platforms).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_boot_seeds_donthidepvr(tmp_path, platform):
    store, _ = _make_box(tmp_path, platform)
    modules = make_modules(store)

    _exec_seed(modules)

    assert _donthidepvr(modules) == "true", (
        "the boot service must seed skinshortcuts donthidepvr=true so Live "
        "TV/Radio stay always-visible like stock"
    )
    assert any("seeded skinshortcuts donthidepvr=true" in m for m in store.log)


# ---------------------------------------------------------------------------
# (b) donthidepvr seed is idempotent - a second boot does not re-write it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_donthidepvr_seed_idempotent(tmp_path, platform):
    store, _ = _make_box(tmp_path, platform)
    modules = make_modules(store)

    _exec_seed(modules)
    store.log.clear()
    _exec_seed(modules)

    assert _donthidepvr(modules) == "true"
    assert not any("seeded skinshortcuts donthidepvr=true" in m for m in store.log), (
        "donthidepvr was re-seeded when it was already 'true' (not idempotent)"
    )


# ---------------------------------------------------------------------------
# (c) THE FIX: the boot service seeds NO hash. Not on a virgin box, and not
#     when the owner already has a menu of their own. A seeded hash is exactly
#     what made Home main-menu edits fail to persist.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_virgin_box_seeds_no_hash(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform)
    # no DATA.xml, no hash: a truly virgin box.

    _exec_seed(make_modules(store))

    assert not _hash_path(ssdir).exists(), (
        "the boot service must NOT seed a skinshortcuts hash - a seeded hash "
        "reports 'menu up to date' while blind to addon_data edits, so main-menu "
        "edits never persist across a restart"
    )
    assert not any("seeded skinshortcuts hash" in m for m in store.log)
    assert not any("dropped stale skinshortcuts hash" in m for m in store.log)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_owner_menu_box_seeds_no_hash(tmp_path, platform):
    store, ssdir = _make_box(tmp_path, platform)
    _write_owner_menu(ssdir)

    _exec_seed(make_modules(store))

    assert not _hash_path(ssdir).exists(), (
        "the boot service must NOT seed or freeze a hash when the owner has a menu"
    )
    assert not any("seeded skinshortcuts hash" in m for m in store.log)
    assert not any("dropped stale skinshortcuts hash" in m for m in store.log)


def test_seed_source_has_no_hash_machinery():
    """Belt-and-suspenders: the payload text itself no longer references the
    removed hash-seed / self-heal machinery. Guards against a future re-add of
    the exact code that broke edit persistence."""
    src = skin_transforms._SERVICES_SEED
    for token in (".hash", "_hashfile", "_needseed", "_healed", "_usermenu"):
        assert token not in src, "removed hash-seed token reappeared: %r" % token


# ---------------------------------------------------------------------------
# Siri remote keymap seed (1.0.49): Fire TV parity on tvOS, no-op elsewhere.
# ---------------------------------------------------------------------------


def _keymap_path(tmp_path):
    return tmp_path / "home" / "userdata" / "keymaps" / "t7b-siriremote.xml"


def test_siri_keymap_written_on_tvos_and_idempotent(tmp_path):
    store, _ = _make_box(tmp_path, "tvos")
    modules = make_modules(store)
    _exec_seed(modules)
    km = _keymap_path(tmp_path)
    assert km.is_file(), "tvOS boot must write the Siri keymap"
    body = km.read_text()
    # back exits fullscreen video (playback continues) - both live-TV and
    # plain video sections override upstream's button-6 Stop.
    assert body.count('<button id="6">Back</button>') == 2
    assert "<FullscreenVideo>" in body and "<FullscreenLiveTV>" in body
    # select opens the OSD on live TV ONLY (1.0.54): upstream's select=Pause
    # is a dead button on non-timeshift live streams; the FullscreenLiveTV
    # section wins over FullscreenVideo while a PVR channel plays, so movies
    # keep select=Pause (exactly one id-5 override, inside the live section).
    assert body.count('<button id="5">OSD</button>') == 1
    assert (
        body.index("<FullscreenLiveTV>")
        < body.index('<button id="5">OSD</button>')
        < body.index("</FullscreenLiveTV>")
    )
    # double play/pause (upstream noop) toggles fullscreen back.
    assert '<button id="21">FullScreen</button>' in body
    # back at Home returns to the playing video (upstream opened the
    # Favourites browser - a blank screen with no favourites set).
    assert "<Home>" in body
    assert body.count(">FullScreen</button>") == 2
    assert "builtin: Action(reloadkeymaps)" in store.log
    # Second boot of the SAME box: content unchanged, NO second reload.
    reloads = store.log.count("builtin: Action(reloadkeymaps)")
    _exec_seed(modules)
    assert km.read_text() == body
    assert store.log.count("builtin: Action(reloadkeymaps)") == reloads


def test_siri_keymap_not_written_on_android(tmp_path):
    store, _ = _make_box(tmp_path, "android")
    _exec_seed(make_modules(store))
    assert not _keymap_path(tmp_path).exists(), (
        "the Siri keymap is tvOS-only; Fire OS boxes must stay untouched"
    )
    assert "builtin: Action(reloadkeymaps)" not in store.log
