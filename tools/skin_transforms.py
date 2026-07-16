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
import struct  # noqa: F401 - used by the Textures.xbt shadow (offsets below)
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


def _delete_block(text: str, first: str, last: str, *, path: str) -> str:
    """Delete the span from ``first`` through ``last`` inclusive. Both anchors
    must occur exactly once and in order - same fail-loud contract as
    _replace, for blocks too large to embed as a full literal."""
    for anchor in (first, last):
        found = text.count(anchor)
        if found != 1:
            raise TransformError(
                "{}: block anchor occurs {}x, expected 1x: {!r}".format(
                    path, found, anchor[:120]
                )
            )
    start = text.index(first)
    end = text.index(last)
    if end < start:
        raise TransformError(
            "{}: block anchors out of order: {!r} .. {!r}".format(
                path, first[:60], last[:60]
            )
        )
    return text[:start] + text[end + len(last) :]


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
# an opt-OUT despite its name). Renamed to a plain opt-IN ShowSplashScreen so a
# fresh box boots WITHOUT the splash (owner directive 2026-07-12: no splash by
# default). Still toggleable in Skin Settings; when enabled it shows our
# background.jpg. Negated atom replaced FIRST - the positive atom is its substring.
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

# System-page grid tile chooser: OFF (default) = stock Games card, ON = Skin
# Settings. Read by _SYSTEM_PAGE's mutually-exclusive Games/Skin-Settings items.
_SKINSETTINGS_TILE_TOGGLE = """\t\t\t\t<control type="radiobutton" id="1102">
\t\t\t\t\t<label>Toggle Skin Settings / Games</label>
\t\t\t\t\t<include>DefaultSettingButton</include>
\t\t\t\t\t<onclick>Skin.ToggleSetting(SkinSettingsTile)</onclick>
\t\t\t\t\t<selected>Skin.HasSetting(SkinSettingsTile)</selected>
\t\t\t\t</control>
"""

# "Show labeled tiles" sub-option (owner request 2026-07-15, shipped 1.0.41),
# styled like the PVR-info sub-option above it (indented ∟ label, visible
# only while the parent is on): hide the fork poster fade + label on
# Movies & TV Shows tiles only (see _VIDEO_LABEL_OPTOUT, which the fork
# fade/label controls read per item). Written in POST-FLIP names on purpose -
# step 1c only rewrites the upstream HideWidgetLabels forms, so this block
# passes through untouched. Id 1103 is unused by upstream; default off =
# zero settings writes, the shipped 1.0.40 look.
_VIDEO_LABEL_OPTOUT_TOGGLE = """\t\t\t\t<control type="radiobutton" id="1103">
\t\t\t\t\t<include>DefaultSettingButton</include>
\t\t\t\t\t<label>  ∟Do not apply labels to Movies &amp; TV Shows</label>
\t\t\t\t\t<onclick>Skin.ToggleSetting(hide_video_tile_labels)</onclick>
\t\t\t\t\t<selected>Skin.HasSetting(hide_video_tile_labels)</selected>
\t\t\t\t\t<visible>!Skin.HasSetting(hide_tile_labels)</visible>
\t\t\t\t</control>
"""

# POV search toggle (owner request 2026-07-15, 1.0.42; renamed and moved
# 1.0.43): the home Search popup (Custom_1107) swaps its four provider
# buttons for POV's four search entries when this is on. Only VISIBLE while
# plugin.video.pov is installed AND enabled; the dialog items double-check
# the same condition, so a vanished POV silently falls back to the stock
# popup. Sits in the Home menu pane just above the "Enable background of
# 'Power options' shortcut" toggle (10006). Id 1104 is unused by upstream;
# default off = zero settings writes, stock popup.
_POV_SEARCH_TOGGLE = """\t\t\t\t<control type="radiobutton" id="1104">
\t\t\t\t\t<label>Enable POV search</label>
\t\t\t\t\t<include>DefaultSettingButton</include>
\t\t\t\t\t<onclick>Skin.ToggleSetting(use_pov_search)</onclick>
\t\t\t\t\t<selected>Skin.HasSetting(use_pov_search)</selected>
\t\t\t\t\t<visible>System.AddonIsEnabled(plugin.video.pov)</visible>
\t\t\t\t</control>
"""

# The condition the popup items ride: POV mode is opted in AND POV is
# actually available. Stock items carry the negation, POV items the
# affirmative - the popup always shows exactly four entries.
_POV_SEARCH_ON = (
    "Skin.HasSetting(use_pov_search) + System.AddonIsEnabled(plugin.video.pov)"
)

# POV's four search entries, exactly as its navigator.search menu emits them
# (labels and search_history routes read live from the bench box 2026-07-15;
# each opens POV's search-history page - prior searches plus New Search -
# per owner decision).
_POV_SEARCH_ITEMS = (
    ("Movies", "mode=search_history&amp;action=movie&amp;name=Movies"),
    ("TV Shows", "mode=search_history&amp;action=tvshow&amp;name=TV+Shows"),
    ("People", "mode=search_history&amp;action=people&amp;name=People"),
    (
        "Movies Collection (TMDb)",
        "mode=search_history&amp;action=tmdb_collections"
        "&amp;name=Movies+Collection+%28TMDb%29",
    ),
)


def _edit_searchdialog(text: str, path: str) -> str:
    # Gate each stock provider item on the POV toggle being off (or POV
    # gone). The four items end on distinct lines, so each anchor is unique.
    for tail in (
        "InstallAddon(script.globalsearch)</onclick>",
        "<onclick>ActivateWindow(addonbrowser,addons://search/,return)</onclick>",
        "InstallAddon(plugin.video.youtube)</onclick>",
        "InstallAddon(script.embuary.info)</onclick>",
    ):
        text = _replace(
            text,
            tail + "\n\t\t\t\t\t</item>",
            tail + "\n\t\t\t\t\t\t<visible>![" + _POV_SEARCH_ON + "]</visible>"
            "\n\t\t\t\t\t</item>",
            path=path,
        )
    # Append POV's four search entries, shown only in POV mode.
    pov_items = "".join(
        "\t\t\t\t\t<item>\n"
        "\t\t\t\t\t\t<label>" + label + "</label>\n"
        "\t\t\t\t\t\t<onclick>Dialog.Close(all)</onclick>\n"
        '\t\t\t\t\t\t<onclick>ActivateWindow(videos,"plugin://plugin.video.pov/?'
        + query
        + '",return)</onclick>\n'
        "\t\t\t\t\t\t<visible>" + _POV_SEARCH_ON + "</visible>\n"
        "\t\t\t\t\t</item>\n"
        for label, query in _POV_SEARCH_ITEMS
    )
    return _insert_before(text, "\t\t\t\t</content>\n", pov_items, path=path)


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
    # (8, 31273) "Necessary add-ons" tab removed (owner directive): the
    # fleet installs deps via Setup, not MOD V2's in-skin installer. Its
    # pane (grouplist 300) stays in the XML but is unreachable now that no
    # list item focuses HasFocus(8).
)


