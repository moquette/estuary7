"""Anchored, fail-loud transforms: pinned Estuary MOD V2 -> Estuary 7.

Every customization is expressed as an exact-string edit against the PINNED
upstream tree (see skin_build.lock). Each edit asserts its anchor occurs the
expected number of times; a miscount raises TransformError naming the file.
Upstream drift therefore breaks the BUILD, never the fleet - this is the
contract that kills the "wrong-era file silently shipped" bug class.

Transform inventory (mirrors docs/PLAN.md Phase 1):
  1. rebrand      - addon.xml identity + global skin-id rename
  2. bold sweep   - strip [B]/[/B] markup from every window XML
  3. Font.xml     - Estuary weights in the Default fontset, ids untouched
  4. file tweaks  - overlay gate, wordmark, gear order, side-nav fonts,
                    our Skin Settings category (per-item toggles only; the
                    patch-era master Apply/Restore toggle does not exist here)
  5. baked defaults - every skin setting the retired runtime overlay used to
                    write is inverted into an opt-OUT XML condition, so a
                    fresh box renders the Tony.7.Bones look with ZERO
                    settings writes (the !Skin.HasSetting() house pattern)

Ordering contract inside transform_tree(): per-file anchored edits run FIRST
(anchors are authored against pristine upstream bytes), then the global skin-id
rename, then the bold sweep, then the Font.xml rewrite. An edit whose anchor
contains [B] or the upstream id must therefore never be added after step 1.
"""

from __future__ import annotations

import re
from pathlib import Path

UPSTREAM_ID = "skin.estuary.modv2"
SKIN_ID = "skin.estuary7"
SKIN_NAME = "Estuary 7"

BOLD_MARKUP = ("[B]", "[/B]")

# Faces the Default fontset re-binds (stock-Estuary parity for the NotoSans
# ids; family-internal weight drop for the condensed media-flag badges - a
# non-condensed face would overflow the flag layouts).
FONT_FACE_SWAPS = (
    ("NotoSans-Bold.ttf", "NotoSans-Regular.ttf", 11),
    ("RobotoCondensed-Bold.ttf", "RobotoCondensed-Light.ttf", 5),
)
# UI ids whose <style>bold</style> is synthetic bold (FreeType renders it
# regardless of the bound file). The lyr* lyrics faces keep theirs: they are
# decorative overlay art, not UI chrome.
FONT_STYLE_BOLD_UI_IDS = 3


class TransformError(RuntimeError):
    """An anchor is missing or ambiguous - upstream drifted; fix the pin."""


def _replace(text: str, old: str, new: str, *, path: str, count: int = 1) -> str:
    found = text.count(old)
    if found != count:
        raise TransformError(
            "{}: anchor occurs {}x, expected {}x: {!r}".format(
                path, found, count, old[:120]
            )
        )
    return text.replace(old, new)


def _insert_before(text: str, anchor: str, insertion: str, *, path: str) -> str:
    return _replace(text, anchor, insertion + anchor, path=path)


def _insert_after(text: str, anchor: str, insertion: str, *, path: str) -> str:
    return _replace(text, anchor, anchor + insertion, path=path)


# ---------------------------------------------------------------------------
# 5. Baked defaults - the retired overlay's apply_skin_settings(), as XML.
#
# Each entry inverts one flag so the UNSET (fresh-box) state is the
# Tony.7.Bones look and the Skin Settings toggle now opts back toward stock.
# selected/onclick pairs are rewritten together so the checkbox display
# semantics ("checked" means exactly what it meant before) never change.
# ---------------------------------------------------------------------------

# Top-bar weather readout: stock hides it until show_weatherinfo is set.
# Inverted to hide_weatherinfo so a fresh box shows weather under the clock.
_WEATHERINFO_INCLUDES = [
    (
        "Skin.HasSetting(show_weatherinfo)",
        "!Skin.HasSetting(hide_weatherinfo)",
        3,
    ),
]

# Splash screen: stock plays it until EnableSplashScreen is set (the flag is
# an opt-OUT despite its name). Renamed to a plain opt-IN ShowSplashScreen so
# a fresh box boots without the splash. Negated atom replaced FIRST - the
# positive atom is its substring.
_SPLASH_NEG = (
    "!Skin.HasSetting(EnableSplashScreen)",
    "Skin.HasSetting(ShowSplashScreen)",
)
_SPLASH_POS = (
    "Skin.HasSetting(EnableSplashScreen)",
    "!Skin.HasSetting(ShowSplashScreen)",
)

# Seasonal themes: stock shows them until DisableThemes is set. Renamed to
# opt-in EnableThemes so a fresh box stays plain.
_THEMES_NEG = ("!Skin.HasSetting(DisableThemes)", "Skin.HasSetting(EnableThemes)")

