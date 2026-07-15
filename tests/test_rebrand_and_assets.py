"""Rebrand + shipped-assets contracts."""

from __future__ import annotations

from conftest import GOLDENS, ROOT
from skin_transforms import SKIN_ID, SKIN_NAME, UPSTREAM_ID

TEXT_SUFFIXES = (".xml", ".py", ".po", ".md", ".properties")


def test_addon_xml_identity(built):
    addon = (built.tree / "addon.xml").read_text(encoding="utf-8")
    assert (
        '<addon id="{}" version="{}" name="{}"'.format(
            SKIN_ID, built.lock["our_version"], SKIN_NAME
        )
        in addon
    )
    # The upstream dependency closure survives the rebrand intact.
    for dep in (
        "script.skinshortcuts",
        "script.image.resource.select",
        "resource.images.weathericons.outline-hd",
        "script.module.autocompletion",
    ):
        assert '<import addon="{}"'.format(dep) in addon
    # pvr.artwork is GONE from the manifest (owner directive 2026-07-15,
    # 1.0.45; it had been optional since 2026-07-10): the bench never had it
    # installed and never missed it - every skin read is emptiness-guarded,
    # and the SkinSettings "PVR Artwork" toggle still one-click-installs it
    # for anyone who wants the enrichment.
    assert "pvr.artwork" not in addon
    # No unrelated couplings: Setup owns EZ Maintenance++ (owner decision
    # 2026-07-10 - the skin declares only what it uses).
    assert "ezmaintenanceplusplus" not in addon
    # The "by" line (provider-name) is Tony.7.Bones ALONE, and upstream author
    # names appear NOWHERE in the visible addon.xml - not the author line, not
    # the description (owner directive 2026-07-10). License-required attribution
    # lives in ATTRIBUTION.md + LICENSE.txt inside the zip, not on the info page.
    assert 'provider-name="Tony.7.Bones">' in addon
    for name in ("Guilouz", "PvD", "b-jesch", "Team Kodi", "phil65", "Piers"):
        assert name not in addon, (
            "upstream author {} must not appear in addon.xml".format(name)
        )
    # License markers survive (obligation is met via ATTRIBUTION.md).
    assert "CC BY-SA 4.0" in addon and "GENERAL PUBLIC LICENSE" in addon
    # Screenshots are original Estuary's (stock), not MOD V2's branded set.
    assert "resources/screenshots/screenshot_" not in addon
    assert addon.count("<screenshot>resources/screenshot-") == 8
    assert built.lock["our_version"] in addon.split("<news>")[1]
    # No python.script extension: Kodi's executable browser node buckets any
    # script-extension addon under Program add-ons regardless of <provides>;
    # a skin must list only as a skin (like stock Estuary).
    assert "xbmc.python.script" not in addon
    # The service + context-menu extensions survive.
    assert '<extension point="xbmc.service"' in addon
    assert '<extension point="kodi.context.item">' in addon


def test_helper_script_runs_by_path(built):
    """The helpers bridge still ships and every caller invokes it by file
    path (the addon-id form died with the script extension)."""
    assert (built.tree / "scripts" / "helpers.py").is_file()
    total = 0
    for xml in sorted((built.tree / "xml").glob("*.xml")):
        text = xml.read_text(encoding="utf-8")
        assert "RunScript({},".format(SKIN_ID) not in text, xml.name
        total += text.count("RunScript(special://skin/scripts/helpers.py,")
    # 16 rewired getKodiSetting/reset callers + the Home onload seedPVR (1.0.33).
    assert total == 17


def test_upstream_id_fully_renamed(built):
    offenders = []
    for path in sorted(built.tree.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if path.name == "ATTRIBUTION.md":
            continue  # provenance doc - naming upstream is the point
        if UPSTREAM_ID in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(built.tree)))
    assert not offenders, offenders


def test_current_skin_property_uses_new_id(built):
    home = (built.tree / "xml" / "Home.xml").read_text(encoding="utf-8")
    assert "<onload>SetProperty(CurrentSkin,{},home)</onload>".format(SKIN_ID) in home


def test_license_and_attribution_ship_in_the_zip_tree(built):
    assert (built.tree / "LICENSE.txt").is_file()  # upstream GPL text, untouched
    attribution = (built.tree / "ATTRIBUTION.md").read_text(encoding="utf-8")
    for credit in ("b-jesch", "Guilouz", "Team Kodi"):
        assert credit in attribution