def _edit_home(text: str, path: str) -> str:
    # Home window-close transition (owner request 2026-07-15, 1.0.51,
    # "Apple Elegance"): upstream fades only some background groups on
    # WindowClose, so leaving Home for fullscreen video (the 1.0.50
    # back-at-Home path, or any window switch) CUTS the menu/widgets
    # abruptly. These window-level animations dissolve the WHOLE Home UI
    # while it swells slightly toward the viewer - the tvOS "hand off to
    # the content" feel. tvOS-ONLY by owner directive ("the office TV is
    # firetv which shouldn't be touched") - Fire OS keeps stock timing.
    # WindowOpen is untouched (the groups' staggered 400ms fades already
    # read well).
    text = _replace(
        text,
        "\t<controls>\n",
        '\t<animation effect="fade" start="100" end="0" time="260" '
        'tween="sine" easing="out" '
        'condition="System.Platform.TVOS">WindowClose</animation>\n'
        '\t<animation effect="zoom" start="100" end="106" center="960,540" '
        'time="260" tween="sine" easing="out" '
        'condition="System.Platform.TVOS">WindowClose</animation>\n'
        "\t<controls>\n",
        path=path,
    )
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
    # left=78 + left-align pulls "KODI" tight against the diamond (the
    # Estuary-matched gap, owner-verified on the bench 2026-07-10).
    text = _replace(
        text,
        "\t\t\t\t\t<left>55</left>\n"
        "\t\t\t\t\t<top>4</top>\n"
        "\t\t\t\t\t<aspectratio>keep</aspectratio>\n"
        "\t\t\t\t\t<width>202</width>\n"
        "\t\t\t\t\t<height>50</height>\n"
        "\t\t\t\t\t<texture>$VAR[LogoTextVar]</texture>",
        "\t\t\t\t\t<left>78</left>\n"
        "\t\t\t\t\t<top>8</top>\n"
        '\t\t\t\t\t<aspectratio align="left">keep</aspectratio>\n'
        "\t\t\t\t\t<width>202</width>\n"
        "\t\t\t\t\t<height>39</height>\n"
        "\t\t\t\t\t<texture>extras/logo-text-hires.png</texture>",
        path=path,
    )
    # Centered ◆KODI like Estuary, WITHOUT breaking the minimized state: the
    # main logo group keeps its default left=20 (so the lone diamond centers
    # over the icon column when the menu is minimized, the MOD V2 default), and
    # a conditional slide shifts it +70 ONLY when the menu is full - putting the
    # ◆KODI unit at Estuary's left-of-center spot. time=0 = no visible slide.
    # (owner-verified in both states on the bench 2026-07-10). The fallback
    # "clear logo" group is untouched for now - a follow-up mirrors this there.
    text = _replace(
        text,
        "!Skin.HasSetting(MinimizeMainMenu)]]</visible>\n"
        "\t\t\t\t<top>20</top>\n\t\t\t\t<left>20</left>",
        "!Skin.HasSetting(MinimizeMainMenu)]]</visible>\n"
        '\t\t\t\t<animation effect="slide" end="70,0" time="0" '
        'condition="!Skin.HasSetting(MinimizeMainMenu)">Conditional</animation>\n'
        "\t\t\t\t<top>20</top>\n\t\t\t\t<left>20</left>",
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
    # FIRST, unconditionally clear skinshortcuts-isrunning. build_menu no-ops when
    # Window(10000).Property(skinshortcuts-isrunning)=='True'; that flag is left
    # stuck when a build is interrupted by the skin reload during install, and it
    # survives ReloadSkin/addon-restart - only a reboot (or an explicit clear)
    # resets it. A stuck flag is exactly a menu that "won't complete until a hard
    # restart". Clearing it on every Home load (before the build fires) is safe (no
    # build runs concurrently at Home load) and is what the reset helper already
    # does. Then defer the FIRST-per-boot buildxml past Kodi's ~10s "keep this
    # skin?" timer - this also gives the boot service's hash seed its head start
    # (the service seeds in <1s, inside the 15s window, so the deferred buildxml
    # finds a matching hash and no-ops: no rebuild, no ReloadSkin). If the seed
    # loses the race, the ReloadSkin fires AFTER the keep-dialog is answered, so it
    # can't destroy it (the silent-revert bug). The gate is a per-SESSION
    # Home(10000) property, NOT a persisted skin bool (a bool survives
    # uninstall/reinstall and would wrongly skip the defer on a reinstalled box);
    # it is empty at every boot, so the first Home load per session defers and
    # later loads (e.g. after a menu edit) build immediately. The shipped includes
    # render the menu during the wait. The added RunScripts target
    # script.skinshortcuts, not the skin id, so the RunScript rewire (15) is intact.
    text = _replace(
        text,
        "\t<onload>RunScript(script.skinshortcuts,type=buildxml&amp;"
        "mainmenuID=9000&amp;group=mainmenu)</onload>\n",
        "\t<onload>RunScript(special://skin/scripts/helpers.py,seedPVR)</onload>\n"
        "\t<onload>ClearProperty(skinshortcuts-isrunning,10000)</onload>\n"
        '\t<onload condition="String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
        "AlarmClock(t7bbuild,RunScript(script.skinshortcuts,type=buildxml&amp;"
        "mainmenuID=9000&amp;group=mainmenu),00:15,silent)</onload>\n"
        '\t<onload condition="!String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
        "RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;"
        "group=mainmenu)</onload>\n"
        '\t<onload condition="String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
        "SetProperty(t7b_firstbuild_done,1,10000)</onload>\n",
        path=path,
    )
    return text


_HELPERS_ELSE = (
    "        else:\n            xbmc.log('unknown parameter', xbmc.LOGERROR)\n"
)

# Lightweight PVR-visibility seed (no rebuild). Home's onload fires this BEFORE
# the buildxml so donthidepvr=true is set by the time the menu builds, keeping
# Live TV/Radio always-visible like stock even when no PVR client is installed.
# It is the reliable partner to the boot service's seed: the service can start
# late (it is gated on CurrentSkin), so a fresh-install menu could otherwise
# build before donthidepvr is set and drop Live TV/Radio (owner-reported on the
# ATV). Idempotent; only writes when the setting is not already 'true'.
_SEED_PVR_ACTION = (
    "        elif sys.argv[1] == 'seedPVR':\n"
    "            try:\n"
    "                _ss = xbmcaddon.Addon('script.skinshortcuts')\n"
    "                if _ss.getSetting('donthidepvr') != 'true':\n"
    "                    _ss.setSetting('donthidepvr', 'true')\n"
    "                    xbmc.log('estuary7: seedPVR set donthidepvr=true', xbmc.LOGINFO)\n"
    "            except Exception as e:\n"
    "                xbmc.log('estuary7: seedPVR failed: %s' % e, xbmc.LOGWARNING)\n"
)

_RESET_MENU_ACTION = (
    "        elif sys.argv[1] == 'resetMenu':\n"
    "            if xbmcgui.Dialog().yesno('Reset main menu', 'Reset the main menu back to the skin defaults?'):\n"
    "                home = xbmcgui.Window(10000)\n"
    "                report = []\n"
    "                # Clear the stuck build guard + edit caches. skinshortcuts-isrunning lives on\n"
    "                # window 10000 and survives ReloadSkin/addon-restart (cleared only by a reboot);\n"
    "                # a stale 'True' makes every build_menu a silent no-op - the reboot-only bug.\n"
    "                for prop in ('skinshortcuts-isrunning', 'skinshortcuts-loading', 'skinshortcuts-mainmenu', 'skinshortcutsWidgets', 'skinshortcutsCustomProperties', 'skinshortcutsBackgrounds'):\n"
    "                    home.clearProperty(prop)\n"
    "                # skinshortcuts reads/writes menu files with REAL filesystem paths (Python open/\n"
    "                # ETree). On tvOS xbmcvfs special:// operations hit a different layer, so we must\n"
    "                # use translatePath + os here or the builder keeps reading the un-cleaned file.\n"
    "                dirs = set()\n"
    "                for _sp in ('special://profile/addon_data/script.skinshortcuts/', 'special://masterprofile/addon_data/script.skinshortcuts/'):\n"
    "                    dirs.add(xbmcvfs.translatePath(_sp))\n"
    "                defaults = xbmcvfs.translatePath('special://skin/shortcuts/')\n"
    "                target = xbmcvfs.translatePath('special://profile/addon_data/script.skinshortcuts/')\n"
    "                includes = xbmcvfs.translatePath('special://skin/xml/script-skinshortcuts-includes.xml')\n"
    "                wiped = 0\n"
    "                for base in dirs:\n"
    "                    if not os.path.isdir(base):\n"
    "                        continue\n"
    "                    for name in os.listdir(base):\n"
    "                        if name != 'settings.xml' and name.endswith(('.DATA.xml', '.properties', '.hash')):\n"
    "                            try:\n"
    "                                os.remove(os.path.join(base, name))\n"
    "                                wiped += 1\n"
    "                            except Exception:\n"
    "                                pass\n"
    "                report.append('wiped=%i' % wiped)\n"
    "                try:\n"
    "                    if os.path.exists(includes):\n"
    "                        os.remove(includes)\n"
    "                        report.append('inc=del')\n"
    "                    else:\n"
    "                        report.append('inc=absent')\n"
    "                except Exception as e:\n"
    "                    report.append('inc_err=%s' % e)\n"
    "                if not os.path.isdir(target):\n"
    "                    try:\n"
    "                        os.makedirs(target)\n"
    "                    except Exception:\n"
    "                        pass\n"
    "                copied = 0\n"
    "                if os.path.isdir(defaults):\n"
    "                    for name in os.listdir(defaults):\n"
    "                        if name.endswith('.DATA.xml'):\n"
    "                            try:\n"
    "                                with open(os.path.join(defaults, name), 'rb') as _s:\n"
    "                                    _b = _s.read()\n"
    "                                with open(os.path.join(target, name), 'wb') as _d:\n"
    "                                    _d.write(_b)\n"
    "                                copied += 1\n"
    "                            except Exception:\n"
    "                                pass\n"
    "                report.append('copied=%i' % copied)\n"
    "                try:\n"
    "                    xbmcaddon.Addon('script.skinshortcuts').setSetting('donthidepvr', 'true')\n"
    "                    report.append('donthidepvr=true')\n"
    "                except Exception as e:\n"
    "                    report.append('donthidepvr_err=%s' % e)\n"
    "                home.clearProperty('skinshortcuts-isrunning')\n"
    "                home.setProperty('skinshortcuts-reloadmainmenu', 'True')\n"
    "                home.setProperty('t7b_resetmenu', 'reset: ' + ' '.join(report))\n"
    "                xbmc.log('resetMenu: ' + ' '.join(report), xbmc.LOGINFO)\n"
    "                xbmc.executebuiltin('RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&group=mainmenu)')\n"
)

_SYSTEM_PAGE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<window>\n"
    "\t<onunload>RunScript(skin.estuary.modv2,getKodiSetting,lookandfeel.startupaction)</onunload>\n"
    '\t<onunload condition="!String.IsEmpty(Window(home).property(lookandfeel.startupaction)) + !String.IsEqual(Window(home).property(lookandfeel.startupaction),0)">Skin.Reset(ShowSplashScreen)</onunload>\n'
    "\t<onunload>RunScript(skin.estuary.modv2,getKodiSetting,videolibrary.showunwatchedplots)</onunload>\n"
    "\t<defaultcontrol>9000</defaultcontrol>\n"
    "\t<backgroundcolor>background</backgroundcolor>\n"
    "\t<controls>\n"
    "\t\t<include>DefaultBackground</include>\n"
    '\t\t<control type="group">\n'
    "\t\t\t<centerleft>50%</centerleft>\n"
    "\t\t\t<width>1600</width>\n"
    "\t\t\t<top>0</top>\n"
    "\t\t\t<bottom>0</bottom>\n"
    "\t\t\t<include>OpenClose_Right</include>\n"
    '\t\t\t<control type="panel" id="9000">\n'
    "\t\t\t\t<left>0</left>\n"
    "\t\t\t\t<width>100%</width>\n"
    "\t\t\t\t<top>120</top>\n"
    "\t\t\t\t<height>300</height>\n"
    "\t\t\t\t<ondown>9001</ondown>\n"
    "\t\t\t\t<include>SettingsPanel</include>\n"
    "\t\t\t\t<content>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[10003]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(filemanager)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/filemanager.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[24001]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(addonbrowser)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/addons.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[138]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(systeminfo)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/sysinfo.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[31067]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(eventlog)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/eventlog.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t</content>\n"
    "\t\t\t</control>\n"
    '\t\t\t<control type="label">\n'
    "\t\t\t\t<left>0</left>\n"
    "\t\t\t\t<right>0</right>\n"
    "\t\t\t\t<top>420</top>\n"
    "\t\t\t\t<height>50</height>\n"
    "\t\t\t\t<label>$LOCALIZE[5]</label>\n"
    "\t\t\t\t<align>center</align>\n"
    "\t\t\t\t<font>font37</font>\n"
    "\t\t\t\t<textcolor>grey</textcolor>\n"
    "\t\t\t</control>\n"
    '\t\t\t<control type="panel" id="9001">\n'
    "\t\t\t\t<left>0</left>\n"
    "\t\t\t\t<width>100%</width>\n"
    "\t\t\t\t<top>490</top>\n"
    "\t\t\t\t<bottom>0</bottom>\n"
    "\t\t\t\t<onup>9000</onup>\n"
    "\t\t\t\t<include>SettingsPanel</include>\n"
    "\t\t\t\t<content>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[14200]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(PlayerSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/player.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[14211]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(MediaSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/media.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[14204]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(PVRSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/livetv.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[14036]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(ServiceSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/network.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    # Games slot: stock Estuary's Games card by default; a General toggle
    # (Skin.HasSetting(SkinSettingsTile), default off) swaps it to Skin Settings.
    # Mutually exclusive, so the grid always shows exactly eight tiles.
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[15016]</label>\n"
    "\t\t\t\t\t\t<visible>System.GetBool(gamesgeneral.enable) + !Skin.HasSetting(SkinSettingsTile)</visible>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(GameSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/games.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
    "\t\t\t\t\t\t<visible>Skin.HasSetting(SkinSettingsTile)</visible>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(SkinSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/skin.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[14206]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(InterfaceSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/interface.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[13200]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(Profiles)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/profiles.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[13000]</label>\n"
    "\t\t\t\t\t\t<onclick>ActivateWindow(SystemSettings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/system.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>LibreELEC</label>\n"
    "\t\t\t\t\t\t<visible>System.HasAddon(service.libreelec.settings)</visible>\n"
    "\t\t\t\t\t\t<onclick>RunAddon(service.libreelec.settings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/libreelec.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>CoreELEC</label>\n"
    "\t\t\t\t\t\t<visible>System.HasAddon(service.coreelec.settings)</visible>\n"
    "\t\t\t\t\t\t<onclick>RunAddon(service.coreelec.settings)</onclick>\n"
    "\t\t\t\t\t\t<icon>icons/settings/coreelec.png</icon>\n"
    "\t\t\t\t\t</item>\n"
    "\t\t\t\t</content>\n"
    "\t\t\t</control>\n"
    "\t\t</control>\n"
    '\t\t<include content="TopBar">\n'
    '\t\t\t<param name="breadcrumbs_label" value="$LOCALIZE[5]" />\n'
    "\t\t</include>\n"
    "\t\t<include>BottomBar</include>\n"
    "\t</controls>\n"
    "</window>\n"
)