# Power menu style: stock's default (no flag set) is the fullscreen dialog
# ("panel") style; ours is Classic list. PowerMenuList is an expression so the
# default flips without renaming the three exclusive powermenu_* bools that
# Skin.SelectBool writes - selecting Classic list simply sets a now-vestigial
# bool, selecting another style sets its bool and falsifies the expression.
_POWERMENU_EXPR = (
    '\t<expression name="PowerMenuList">!Skin.HasSetting(powermenu_panel) + '
    "!Skin.HasSetting(powermenu_iconlist)</expression>\n"
)

# Home-item backgrounds (Power/Settings/Search): stock shows the dedicated
# image until enable_*_background is set. Inverted to show_*_background so a
# fresh box gets the plain look.
_BACKGROUND_FLAGS = ("power", "settings", "search")

# Home widgets hidden by default: stock shows each until hide_* is set.
# Inverted to show_* so a fresh box gets the trimmed widget set. The toggle
# labels read "Hide : <widget>", so checked-means-hidden is preserved by
# rewriting selected to the negated new flag.
_WIDGET_FLAGS = (
    "recordingchannels",  # Recent recordings (#31015)
    "searches",  # Saved Search Results (#31617)
    "allchannels",  # All channels (#31361)
    "audioaddons",  # Music add-ons (#1038)
    "gameaddons",  # Game add-ons (#35049)
    "imageaddons",  # Picture add-ons (#1039)
)

# The system-info toggle lives in stock Estuary's OWN structure (owner
# directive 2026-07-10: no custom "Estuary 7" tab - as close to stock Estuary
# as possible): General category, right below "Disable zoom effect"
# (radiobutton 702), i.e. before "Default button on Video/Audio OSD" (button
# 703). Id 1101 is unused by upstream.
_SYSINFO_TOGGLE = """\t\t\t\t<control type="radiobutton" id="1101">
\t\t\t\t\t<label>Show system info on Settings focus</label>
\t\t\t\t\t<include>DefaultSettingButton</include>
\t\t\t\t\t<onclick>Skin.ToggleSetting(show_system_info_overlay)</onclick>
\t\t\t\t\t<selected>Skin.HasSetting(show_system_info_overlay)</selected>
\t\t\t\t</control>
"""


def _category_item(item_id: int, label_id: int) -> str:
    return (
        '\t\t\t\t\t<item id="{}">\n'
        "\t\t\t\t\t\t<label>$LOCALIZE[{}]</label>\n"
        "\t\t\t\t\t</item>\n".format(item_id, label_id)
    )


# Skin Settings categories in STOCK Estuary's order (owner directive
# 2026-07-10). Stock ships General, Main menu items, Artwork, On screen
# display; MOD V2's extra panels follow in their upstream relative order.
# Panes are gated on Container(9000).HasFocus(<item id>), so reordering the
# list items never rewires a pane.
_CATEGORY_ORDER_UPSTREAM = (
    (2, 31203),  # Home menu
    (1, 128),  # General
    (5, 14022),  # Library
    (3, 31159),  # Artworks
    (9, 31278),  # Music OSD
    (10, 31279),  # Video OSD
    (7, 14204),  # PVR & Live TV
    (4, 31219),  # Colors
    (6, 31266),  # Extras
    (8, 31273),  # Necessary add-ons
)
_CATEGORY_ORDER_STOCK = (
    (1, 128),  # General            (stock #1)
    (2, 31203),  # Home menu        (stock #2: Main menu items)
    (3, 31159),  # Artworks         (stock #3: Artwork)
    (9, 31278),  # Music OSD        (stock #4: On screen display...)
    (10, 31279),  # Video OSD       (...which MOD V2 splits in two)
    (5, 14022),  # Library
    (7, 14204),  # PVR & Live TV
    (4, 31219),  # Colors
    (6, 31266),  # Extras
    (8, 31273),  # Necessary add-ons
)