def test_home_menu_is_stock_estuary(built):
    """The shipped main menu is STOCK ESTUARY's item set and order (owner
    directive): Movies, TV shows, Music, Disc, Music videos, TV, Radio, Games,
    Add-ons, Pictures, Videos, Favourites, Weather.

    Stock Estuary shows Live TV / Radio ALWAYS (gated only by an opt-out skin
    setting, not by PVR). They keep stock's named windows (TVChannels/
    RadioChannels); the boot service + reset helper seed skinshortcuts'
    donthidepvr=true so its check_visibility() never injects System.HasPVRAddon,
    keeping the tiles always-visible like stock. Numeric window ids do NOT help
    (hardware-verified: skinshortcuts normalises them back to the named windows
    at build time and injects the PVR condition anyway).
    """
    import xml.etree.ElementTree as ET

    data = built.tree / "shortcuts" / "mainmenu.DATA.xml"
    text = data.read_text(encoding="utf-8")
    root = ET.fromstring(text)

    order, seen = [], set()
    for sc in root.findall("shortcut"):
        did = sc.findtext("defaultID")
        if did and did not in seen:
            seen.add(did)
            order.append(did)
    assert order == [
        "movies",
        "tvshows",
        "music",
        "disc",
        "musicvideos",
        "livetv",
        "radio",
        "games",
        "addons",
        "pictures",
        "video",
        "favorites",
        "weather",
    ], order

    # PVR items keep stock's named windows; donthidepvr (seeded at boot) keeps
    # them visible. Numeric ids are normalised back at build time, so don't ship them.
    assert (
        "ActivateWindow(TVChannels)" in text and "ActivateWindow(RadioChannels)" in text
    )
    assert "ActivateWindow(10700)" not in text
    assert "ActivateWindow(10705)" not in text

    # the boot service seeds skinshortcuts donthidepvr=true so PVR tiles stay visible
    services = (built.tree / "scripts" / "services.py").read_text(encoding="utf-8")
    assert "donthidepvr" in services and "setSetting" in services

    # stock has no LibreELEC/CoreELEC entries
    assert "service.libreelec.settings" not in text
    assert "service.coreelec.settings" not in text

    # MOD V2's library-aware action variants survive (3 movie shortcuts)
    assert (
        sum(
            1 for sc in root.findall("shortcut") if sc.findtext("defaultID") == "movies"
        )
        == 3
    )

    # and it deliberately DIFFERS from upstream now (regression guard)
    upstream = (
        ROOT
        / "upstream-cache"
        / built.lock["upstream_sha"]
        / "shortcuts"
        / "mainmenu.DATA.xml"
    )
    if upstream.is_file():
        assert data.read_bytes() != upstream.read_bytes()

    # still no fork/upstream skinshortcuts properties shipped
    assert not (built.tree / "shortcuts" / "{}.properties".format(SKIN_ID)).exists()
    assert not (built.tree / "shortcuts" / "{}.properties".format(UPSTREAM_ID)).exists()


def test_wordmark_ships_where_home_points(built):
    golden = (GOLDENS / "logo-text-hires.png").read_bytes()
    shipped = built.tree / "media" / "extras" / "logo-text-hires.png"
    assert shipped.read_bytes() == golden
    home = (built.tree / "xml" / "Home.xml").read_text(encoding="utf-8")
    assert home.count("<texture>extras/logo-text-hires.png</texture>") == 2


def test_skin_selection_artwork_is_stock_estuary(built):
    """Kodi's skin chooser + info screen show resources/icon.png, fanart.jpg,
    and the 8 screenshots - the fork ships ORIGINAL Estuary's set (vendored in
    assets/), not MOD V2's branded art."""

    names = ["icon.png", "fanart.jpg"] + [
        "screenshot-{:02d}.jpg".format(n) for n in range(1, 9)
    ]
    for name in names:
        shipped = (built.tree / "resources" / name).read_bytes()
        vendored = (ROOT / "assets" / "resources" / name).read_bytes()
        assert shipped == vendored, name
    # MOD V2's branded screenshot dir is gone.
    assert not (built.tree / "resources" / "screenshots").exists()


def test_stock_upstream_shortcuts_survive(built):
    """Upstream's shortcuts dir ships intact (nothing overwritten): the full
    default menu, overrides.xml + template.xml that skinshortcuts builds from,
    and every submenu DATA file."""
    for name in (
        "mainmenu.DATA.xml",
        "overrides.xml",
        "template.xml",
        "powermenu.DATA.xml",
        "music.DATA.xml",
        "addons.DATA.xml",
    ):
        assert (built.tree / "shortcuts" / name).is_file(), name


def test_powermenu_leads_with_skin_settings(built):
    """The power menu leads with 'Skin settings' (owner request). It is a static
    list with one <content> per display mode; the item must be FIRST in each and
    open this skin's settings window."""
    import re

    text = (built.tree / "xml" / "DialogButtonMenu.xml").read_text("utf-8")
    blocks = re.findall(r"<content>\s*(<item>.*?</item>)", text, re.S)
    assert len(blocks) == 3, "expected 3 power-menu content modes"
    for first_item in blocks:
        assert "$LOCALIZE[10035]" in first_item
        # the power menu is a modal dialog: it MUST close before navigating,
        # or ActivateWindow is ignored (nothing happens on click).
        assert first_item.index("dialog.close(all,true)") < first_item.index(
            "ActivateWindow(SkinSettings)"
        )
    # exactly three inserted (one per mode), no more
    assert text.count("<onclick>ActivateWindow(SkinSettings)</onclick>") == 3


