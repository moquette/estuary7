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
    # (8, 31273) "Necessary add-ons" tab removed (owner directive): the
    # fleet installs deps via Setup, not MOD V2's in-skin installer. Its
    # pane (grouplist 300) stays in the XML but is unreachable now that no
    # list item focuses HasFocus(8).
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
    return text


_HELPERS_ELSE = (
    "        else:\n            xbmc.log('unknown parameter', xbmc.LOGERROR)\n"
)

_RESET_MENU_ACTION = (
    "        elif sys.argv[1] == 'resetMenu':\n"
    "            if xbmcgui.Dialog().yesno('Reset main menu', 'Reset the main menu back to the skin defaults?'):\n"
    "                profile = 'special://profile/addon_data/script.skinshortcuts/'\n"
    "                master = 'special://masterprofile/addon_data/script.skinshortcuts/'\n"
    "                defaults = 'special://skin/shortcuts/'\n"
    "                includes = 'special://skin/xml/script-skinshortcuts-includes.xml'\n"
    "                home = xbmcgui.Window(10000)\n"
    "                report = []\n"
    "                home.clearProperty('skinshortcuts-isrunning')\n"
    "                home.clearProperty('skinshortcuts-loading')\n"
    "                for prop in ('skinshortcuts-mainmenu', 'skinshortcutsWidgets', 'skinshortcutsCustomProperties', 'skinshortcutsBackgrounds'):\n"
    "                    home.clearProperty(prop)\n"
    "                wiped = 0\n"
    "                for base in (profile, master):\n"
    "                    if not xbmcvfs.exists(base):\n"
    "                        continue\n"
    "                    for name in (xbmcvfs.listdir(base)[1] or []):\n"
    "                        if name != 'settings.xml' and name.endswith(('.DATA.xml', '.properties', '.hash')):\n"
    "                            if xbmcvfs.delete(base + name):\n"
    "                                wiped += 1\n"
    "                report.append('wiped=%i' % wiped)\n"
    "                gone = bool(xbmcvfs.exists(includes)) and bool(xbmcvfs.delete(includes))\n"
    "                report.append('includes_deleted=%s' % gone)\n"
    "                if not xbmcvfs.exists(profile):\n"
    "                    xbmcvfs.mkdirs(profile)\n"
    "                copied = 0\n"
    "                for name in (xbmcvfs.listdir(defaults)[1] or []):\n"
    "                    if name.endswith('.DATA.xml') and xbmcvfs.copy(defaults + name, profile + name):\n"
    "                        copied += 1\n"
    "                report.append('copied=%i' % copied)\n"
    "                try:\n"
    "                    xbmcaddon.Addon('script.skinshortcuts').setSetting('donthidepvr', 'true')\n"
    "                    report.append('donthidepvr=true')\n"
    "                except Exception as e:\n"
    "                    report.append('donthidepvr_err=%s' % e)\n"
    "                home.setProperty('skinshortcuts-reloadmainmenu', 'True')\n"
    "                built = 'async'\n"
    "                try:\n"
    "                    _lib = xbmcvfs.translatePath('special://home/addons/script.skinshortcuts/resources/lib')\n"
    "                    if _lib not in sys.path:\n"
    "                        sys.path.insert(0, _lib)\n"
    "                    from skinshorcuts import xmlfunctions as _xf\n"
    "                    home.clearProperty('skinshortcuts-isrunning')\n"
    "                    _xf.XMLFunctions().build_menu('9000', 'mainmenu', '0', None, [''], 0)\n"
    "                    built = 'inproc'\n"
    "                except Exception as e:\n"
    "                    built = 'async(%s)' % e\n"
    "                    xbmc.executebuiltin('RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&group=mainmenu)')\n"
    "                report.append('build=' + built)\n"
    "                home.setProperty('t7b_resetmenu', 'reset: ' + ' '.join(report))\n"
    "                xbmc.log('resetMenu: ' + ' '.join(report), xbmc.LOGINFO)\n"
    "        elif sys.argv[1] == 'menuDump':\n"
    "            import xml.etree.ElementTree as ET\n"
    "            out = []\n"
    "            def _ld(p):\n"
    "                fh = xbmcvfs.File(p)\n"
    "                b = fh.readBytes()\n"
    "                fh.close()\n"
    "                return ET.fromstring(bytes(b))\n"
    "            try:\n"
    "                r = _ld('special://masterprofile/addon_data/script.skinshortcuts/mainmenu.DATA.xml')\n"
    "                p = []\n"
    "                for sc in r.findall('shortcut'):\n"
    "                    p.append((sc.findtext('defaultID') or '?') + ('*DIS' if sc.find('disabled') is not None else ''))\n"
    "                out.append('DATA(%i):%s' % (len(p), ','.join(p)))\n"
    "            except Exception as e:\n"
    "                out.append('DATA_ERR:%s' % e)\n"
    "            try:\n"
    "                r = _ld('special://skin/xml/script-skinshortcuts-includes.xml')\n"
    "                mm = None\n"
    "                for inc in r.findall('include'):\n"
    "                    if inc.get('name') == 'skinshortcuts-mainmenu':\n"
    "                        mm = inc\n"
    "                        break\n"
    "                if mm is None:\n"
    "                    out.append('INC:no-mainmenu-include')\n"
    "                else:\n"
    "                    p = []\n"
    "                    for it in mm.findall('item'):\n"
    "                        lid = it.findtext(\"property[@name='labelID']\") or '?'\n"
    "                        vis = it.findtext('visible')\n"
    "                        p.append(lid + (('=' + vis) if vis else ''))\n"
    "                    out.append('INC(%i):%s' % (len(p), ','.join(p)))\n"
    "            except Exception as e:\n"
    "                out.append('INC_ERR:%s' % e)\n"
    "            xbmcgui.Window(10000).setProperty('t7b_menudump', ' || '.join(out))\n"
    "        elif sys.argv[1] == 'fileHas':\n"
    "            try:\n"
    "                fh = xbmcvfs.File(sys.argv[2])\n"
    "                blob = fh.read()\n"
    "                fh.close()\n"
    "                present = str(sys.argv[3] in blob)\n"
    "            except Exception as e:\n"
    "                present = 'ERR:%s' % e\n"
    "            xbmcgui.Window(10000).setProperty('t7b_filehas', '%s|%s' % (sys.argv[2].split('/')[-1], present))\n"
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
    "\t\t\t\t\t<item>\n"
    "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
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
    divider, then one non-scrolling block of eight category tiles. Skin
    Settings takes the slot upstream gave Games (unused on the fleet; stock
    only shows Games conditionally); the MOD V2 "Media sources" tile is gone,
    relocated into Skin Settings > Extras (see _MEDIA_SOURCES_BLOCK). The two
    onunload RunScripts keep upstream's addon-id form so the global rewiring
    converts them (the count-15 contract); the splash onunload is baked to the
    opt-in Reset form. Fail loud if the upstream page is not the shape we
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
    return _insert_before(text, _HELPERS_ELSE, _RESET_MENU_ACTION, path=path)


_SERVICES_IMPORT_OLD = "import xbmc\n\n# view switcher\n"
_SERVICES_IMPORT_NEW = (
    "import xbmc\nimport xbmcaddon\nimport xbmcvfs\nimport xbmcgui\n\n# view switcher\n"
)

# Anchor: the service's own startup log line (inside __main__, 4-space indent).
_SERVICES_START_ANCHOR = (
    "    xbmc.log('Estuary MOD V2 Nexus service handler started', level=xbmc.LOGINFO)\n"
)

# Seed skinshortcuts' donthidepvr=true once, so it never injects System.HasPVRAddon
# onto the Live TV/Radio menu items - the only reliable way to keep them
# always-visible like stock (numeric window ids are normalised back to the named
# windows and injected anyway; hardware-verified). On the first boot that flips
# the setting, drop the generated includes and rebuild so the change takes effect.
_SERVICES_SEED = (
    "    try:\n"
    "        _ss = xbmcaddon.Addon('script.skinshortcuts')\n"
    "        if _ss.getSetting('donthidepvr') != 'true':\n"
    "            _ss.setSetting('donthidepvr', 'true')\n"
    "            _inc = 'special://skin/xml/script-skinshortcuts-includes.xml'\n"
    "            if xbmcvfs.exists(_inc):\n"
    "                xbmcvfs.delete(_inc)\n"
    "            xbmcgui.Window(10000).setProperty('skinshortcuts-reloadmainmenu', 'True')\n"
    "            xbmc.executebuiltin('RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&group=mainmenu)')\n"
    "            xbmc.log('estuary7: seeded skinshortcuts donthidepvr=true, rebuilding menu', level=xbmc.LOGINFO)\n"
    "    except Exception as _pvr_e:\n"
    "        xbmc.log('estuary7: donthidepvr seed failed: %s' % _pvr_e, level=xbmc.LOGWARNING)\n"
)


def _edit_services(text: str, path: str) -> str:
    """Seed skinshortcuts' donthidepvr=true at boot.

    Stock Estuary shows Live TV/Radio always; skinshortcuts hides them without a
    PVR client by injecting System.HasPVRAddon. Its donthidepvr setting is the
    only switch that suppresses that (a skin cannot ship the setting file, but the
    boot service can set it via the addon API). Runs once - on the boot that flips
    the setting it forces a menu rebuild so the tiles appear immediately."""
    text = _replace(text, _SERVICES_IMPORT_OLD, _SERVICES_IMPORT_NEW, path=path)
    return _replace(
        text,
        _SERVICES_START_ANCHOR,
        _SERVICES_START_ANCHOR + _SERVICES_SEED,
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
    # pre-installed. pvr.artwork is the one dep NOT in Kodi's official repo
    # (b-jesch GitHub-only) - as a REQUIRED import it made Kodi abandon the
    # whole dependency install and disable the skin. It becomes OPTIONAL (the
    # skin already gates every pvr.artwork context item on System.HasAddon, so
    # it enables fine without it; Setup still direct-extracts it on the fleet,
    # and it is one-click otherwise). The remaining hard deps (outline-hd
    # weather default + autocompletion, plus upstream's skinshortcuts +
    # image.resource.select) are all no-sub-dep add-ons served by OUR proxy
    # repo, so the closure resolves from the repo the user just installed.
    text = _replace(
        text,
        '\t\t<import addon="script.module.pvr.artwork" version="2.0.0"/>\n',
        '\t\t<import addon="script.module.pvr.artwork" version="2.0.0" optional="true"/>\n'
        '\t\t<import addon="resource.images.weathericons.outline-hd" version="0.0.1"/>\n'
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
        "        <news>\nv{}: the main menu is fully customizable again (the "
        "editor works), its default items are stock Estuary's set, and 'Reset "
        "main menu settings' now reliably restores that default by copying the "
        "shipped defaults into place and rebuilding. Live TV and Radio show by "
        "default.\n"
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
    return summary