def _edit_home(text: str, path: str) -> str:
    # The system-info overlay's skin line names the skin literally (the
    # version $INFO beside it is covered by the global id rename).
    text = _replace(
        text,
        "$LOCALIZE[166] Estuary MOD V2 • ",
        "$LOCALIZE[166] Estuary 7 • ",
        path=path,
    )
    # System-info overlay opt-in gate (fresh box: hidden).
    text = _replace(
        text,
        "<visible>Control.HasFocus(802) + !Skin.HasSetting(enable_settingswidget)</visible>",
        "<visible>Skin.HasSetting(show_system_info_overlay) + Control.HasFocus(802) + "
        "!Skin.HasSetting(enable_settingswidget)</visible>",
        path=path,
    )
    # Nav wordmark, fallback group: stock white hi-res wordmark.
    text = _replace(
        text,
        "\t\t\t\t\t<left>40</left>\n"
        "\t\t\t\t\t<top>10</top>\n"
        "\t\t\t\t\t<aspectratio>keep</aspectratio>\n"
        "\t\t\t\t\t<width>192</width>\n"
        "\t\t\t\t\t<height>36</height>\n"
        "\t\t\t\t\t<texture>icons/logo-text.png</texture>",
        "\t\t\t\t\t<left>40</left>\n"
        "\t\t\t\t\t<top>8</top>\n"
        "\t\t\t\t\t<aspectratio>keep</aspectratio>\n"
        "\t\t\t\t\t<width>192</width>\n"
        "\t\t\t\t\t<height>39</height>\n"
        "\t\t\t\t\t<texture>extras/logo-text-hires.png</texture>",
        path=path,
    )
    # Nav wordmark, main group (replaces the seasonal $VAR[LogoTextVar]).
    text = _replace(
        text,
        "\t\t\t\t\t<left>55</left>\n"
        "\t\t\t\t\t<top>4</top>\n"
        "\t\t\t\t\t<aspectratio>keep</aspectratio>\n"
        "\t\t\t\t\t<width>202</width>\n"
        "\t\t\t\t\t<height>50</height>\n"
        "\t\t\t\t\t<texture>$VAR[LogoTextVar]</texture>",
        "\t\t\t\t\t<left>55</left>\n"
        "\t\t\t\t\t<top>8</top>\n"
        "\t\t\t\t\t<aspectratio>keep</aspectratio>\n"
        "\t\t\t\t\t<width>202</width>\n"
        "\t\t\t\t\t<height>39</height>\n"
        "\t\t\t\t\t<texture>extras/logo-text-hires.png</texture>",
        path=path,
    )
    # Widget-hide bakes: fresh box shows only the trimmed widget set.
    for flag in _WIDGET_FLAGS:
        text = _replace(
            text,
            "!Skin.HasSetting(hide_{})".format(flag),
            "Skin.HasSetting(show_{})".format(flag),
            path=path,
        )
    return text


def _edit_settings(text: str, path: str) -> str:
    """Gear-menu reorder via placeholder rotation (the two items swap slots,
    so plain replace would collide with its own output)."""
    sources_item = (
        "\t\t\t\t\t\t<label>$LOCALIZE[20094]</label>\n"
        "\t\t\t\t\t\t<onclick>ActivateWindow(1120)</onclick>\n"
        "\t\t\t\t\t\t<icon>icons/settings/sources.png</icon>"
    )
    skin_item = (
        "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
        "\t\t\t\t\t\t<onclick>ActivateWindow(SkinSettings)</onclick>\n"
        "\t\t\t\t\t\t<icon>icons/settings/skin.png</icon>"
    )
    placeholder = "\x00T7B-SWAP\x00"
    text = _replace(text, sources_item, placeholder, path=path)
    text = _replace(text, skin_item, sources_item, path=path)
    text = _replace(text, placeholder, skin_item, path=path)
    # Splash is opt-in now; the "startup window is not Home" auto-disable
    # becomes a reset of the new flag.
    text = _replace(
        text,
        "Skin.SetBool(EnableSplashScreen)",
        "Skin.Reset(ShowSplashScreen)",
        path=path,
    )
    return text


def _edit_includes(text: str, path: str) -> str:
    # Classic-list power menu is the fresh-box default (see _POWERMENU_EXPR).
    text = _insert_before(
        text, '\t<expression name="EnableTheme">', _POWERMENU_EXPR, path=path
    )
    text = _replace(text, *_THEMES_NEG, path=path, count=6)
    for old, new, count in _WEATHERINFO_INCLUDES:
        text = _replace(text, old, new, path=path, count=count)
    # Top-bar weather icon: the official Outline HD resource pack replaces the
    # skin-local PNG set.
    text = _replace(
        text,
        "<texture>$INFO[Weather.FanartCode,special://skin/extras/weather/,.png]</texture>",
        "<texture>$INFO[Weather.FanartCode,"
        "resource://resource.images.weathericons.outline-hd/,.png]</texture>",
        path=path,
    )
    text = _replace(
        text,
        "[Window.IsVisible(shutdownmenu) + Skin.HasSetting(powermenu_list)]",
        "[Window.IsVisible(shutdownmenu) + $EXP[PowerMenuList]]",
        path=path,
        count=3,
    )
    return text


def _edit_variables(text: str, path: str) -> str:
    # Plain Power/Settings/Search backgrounds by default.
    for flag in _BACKGROUND_FLAGS:
        text = _replace(
            text,
            "!Skin.HasSetting(enable_{}_background)".format(flag),
            "Skin.HasSetting(show_{}_background)".format(flag),
            path=path,
            count=2,
        )
    # Current-power-menu-style label: Classic list is the fallthrough default.
    text = _replace(
        text,
        '<value condition="Skin.HasSetting(powermenu_list)">$LOCALIZE[31427]</value>',
        "<value>$LOCALIZE[31427]</value>",
        path=path,
    )
    return text