def test_videos_override_removed(built, upstream_tree):
    """Upstream ships a videos labelID override; the build must REMOVE it.

    Any <icon labelID="videos"> override that resolves to a skin image makes the
    skinshortcuts editor draw the Videos entry blank (its gui.py setArt uses the
    literal 'icon' string). Removing it is the fix - re-adding ANY skin-image
    override reintroduces the blank."""
    pristine = (upstream_tree / "shortcuts" / "overrides.xml").read_text("utf-8")
    assert 'labelID="videos"' in pristine, "upstream lost the videos override anchor"
    built_overrides = (built.tree / "shortcuts" / "overrides.xml").read_text("utf-8")
    assert 'labelID="videos"' not in built_overrides
    # livetv/radio overrides must stay (their Default* icons are not skin images).
    assert 'labelID="livetv"' in built_overrides
    assert 'labelID="radio"' in built_overrides


def test_stock_videos_icon_shadows_the_bundle(built):
    """The Videos glyph must match ORIGINAL Estuary, not MOD V2's film-reel.

    Kodi's loader checks Textures.xbt before loose files (bundle wins), so the
    build (a) shadows the bundled icons/sidemenu/videos.png entry and (b) ships
    stock's videos.png loose at that path for Kodi to fall back to."""
    from skin_transforms import _XBT_VIDEOS_PATH, _xbt_entry_offsets

    xbt = built.tree / "media" / "Textures.xbt"
    names = {name for name, _ in _xbt_entry_offsets(xbt.read_bytes())}
    assert _XBT_VIDEOS_PATH not in names, (
        "MOD V2 videos.png still bundled (film-reel wins)"
    )

    loose = built.tree / "media" / "icons" / "sidemenu" / "videos.png"
    assert loose.is_file(), "stock videos.png not shipped loose"
    vendored = ROOT / "assets" / "media" / "icons" / "sidemenu" / "videos.png"
    assert loose.read_bytes() == vendored.read_bytes()


def test_prebuilt_includes_shipped_into_every_res_folder(built):
    """The pre-built skinshortcuts includes ship byte-identical to the vendored
    source, in EVERY resolution folder addon.xml declares. Required by the boot
    service's hash seed: shouldwerun() only returns False (no rebuild+reload on
    first launch) when this file already exists."""
    import re

    vendored = ROOT / "assets" / "xml" / "script-skinshortcuts-includes.xml"
    want = vendored.read_bytes()
    addon = (built.tree / "addon.xml").read_text(encoding="utf-8")
    folders = set(re.findall(r'<res\b[^>]*\bfolder="([^"]+)"', addon)) or {"xml"}
    for folder in sorted(folders):
        shipped = built.tree / folder / "script-skinshortcuts-includes.xml"
        assert shipped.is_file(), "includes missing from res folder {}".format(folder)
        assert shipped.read_bytes() == want, (
            "shipped includes in {} diverge from the vendored source".format(folder)
        )


def test_includes_provenance_matches_built_menu(built):
    """Staleness guard: the vendored includes were captured from a specific menu
    DATA set. If any of those DATA/override/template files change in the built
    tree without re-capturing the includes, fail loud - a stale includes file
    would seed a hash that no longer matches the menu skinshortcuts rebuilds."""
    import hashlib
    import json

    prov = json.loads(
        (ROOT / "assets" / "xml" / "includes.provenance.json").read_text("utf-8")
    )
    assert prov["skin_id"] == SKIN_ID
    drift = []
    for rel, want in prov["data_sha256"].items():
        f = built.tree / rel
        assert f.is_file(), "provenance file {} missing from built tree".format(rel)
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != want:
            drift.append(rel)
    assert not drift, (
        "menu DATA changed ({}); re-capture "
        "assets/xml/script-skinshortcuts-includes.xml and its provenance".format(drift)
    )


def test_splash_image_shipped(built):
    """The restored splash (owner's background.jpg) ships at the path Startup.xml
    references, byte-identical to the vendored source."""
    vendored = ROOT / "assets" / "extras" / "themes" / "t7b-splash.jpg"
    shipped = built.tree / "extras" / "themes" / "t7b-splash.jpg"
    assert shipped.is_file(), "splash image not shipped"
    assert shipped.read_bytes() == vendored.read_bytes()
    startup = (built.tree / "xml" / "Startup.xml").read_text(encoding="utf-8")
    assert "special://skin/extras/themes/t7b-splash.jpg" in startup
