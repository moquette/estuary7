"""Rebrand + shipped-assets contracts."""

from __future__ import annotations

from conftest import GOLDENS
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
    # pvr.artwork is OPTIONAL: it is the one dep not in Kodi's official repo,
    # so a REQUIRED import made a clean-box install abandon the whole closure
    # and disable the skin. Optional = the skin enables without it (owner
    # directive 2026-07-10). Setup still installs it on the fleet.
    assert (
        '<import addon="script.module.pvr.artwork" version="2.0.0" optional="true"/>'
        in addon
    )
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
    assert total == 15


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


def test_shortcuts_assets_match_goldens(built):
    """The shipped menu defaults are byte-identical to the hardware-verified
    goldens; only the properties file is re-keyed (name only, same bytes)."""
    golden_dir = GOLDENS / "skinshortcuts"
    for golden in sorted(golden_dir.glob("*.DATA.xml")):
        shipped = built.tree / "shortcuts" / golden.name
        assert shipped.is_file(), "shortcuts/{} missing".format(golden.name)
        assert shipped.read_bytes() == golden.read_bytes(), golden.name
    props = built.tree / "shortcuts" / "{}.properties".format(SKIN_ID)
    golden_props = golden_dir / "{}.properties".format(UPSTREAM_ID)
    assert props.read_bytes() == golden_props.read_bytes()
    # Exactly one properties file ships - the upstream-keyed one must not.
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
    from conftest import ROOT

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
    """Our defaults OVERWRITE mainmenu/movies/tvshows and ADD submenu files;
    the rest of upstream's shortcuts dir (incl. overrides.xml + template.xml,
    which skinshortcuts builds from) must still be there."""
    for name in (
        "overrides.xml",
        "template.xml",
        "powermenu.DATA.xml",
        "music.DATA.xml",
        "addons.DATA.xml",
    ):
        assert (built.tree / "shortcuts" / name).is_file(), name