def _edit_skinsettings(text: str, path: str) -> str:
    # System-info toggle: General category, below "Disable zoom effect"
    # (stock structure, no custom tab - THE FIRST MANDATE).
    text = _insert_before(
        text,
        '\t\t\t\t<control type="button" id="703">\n',
        _SYSINFO_TOGGLE,
        path=path,
    )
    # Categories in stock Estuary's order.
    text = _replace(
        text,
        "".join(_category_item(i, l) for i, l in _CATEGORY_ORDER_UPSTREAM),
        "".join(_category_item(i, l) for i, l in _CATEGORY_ORDER_STOCK),
        path=path,
    )
    # No MOD V2 wordmark (stock shows nothing here).
    text = _replace(text, _LOGO_SKINSETTINGS, "", path=path)
    # Thin category nav column (stock Estuary emphasis-by-size, not weight).
    text = _replace(
        text, "<font>font30_title</font>", "<font>font13</font>", path=path, count=2
    )
    # Splash toggle -> opt-in ShowSplashScreen (selected line first: it is the
    # only site that pairs the flag with the startupaction condition).
    text = _replace(
        text,
        "<selected>!Skin.HasSetting(EnableSplashScreen) + "
        "String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</selected>",
        "<selected>Skin.HasSetting(ShowSplashScreen) + "
        "String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</selected>",
        path=path,
    )
    text = _replace(text, *_SPLASH_NEG, path=path, count=2)
    text = _replace(
        text,
        "Skin.ToggleSetting(EnableSplashScreen)",
        "Skin.ToggleSetting(ShowSplashScreen)",
        path=path,
    )
    # Themes toggle -> opt-in EnableThemes.
    text = _replace(text, *_THEMES_NEG, path=path)
    text = _replace(
        text,
        "Skin.ToggleSetting(DisableThemes)",
        "Skin.ToggleSetting(EnableThemes)",
        path=path,
    )
    # Weather readout toggle -> opt-out hide_weatherinfo.
    text = _replace(
        text,
        "<selected>Skin.HasSetting(show_weatherinfo) + !String.IsEmpty(Weather.Plugin)</selected>",
        "<selected>!Skin.HasSetting(hide_weatherinfo) + !String.IsEmpty(Weather.Plugin)</selected>",
        path=path,
    )
    text = _replace(
        text,
        "Skin.ToggleSetting(show_weatherinfo)",
        "Skin.ToggleSetting(hide_weatherinfo)",
        path=path,
    )
    # Background toggles -> opt-in show_*_background.
    for flag in _BACKGROUND_FLAGS:
        text = _replace(
            text,
            "<selected>!Skin.HasSetting(enable_{}_background)</selected>".format(flag),
            "<selected>Skin.HasSetting(show_{}_background)</selected>".format(flag),
            path=path,
        )
        text = _replace(
            text,
            "Skin.ToggleSetting(enable_{}_background)".format(flag),
            "Skin.ToggleSetting(show_{}_background)".format(flag),
            path=path,
        )
        text = _replace(
            text,
            "<visible>!Skin.HasSetting(enable_{}_background)</visible>".format(flag),
            "<visible>Skin.HasSetting(show_{}_background)</visible>".format(flag),
            path=path,
        )
    return text


# MOD V2's "ESTUARY MOD V2" wordmark (dialogs/logo.png) - a MOD V2 addition;
# stock Estuary shows NOTHING in either spot (owner decision 2026-07-10:
# remove both). Note Includes_MediaMenu's space-indented body is upstream's
# own byte-exact quirk.
_LOGO_SKINSETTINGS = (
    '\t\t\t<control type="image">\n'
    "\t\t\t\t<left>66.5</left>\n"
    "\t\t\t\t<bottom>20</bottom>\n"
    "\t\t\t\t<width>337</width>\n"
    "\t\t\t\t<height>100</height>\n"
    "\t\t\t\t<texture>dialogs/logo.png</texture>\n"
    '\t\t\t\t<animation effect="slide" end="0,-70" time="0" '
    'condition="Skin.HasSetting(touchmode)">Conditional</animation>\n'
    "\t\t\t</control>\n"
)
_LOGO_MEDIAMENU = (
    '\t\t<control type="image">\n'
    "            <left>66.5</left>\n"
    "            <bottom>20</bottom>\n"
    "            <width>337</width>\n"
    "            <height>100</height>\n"
    "            <texture>dialogs/logo.png</texture>\n"
    '            <animation effect="slide" end="0,-70" time="0" '
    'condition="Window.Isvisible(AddonBrowser.xml)">Conditional</animation>\n'
    "\t\t\t<visible>!Player.HasMedia</visible>\n"
    "        </control>\n"
)


def _edit_includes_mediamenu(text: str, path: str) -> str:
    return _replace(text, _LOGO_MEDIAMENU, "", path=path)


def _edit_settingscategory(text: str, path: str) -> str:
    return _replace(text, "<font>font30_title</font>", "<font>font13</font>", path=path)