_MEDIA_SOURCES_BLOCK = (
    '\t\t\t\t<control type="label" id="900020">\n'
    "\t\t\t\t\t<textoffsetx>45</textoffsetx>\n"
    "\t\t\t\t\t<top>0</top>\n"
    "\t\t\t\t\t<height>80</height>\n"
    "\t\t\t\t\t<label>$LOCALIZE[31201]</label>\n"
    "\t\t\t\t\t<align>center</align>\n"
    "\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t<font>font28_title</font>\n"
    "\t\t\t\t\t<textcolor>grey</textcolor>\n"
    "\t\t\t\t\t<shadowcolor>black</shadowcolor>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="520">\n'
    "\t\t\t\t\t<label>$LOCALIZE[3]</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>ActivateWindow(Videos,Files,return)</onclick>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="521">\n'
    "\t\t\t\t\t<label>$LOCALIZE[2]</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>ActivateWindow(Music,Files,return)</onclick>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="522">\n'
    "\t\t\t\t\t<label>$LOCALIZE[1]</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>ActivateWindow(pictures,root)</onclick>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="523">\n'
    "\t\t\t\t\t<label>$LOCALIZE[15016]</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>ActivateWindow(games,root)</onclick>\n"
    "\t\t\t\t\t<visible>System.GetBool(gamesgeneral.enable)</visible>\n"
    "\t\t\t\t</control>\n"
)

_DEBUG_HEADER_ANCHOR = '\t\t\t\t<control type="label" id="900014">'


def _edit_settings(text: str, path: str) -> str:
    """Replace upstream's single scrolling 5-column System page with the
    owner-approved stock-style 4x3 grid (see _SYSTEM_PAGE): a fixed top
    utility row (File manager, Add-ons, System info, Event log), a "Settings"
    divider, then one non-scrolling block of eight category tiles. The Games
    slot shows stock Estuary's Games card by default; the General toggle
    'Toggle Skin Settings / Games' (Skin.HasSetting(SkinSettingsTile), default
    off) swaps that one tile to Skin Settings. The MOD V2 "Media sources" tile
    is gone,
    relocated into Skin Settings > Extras (see _MEDIA_SOURCES_BLOCK). The two
    onunload RunScripts keep upstream's addon-id form so the global rewiring
    converts them (the count-15 contract); the splash onunload resets the opt-in
    ShowSplashScreen flag. Fail loud if the upstream page is not the shape we
    redesigned from."""
    for anchor in (
        "<onclick>ActivateWindow(1120)</onclick>",  # MOD V2 "Media sources" tile
        "<width>1900</width>",  # the single 5-column panel group
        "RunScript(skin.estuary.modv2,getKodiSetting,lookandfeel.startupaction)",
    ):
        if anchor not in text:
            raise TransformError(
                "{}: upstream System page drifted (missing {!r})".format(path, anchor)
            )
    return _SYSTEM_PAGE


def _edit_includes(text: str, path: str) -> str:
    # Classic-list power menu is the fresh-box default (see _POWERMENU_EXPR).
    text = _insert_before(
        text, '\t<expression name="EnableTheme">', _POWERMENU_EXPR, path=path
    )
    text = _replace(text, *_THEMES_NEG, path=path, count=6)
    for old, new, count in _WEATHERINFO_INCLUDES:
        text = _replace(text, old, new, path=path, count=count)
    # System-page tiles: match stock Estuary's 400-wide SettingsPanel cell so 4
    # columns fill the redesigned System page's 1600 container exactly - centered,
    # like stock. MOD V2 sized these for its 5-column 1900 layout (cell 380, bg
    # 390, label left 15); in our 1600/4-column container that left the grid 80px
    # short on the right AND each tile's content ~10px left of centre. Stock's
    # values (cell 400; bg 410, which at left -5 centres in the 400 cell; label
    # left 25) fix both. Only Settings.xml uses SettingsPanel (itemlayout at 4
    # tabs, focusedlayout at 5), so this is contained to the System page.
    text = _replace(
        text, 'height="260" width="380"', 'height="260" width="400"', path=path, count=2
    )
    text = _replace(
        text, "<width>390</width>", "<width>410</width>", path=path, count=2
    )
    text = _replace(
        text,
        "\t\t\t\t<left>15</left>\n\t\t\t\t<top>190</top>\n\t\t\t\t<width>350</width>",
        "\t\t\t\t<left>25</left>\n\t\t\t\t<top>190</top>\n\t\t\t\t<width>350</width>",
        path=path,
    )
    text = _replace(
        text,
        "\t\t\t\t\t<left>15</left>\n\t\t\t\t\t<top>190</top>\n\t\t\t\t\t<width>350</width>",
        "\t\t\t\t\t<left>25</left>\n\t\t\t\t\t<top>190</top>\n\t\t\t\t\t<width>350</width>",
        path=path,
    )
    # Focus highlight (the two focusedlayout overlays: SkinColorVar sky-blue +
    # GradientColorVar) was sized -11/402/282 with a -6 top for MOD V2's 380 cell,
    # so on the 400 cell it sits left, bleeds dark on the right, and reads slightly
    # larger than the tile. Match the tile background (and stock's focus): -5/410
    # /270, no top offset, so the highlight covers the tile exactly and centred.
    text = _replace(
        text,
        "\t\t\t\t\t<top>-6</top>\n\t\t\t\t\t<left>-11</left>\n"
        "\t\t\t\t\t<width>402</width>\n\t\t\t\t\t<height>282</height>",
        "\t\t\t\t\t<left>-5</left>\n\t\t\t\t\t<width>410</width>\n"
        "\t\t\t\t\t<height>270</height>",
        path=path,
        count=2,
    )
    # Top-bar weather icon: the official Outline HD resource pack replaces the
    # skin-local PNG set.
    # Top-bar weather icon: upstream's special://skin/extras/weather/ default
    # path stays UNTOUCHED since 1.0.46 - the build ships the vendored
    # Outline HD set at that exact path (see build_skin.add_assets), so the
    # stock default IS the owner's look with no resource-pack download.
    # (1.0.1-1.0.45 rewrote this texture to the outline-hd resource URL.)
    text = _replace(
        text,
        "[Window.IsVisible(shutdownmenu) + Skin.HasSetting(powermenu_list)]",
        "[Window.IsVisible(shutdownmenu) + $EXP[PowerMenuList]]",
        path=path,
        count=3,
    )
    # The finish-time flag is hard-suppressed in plugin-browsed windows
    # (owner-caught 2026-07-15: home widgets showed duration + finish + date,
    # the same item's "More" plugin list dropped the finish badge). Upstream
    # bolted !String.StartsWith(Container.FolderPath,plugin://) onto all four
    # end-time flag groups (short + AM/PM variants in MediaFlags and
    # MediaFlagsInfoDialogRight) - no other flag has it, so the bar goes
    # inconsistent the moment a widget's list opens. Drop the term; the
    # groups keep their real gates (end-time present, not a folder, the
    # show_mediaendtimeflag opt-out). The View_*/Variables plugin:// sites
    # gate unrelated features (spoiler plots, artist variants) and stay.
    text = _replace(
        text,
        "!String.StartsWith(Container.FolderPath,plugin://) + ",
        "",
        path=path,
        count=4,
    )
    # The media-flags bar's TMDB/IMDb rating badge ignores its own toggle
    # (upstream bug, owner-caught on the bench 2026-07-15): the flags dialog
    # (Custom_1137) writes show_tmdbflag and every OTHER flag checks its
    # setting, but the two rating MediaFlag sites never got the term - only
    # the 5px spacer beside them honors it. Add the gate so "TMDB rating"
    # off actually hides the badge, both logo variants.
    for prefix in ("!Skin.HasSetting(use_imdblogo)", "Skin.HasSetting(use_imdblogo)"):
        text = _replace(
            text,
            '<param name="visible" value="' + prefix + " + "
            "!String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            '<param name="visible" value="!Skin.HasSetting(show_tmdbflag) + '
            + prefix
            + " + !String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            path=path,
            count=1,
        )
    return text


# The view-picker dialog's image-lookup variable: 89 focus-conditioned
# extras/views thumbnail paths plus the themes/splash.png fallthrough. Dead
# once _edit_includes_mediamenu unreaches Custom_1131; deleting it removes the
# skin's last reference to the trimmed extras/views AND to the MOD V2 splash
# art. Public (not _-prefixed): test_golden_parity applies the same deletion
# to normalize the golden.
_VIEWS_VAR_FIRST = '\t<variable name="SettingsViewsImagesVar">\n'
_VIEWS_VAR_LAST = "\t\t<value>themes/splash.png</value>\n\t</variable>\n"


def drop_settings_views_variable(text: str, *, path: str = "xml/Variables.xml") -> str:
    return _delete_block(text, _VIEWS_VAR_FIRST, _VIEWS_VAR_LAST, path=path)