def _edit_dialogaddonsettings(text: str, path: str) -> str:
    return _replace(text, "<font>font25_title</font>", "<font>font12</font>", path=path)


def _edit_settingsprofile(text: str, path: str) -> str:
    return _replace(
        text, "<font>font30_title</font>", "<font>font13</font>", path=path, count=2
    )


def _edit_startup(text: str, path: str) -> str:
    text = _replace(text, *_SPLASH_NEG, path=path)
    text = _replace(text, *_SPLASH_POS, path=path)
    return text


def _edit_timers(text: str, path: str) -> str:
    return _replace(text, *_SPLASH_NEG, path=path)


def _edit_dialogbuttonmenu(text: str, path: str) -> str:
    # The unset-flags style ("panel"/fullscreen dialog) becomes explicit opt-in.
    text = _replace(
        text,
        "<visible>!Skin.HasSetting(powermenu_iconlist) + !Skin.HasSetting(powermenu_list)</visible>",
        "<visible>Skin.HasSetting(powermenu_panel)</visible>",
        path=path,
    )
    text = _replace(
        text,
        "!Skin.HasSetting(powermenu_list)",
        "!$EXP[PowerMenuList]",
        path=path,
        count=4,
    )
    text = _replace(
        text,
        "Skin.HasSetting(powermenu_list)",
        "$EXP[PowerMenuList]",
        path=path,
        count=2,
    )
    return text


def _edit_dialognotification(text: str, path: str) -> str:
    return _replace(
        text,
        "[Window.IsVisible(DialogButtonMenu.xml) + Skin.HasSetting(powermenu_list)]",
        "[Window.IsVisible(DialogButtonMenu.xml) + $EXP[PowerMenuList]]",
        path=path,
    )


def _edit_custom_tv_widgets(text: str, path: str) -> str:
    for flag in ("recordingchannels", "searches", "allchannels"):
        text = _widget_toggle_invert(text, flag, path)
    return text


def _edit_custom_programs_widgets(text: str, path: str) -> str:
    for flag in ("audioaddons", "gameaddons", "imageaddons"):
        text = _widget_toggle_invert(text, flag, path)
    return text


def _widget_toggle_invert(text: str, flag: str, path: str) -> str:
    text = _replace(
        text,
        "<selected>Skin.HasSetting(hide_{})</selected>".format(flag),
        "<selected>!Skin.HasSetting(show_{})</selected>".format(flag),
        path=path,
    )
    return _replace(
        text,
        "Skin.ToggleSetting(hide_{})".format(flag),
        "Skin.ToggleSetting(show_{})".format(flag),
        path=path,
    )


# MOD V2 prefixes its section headers ("Categories", widget titles, the info
# dialogs' button headers) with an 11px colored chip (frame/puce.png). Stock
# Estuary headers are plain labels (owner decision 2026-07-10: remove them
# all); each header label then shifts left onto the chip's x so it sits flush
# like stock.
_PUCE_HOME = (
    '\t\t\t<control type="image">\n'
    "\t\t\t\t<left>2</left>\n"
    "\t\t\t\t<top>13</top>\n"
    "\t\t\t\t<width>11</width>\n"
    "\t\t\t\t<height>11</height>\n"
    '\t\t\t\t<texture colordiffuse="$VAR[SkinColorVar]">frame/puce.png</texture>\n'
    "\t\t\t</control>\n"
)
_PUCE_HOME_DEEP = _PUCE_HOME.replace("\t\t\t", "\t\t\t\t")
# (sites, header labels per indent variant - counts asserted below)
_PUCE_HOME_PLAN = ((_PUCE_HOME, 4), (_PUCE_HOME_DEEP, 1))
_PUCE_HOME_LABELS = 11  # of 13 <left>22</left> in the file; 2 are unrelated
_PUCE_WINDOW = 1500  # header labels sit well inside; sites are >4000 apart

_PUCE_VIDEOINFO = (
    '\t\t\t<control type="image">\n'
    "\t\t\t\t<left>-2</left>\n"
    "\t\t\t\t<top>10</top>\n"
    "\t\t\t\t<width>11</width>\n"
    "\t\t\t\t<height>11</height>\n"
    '\t\t\t\t<texture colordiffuse="$VAR[SkinColorVar]">frame/puce.png</texture>\n'
    "\t\t\t\t<visible>Control.HasFocus(9004) | Control.HasFocus(5002) | "
    "Control.HasFocus(63000) | Control.HasFocus(50) | Control.HasFocus(5100) | "
    "Control.HasFocus(5200) | Control.HasFocus(5300) | Control.HasFocus(5400) | "
    "Control.HasFocus(5500) | Control.HasFocus(5600) | Control.HasFocus(5700) | "
    "Control.HasFocus(5800) | Control.HasFocus(5900) | Control.HasFocus(6000)"
    "</visible>\n"
    "\t\t\t</control>\n"
)
_PUCE_MUSICINFO = (
    '\t\t\t<control type="image">\n'
    "\t\t\t\t<left>-2</left>\n"
    "\t\t\t\t<top>13</top>\n"
    "\t\t\t\t<width>11</width>\n"
    "\t\t\t\t<height>11</height>\n"
    '\t\t\t\t<texture colordiffuse="$VAR[SkinColorVar]">frame/puce.png</texture>\n'
    "\t\t\t\t<visible>Control.HasFocus(5002) | Control.HasFocus(63000) | "
    "Control.HasFocus(50) | Control.HasFocus(5100)</visible>\n"
    "\t\t\t</control>\n"
)
_PUCE_FULLSCREENINFO = (
    '\t\t\t\t<control type="image">\n'
    "\t\t\t\t\t<top>13</top>\n"
    "\t\t\t\t\t<width>11</width>\n"
    "\t\t\t\t\t<height>11</height>\n"
    '\t\t\t\t\t<texture colordiffuse="$VAR[SkinColorVar]">frame/puce.png</texture>\n'
    "\t\t\t\t\t<visible>Control.HasFocus(5002) | Control.HasFocus(63000) | "
    "Control.HasFocus(50)</visible>\n"
    "\t\t\t\t</control>\n"
)


def _strip_home_header_bullets(text: str, path: str) -> str:
    relabeled = 0
    for block, expected in _PUCE_HOME_PLAN:
        found = text.count(block)
        if found != expected:
            raise TransformError(
                "{}: {} header chips found, expected {}".format(path, found, expected)
            )
        for _ in range(expected):
            i = text.index(block)
            text = text[:i] + text[i + len(block) :]
            window = text[i : i + _PUCE_WINDOW]
            n = window.count("<left>22</left>")
            if n not in (1, 3):
                raise TransformError(
                    "{}: {} header labels near a chip, expected 1 or 3".format(path, n)
                )
            text = (
                text[:i]
                + window.replace("<left>22</left>", "<left>2</left>")
                + text[i + _PUCE_WINDOW :]
            )
            relabeled += n
    if relabeled != _PUCE_HOME_LABELS:
        raise TransformError(
            "{}: shifted {} header labels, expected {}".format(
                path, relabeled, _PUCE_HOME_LABELS
            )
        )
    return text


def _edit_includes_home(text: str, path: str) -> str:
    # Weather-icon fallback (no pack chosen) -> the Outline HD pack.
    text = _replace(
        text,
        "resource://resource.images.weathericons.default/",
        "resource://resource.images.weathericons.outline-hd/",
        path=path,
        count=4,
    )
    return _strip_home_header_bullets(text, path)


def _edit_dialogvideoinfo(text: str, path: str) -> str:
    text = _replace(text, _PUCE_VIDEOINFO, "", path=path)
    return _replace(text, "<left>18</left>", "<left>-2</left>", path=path)


def _edit_dialogmusicinfo(text: str, path: str) -> str:
    text = _replace(text, _PUCE_MUSICINFO, "", path=path)
    return _replace(text, "<left>18</left>", "<left>-2</left>", path=path)


def _edit_dialogfullscreeninfo(text: str, path: str) -> str:
    text = _replace(text, _PUCE_FULLSCREENINFO, "", path=path)
    return _replace(text, "<left>20</left>", "<left>0</left>", path=path)


# Relative path under the skin root -> edit function. Every file listed here
# MUST exist in upstream; a vanished file is upstream drift and fails loudly.
FILE_EDITS = {
    "xml/Home.xml": _edit_home,
    "xml/Settings.xml": _edit_settings,
    "xml/Includes.xml": _edit_includes,
    "xml/Variables.xml": _edit_variables,
    "xml/SkinSettings.xml": _edit_skinsettings,
    "xml/SettingsCategory.xml": _edit_settingscategory,
    "xml/DialogAddonSettings.xml": _edit_dialogaddonsettings,
    "xml/SettingsProfile.xml": _edit_settingsprofile,
    "xml/Startup.xml": _edit_startup,
    "xml/Timers.xml": _edit_timers,
    "xml/DialogButtonMenu.xml": _edit_dialogbuttonmenu,
    "xml/DialogNotification.xml": _edit_dialognotification,
    "xml/Custom_1127_SettingsTVWidgets.xml": _edit_custom_tv_widgets,
    "xml/Custom_1129_SettingsProgramsWidgets.xml": _edit_custom_programs_widgets,
    "xml/Includes_Home.xml": _edit_includes_home,
    "xml/Includes_MediaMenu.xml": _edit_includes_mediamenu,
    "xml/DialogVideoInfo.xml": _edit_dialogvideoinfo,
    "xml/DialogMusicInfo.xml": _edit_dialogmusicinfo,
    "xml/DialogFullScreenInfo.xml": _edit_dialogfullscreeninfo,
}


# ---------------------------------------------------------------------------
# 1. Rebrand
# ---------------------------------------------------------------------------