def _edit_variables(text: str, path: str) -> str:
    text = drop_settings_views_variable(text, path=path)
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
    # 'Toggle Skin Settings / Games' - swaps the System-page Games tile for a
    # Skin Settings tile (owner request; default off = Games). Same General
    # pane, just above the default-OSD button (id 703).
    text = _insert_before(
        text,
        '\t\t\t\t<control type="button" id="703">\n',
        _SKINSETTINGS_TILE_TOGGLE,
        path=path,
    )
    # "Add media sources" launcher (Videos/Music/Pictures/Games file
    # browsers) in the Extras category pane, directly above the Debug
    # section - the relocated home for the System page's old Media sources
    # tile (owner directive). Anchored on upstream's Debug header label.
    text = _insert_before(text, _DEBUG_HEADER_ANCHOR, _MEDIA_SOURCES_BLOCK, path=path)
    # The reset button calls OUR helper: skinshortcuts 2.0.3's resetall is
    # broken for this skin (see _edit_helpers) and silently deletes nothing.
    text = _replace(
        text,
        "\t\t\t\t\t<onclick>RunScript(script.skinshortcuts,type=resetall)</onclick>",
        "\t\t\t\t\t<onclick>RunScript(special://skin/scripts/helpers.py,resetMenu)</onclick>",
        path=path,
    )
    # Rename the garbled upstream widget-labels toggle (id 10021,
    # "Show media names with widgets names" - doubled "names", reads
    # backwards) to a clear "Show labeled tiles". Wiring is already correct:
    # checked = labels shown (selected = !HasSetting(HideWidgetLabels)).
    text = _replace(
        text,
        "\t\t\t\t\t<label>$LOCALIZE[31468]</label>",
        "\t\t\t\t\t<label>Show labeled tiles</label>",
        path=path,
    )
    # The flag is inverted vs its name (HideWidgetLabels=true SHOWS labels,
    # bench-proven), so upstream's selected=!HasSetting rendered the switch
    # BACKWARDS (OFF while labels shown - owner caught it). Flip selected so
    # "Show labeled tiles" ON = labels shown, and the PVR sub-option shows
    # when the parent is on.
    text = _replace(
        text,
        "\t\t\t\t\t<selected>!Skin.HasSetting(HideWidgetLabels)</selected>",
        "\t\t\t\t\t<selected>Skin.HasSetting(HideWidgetLabels)</selected>",
        path=path,
    )
    text = _replace(
        text,
        "\t\t\t\t\t<visible>!Skin.HasSetting(HideWidgetLabels)</visible>",
        "\t\t\t\t\t<visible>Skin.HasSetting(HideWidgetLabels)</visible>",
        path=path,
    )
    # New sub-option under "Show labeled tiles", after the PVR-info
    # sub-option (10022) and before the next stock toggle (10014): hide the
    # fork poster labels on Movies & TV Shows tiles only (see
    # _VIDEO_LABEL_OPTOUT_TOGGLE).
    text = _insert_before(
        text,
        '\t\t\t\t<control type="radiobutton" id="10014">\n',
        _VIDEO_LABEL_OPTOUT_TOGGLE,
        path=path,
    )
    # POV search toggle, just above the Power-options background toggle
    # (see _POV_SEARCH_TOGGLE).
    text = _insert_before(
        text,
        '\t\t\t\t<control type="radiobutton" id="10006">\n',
        _POV_SEARCH_TOGGLE,
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
    # Extras declutter (owner directive 2026-07-15, 1.0.46): the splash
    # CLUSTER leaves Skin Settings entirely - the "Enable Splash Screen"
    # toggle (503) plus its two gated sub-rows (504 splash background, 505
    # splash image picker). Startup.xml still honors ShowSplashScreen for a
    # box that set it before the toggle vanished; a fresh box has no splash
    # (the 2026-07-12 default) and no switch. This replaces the 1.0.32-era
    # selected/onclick rewrites, whose anchors lived inside these rows.
    text = _delete_block(
        text,
        '\t\t\t\t<control type="radiobutton" id="503">\n',
        "<visible>!Skin.HasSetting(EnableSplashScreen) + "
        "!Skin.HasSetting(enable_splash_background) + "
        "String.IsEqual(Window(home).property(lookandfeel.startupaction),0)"
        "</visible>\n\t\t\t\t</control>\n",
        path=path,
    )
    # "Enable themes" toggle (506) leaves too: 1.0.44 trimmed the seasonal
    # art packs, so the toggle could only enable artless themes. The
    # EnableThemes expressions stay inert; a fresh box never sets the flag.
    text = _replace(
        text,
        '\t\t\t\t<control type="radiobutton" id="506">\n'
        "\t\t\t\t\t<label>$LOCALIZE[31459]</label>\n"
        "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
        "\t\t\t\t\t<onclick>Skin.ToggleSetting(DisableThemes)</onclick>\n"
        "\t\t\t\t\t<selected>!Skin.HasSetting(DisableThemes)</selected>\n"
        "\t\t\t\t</control>\n",
        "",
        path=path,
    )
    # "Kodi/Distribution Logo" chooser (10023) leaves the Home menu pane
    # (owner directive 2026-07-15: "It should only be Kodi"): the fork ships
    # the stock Kodi wordmark and offers no LibreELEC/CoreELEC variants. The
    # MenuLogo* bools stay unset on the fleet, so the default renders.
    text = _replace(
        text,
        '\t\t\t\t<control type="button" id="10023">\n'
        "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
        "\t\t\t\t\t<description>menu logo</description>\n"
        "\t\t\t\t\t<onclick>Skin.SelectBool(31567, 15109|MenuLogoDefault, "
        "31568|MenuLogoLE, 31569|MenuLogoCE)</onclick>\n"
        "\t\t\t\t\t<label>$LOCALIZE[31567]</label>\n"
        "\t\t\t\t\t<label2>$VAR[Label_SkinSetting_Logo]</label2>\n"
        "\t\t\t\t</control>\n",
        "",
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


# MOD V2 splits stock Estuary's single Viewtype button into a pair: 6051 keeps
# the stock Container.NextViewMode cycle for non-library content, 60511 opens
# the custom view-picker dialog (Custom_1131) for library content. The picker
# existed to show preview thumbnails (extras/views, 49MB) that this build
# trims, leaving it rendering its MOD V2 splash-art fallback instead (owner
# report 2026-07-15). Restore the stock button - one Viewtype entry, label
# 31023, cycle on click (THE FIRST MANDATE) - so the dialog is unreachable;
# build_skin.py TRIM_PATHS then drops the dialog XML and the splash art, and
# _edit_variables drops the picker's dead image-lookup variable.
_VIEW_BUTTONS_MODV2 = (
    '\t\t\t<control type="button" id="6051">\n'
    "\t\t\t\t<include>MediaMenuItemsCommon</include>\n"
    "\t\t\t\t<label>$LOCALIZE[31347]</label>\n"
    "\t\t\t\t<label2>[B]$INFO[Container.Viewmode][/B]</label2>\n"
    "\t\t\t\t<visible>Integer.IsGreater(Container.ViewCount,1)</visible>\n"
    "\t\t\t\t<onclick>Container.NextViewMode</onclick>\n"
    "\t\t\t\t<visible>!Container.Content(movies) + !Container.Content(sets) + "
    "!Container.Content(tvshows) + !Container.Content(seasons) + "
    "!Container.Content(episodes) + !Container.Content(musicvideos) + "
    "!Container.Content(artists) + !Container.Content(albums) + "
    "!Container.Content(images)</visible>\n"
    "\t\t\t</control>\n"
    '\t\t\t<control type="button" id="60511">\n'
    "\t\t\t\t<include>MediaMenuItemsCommon</include>\n"
    "\t\t\t\t<label>$LOCALIZE[31347]</label>\n"
    "\t\t\t\t<label2>[B]$INFO[Container.Viewmode][/B]</label2>\n"
    "\t\t\t\t<visible>Integer.IsGreater(Container.ViewCount,1)</visible>\n"
    "\t\t\t\t<onclick>SetFocus(50)</onclick>\n"
    "\t\t\t\t<onclick>ActivateWindow(1131)</onclick>\n"
    "\t\t\t\t<visible>Container.Content(movies) | Container.Content(sets) | "
    "Container.Content(tvshows) | Container.Content(seasons) | "
    "Container.Content(episodes) | Container.Content(musicvideos) | "
    "Container.Content(artists) | Container.Content(albums) | "
    "Container.Content(images)</visible>\n"
    "\t\t\t</control>\n"
)
# Stock Estuary Omega's button (xbmc/xbmc Omega Includes_MediaMenu.xml), with
# the label2 [B] markup pre-stripped per the no-bold mandate.
_VIEW_BUTTON_STOCK = (
    '\t\t\t<control type="button" id="6051">\n'
    "\t\t\t\t<include>MediaMenuItemsCommon</include>\n"
    "\t\t\t\t<label>$LOCALIZE[31023]</label>\n"
    "\t\t\t\t<label2>$INFO[Container.Viewmode]</label2>\n"
    "\t\t\t\t<visible>Integer.IsGreater(Container.ViewCount,1)</visible>\n"
    "\t\t\t\t<onclick>Container.NextViewMode</onclick>\n"
    "\t\t\t</control>\n"
)


def _edit_includes_mediamenu(text: str, path: str) -> str:
    text = _replace(text, _LOGO_MEDIAMENU, "", path=path)
    text = _replace(text, _VIEW_BUTTONS_MODV2, _VIEW_BUTTON_STOCK, path=path)
    # The EPG genre-colors cycle loses its "genre artwork" mode (20190): its
    # 4.9MB image set is trimmed (1.0.44, owner-approved - unused on the
    # fleet). Cycle becomes defined-colors <-> converted-colors, and a stale
    # genrecolors=20190 falls out of the guard's valid list, resetting to
    # defined colors on the next click.
    text = _replace(
        text,
        " + !String.IsEqual(Skin.String(genrecolors),20190)]"
        '">Skin.SetString(genrecolors,1223)</onclick>',
        ']">Skin.SetString(genrecolors,1223)</onclick>',
        path=path,
    )
    text = _replace(
        text,
        '<onclick condition="String.IsEqual(Skin.String(genrecolors),571)">'
        "Skin.SetString(genrecolors,20190)</onclick>",
        '<onclick condition="String.IsEqual(Skin.String(genrecolors),571)">'
        "Skin.SetString(genrecolors,1223)</onclick>",
        path=path,
    )
    return _replace(
        text,
        '\t\t\t\t\t<onclick condition="String.IsEqual(Skin.String(genrecolors),'
        '20190)">Skin.SetString(genrecolors,1223)</onclick>\n',
        "",
        path=path,
    )


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
    # Our splash art: full-screen background.jpg at full opacity (stock's
    # semi-transparent logo becomes the owner's photo). Shipped by add_assets.
    text = _replace(
        text,
        '<texture colordiffuse="BFFFFFFF">special://skin/extras/themes/splash.png</texture>',
        '<texture colordiffuse="FFFFFFFF">special://skin/extras/themes/t7b-splash.jpg</texture>',
        path=path,
    )
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
    # Prepend 'Skin settings' as the FIRST power-menu item (owner request),
    # opening this skin's settings window. The power menu is a static list here
    # (not skinshortcuts-driven), with one <content> per display mode (panel /
    # iconlist / default); insert into all three so it leads regardless of mode.
    # tvOS: the icon MUST be a loose special://skin file, NOT a bundle-relative
    # Textures.xbt path. 1.0.28 used icons/settings/skin.png (bundle) here and it
    # CRASHED Kodi on the Apple TV the instant the power menu opened (fine on
    # macOS; ATV kodi.log showed DialogButtonMenu.xml load then a native
    # shutdown). Every other power-menu item uses a loose
    # special://skin/extras/icons/... file; matching that fixes it (1.0.29).
    # 'Customize Main Menu' LEADS (owner request 2026-07-15; order swapped
    # and title-cased in 1.0.48 - the literal label matches the adjacent
    # "Skin Settings" and costs nothing since 1.0.44 trimmed to English
    # only), opening the skinshortcuts menu editor directly - the same
    # action as Skin Settings > Home menu > Customize main menu. Same
    # loose-icon rule as above; skinshortcuts is a hard manifest import, so
    # no InstallAddon guard is needed.
    text = _replace(
        text,
        "\t\t\t\t<content>\n",
        "\t\t\t\t<content>\n"
        "\t\t\t\t\t<item>\n"
        "\t\t\t\t\t\t<label>Customize Main Menu</label>\n"
        "\t\t\t\t\t\t<icon>special://skin/extras/icons/controlpanel.png</icon>\n"
        "\t\t\t\t\t\t<onclick>dialog.close(all,true)</onclick>\n"
        "\t\t\t\t\t\t<onclick>RunScript(script.skinshortcuts,"
        "type=manage&amp;group=mainmenu)</onclick>\n"
        "\t\t\t\t\t</item>\n"
        "\t\t\t\t\t<item>\n"
        "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
        "\t\t\t\t\t\t<icon>special://skin/extras/icons/skinsettings.png</icon>\n"
        "\t\t\t\t\t\t<onclick>dialog.close(all,true)</onclick>\n"
        "\t\t\t\t\t\t<onclick>ActivateWindow(SkinSettings)</onclick>\n"
        "\t\t\t\t\t</item>\n",
        path=path,
        count=3,
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


# Home widget tiles, labeled mode (owner request 2026-07-15): poster items
# render the CLEAN full poster with a label BELOW it. Upstream's generic
# 'Widget' include - the include every skinshortcuts home widget row on the
# fleet instantiates - stacks InfoWallMovieLayout (full-bleed poster) UNDER
# the labeled InfoWallMusicLayout chrome in its itemlayout (its own
# focusedlayout and WidgetListPoster gate that pair mutually exclusively; the
# itemlayout forgot the condition). Labeled mode therefore drew a poster with
# a second square-fit copy and dark side bars superimposed - invisible on
# upstream's unlabeled default, exposed by our labeled default, and
# owner-rejected on the bench. Even with the stack fixed, the intended
# labeled design (InfoWallMusicLayout alone) is a square-fit thumb with dark
# side bars - also owner-rejected for posters. The fork instead splits the
# labeled tile PER ITEM: poster-art items get InfoWallMovieLayout's poster
# plus a fork-authored label under it; no-poster items (music, genres,
# categories) keep the stock square look byte-for-byte. The split rides
# <control type="group"> visibility, NEVER include conditions - Kodi resolves
# include conditions once at window load with no item context (the withdrawn
# first 1.0.40 attempt's hardware lesson, see TASKS.md).
_POSTER_EMPTY = (
    "[String.IsEmpty(ListItem.Art(poster)) + "
    "String.IsEmpty(ListItem.Art(tvshow.poster)) + "
    "String.IsEmpty(ListItem.Art(season.poster)) + "
    "String.IsEmpty(ListItem.Art(animatedposter))]"
)

# The 1103 sub-toggle's per-item gate (owner request 2026-07-15, wired as
# 1.0.41): 'Do not apply labels to Movies & TV Shows' hides the fork fade +
# label on video-library items only. Safe where the withdrawn first 1.0.40
# attempt was not: the fade and label are fork-authored CONTROLS gated by
# per-item <visible> conditions - the poster art renders identically either
# way, so no include-condition split can desynchronize. Default off = the
# owner's shipped 1.0.40 look, zero settings writes.
_VIDEO_LABEL_OPTOUT = (
    "![Skin.HasSetting(hide_video_tile_labels) + ["
    "String.IsEqual(ListItem.DBType,movie) | "
    "String.IsEqual(ListItem.DBType,set) | "
    "String.IsEqual(ListItem.DBType,tvshow) | "
    "String.IsEqual(ListItem.DBType,season) | "
    "String.IsEqual(ListItem.DBType,episode)]]"
)

# The upstream labeled-mode include run of the 486-tall widget layouts
# (generic Widget + WidgetListPoster; WidgetPanelPoster's focused run is
# excluded by anchoring on the Animation_FocusBounce line, see below).
_ANIM_BOUNCE_LINE = (
    '\t\t\t\t\t\t<include content="Animation_FocusBounce" '
    'condition="!Skin.HasSetting(no_animations)" />\n'
)


def _widget_movie_include(focused: bool, condition: str = "") -> str:
    cond = ' condition="{}"'.format(condition) if condition else ""
    return (
        '\t\t\t\t\t\t<include content="InfoWallMovieLayout"{}>\n'
        '\t\t\t\t\t\t\t<param name="focused" value="{}" />\n'
        "\t\t\t\t\t\t</include>\n".format(cond, "true" if focused else "false")
    )


def _widget_labeled_run(focused: bool) -> str:
    f = "true" if focused else "false"
    return (
        '\t\t\t\t\t\t<include content="InfoWallMusicLayout" condition="Skin.HasSetting(HideWidgetLabels) + Skin.HasSetting(hide_pubyear)">\n'
        '\t\t\t\t\t\t\t<param name="single_label" value="$VAR[ListLabelVar]$INFO[ListItem.Year, (,)]" />\n'
        '\t\t\t\t\t\t\t<param name="focused" value="' + f + '" />\n'
        '\t\t\t\t\t\t\t<param name="fallback_image" value="$PARAM[fallback_icon]" />\n'
        "\t\t\t\t\t\t</include>\n"
        '\t\t\t\t\t\t<include content="InfoWallMusicLayout" condition="Skin.HasSetting(HideWidgetLabels) + !Skin.HasSetting(hide_pubyear)">\n'
        '\t\t\t\t\t\t\t<param name="single_label" value="$VAR[ListLabelVar]" />\n'
        '\t\t\t\t\t\t\t<param name="focused" value="' + f + '" />\n'
        '\t\t\t\t\t\t\t<param name="fallback_image" value="$PARAM[fallback_icon]" />\n'
        "\t\t\t\t\t\t</include>\n"
        '\t\t\t\t\t\t<include content="InfoWallProgressLayout" condition="Skin.HasSetting(HideWidgetLabels)">\n'
        '\t\t\t\t\t\t\t<param name="top" value="350" />\n'
        '\t\t\t\t\t\t\t<param name="top_2" value="378" />\n'
        '\t\t\t\t\t\t\t<param name="left" value="20" />\n'
        '\t\t\t\t\t\t\t<param name="width" value="275" />\n'
        "\t\t\t\t\t\t</include>\n"
    )


def _widget_poster_label(focused: bool, with_year: bool) -> str:
    # Mirrors InfoWallMusicLayout's tile label (font12, centered, year
    # appended per the same hide_pubyear split) at the STOCK vertical
    # position - the bottom band of the tile (bench-compared screenshots:
    # the old label center sat at y~330). The poster fills the tile
    # (visible art 35..285 x 10..370, bordersize 20 off 15/-10/290x400), so
    # the label rides ON its bottom 70px over the fade texture
    # InfoWallMovieLayout already uses for its episode-count band.
    return (
        '\t\t\t\t\t\t<control type="textbox">\n'
        "\t\t\t\t\t\t\t<left>35</left>\n"
        "\t\t\t\t\t\t\t<top>300</top>\n"
        "\t\t\t\t\t\t\t<width>250</width>\n"
        "\t\t\t\t\t\t\t<height>70</height>\n"
        "\t\t\t\t\t\t\t<font>font12</font>\n"
        "\t\t\t\t\t\t\t<align>center</align>\n"
        "\t\t\t\t\t\t\t<aligny>center</aligny>\n"
        "\t\t\t\t\t\t\t<label>$VAR[ListLabelVar]{}</label>\n".format(
            "$INFO[ListItem.Year, (,)]" if with_year else ""
        )
        + (
            '\t\t\t\t\t\t\t<autoscroll delay="1000" time="1000" repeat="1000">true</autoscroll>\n'
            if focused
            else ""
        )
        + "\t\t\t\t\t\t\t<visible>!"
        + _POSTER_EMPTY
        + "</visible>\n"
        "\t\t\t\t\t\t\t<visible>Skin.HasSetting(HideWidgetLabels) + "
        + ("" if with_year else "!")
        + "Skin.HasSetting(hide_pubyear)</visible>\n"
        "\t\t\t\t\t\t\t<visible>" + _VIDEO_LABEL_OPTOUT + "</visible>\n"
        "\t\t\t\t\t\t</control>\n"
    )


def _widget_poster_label_fade() -> str:
    # The dark fade band the label sits on (the texture InfoWallMovieLayout
    # uses for its episode-count band, full strength and taller per owner
    # taste 2026-07-15), spanning the drawn poster width so it reads as part
    # of the artwork. The label textbox sits in its lower 70px.
    return (
        '\t\t\t\t\t\t<control type="image">\n'
        "\t\t\t\t\t\t\t<left>35</left>\n"
        "\t\t\t\t\t\t\t<top>220</top>\n"
        "\t\t\t\t\t\t\t<width>250</width>\n"
        "\t\t\t\t\t\t\t<height>150</height>\n"
        "\t\t\t\t\t\t\t<texture>overlays/overlayfade.png</texture>\n"
        "\t\t\t\t\t\t\t<visible>!" + _POSTER_EMPTY + "</visible>\n"
        "\t\t\t\t\t\t\t<visible>Skin.HasSetting(HideWidgetLabels)</visible>\n"
        "\t\t\t\t\t\t\t<visible>" + _VIDEO_LABEL_OPTOUT + "</visible>\n"
        "\t\t\t\t\t\t</control>\n"
    )


def _widget_poster_label_fix(text: str, focused: bool, *, path: str) -> str:
    """Wrap the labeled square chrome in a per-item no-poster group and add
    the poster labels. Anchored on the exact upstream run; count=2 = the
    generic Widget + WidgetListPoster layouts."""
    run = _widget_labeled_run(focused)
    wrapped = (
        '\t\t\t\t\t\t<control type="group">\n'
        "\t\t\t\t\t\t\t<visible>"
        + _POSTER_EMPTY
        + "</visible>\n"
        + run
        + "\t\t\t\t\t\t</control>\n"
        + _widget_poster_label_fade()
        + _widget_poster_label(focused, True)
        + _widget_poster_label(focused, False)
    )
    if focused:
        # The focused layouts' labeled mode dropped InfoWallMovieLayout via a
        # load-time include condition; poster items need it back. Add it in a
        # per-item poster-present group; the Animation_FocusBounce anchor
        # scopes the edit to Widget/WidgetListPoster (WidgetPanelPoster uses
        # a raw <animation> block and keeps its stock focused design).
        movie = _widget_movie_include(True, "!Skin.HasSetting(HideWidgetLabels)")
        old = _ANIM_BOUNCE_LINE + movie + run
        new = (
            _ANIM_BOUNCE_LINE
            + movie
            + '\t\t\t\t\t\t<control type="group">\n'
            + "\t\t\t\t\t\t\t<visible>!"
            + _POSTER_EMPTY
            + "</visible>\n"
            + _widget_movie_include(True, "Skin.HasSetting(HideWidgetLabels)")
            + "\t\t\t\t\t\t</control>\n"
            + wrapped
        )
        return _replace(text, old, new, path=path, count=2)
    return _replace(text, run, wrapped, path=path, count=2)


def _edit_includes_home(text: str, path: str) -> str:
    # Weather-icon fallback (no pack chosen) -> the BAKED-IN Outline HD set
    # (1.0.46; 1.0.1-1.0.45 pointed these at the outline-hd resource pack).
    text = _replace(
        text,
        "resource://resource.images.weathericons.default/",
        "special://skin/extras/weather/",
        path=path,
        count=4,
    )
    # Labeled poster tiles: clean poster + label, per item (see _POSTER_EMPTY
    # block comment). Focused first: its anchor contains the unfocused run's
    # sibling bytes, so ordering keeps both counts exact.
    text = _widget_poster_label_fix(text, True, path=path)
    text = _widget_poster_label_fix(text, False, path=path)
    # WidgetListPoster's itemlayout gates InfoWallMovieLayout behind the
    # unlabeled mode (a load-time include condition); drop the condition so
    # poster items render their poster in labeled mode too. The include
    # self-gates per item on poster art, exactly like the generic Widget
    # itemlayout, whose InfoWallMovieLayout upstream already ships
    # unconditioned. No-poster items keep the square chrome drawn OVER the
    # icon fallback - the same stock stacking the generic Widget has always
    # had.
    text = _replace(
        text,
        _widget_movie_include(False, "!Skin.HasSetting(HideWidgetLabels)"),
        _widget_movie_include(False),
        path=path,
        count=1,
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
# Live TV/Radio keep stock's named windows (TVChannels/RadioChannels). Stock
# Estuary shows both tiles ALWAYS (gated only by an opt-out skin setting, not
# by PVR). skinshortcuts otherwise INJECTS System.HasPVRAddon onto any action
# starting with 'activatewindow(tv'/'(radio', hiding them without a PVR client
# (a MOD V2 deviation). Numeric window ids do NOT dodge this: hardware-verified
# on the ATV, skinshortcuts NORMALISES ActivateWindow(10700) back to
# ActivateWindow(TVChannels) at build time, then injects the condition anyway.
# The only real lever is skinshortcuts' own 'donthidepvr' setting - when true,
# check_visibility() injects nothing. We seed donthidepvr=true from the boot
# service and the reset helper (see _edit_services / _edit_helpers), so the
# named-window tiles stay always-visible like stock.

_MAINMENU_DISC = (
    "    <shortcut>\n"
    "        <label>427</label>\n"
    "        <label2>Common Shortcut</label2>\n"
    "        <defaultID>disc</defaultID>\n"
    "        <icon>icons/sidemenu/disc.png</icon>\n"
    "        <action>PlayDisc</action>\n"
    "        <visible>System.HasMediaDVD</visible>\n"
    "    </shortcut>\n"
)

_MAINMENU_MUSICVIDEOS_FIRST = (
    "    <shortcut>\n"
    "        <label>20389</label>\n"
    "        <label2>Common Shortcut</label2>\n"
    "        <defaultID>musicvideos</defaultID>\n"
    "        <icon>icons/sidemenu/musicvideos.png</icon>\n"
    "        <action>ActivateWindow(Videos,videodb://musicvideos/titles/,return)</action>\n"
    "        <visible>Library.HasContent(musicvideos) + !Skin.HasSetting(hide_musicvideocategory)</visible>\n"
    "    </shortcut>\n"
)

_MAINMENU_LIBREELEC = (
    "    <shortcut>\n"
    "        <label>LibreELEC</label>\n"
    "        <label2>Common Shortcut</label2>\n"
    "        <defaultID>libreelec</defaultID>\n"
    "        <icon>icons/sidemenu/libreelec.png</icon>\n"
    "        <action>RunAddon(service.libreelec.settings)</action>\n"
    "        <visible>System.HasAddon(service.libreelec.settings)</visible>\n"
    "    </shortcut>\n"
)

_MAINMENU_COREELEC = (
    "    <shortcut>\n"
    "        <label>CoreELEC</label>\n"
    "        <label2>Common Shortcut</label2>\n"
    "        <defaultID>coreelec</defaultID>\n"
    "        <icon>icons/sidemenu/coreelec.png</icon>\n"
    "        <action>RunAddon(service.coreelec.settings)</action>\n"
    "        <visible>System.HasAddon(service.coreelec.settings)</visible>\n"
    "    </shortcut>\n"
)


_OVERRIDES_VIDEO_ICON_LINE = '    <icon labelID="videos">DefaultAddonVideo.png</icon>\n'


def _edit_overrides(text: str, path: str) -> str:
    """Remove upstream's "videos" labelID icon override entirely.

    ANY <icon labelID="videos"> override that resolves to a SKIN image makes the
    skinshortcuts editor render the Videos entry BLANK: its gui.py sets
    setArt({'icon': 'icon'}) - the literal string 'icon', not the resolved path -
    whenever an override's icon is a skin image (skinHasImage=True). Hardware
    root-caused on the ATV and reproduced on local Kodi; livetv/radio survive
    only because their Default* overrides are NOT skin images.

    Removing the override lets Videos fall back to the DATA icon
    icons/sidemenu/videos.png. That path exists in MOD V2's Textures.xbt as a
    REDRAWN film-reel (a deviation from stock Estuary's film-strip). To honour
    THE FIRST MANDATE (match stock), the build shadows that bundle entry - see
    shadow_videos_texture - so Kodi falls back to the loose stock Estuary
    videos.png the build ships at media/icons/sidemenu/videos.png. Net: the
    editor icon is fixed AND the Videos glyph matches original Estuary, with no
    override in play."""
    return _replace(text, _OVERRIDES_VIDEO_ICON_LINE, "", path=path)


# --- Textures.xbt: shadow the MOD V2 videos.png so stock's loose copy wins ----
#
# Kodi's texture loader checks Textures.xbt BEFORE loose media files (bundle
# wins - verified on local Kodi: a loose same-name file is a no-op). MOD V2's
# bundle redrew icons/sidemenu/videos.png into a film-reel, unlike stock
# Estuary's film-strip. Rename that ONE directory entry in place (same 256-byte
# name field, null-padded; every frame offset untouched, no offset math) so
# HasFile("icons/sidemenu/videos.png") misses and Kodi falls back to the loose
# stock videos.png the build ships. In-place rewrite keeps the build
# deterministic. See _edit_overrides for the why.
_XBT_VIDEOS_PATH = b"icons/sidemenu/videos.png"
_XBT_VIDEOS_SHADOW = b"icons/sidemenu/__videos_shadowed__.png"


def _xbt_entry_offsets(data: bytes):
    """Yield (name_bytes, name_field_offset) for every file entry in an XBTF.

    XBTF v3 layout: b"XBTF" magic, version byte, uint32 nofFiles, then per file:
    256-byte path, uint32 loop, uint32 nofFrames, then nofFrames x 40-byte frame
    records (w,h,fmt: uint32; packed,unpacked: uint64; duration: uint32;
    offset: uint64)."""
    if data[:4] != b"XBTF":
        raise TransformError("media/Textures.xbt: not an XBTF bundle")
    nof = struct.unpack_from("<I", data, 5)[0]
    off = 9
    for _ in range(nof):
        name = bytes(data[off : off + 256]).split(b"\x00", 1)[0]
        yield name, off
        p = off + 256 + 4  # skip path + loop
        nframes = struct.unpack_from("<I", data, p)[0]
        off = p + 4 + nframes * 40


def shadow_videos_texture(xbt: Path) -> None:
    """Rename the icons/sidemenu/videos.png entry in Textures.xbt in place.

    Fail-loud anchor: the entry MUST exist (a rebase that renamed or dropped it
    is a build error, never a silent ship of MOD V2's film-reel)."""
    data = bytearray(xbt.read_bytes())
    for name, off in _xbt_entry_offsets(data):
        if name == _XBT_VIDEOS_PATH:
            data[off : off + 256] = b"\x00" * 256
            data[off : off + len(_XBT_VIDEOS_SHADOW)] = _XBT_VIDEOS_SHADOW
            xbt.write_bytes(bytes(data))
            return
    raise TransformError(
        "media/Textures.xbt: '{}' entry not found - cannot shadow it for the "
        "stock Videos icon".format(_XBT_VIDEOS_PATH.decode())
    )


def _edit_mainmenu(text: str, path: str) -> str:
    """Ship STOCK Estuary's menu out of the box (owner directive).

    Anchored edits: move Disc into stock's slot (after Music, before Music
    videos) and drop the LibreELEC/CoreELEC entries stock has no notion of (and
    which can never show on the Fire TV / Apple TV fleet anyway). Live TV/Radio
    keep stock's named windows and stay always-visible because we seed
    skinshortcuts' donthidepvr=true (see the FILE_EDITS comment). The
    library-aware action variants MOD V2 uses are kept - they are strictly
    better than stock's."""
    text = _replace(text, _MAINMENU_DISC, "", path=path)
    text = _insert_before(text, _MAINMENU_MUSICVIDEOS_FIRST, _MAINMENU_DISC, path=path)
    text = _replace(text, _MAINMENU_LIBREELEC, "", path=path)
    text = _replace(text, _MAINMENU_COREELEC, "", path=path)
    return text


def _edit_helpers(text: str, path: str) -> str:
    """Add a resetMenu action that actually resets the main menu.

    skinshortcuts 2.0.3 CANNOT do this itself: _reset_all_shortcuts() only
    deletes files whose name STARTS WITH the skin id, yet it SAVES the menu
    unprefixed (mainmenu.DATA.xml) whenever its "shared menu" setting is on -
    so the delete matches nothing and the customised menu survives every
    reset (owner-reported, root-caused on the ATV2 against skinshortcuts
    2.0.3's own source). We delete BOTH naming conventions plus the generated
    includes, then rebuild from the skin's shipped shortcuts/ defaults.
    """
    text = _replace(
        text,
        "import xbmc\nimport xbmcvfs\nimport xbmcgui\nimport sys\nimport json\n",
        "import xbmc\nimport xbmcaddon\nimport xbmcvfs\nimport xbmcgui\nimport os\nimport sys\nimport json\n",
        path=path,
    )
    return _insert_before(
        text, _HELPERS_ELSE, _SEED_PVR_ACTION + _RESET_MENU_ACTION, path=path
    )


_SERVICES_IMPORT_OLD = "import xbmc\n\n# view switcher\n"
_SERVICES_IMPORT_NEW = (
    "import xbmc\nimport xbmcaddon\nimport xbmcvfs\nimport xbmcgui\n"
    "import os\nimport hashlib\nimport json\n"
    "import xml.etree.ElementTree as ET\n\n# view switcher\n"
)

# Anchor: the FIRST statement inside __main__ (before the 1s sleep), so we set
# donthidepvr as early as possible - ideally before Home's onload buildxml runs,
# so the very first menu build already has it and no rebuild is ever needed.
_SERVICES_START_ANCHOR = "    TRANS_TITLE = str(xbmc.getLocalizedString(369))\n"

# The boot service (runs on addon-enable, BEFORE Home's onload buildxml) does two
# things on a fresh install:
#  1. Seed skinshortcuts' donthidepvr=true so it never injects System.HasPVRAddon
#     onto Live TV/Radio (the only reliable way to keep them always-visible like
#     stock; hardware-verified).
#  2. Seed a matching skinshortcuts HASH so shouldwerun() (xmlfunctions.py:143)
#     returns False and build_menu()'s ReloadSkin() (line 123) NEVER fires on
#     first launch. That reload is the root cause of BOTH the install black flash
#     AND the silent revert (it destroys Kodi's "keep this skin?" dialog ~270ms
#     after the switch). We ship the generated includes (add_assets), so the only
#     thing shouldwerun still needs is the hash - and the hash is device-specific
#     (absolute paths, Kodi version, profile list) so it CANNOT be a static file;
#     it is generated here. shouldwerun only checks entries we write and we hash
#     only files that exist now, so every entry is guaranteed to match. We seed
#     when the includes exist AND (no hash yet OR the hash is from a different
#     Estuary 7 version) - so upgrades/reinstalls (which carry a stale hash that
#     would otherwise block the seed and force a rebuild) are covered too, while
#     the reset path (which deletes the includes and sets reloadmainmenu) is not
#     fought. Worst case of any failure/race: the hash is absent/rejected,
#     shouldwerun returns True, one rebuild - exactly today's behaviour, never
#     worse (Change 3 defers that fallback build past the keep-dialog). Do NOT set
#     skinshortcuts-reloadmainmenu (that forces a rebuild).
_SERVICES_SEED = """\
    try:
        _ss = xbmcaddon.Addon('script.skinshortcuts')
        if _ss.getSetting('donthidepvr') != 'true':
            _ss.setSetting('donthidepvr', 'true')
            xbmc.log('estuary7: seeded skinshortcuts donthidepvr=true', level=xbmc.LOGINFO)
    except Exception as _pvr_e:
        xbmc.log('estuary7: donthidepvr seed failed: %s' % _pvr_e, level=xbmc.LOGWARNING)
    try:
        _skindir = xbmc.getSkinDir()
        _skinver = xbmcaddon.Addon(_skindir).getAddonInfo('version')
        _master = xbmcvfs.translatePath('special://masterprofile/addon_data/script.skinshortcuts/')
        _hashfile = os.path.join(_master, '%s.hash' % _skindir)
        _inc = xbmcvfs.translatePath('special://skin/xml/script-skinshortcuts-includes.xml')
        # --- SELF-HEAL (tvOS): re-materialize menu DATA orphaned in NSUserDefaults ---
        # An EZ Maintenance++ restore (<= 2026.07.13.6) vectored EVERY userdata *.xml into
        # NSUserDefaults and then DELETED the POSIX copy. skinshortcuts reads its
        # *.DATA.xml with plain open() while GUARDING with xbmcvfs.exists() - and on tvOS
        # CTVOSFile::Exists checks the NSUserDefaults key FIRST (TVOSFile.cpp:113-122), so
        # the guard passes, ElementTree's plain open() then raises, skinshortcuts swallows
        # it and falls through to the SKIN'S SHIPPED DEFAULT menu. The owner's customized
        # menu silently reverts to the full stock menu on every restore.
        # The bytes are NOT lost - they are in the key. xbmcvfs.listdir is the only API that
        # surfaces them (CTVOSDirectory merges the POSIX listing with the keys), so read each
        # orphan back THROUGH xbmcvfs and write it to disk with plain open() - the API
        # skinshortcuts actually reads with. Entered ONLY when the POSIX file is missing AND
        # the VFS can still see it: unreachable on Fire TV / desktop and on a healthy Apple
        # TV, so a strict no-op everywhere else. Full model: the kodi-storage-map skill.
        _healed = 0
        _ssdir = 'special://profile/addon_data/script.skinshortcuts/'
        _ssreal = xbmcvfs.translatePath(_ssdir)
        try:
            _dirs, _vfsfiles = xbmcvfs.listdir(_ssdir)
            for _fn in _vfsfiles:
                if not _fn.endswith('.DATA.xml'):
                    continue
                _fp = os.path.join(_ssreal, _fn)
                if os.path.isfile(_fp):
                    continue
                _rf = None
                try:
                    _rf = xbmcvfs.File(_ssdir + _fn)
                    _bytes = _rf.readBytes()
                finally:
                    try:
                        if _rf is not None:
                            _rf.close()
                    except Exception:
                        pass
                if not _bytes:
                    continue
                if not os.path.isdir(_ssreal):
                    os.makedirs(_ssreal)
                with open(_fp, 'wb') as _out:
                    _out.write(bytes(_bytes))
                _healed += 1
            if _healed:
                xbmc.log('estuary7: re-materialized %d skinshortcuts DATA file(s) orphaned in NSUserDefaults' % _healed, level=xbmc.LOGWARNING)
        except Exception as _he:
            xbmc.log('estuary7: DATA re-materialize skipped: %s' % _he, level=xbmc.LOGWARNING)
        # --- PURGE the now-redundant NSUserDefaults keys ---
        # A file living in BOTH layers is listed TWICE by CTVOSDirectory (it merges the POSIX
        # listing with the keys and never dedupes, TVOSDirectory.cpp:48-106), the stale key
        # SHADOWS the disk file for any VFS reader (CTVOSFile::Exists/Open check the key
        # first), and it burns the tvOS defaults budget - which Apple TERMINATES the app over
        # at 1 MB (warning at 512 KB, whole database). skinshortcuts reads its DATA with plain
        # open(), so the key is pure liability: drop it and leave one coherent POSIX file.
        # SAFETY. Verified against Kodi Omega source (xbmc@f8815ee4), NOT against intuition:
        #   CTVOSFile::Delete       -> DeleteKeyFromPath(); if (!ret) POSIX delete
        #   DeleteKeyFromPath       -> translatePathIntoKey() succeeds for ANY path under
        #                              userdata, then DeleteKey()
        #   DeleteKey               -> removeObjectForKey (SILENT no-op if absent), then
        #                              `return [defaults synchronize] == YES` -> true
        # So ret is TRUE whether or not a key existed, and the `if (!ret)` POSIX fallback is
        # UNREACHABLE for exactly the files CTVOSFile is dispatched for (FileFactory.cpp:117
        # gates on WantsFile). Net rule, which no doc of ours stated correctly until now:
        # xbmcvfs.delete() on a userdata *.xml CANNOT delete the POSIX file on tvOS - it drops
        # the key and reports success. That is precisely what we want here, and it means the
        # purge cannot destroy the disk copy. We still (a) only touch files whose POSIX copy
        # EXISTS - never one where the key is the only copy, (b) hold the bytes first, and
        # (c) re-write from memory if the file vanished anyway. (c) is now known-unreachable
        # defence-in-depth against a future Kodi changing these semantics on us; it is cheap.
        # Only files present in BOTH layers (name listed twice by the VFS) are touched, so this
        # is a strict no-op once clean and on every non-tvOS platform. See: kodi-storage-map.
        _purged = 0
        try:
            _dirs2, _vfs2 = xbmcvfs.listdir(_ssdir)
            _dupes = set()
            _once = set()
            for _fn in _vfs2:
                if not _fn.endswith('.DATA.xml'):
                    continue
                if _fn in _once:
                    _dupes.add(_fn)
                _once.add(_fn)
            for _fn in sorted(_dupes):
                _fp = os.path.join(_ssreal, _fn)
                if not os.path.isfile(_fp):
                    continue  # no POSIX copy: the key may be the ONLY copy - never touch it
                with open(_fp, 'rb') as _sf:
                    _keep = _sf.read()
                if not _keep:
                    continue
                try:
                    xbmcvfs.delete(_ssdir + _fn)
                except Exception:
                    pass
                if not os.path.isfile(_fp):
                    # the POSIX fallback fired - put the file straight back
                    with open(_fp, 'wb') as _rw:
                        _rw.write(_keep)
                    xbmc.log('estuary7: key purge hit the POSIX-delete fallback; restored %s' % _fn, level=xbmc.LOGWARNING)
                else:
                    _purged += 1
            if _purged:
                xbmc.log('estuary7: purged %d redundant skinshortcuts NSUserDefaults key(s)' % _purged, level=xbmc.LOGINFO)
        except Exception as _pe:
            xbmc.log('estuary7: key purge skipped: %s' % _pe, level=xbmc.LOGWARNING)
        # Does the owner have a menu of their OWN (restored or hand-edited)?
        _usermenu = False
        try:
            for _fn in os.listdir(_ssreal):
                if _fn.endswith('.DATA.xml'):
                    _usermenu = True
                    break
        except Exception:
            _usermenu = False
        # The seed exists ONLY to kill the first-launch rebuild+ReloadSkin flash on a VIRGIN
        # box - and a virgin box has NO user DATA by definition. If the owner HAS a menu, we
        # must NOT suppress the rebuild: a rebuild READS the owner's DATA first
        # (datafunctions.py: [user_shortcuts, skin_shortcuts, default_shortcuts]) and
        # REGENERATES their custom menu. Seeding a hash there would freeze whatever includes
        # happen to be on disk (the SHIPPED DEFAULT on a fresh/updated skin) and permanently
        # disarm the only mechanism that can rebuild their menu.
        #
        # But NOT seeding is all that takes. Do NOT also DELETE their hash: that is THEIR
        # hash from THEIR last build, and dropping it on every boot makes skinshortcuts
        # rebuild + ReloadSkin on every boot forever (it just writes a fresh hash, which we
        # then delete again). 1.0.36/1.0.37 did exactly that. A skin version bump does not
        # need it either - skinshortcuts compares ::SKINVER:: in the hash ITSELF and rebuilds
        # from the owner's DATA when it changes.
        #
        # The hash is dropped in exactly ONE case: we just re-materialized DATA off the keys.
        # There the on-disk includes ARE stale - they were generated from the SHIPPED DEFAULT
        # while the owner's DATA was invisible - so force one rebuild from the restored data.
        # _healed is 0 on the next boot, so this is self-limiting: one rebuild, not a loop.
        if _healed:
            try:
                if os.path.exists(_hashfile):
                    os.remove(_hashfile)
                    xbmc.log('estuary7: dropped stale skinshortcuts hash - rebuilding menu from the re-materialized owner DATA', level=xbmc.LOGINFO)
            except Exception:
                pass
            _needseed = False
        elif _usermenu:
            # The owner has their own menu and nothing needed healing: leave it ALONE.
            # No seed (would freeze the shipped default), no hash drop (would rebuild forever).
            _needseed = False
        else:
            # Virgin box: seed the hash so the first launch does not rebuild + ReloadSkin.
            # The reset helper deletes the includes (isfile False here), so this never
            # fights the reset path.
            _needseed = False
            if os.path.isfile(_inc):
                if not os.path.exists(_hashfile):
                    _needseed = True
                else:
                    try:
                        with open(_hashfile) as _oh:
                            _old = json.load(_oh)
                        _oldver = None
                        for _e in _old:
                            if _e and _e[0] == '::SKINVER::':
                                _oldver = _e[1] if len(_e) > 1 else None
                                break
                        if _oldver != _skinver:
                            _needseed = True
                    except Exception:
                        _needseed = True
        if _needseed:
            _ssa = xbmcaddon.Addon('script.skinshortcuts')
            def _t7b_md5(_p):
                _h = hashlib.md5()
                with open(_p, 'rb') as _f:
                    for _blk in iter(lambda: _f.read(65536), b''):
                        _h.update(_blk)
                return _h.hexdigest()
            _plist = []
            _pf = xbmcvfs.translatePath('special://userdata/profiles.xml')
            try:
                if os.path.isfile(_pf):
                    for _pr in ET.parse(_pf).getroot().findall('profile'):
                        _pnm = _pr.find('name').text
                        _pdir = _pr.find('directory').text
                        if '://' in _pdir:
                            _pdir = xbmcvfs.translatePath(_pdir)
                        _pdir = xbmcvfs.translatePath(os.path.join('special://masterprofile', _pdir))
                        _plist.append([_pdir, 'String.IsEqual(System.ProfileName,%s)' % _pnm, _pnm])
            except Exception:
                _plist = []
            if not _plist:
                _pnm = xbmc.getInfoLabel('System.ProfileName')
                _plist = [[xbmcvfs.translatePath('special://masterprofile/'), 'String.IsEqual(System.ProfileName,%s)' % _pnm, _pnm]]
            _hl = [
                ['::PROFILELIST::', _plist],
                ['::SCRIPTVER::', _ssa.getAddonInfo('version')],
                ['::XBMCVER::', xbmc.getInfoLabel('System.BuildVersion').split('.')[0]],
                ['::HIDEPVR::', _ssa.getSetting('donthidepvr')],
                ['::SHARED::', _ssa.getSetting('shared_menu')],
                ['::SKINDIR::', _skindir],
                ['::FULLMENU::', 'True'],
                ['::SKINVER::', _skinver],
            ]
            _files = [_inc]
            _scd = xbmcvfs.translatePath('special://skin/shortcuts/')
            if os.path.isdir(_scd):
                for _fn in sorted(os.listdir(_scd)):
                    if _fn.endswith('.DATA.xml') or _fn in ('overrides.xml', 'template.xml'):
                        _files.append(os.path.join(_scd, _fn))
            for _fp in _files:
                if os.path.isfile(_fp):
                    _hl.append([_fp, _t7b_md5(_fp)])
            if not os.path.isdir(_master):
                os.makedirs(_master)
            with open(_hashfile, 'w') as _hf:
                _hf.write(json.dumps(_hl, indent=4))
            xbmc.log('estuary7: seeded skinshortcuts hash (%d entries)' % len(_hl), level=xbmc.LOGINFO)
    except Exception as _hxe:
        xbmc.log('estuary7: hash seed failed (falls back to one rebuild): %s' % _hxe, level=xbmc.LOGWARNING)
    # --- Siri remote keymap (tvOS ONLY): Fire TV parity for live TV ---
    # Kodi's shipped customcontroller.SiriRemote.xml maps back/menu (button
    # 6) to STOP inside FullscreenVideo, so live TV dies on back - and the
    # remote has no button that RETURNS to fullscreen (double play/pause,
    # button 21, is upstream noop). Owner directive 2026-07-15: back exits
    # fullscreen with playback continuing (like the Fire TV remote), and
    # double-click play/pause toggles fullscreen back. Stop stays on
    # hold-play/pause and in the OSD. Written with plain open() (the tvOS
    # xbmcvfs/POSIX split lesson), rewritten only when the payload changes,
    # then keymaps reload in place. Android/desktop: strict no-op.
    try:
        if xbmc.getCondVisibility('System.Platform.TVOS'):
            _km = '\\n'.join([
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<!-- Written by skin.estuary7 (boot service): Fire TV parity for the',
                '     Siri remote. Back exits fullscreen video with playback continuing;',
                '     double play/pause toggles fullscreen. Delete this file and run',
                '     Action(reloadkeymaps) to revert to stock behavior. -->',
                '<keymap>',
                '  <FullscreenVideo>',
                '    <customcontroller name="SiriRemote">',
                '      <button id="6">Back</button>',
                '    </customcontroller>',
                '  </FullscreenVideo>',
                '  <FullscreenLiveTV>',
                '    <customcontroller name="SiriRemote">',
                '      <button id="6">Back</button>',
                '    </customcontroller>',
                '  </FullscreenLiveTV>',
                '  <Home>',
                '    <!-- upstream opens the Favourites browser here (a blank blue',
                '         screen when favourites are empty); the owner expects back',
                '         at Home to return to the playing video instead. FullScreen',
                '         is a no-op when nothing plays. -->',
                '    <customcontroller name="SiriRemote">',
                '      <button id="6">FullScreen</button>',
                '    </customcontroller>',
                '  </Home>',
                '  <global>',
                '    <customcontroller name="SiriRemote">',
                '      <button id="21">FullScreen</button>',
                '    </customcontroller>',
                '  </global>',
                '</keymap>',
                '',
            ])
            _km_dir = xbmcvfs.translatePath('special://profile/keymaps/')
            _km_path = os.path.join(_km_dir, 't7b-siriremote.xml')
            _have = None
            if os.path.isfile(_km_path):
                with open(_km_path, 'r') as _kf:
                    _have = _kf.read()
            if _have != _km:
                if not os.path.isdir(_km_dir):
                    os.makedirs(_km_dir)
                with open(_km_path, 'w') as _kf:
                    _kf.write(_km)
                xbmc.executebuiltin('Action(reloadkeymaps)')
                xbmc.log('estuary7: wrote Siri remote keymap (Fire TV parity)', level=xbmc.LOGINFO)
    except Exception as _km_e:
        xbmc.log('estuary7: siri keymap write failed: %s' % _km_e, level=xbmc.LOGWARNING)
"""


def _edit_services(text: str, path: str) -> str:
    """Seed skinshortcuts' donthidepvr=true at boot.

    Stock Estuary shows Live TV/Radio always; skinshortcuts hides them without a
    PVR client by injecting System.HasPVRAddon. Its donthidepvr setting is the
    only switch that suppresses that (a skin cannot ship the setting file, but the
    boot service can set it via the addon API). Runs once and ONLY sets the
    setting - it does not nudge or force a menu rebuild/ReloadSkin. The service
    runs before Home's onload buildxml, so the first natural build already reads
    donthidepvr (see _SERVICES_SEED for why the old reload nudge was dropped)."""
    text = _replace(text, _SERVICES_IMPORT_OLD, _SERVICES_IMPORT_NEW, path=path)
    return _replace(
        text,
        _SERVICES_START_ANCHOR,
        _SERVICES_SEED + _SERVICES_START_ANCHOR,
        path=path,
    )


FILE_EDITS = {
    "xml/Home.xml": _edit_home,
    "xml/Settings.xml": _edit_settings,
    "xml/Includes.xml": _edit_includes,
    "xml/Variables.xml": _edit_variables,
    "xml/SkinSettings.xml": _edit_skinsettings,
    "scripts/helpers.py": _edit_helpers,
    "scripts/services.py": _edit_services,
    "shortcuts/mainmenu.DATA.xml": _edit_mainmenu,
    "shortcuts/overrides.xml": _edit_overrides,
    "xml/SettingsCategory.xml": _edit_settingscategory,
    "xml/DialogAddonSettings.xml": _edit_dialogaddonsettings,
    "xml/SettingsProfile.xml": _edit_settingsprofile,
    "xml/Startup.xml": _edit_startup,
    "xml/Timers.xml": _edit_timers,
    "xml/DialogButtonMenu.xml": _edit_dialogbuttonmenu,
    "xml/DialogNotification.xml": _edit_dialognotification,
    "xml/Custom_1107_SearchDialog.xml": _edit_searchdialog,
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
        'provider-name="Tony.7.Bones">'.format(
            sid=SKIN_ID, ver=version, name=SKIN_NAME
        ),
        path=path,
    )
    # Screenshots: MOD V2 ships its own branded set; the fork uses ORIGINAL
    # Estuary's 8 (Team Kodi, vendored into assets/resources/ and copied in by
    # the build). Provenance stays in <description> as THANKS, not authorship.
    text = _replace(
        text,
        "".join(
            "\t\t\t\t<screenshot>resources/screenshots/screenshot_{}.png</screenshot>\n".format(
                n
            )
            for n in (1, 2, 5, 7, 8, 9, 10, 13, 14, 15)
        ),
        "".join(
            "\t\t\t\t<screenshot>resources/screenshot-{:02d}.jpg</screenshot>\n".format(
                n
            )
            for n in range(1, 9)
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
    # Dependency closure for a CLEAN-BOX manual install (owner directive
    # 2026-07-10): the skin must enable from our repo alone, nothing
    # pre-installed. pvr.artwork was first demoted from REQUIRED (it is the
    # one dep NOT in Kodi's official repo - b-jesch GitHub-only - and as a
    # required import it made Kodi abandon the whole dependency install and
    # disable the skin) to optional, then DROPPED ENTIRELY (owner directive
    # 2026-07-15, 1.0.45): the fleet's bench never had it installed and never
    # missed it - every pvr.artwork read in the skin is emptiness-guarded, so
    # the skin renders stock PVR labels without it, and the SkinSettings
    # "PVR Artwork" toggle still one-click-installs it from the hosted mirror
    # for anyone who wants the enrichment. The remaining hard deps
    # (outline-hd weather default + autocompletion, plus upstream's
    # skinshortcuts + image.resource.select) are all no-sub-dep add-ons
    # served by OUR proxy repo, so the closure resolves from the repo the
    # user just installed.
    # (outline-hd was a hard import 1.0.1-1.0.45; since 1.0.46 the icons are
    # BAKED IN at extras/weather and the skin imports no icon pack at all.)
    text = _replace(
        text,
        '\t\t<import addon="script.module.pvr.artwork" version="2.0.0"/>\n',
        '\t\t<import addon="script.module.autocompletion" version="1.0.0"/>\n',
        path=path,
    )
    text = _replace(
        text,
        '<summary lang="en_GB">Estuary MOD V2 skin by Guilouz, adapted for Omega by PvD</summary>',
        '<summary lang="en_GB">A modern, customizable take on '
        "Kodi's Estuary.</summary>",
        path=path,
    )
    text = _replace(
        text,
        '<description lang="en_GB">Estuary MOD V2 is a mod from Estuary by Guilouz '
        "for Kodi 18 and adapted for Kodi 21 (Omega) by PvD from Kodinerds Community. "
        "It attempts to be easy for first time Kodi users to understand and use.</description>",
        '<description lang="en_GB">Estuary 7 brings Kodi\'s classic Estuary '
        "into the present: a clean, modern interface with rich skin settings, "
        "smart home widgets, and a light, uncluttered layout that stays fast "
        "and familiar. Yours to shape.</description>",
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
        "        <news>\nv{}: the Viewtype button in the media sidebar now "
        "cycles views like stock Estuary. The MOD V2 view-picker dialog (its "
        "preview images were removed to slim the install, leaving it showing "
        "placeholder art) is gone, along with the MOD V2 splash artwork.\n"
        "        </news>".format(version),
        path=path,
    )
    return text


def rename_skin_id(text: str) -> str:
    """Global rename; used for every text file that mentions the upstream id."""
    return text.replace(UPSTREAM_ID, SKIN_ID)


def invert_widget_labels(text: str) -> str:
    """Flip the upstream HideWidgetLabels flag to hide_tile_labels with a
    polarity swap. Upstream misnamed it (SET = SHOW labels) and defaults it
    unset = UNLABELED; the swap makes a fresh box default to LABELED tiles
    (owner directive) while preserving every layout's behavior. The Skin
    Settings toggle was already re-aligned to the layouts' polarity in
    _edit_skinsettings, so this single swap corrects the toggle AND the
    default with no special case. Forms are uniform (verified): plain and
    negated Skin.HasSetting, plus the one Skin.ToggleSetting."""
    ph = "\x00T7B-TILELABELS\x00"
    text = text.replace("!Skin.HasSetting(HideWidgetLabels)", ph)
    text = text.replace(
        "Skin.HasSetting(HideWidgetLabels)", "!Skin.HasSetting(hide_tile_labels)"
    )
    text = text.replace(ph, "Skin.HasSetting(hide_tile_labels)")
    text = text.replace(
        "Skin.ToggleSetting(HideWidgetLabels)", "Skin.ToggleSetting(hide_tile_labels)"
    )
    return text


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
    return repoint_lyrics_fonts(text[:start] + segment + text[end:], path=path)


_LYRICS_FILENAME_RE = re.compile(r"<filename>lyrics/[^<]+</filename>")


def repoint_lyrics_fonts(text: str, *, path: str = "xml/Font.xml") -> str:
    """Re-point the DEFAULT fontset's lyrics font FILES at NotoSans-Regular.

    1.0.44 trimmed fonts/lyrics/ (the karaoke faces nobody on the fleet
    uses), which left the lyr* definitions binding missing files - harmless
    (Kodi falls back) but it spams ~40 GUIFontManager::LoadTTF errors into
    the log at EVERY skin load (bench-caught 2026-07-15). Only the ACTIVE
    fontset's fonts load, so the swap is scoped to Default; the alternate
    fontsets stay byte-stock (the test_nobold invariant) and never spam.
    The font-id INVENTORY stays byte-identical (only <filename> values
    change); the lyr* ids keep their sizes and synthetic-bold styles, so if
    a lyrics add-on ever appears its overlays render in NotoSans instead of
    the decorative faces. Public (not _-prefixed): golden parity applies
    the same repoint to normalize the golden."""
    start = text.find('<fontset id="Default"')
    if start == -1:
        raise TransformError("{}: Default fontset not found".format(path))
    end = text.find("<fontset id=", start + 1)
    if end == -1:
        raise TransformError(
            "{}: Default fontset is not followed by another fontset".format(path)
        )
    segment, swaps = _LYRICS_FILENAME_RE.subn(
        "<filename>NotoSans-Regular.ttf</filename>", text[start:end]
    )
    if swaps == 0:
        raise TransformError(
            "{}: no lyrics font filenames found to repoint".format(path)
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

    # 1c. Widget-label default: HideWidgetLabels is upstream-misnamed (SET =
    # SHOW) and defaults unlabeled; flip it to hide_tile_labels with a
    # polarity swap so a fresh box shows LABELED tiles (owner directive).
    for target in sorted((root / "xml").glob("*.xml")):
        text = target.read_text(encoding="utf-8")
        if "HideWidgetLabels" in text:
            new = invert_widget_labels(text)
            if "HideWidgetLabels" in new:
                raise TransformError(
                    "{}: HideWidgetLabels survived the label flip".format(target.name)
                )
            target.write_text(new, encoding="utf-8")
            summary["labelflip"] = summary.get("labelflip", 0) + 1

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

    # 5. Shadow MOD V2's videos.png in Textures.xbt so the loose stock Estuary
    #    videos.png the build ships (add_assets) renders instead - matching
    #    original Estuary's Videos glyph. Fail-loud if the entry is gone.
    shadow_videos_texture(root / "media" / "Textures.xbt")
    summary["xbt_shadowed"] = "icons/sidemenu/videos.png"
    return summary