def rebrand_addon_xml(text: str, version: str, *, path: str = "addon.xml") -> str:
    text = _replace(
        text,
        '<addon id="skin.estuary.modv2" version="21.4+omega.4" '
        'name="Estuary MOD V2 Omega" provider-name="Guilouz, K21 branch by PvD">',
        '<addon id="{sid}" version="{ver}" name="{name}" '
        'provider-name="Tony.7.Bones, Guilouz, PvD (b-jesch), Team Kodi">'.format(
            sid=SKIN_ID, ver=version, name=SKIN_NAME
        ),
        path=path,
    )
    # A python.script extension lists the addon under Program add-ons -
    # Kodi's addons://sources/executable/ node buckets scripts there by TYPE,
    # ignoring <provides> (empty provides was tried and does not help). Stock
    # Estuary has no script extension, so the fork drops it too (owner
    # directive 2026-07-10); every RunScript caller is rewired to the file
    # path instead (see RUNSCRIPT_OLD/NEW in transform_tree). helpers.py
    # itself still ships - it is addon-context-free.
    text = _replace(
        text,
        '\t<extension point="xbmc.python.script" library="scripts/helpers.py" />\n',
        "",
        path=path,
    )
    # The weather-icon pack is baked into XML defaults, so it must resolve as
    # a dependency instead of being a user pick.
    text = _insert_after(
        text,
        '<import addon="script.module.pvr.artwork" version="2.0.0"/>\n',
        '\t\t<import addon="resource.images.weathericons.outline-hd" version="0.0.1"/>\n',
        path=path,
    )
    text = _replace(
        text,
        '<summary lang="en_GB">Estuary MOD V2 skin by Guilouz, adapted for Omega by PvD</summary>',
        '<summary lang="en_GB">Estuary 7 - the Tony.7.Bones fleet skin, '
        "a fork-by-build of Estuary MOD V2 (Omega)</summary>",
        path=path,
    )
    text = _replace(
        text,
        '<description lang="en_GB">Estuary MOD V2 is a mod from Estuary by Guilouz '
        "for Kodi 18 and adapted for Kodi 21 (Omega) by PvD from Kodinerds Community. "
        "It attempts to be easy for first time Kodi users to understand and use.</description>",
        '<description lang="en_GB">Estuary 7 keeps the look and feel of original '
        "Estuary with thin fonts everywhere, built from Estuary MOD V2. Credits: "
        "Estuary MOD V2 by Guilouz, adapted for Kodi 21 (Omega) by PvD / b-jesch "
        "(Kodinerds); Estuary by phil65 and Piers (Team Kodi). "
        "Code GPL-2.0, artwork CC-BY-SA-4.0.</description>",
        path=path,
    )
    text = _replace(
        text,
        "<source>https://github.com/b-jesch/skin.estuary.modv2/tree/Omega</source>",
        "<source>https://github.com/moquette/estuary7</source>",
        path=path,
    )
    text = _replace(
        text,
        "        <news>\nFor a complete view of changes visit "
        "https://github.com/b-jesch/skin.estuary.modv2/tree/Omega\n        </news>",
        "        <news>\nv{}: stock-Estuary alignment - no custom settings tab, "
        "stock category order and artwork, MOD V2 branding and header chips removed, "
        "skin lists only as a skin. Base: fork-by-build of Estuary MOD V2 "
        "21.4+omega.4, no bold anywhere, baked Tony.7.Bones defaults.\n"
        "        </news>".format(version),
        path=path,
    )
    return text


def rename_skin_id(text: str) -> str:
    """Global rename; used for every text file that mentions the upstream id."""
    return text.replace(UPSTREAM_ID, SKIN_ID)


# ---------------------------------------------------------------------------
# 2. Bold sweep
# ---------------------------------------------------------------------------


def sweep_bold_markup(text: str) -> str:
    """Strip literal [B]/[/B] markup - Kodi synthesizes bold for it no matter
    what any fontset binds (the third bold vector; see docs/DESIGN.md)."""
    for tag in BOLD_MARKUP:
        text = text.replace(tag, "")
    return text


# ---------------------------------------------------------------------------
# 3. Font.xml - Estuary weights in the Default fontset only
# ---------------------------------------------------------------------------

_FONT_BLOCK_RE = re.compile(r"<font>.*?</font>", re.DOTALL)
_FONT_NAME_RE = re.compile(r"<name>([^<]+)</name>")
_STYLE_BOLD_LINE = "\t\t\t<style>bold</style>\n"


def transform_font_xml(text: str, *, path: str = "xml/Font.xml") -> str:
    """Re-bind the Default fontset to Estuary weights.

    INVARIANT: the font-id inventory stays byte-identical to upstream - a
    control whose id vanishes falls back SILENTLY to font13. Only faces and
    style tags change here, never names, sizes, or the other fontsets (Arial /
    Arial Unicode MS / Economica are alternates nobody runs; lyrics faces are
    decorative and keep synthetic bold).
    """
    start = text.find('<fontset id="Default"')
    if start == -1:
        raise TransformError("{}: Default fontset not found".format(path))
    end = text.find("<fontset id=", start + 1)
    if end == -1:
        raise TransformError(
            "{}: Default fontset is not followed by another fontset".format(path)
        )
    segment = text[start:end]

    for old_face, new_face, expected in FONT_FACE_SWAPS:
        found = segment.count(old_face)
        if found != expected:
            raise TransformError(
                "{}: {} bound {}x in the Default fontset, expected {}x".format(
                    path, old_face, found, expected
                )
            )
        segment = segment.replace(old_face, new_face)

    removed = 0

    def _neutralize(match: re.Match) -> str:
        nonlocal removed
        block = match.group(0)
        if _STYLE_BOLD_LINE not in block:
            return block
        name = _FONT_NAME_RE.search(block)
        if name and name.group(1).startswith("lyr"):
            return block
        removed += 1
        return block.replace(_STYLE_BOLD_LINE, "")

    segment = _FONT_BLOCK_RE.sub(_neutralize, segment)
    if removed != FONT_STYLE_BOLD_UI_IDS:
        raise TransformError(
            "{}: neutralized {} UI style-bold tags, expected {}".format(
                path, removed, FONT_STYLE_BOLD_UI_IDS
            )
        )
    return text[:start] + segment + text[end:]


def font_id_inventory(text: str) -> list:
    """Every <name> in file order - the silent-fallback invariant's witness."""
    return _FONT_NAME_RE.findall(text)


# ---------------------------------------------------------------------------
# Tree driver
# ---------------------------------------------------------------------------

RENAME_GLOBS = ("xml/*.xml", "scripts/*.py", "language/*/strings.po")

# The skin's helper-script invocations run the FILE, not the addon id, so the
# skin needs no python.script extension (which would list it under Program
# add-ons). Rewired BEFORE the global id rename; the count is a property of
# the pin.
RUNSCRIPT_OLD = "RunScript({},".format(UPSTREAM_ID)
RUNSCRIPT_NEW = "RunScript(special://skin/scripts/helpers.py,"
RUNSCRIPT_SITES = 15


def transform_tree(root: Path, version: str) -> dict:
    """Apply every transform to an extracted upstream tree, in place.

    Returns a summary dict (counts per step). Raises TransformError on any
    missing anchor. Assets (shortcuts, wordmark media, README) are the build
    script's job - this module only rewrites what upstream ships.
    """
    root = Path(root)
    summary = {"edited": [], "renamed": 0, "swept": 0, "runscript": 0}

    # 1. Per-file anchored edits (pristine upstream bytes).
    for rel, edit in sorted(FILE_EDITS.items()):
        target = root / rel
        if not target.is_file():
            raise TransformError("{}: file vanished from upstream".format(rel))
        text = target.read_text(encoding="utf-8")
        text = edit(text, rel)
        target.write_text(text, encoding="utf-8")
        summary["edited"].append(rel)

    # 1b. Helper invocations run the file, not the addon id (must precede the
    # id rename, whose output would otherwise hide these sites).
    for target in sorted((root / "xml").glob("*.xml")):
        text = target.read_text(encoding="utf-8")
        if RUNSCRIPT_OLD in text:
            summary["runscript"] += text.count(RUNSCRIPT_OLD)
            target.write_text(
                text.replace(RUNSCRIPT_OLD, RUNSCRIPT_NEW), encoding="utf-8"
            )
    if summary["runscript"] != RUNSCRIPT_SITES:
        raise TransformError(
            "rewired {} RunScript sites, expected {}".format(
                summary["runscript"], RUNSCRIPT_SITES
            )
        )

    # 2. Rebrand: addon.xml identity, then the global id rename.
    addon_xml = root / "addon.xml"
    addon_xml.write_text(
        rebrand_addon_xml(addon_xml.read_text(encoding="utf-8"), version),
        encoding="utf-8",
    )
    for pattern in RENAME_GLOBS:
        for target in sorted(root.glob(pattern)):
            text = target.read_text(encoding="utf-8")
            if UPSTREAM_ID in text:
                target.write_text(rename_skin_id(text), encoding="utf-8")
                summary["renamed"] += 1

    # 3. Bold sweep over every window XML (Font.xml carries no markup, but
    # sweeping it too is a harmless no-op and keeps the contract simple).
    for target in sorted((root / "xml").glob("*.xml")):
        text = target.read_text(encoding="utf-8")
        if any(tag in text for tag in BOLD_MARKUP):
            target.write_text(sweep_bold_markup(text), encoding="utf-8")
            summary["swept"] += 1

    # 4. Font.xml Estuary weights.
    font_xml = root / "xml" / "Font.xml"
    font_xml.write_text(
        transform_font_xml(font_xml.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return summary
