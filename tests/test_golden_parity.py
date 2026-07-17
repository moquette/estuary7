"""Golden parity: the transformed files must match the hardware-verified
modv2plus 1.8.0 bytes (tests/goldens/xml/), modulo the DOCUMENTED divergences.

The normalization applied to each golden below IS the divergence record:

  every file   - XML comments stripped from both sides (the goldens carry
                 patch-era marker comments; the fork needs none), and the
                 golden's skin id renamed (the fork is skin.estuary7).
  Settings.xml - the System page is FORK-AUTHORED (owner directive
                 2026-07-10, bench-verified on the Office Fire TV): upstream's
                 single scrolling 5-column panel is replaced by a stock-style
                 4x3 grid - a fixed top utility row (File manager, Add-ons,
                 System info, Event log), a "Settings" divider, then one
                 non-scrolling block of eight tiles where Skin Settings takes
                 the slot upstream gave Games and the MOD V2 "Media sources"
                 tile is gone. The golden here is that design in golden form
                 (upstream runscripts + Skin.SetBool splash); its normalization
                 is only the splash opt-in flip and the runscript rewire.
  Includes.xml / Variables.xml / SkinSettings.xml / Home.xml
               - the runtime-written skin settings are baked as inverted
                 opt-out conditions (see skin_transforms module docstring).
  SkinSettings.xml
               - the overlay's whole custom category (grouplist 1100 with the
                 master Apply/Restore toggle 1102, its category-list item 11,
                 the scrollbar wiring, the stretched category list) does not
                 exist in the fork (owner directive 2026-07-10: stock
                 structure only); the System Info overlay toggle moves into
                 General > Top Bar above "Show date"; the category nav column
                 is UNCONDITIONALLY thin (the golden carried a dual thin/bold
                 label pair driven by the runtime t7b_patch_on mirror -
                 plumbing the fork does not need); the Extras pane gains an
                 "Add media sources" launcher (header + Videos/Music/Pictures/
                 Games file-browser buttons) above the Debug section - the
                 relocated home for the System page's old Media sources tile.

Anything NOT normalized here that differs from the golden fails the test.
"""

from __future__ import annotations

import re

import pytest

from conftest import GOLDENS
from skin_transforms import (
    _GREYEDOUT_HOME_ROW,
    _HIDE_WATCHED_TOGGLE,
    SKIN_ID,
    UPSTREAM_ID,
    drop_settings_views_variable,
    repoint_lyrics_fonts,
)

_COMMENT_RE = re.compile(r"[ \t]*<!--.*?-->\n?", re.DOTALL)

GOLDEN_FILES = [
    "Home.xml",
    "Settings.xml",
    "Includes.xml",
    "Variables.xml",
    "SettingsCategory.xml",
    "DialogAddonSettings.xml",
    "SettingsProfile.xml",
    "Font.xml",
    "SkinSettings.xml",
]

# The golden's dual thin/bold category labels (visibility-gated on the runtime
# display mirror) collapse to a single, unconditionally thin label in the fork.
_GOLDEN_DUAL_ITEMLAYOUT = (
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<visible>Skin.HasSetting(t7b_patch_on)</visible>\n"
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t\t<font>font13</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t</control>\n"
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<visible>!Skin.HasSetting(t7b_patch_on)</visible>\n"
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t\t<font>font30_title</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t</control>\n"
)
_FORK_SINGLE_ITEMLAYOUT = (
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t\t<font>font13</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t</control>\n"
)
_GOLDEN_DUAL_FOCUSEDLAYOUT = (
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<visible>Skin.HasSetting(t7b_patch_on)</visible>\n"
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<font>font13</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t\t<scroll>true</scroll>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t</control>\n"
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<visible>!Skin.HasSetting(t7b_patch_on)</visible>\n"
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<font>font30_title</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t\t<scroll>true</scroll>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t</control>\n"
)
_FORK_SINGLE_FOCUSEDLAYOUT = (
    '\t\t\t\t\t<control type="label">\n'
    "\t\t\t\t\t\t<textoffsetx>30</textoffsetx>\n"
    "\t\t\t\t\t\t<width>470</width>\n"
    "\t\t\t\t\t\t<height>70</height>\n"
    "\t\t\t\t\t\t<font>font13</font>\n"
    "\t\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t\t<scroll>true</scroll>\n"
    "\t\t\t\t\t\t<label>$INFO[ListItem.Label]</label>\n"
    "\t\t\t\t\t</control>\n"
)
# The overlay's whole custom category dies in the fork (owner directive
# 2026-07-10: no Estuary 7 tab): the grouplist with the header label, the
# master toggle 1102, and the System Info radiobutton 1101 - which moves into
# stock General > Top Bar instead (see _SYSINFO_IN_TOPBAR).
_GOLDEN_T7B_GROUPLIST = (
    '\t\t\t<control type="grouplist" id="1100">\n'
    "\t\t\t\t<top>168</top>\n"
    "\t\t\t\t<left>0</left>\n"
    "\t\t\t\t<right>0</right>\n"
    "\t\t\t\t<bottom>142</bottom>\n"
    "\t\t\t\t<onleft>9000</onleft>\n"
    "\t\t\t\t<onright>60</onright>\n"
    "\t\t\t\t<onup>1100</onup>\n"
    "\t\t\t\t<ondown>1100</ondown>\n"
    "\t\t\t\t<pagecontrol>60</pagecontrol>\n"
    "\t\t\t\t<visible>Container(9000).HasFocus(11)</visible>\n"
    '\t\t\t\t<control type="label" id="100111">\n'
    "\t\t\t\t\t<textoffsetx>45</textoffsetx>\n"
    "\t\t\t\t\t<top>0</top>\n"
    "\t\t\t\t\t<height>80</height>\n"
    "\t\t\t\t\t<label>Tony.7.Bones MOD V2++</label>\n"
    "\t\t\t\t\t<align>center</align>\n"
    "\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t<font>font28_title</font>\n"
    "\t\t\t\t\t<textcolor>grey</textcolor>\n"
    "\t\t\t\t\t<shadowcolor>black</shadowcolor>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="radiobutton" id="1102">\n'
    "\t\t\t\t\t<label>Tony.7.Bones MOD V2++</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>RunScript(script.tony7bones.modv2plus,toggle)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(t7b_patch_on)</selected>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="radiobutton" id="1101">\n'
    "\t\t\t\t\t<label>System Info overlay</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>Skin.ToggleSetting(show_system_info_overlay)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(show_system_info_overlay)</selected>\n"
    "\t\t\t\t</control>\n"
    "\t\t\t</control>\n"
)
_GOLDEN_T7B_ITEM11 = (
    '\t\t\t\t\t<item id="11">\n'
    "\t\t\t\t\t\t<label>Tony.7.Bones MOD V2++</label>\n"
    "\t\t\t\t\t\t<visible>System.AddonIsEnabled(script.tony7bones.modv2plus)</visible>\n"
    "\t\t\t\t\t</item>\n"
)


def _cat_item(item_id, label_id):
    return (
        '\t\t\t\t\t<item id="{}">\n'
        "\t\t\t\t\t\t<label>$LOCALIZE[{}]</label>\n"
        "\t\t\t\t\t</item>\n".format(item_id, label_id)
    )


# The fork lists the categories in stock Estuary's order (General, Main menu,
# Artwork, OSD, then MOD V2's extra panels); the golden kept upstream's order.
_GOLDEN_CATEGORY_ORDER = "".join(
    _cat_item(i, l)
    for i, l in (
        (2, 31203),
        (1, 128),
        (5, 14022),
        (3, 31159),
        (9, 31278),
        (10, 31279),
        (7, 14204),
        (4, 31219),
        (6, 31266),
        (8, 31273),
    )
)
_FORK_CATEGORY_ORDER = "".join(
    _cat_item(i, l)
    for i, l in (
        (1, 128),
        (2, 31203),
        (3, 31159),
        (9, 31278),
        (10, 31279),
        (5, 14022),
        (7, 14204),
        (4, 31219),
        (6, 31266),
    )
)

# MOD V2's SkinSettings wordmark - removed in the fork (stock shows nothing).
_GOLDEN_SKINSETTINGS_LOGO = (
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

_GOLDEN_SCROLLBAR_WIRING = (
    '\t\t\t\t<onleft condition="Container(9000).HasFocus(11)">1100</onleft>\n'
    '\t\t\t\t<onright condition="Container(9000).HasFocus(11)">1100</onright>\n'
)
# The fork inserts two toggles below "Disable zoom effect" (radiobutton 702),
# i.e. before "Default button on Video/Audio OSD" (button 703): the system-info
# overlay toggle, then 'Toggle Skin Settings / Games' (swaps the System-page
# Games tile for a Skin Settings tile; default off = Games).
_SYSINFO_IN_GENERAL = (
    '\t\t\t\t<control type="radiobutton" id="1101">\n'
    "\t\t\t\t\t<label>Show system info on Settings focus</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>Skin.ToggleSetting(show_system_info_overlay)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(show_system_info_overlay)</selected>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="radiobutton" id="1102">\n'
    "\t\t\t\t\t<label>Toggle Skin Settings / Games</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>Skin.ToggleSetting(SkinSettingsTile)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(SkinSettingsTile)</selected>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="703">\n'
)

# The fork's "Show labeled tiles" sub-option (1.0.41, owner request
# 2026-07-15): hide the fork poster fade + label on Movies & TV Shows tiles
# only. Inserted after the PVR-info sub-option (10022), before the next
# stock toggle (10014).
_VIDEO_LABEL_OPTOUT_TOGGLE = (
    '\t\t\t\t<control type="radiobutton" id="1103">\n'
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<label>  ∟Do not apply labels to Movies &amp; TV Shows</label>\n"
    "\t\t\t\t\t<onclick>Skin.ToggleSetting(hide_video_tile_labels)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(hide_video_tile_labels)</selected>\n"
    "\t\t\t\t\t<visible>!Skin.HasSetting(hide_tile_labels)</visible>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="radiobutton" id="10014">\n'
)


# The fork's helper invocations run the file, not the addon id (the skin
# ships no python.script extension). Applied after the golden's id rename.
def _runscript_rewire(count):
    return (
        "RunScript(skin.estuary7,",
        "RunScript(special://skin/scripts/helpers.py,",
        count,
    )


# (old, new, count) replaces that turn each GOLDEN into the expected fork
# bytes. Counts are asserted - a golden that stops matching its own
# normalization is itself drift and must fail.
_WIDGET_INVERSIONS = [
    ("!Skin.HasSetting(hide_{})".format(f), "Skin.HasSetting(show_{})".format(f), 1)
    for f in (
        "recordingchannels",
        "searches",
        "allchannels",
        "audioaddons",
        "gameaddons",
        "imageaddons",
    )
]
_BACKGROUND_INVERSIONS = [
    (
        "!Skin.HasSetting(enable_{}_background)".format(f),
        "Skin.HasSetting(show_{}_background)".format(f),
        2,
    )
    for f in ("power", "settings", "search")
]

# The fork's "Add media sources" launcher block (a section header + Videos/
# Music/Pictures/Games file-browser buttons) is inserted into the Extras
# category pane, directly above the Debug section header (id 900014). Pure
# fork addition - the golden gains it verbatim (owner directive 2026-07-10:
# the System page's old Media sources tile relocates here).
_MEDIA_SOURCES_BLOCK = (
    '\t\t\t\t<control type="label" id="900020">\n'
    "\t\t\t\t\t<textoffsetx>45</textoffsetx>\n\t\t\t\t\t<top>0</top>\n\t\t\t\t\t<height>80</height>\n"
    "\t\t\t\t\t<label>$LOCALIZE[31201]</label>\n\t\t\t\t\t<align>center</align>\n\t\t\t\t\t<aligny>center</aligny>\n"
    "\t\t\t\t\t<font>font28_title</font>\n\t\t\t\t\t<textcolor>grey</textcolor>\n\t\t\t\t\t<shadowcolor>black</shadowcolor>\n"
    "\t\t\t\t</control>\n"
    '\t\t\t\t<control type="button" id="520">\n\t\t\t\t\t<label>$LOCALIZE[3]</label>\n\t\t\t\t\t<include>DefaultSettingButton</include>\n\t\t\t\t\t<onclick>ActivateWindow(Videos,Files,return)</onclick>\n\t\t\t\t</control>\n'
    '\t\t\t\t<control type="button" id="521">\n\t\t\t\t\t<label>$LOCALIZE[2]</label>\n\t\t\t\t\t<include>DefaultSettingButton</include>\n\t\t\t\t\t<onclick>ActivateWindow(Music,Files,return)</onclick>\n\t\t\t\t</control>\n'
    '\t\t\t\t<control type="button" id="522">\n\t\t\t\t\t<label>$LOCALIZE[1]</label>\n\t\t\t\t\t<include>DefaultSettingButton</include>\n\t\t\t\t\t<onclick>ActivateWindow(pictures,root)</onclick>\n\t\t\t\t</control>\n'
    '\t\t\t\t<control type="button" id="523">\n\t\t\t\t\t<label>$LOCALIZE[15016]</label>\n\t\t\t\t\t<include>DefaultSettingButton</include>\n\t\t\t\t\t<onclick>ActivateWindow(games,root)</onclick>\n\t\t\t\t\t<visible>System.GetBool(gamesgeneral.enable)</visible>\n\t\t\t\t</control>\n'
)
_DEBUG_HEADER = '\t\t\t\t<control type="label" id="900014">'


NORMALIZE = {
    "Home.xml": _WIDGET_INVERSIONS
    + [
        (
            "$LOCALIZE[166] Estuary MOD V2 • ",
            "$LOCALIZE[166] Estuary 7 • ",
            1,
        ),
        _runscript_rewire(1),
        # Clear the stuck skinshortcuts-isrunning guard; then upstream's single
        # buildxml on every later Home load (self-heals a menu edit OR a hash
        # mismatch via shouldwerun), with the one first-per-boot build deferred
        # past the keep-dialog timer. On tvOS the later-load build is CHAINED by
        # syncMenu (t7b_chainbuild marker, set synchronously before the spawn)
        # instead of racing it as a parallel RunScript.
        (
            "\t<onload>RunScript(script.skinshortcuts,type=buildxml&amp;"
            "mainmenuID=9000&amp;group=mainmenu)</onload>",
            "\t<onload>RunScript(special://skin/scripts/helpers.py,seedPVR)</onload>\n"
            '\t<onload condition="System.Platform.TVOS + !String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
            "SetProperty(t7b_chainbuild,1,10000)</onload>\n"
            '\t<onload condition="System.Platform.TVOS">RunScript(special://skin/scripts/helpers.py,syncMenu)</onload>\n'
            "\t<onload>ClearProperty(skinshortcuts-isrunning,10000)</onload>\n"
            '\t<onload condition="!System.Platform.TVOS + !String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
            "RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;"
            "group=mainmenu)</onload>\n"
            '\t<onload condition="String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
            "AlarmClock(t7bbuild,RunScript(script.skinshortcuts,type=buildxml&amp;"
            "mainmenuID=9000&amp;group=mainmenu),00:15,silent)</onload>\n"
            '\t<onload condition="String.IsEmpty(Window(10000).Property(t7b_firstbuild_done))">'
            "SetProperty(t7b_firstbuild_done,1,10000)</onload>",
            1,
        ),
        # Centered ◆KODI logo (owner directive 2026-07-10): the main logo group
        # gets a conditional +70 slide when the menu is full, and its wordmark
        # is left-aligned at left=78 (tight gap). Both are new vs the golden.
        (
            "!Skin.HasSetting(MinimizeMainMenu)]]</visible>\n"
            "\t\t\t\t<top>20</top>\n\t\t\t\t<left>20</left>",
            "!Skin.HasSetting(MinimizeMainMenu)]]</visible>\n"
            '\t\t\t\t<animation effect="slide" end="70,0" time="0" '
            'condition="!Skin.HasSetting(MinimizeMainMenu)">Conditional</animation>\n'
            "\t\t\t\t<top>20</top>\n\t\t\t\t<left>20</left>",
            1,
        ),
        (
            "\t\t\t\t\t<left>55</left>\n\t\t\t\t\t<top>8</top>\n"
            "\t\t\t\t\t<aspectratio>keep</aspectratio>\n\t\t\t\t\t<width>202</width>\n"
            "\t\t\t\t\t<height>39</height>\n"
            "\t\t\t\t\t<texture>extras/logo-text-hires.png</texture>",
            "\t\t\t\t\t<left>78</left>\n\t\t\t\t\t<top>8</top>\n"
            '\t\t\t\t\t<aspectratio align="left">keep</aspectratio>\n'
            "\t\t\t\t\t<width>202</width>\n"
            "\t\t\t\t\t<height>39</height>\n"
            "\t\t\t\t\t<texture>extras/logo-text-hires.png</texture>",
            1,
        ),
    ],
    "Settings.xml": [
        ("Skin.SetBool(EnableSplashScreen)", "Skin.Reset(ShowSplashScreen)", 1),
        _runscript_rewire(2),
        # System-page Games slot: stock Games card by default, swapped to Skin
        # Settings by the 'Toggle Skin Settings / Games' General toggle (mutually
        # exclusive; the grid keeps eight tiles).
        (
            "\t\t\t\t\t<item>\n"
            "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
            "\t\t\t\t\t\t<onclick>ActivateWindow(SkinSettings)</onclick>\n"
            "\t\t\t\t\t\t<icon>icons/settings/skin.png</icon>\n"
            "\t\t\t\t\t</item>\n",
            "\t\t\t\t\t<item>\n"
            "\t\t\t\t\t\t<label>$LOCALIZE[15016]</label>\n"
            "\t\t\t\t\t\t<visible>System.GetBool(gamesgeneral.enable) + "
            "!Skin.HasSetting(SkinSettingsTile)</visible>\n"
            "\t\t\t\t\t\t<onclick>ActivateWindow(GameSettings)</onclick>\n"
            "\t\t\t\t\t\t<icon>icons/settings/games.png</icon>\n"
            "\t\t\t\t\t</item>\n"
            "\t\t\t\t\t<item>\n"
            "\t\t\t\t\t\t<label>$LOCALIZE[10035]</label>\n"
            "\t\t\t\t\t\t<visible>Skin.HasSetting(SkinSettingsTile)</visible>\n"
            "\t\t\t\t\t\t<onclick>ActivateWindow(SkinSettings)</onclick>\n"
            "\t\t\t\t\t\t<icon>icons/settings/skin.png</icon>\n"
            "\t\t\t\t\t</item>\n",
            1,
        ),
    ],
    "Includes.xml": [
        (
            '\t<expression name="EnableTheme">',
            '\t<expression name="PowerMenuList">!Skin.HasSetting(powermenu_panel) + '
            "!Skin.HasSetting(powermenu_iconlist)</expression>\n"
            '\t<expression name="EnableTheme">',
            1,
        ),
        ("!Skin.HasSetting(DisableThemes)", "Skin.HasSetting(EnableThemes)", 6),
        ("Skin.HasSetting(show_weatherinfo)", "!Skin.HasSetting(hide_weatherinfo)", 3),
        # 1.0.46: the golden carries the outline-hd resource URL (the
        # 1.0.1-1.0.45 rewrite); the fork now bakes those icons into
        # extras/weather and keeps upstream's skin-local default path.
        (
            "<texture>$INFO[Weather.FanartCode,"
            "resource://resource.images.weathericons.outline-hd/,.png]</texture>",
            "<texture>$INFO[Weather.FanartCode,"
            "special://skin/extras/weather/,.png]</texture>",
            1,
        ),
        # 1.0.40: the finish-time flag groups drop upstream's plugin-window
        # suppression so the flag bar matches Home inside widget "More"
        # lists (all four end-time groups; no other flag carried the term).
        ("!String.StartsWith(Container.FolderPath,plugin://) + ", "", 4),
        # 1.0.40: the media-flags rating badge gains the show_tmdbflag gate
        # its toggle always claimed (upstream forgot it; only the spacer
        # honored it) - both logo variants.
        (
            '<param name="visible" value="!Skin.HasSetting(use_imdblogo) + '
            "!String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            '<param name="visible" value="!Skin.HasSetting(show_tmdbflag) + '
            "!Skin.HasSetting(use_imdblogo) + "
            "!String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            1,
        ),
        (
            '<param name="visible" value="Skin.HasSetting(use_imdblogo) + '
            "!String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            '<param name="visible" value="!Skin.HasSetting(show_tmdbflag) + '
            "Skin.HasSetting(use_imdblogo) + "
            "!String.IsEqual($PARAM[infolabel_prefix]ListItem.DBType,album)",
            1,
        ),
        (
            "[Window.IsVisible(shutdownmenu) + Skin.HasSetting(powermenu_list)]",
            "[Window.IsVisible(shutdownmenu) + $EXP[PowerMenuList]]",
            3,
        ),
        # System-page SettingsPanel tiles -> stock Estuary's 400-wide cell (1.0.33).
        ('height="260" width="380"', 'height="260" width="400"', 2),
        ("<width>390</width>", "<width>410</width>", 2),
        (
            "\t\t\t\t<left>15</left>\n\t\t\t\t<top>190</top>\n\t\t\t\t<width>350</width>",
            "\t\t\t\t<left>25</left>\n\t\t\t\t<top>190</top>\n\t\t\t\t<width>350</width>",
            1,
        ),
        (
            "\t\t\t\t\t<left>15</left>\n\t\t\t\t\t<top>190</top>\n\t\t\t\t\t<width>350</width>",
            "\t\t\t\t\t<left>25</left>\n\t\t\t\t\t<top>190</top>\n\t\t\t\t\t<width>350</width>",
            1,
        ),
        (
            "\t\t\t\t\t<top>-6</top>\n\t\t\t\t\t<left>-11</left>\n"
            "\t\t\t\t\t<width>402</width>\n\t\t\t\t\t<height>282</height>",
            "\t\t\t\t\t<left>-5</left>\n\t\t\t\t\t<width>410</width>\n"
            "\t\t\t\t\t<height>270</height>",
            2,
        ),
    ],
    "Variables.xml": [
        (
            '\t\t<value condition="Container(9000).HasFocus(11)">'
            "Tony.7.Bones MOD V2++ settings</value>\n",
            "",
            1,
        ),
        (
            '<value condition="Skin.HasSetting(powermenu_list)">$LOCALIZE[31427]</value>',
            "<value>$LOCALIZE[31427]</value>",
            1,
        ),
    ]
    + _BACKGROUND_INVERSIONS,
    "SkinSettings.xml": [
        _runscript_rewire(3),
        # 1.0.60: the hide-watched-badge switch below the grey-out (home) row
        (_GREYEDOUT_HOME_ROW, _GREYEDOUT_HOME_ROW + _HIDE_WATCHED_TOGGLE, 1),
        (_DEBUG_HEADER, _MEDIA_SOURCES_BLOCK + _DEBUG_HEADER, 1),
        (
            "\t\t\t\t\t<onclick>RunScript(script.skinshortcuts,type=resetall)</onclick>",
            "\t\t\t\t\t<onclick>RunScript(special://skin/scripts/helpers.py,resetMenu)</onclick>",
            1,
        ),
        (
            "\t\t\t\t\t<label>$LOCALIZE[31468]</label>",
            "\t\t\t\t\t<label>Show labeled tiles</label>",
            1,
        ),
        (
            "\t\t\t\t\t<selected>!Skin.HasSetting(HideWidgetLabels)</selected>",
            "\t\t\t\t\t<selected>Skin.HasSetting(HideWidgetLabels)</selected>",
            1,
        ),
        (
            "\t\t\t\t\t<visible>!Skin.HasSetting(HideWidgetLabels)</visible>",
            "\t\t\t\t\t<visible>Skin.HasSetting(HideWidgetLabels)</visible>",
            1,
        ),
        (
            '\t\t\t\t<control type="radiobutton" id="10014">\n',
            _VIDEO_LABEL_OPTOUT_TOGGLE,
            1,
        ),
        # 1.0.42 (moved/renamed 1.0.43): POV search toggle, just above the
        # Power-options background toggle.
        (
            '\t\t\t\t<control type="radiobutton" id="10006">\n',
            '\t\t\t\t<control type="radiobutton" id="1104">\n'
            "\t\t\t\t\t<label>Enable POV search</label>\n"
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            "\t\t\t\t\t<onclick>Skin.ToggleSetting(use_pov_search)</onclick>\n"
            "\t\t\t\t\t<selected>Skin.HasSetting(use_pov_search)</selected>\n"
            "\t\t\t\t\t<visible>System.AddonIsEnabled(plugin.video.pov)</visible>\n"
            "\t\t\t\t</control>\n"
            '\t\t\t\t<control type="radiobutton" id="10006">\n',
            1,
        ),
        (_GOLDEN_T7B_GROUPLIST, "", 1),
        (_GOLDEN_T7B_ITEM11, "", 1),
        (_GOLDEN_CATEGORY_ORDER, _FORK_CATEGORY_ORDER, 1),
        (_GOLDEN_SKINSETTINGS_LOGO, "", 1),
        (_GOLDEN_SCROLLBAR_WIRING, "", 1),
        (
            "\t\t\t\t<width>470</width>\n\t\t\t\t<height>770</height>",
            "\t\t\t\t<width>470</width>\n\t\t\t\t<height>700</height>",
            1,
        ),
        (
            "Control.IsVisible(1000) | Control.IsVisible(1100)</visible>",
            "Control.IsVisible(1000)</visible>",
            1,
        ),
        ('\t\t\t\t<control type="button" id="703">\n', _SYSINFO_IN_GENERAL, 1),
        (_GOLDEN_DUAL_ITEMLAYOUT, _FORK_SINGLE_ITEMLAYOUT, 1),
        (_GOLDEN_DUAL_FOCUSEDLAYOUT, _FORK_SINGLE_FOCUSEDLAYOUT, 1),
        # 1.0.46 Extras declutter: the splash cluster (toggle 503 + gated
        # sub-rows 504/505), the themes toggle (506), and the Home menu
        # pane's Kodi/Distribution logo chooser (10023) leave Skin Settings
        # entirely (owner directives 2026-07-15). These replace the former
        # splash/themes rename pairs, whose anchors lived inside the rows.
        (
            '\t\t\t\t<control type="radiobutton" id="503">\n'
            "\t\t\t\t\t<label>$LOCALIZE[31051]</label>\n"
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            '\t\t\t\t\t<onclick condition="String.IsEqual(Window(home).property(lookandfeel.startupaction),0)">Skin.ToggleSetting(EnableSplashScreen)</onclick>\n'
            "\t\t\t\t\t<selected>!Skin.HasSetting(EnableSplashScreen) + String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</selected>\n"
            "\t\t\t\t\t<enable>String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</enable>\n"
            "\t\t\t\t</control>\n"
            '\t\t\t\t<control type="radiobutton" id="504">\n'
            "\t\t\t\t\t<label>$LOCALIZE[31640]</label>\n"
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            "\t\t\t\t\t<selected>!Skin.HasSetting(enable_splash_background)</selected>\n"
            "\t\t\t\t\t<onclick>Skin.ToggleSetting(enable_splash_background)</onclick>\n"
            "\t\t\t\t\t<visible>!Skin.HasSetting(EnableSplashScreen) + String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</visible>\n"
            "\t\t\t\t</control>\n"
            '\t\t\t\t<control type="button" id="505">\n'
            "\t\t\t\t\t<label>  ∟$LOCALIZE[31344]</label>\n"
            "\t\t\t\t\t<label2>$VAR[Label_SkinSetting_SplashFanart]</label2>\n"
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            '\t\t\t\t\t<onclick condition="!Skin.String(splash_background)">Skin.SetImage(splash_background)</onclick>\n'
            '\t\t\t\t\t<onclick condition="Skin.String(splash_background)">Skin.Reset(splash_background)</onclick>\n'
            "\t\t\t\t\t<visible>!Skin.HasSetting(EnableSplashScreen) + !Skin.HasSetting(enable_splash_background) + String.IsEqual(Window(home).property(lookandfeel.startupaction),0)</visible>\n"
            "\t\t\t\t</control>\n",
            "",
            1,
        ),
        (
            '\t\t\t\t<control type="radiobutton" id="506">\n'
            "\t\t\t\t\t<label>$LOCALIZE[31459]</label>\n"
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            "\t\t\t\t\t<onclick>Skin.ToggleSetting(DisableThemes)</onclick>\n"
            "\t\t\t\t\t<selected>!Skin.HasSetting(DisableThemes)</selected>\n"
            "\t\t\t\t</control>\n",
            "",
            1,
        ),
        (
            '\t\t\t\t<control type="button" id="10023">\n'
            "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
            "\t\t\t\t\t<description>menu logo</description>\n"
            "\t\t\t\t\t<onclick>Skin.SelectBool(31567, 15109|MenuLogoDefault, "
            "31568|MenuLogoLE, 31569|MenuLogoCE)</onclick>\n"
            "\t\t\t\t\t<label>$LOCALIZE[31567]</label>\n"
            "\t\t\t\t\t<label2>$VAR[Label_SkinSetting_Logo]</label2>\n"
            "\t\t\t\t</control>\n",
            "",
            1,
        ),
        (
            "<selected>Skin.HasSetting(show_weatherinfo) + "
            "!String.IsEmpty(Weather.Plugin)</selected>",
            "<selected>!Skin.HasSetting(hide_weatherinfo) + "
            "!String.IsEmpty(Weather.Plugin)</selected>",
            1,
        ),
        (
            "Skin.ToggleSetting(show_weatherinfo)",
            "Skin.ToggleSetting(hide_weatherinfo)",
            1,
        ),
    ]
    + [
        pair
        for f in ("power", "settings", "search")
        for pair in (
            (
                "<selected>!Skin.HasSetting(enable_{}_background)</selected>".format(f),
                "<selected>Skin.HasSetting(show_{}_background)</selected>".format(f),
                1,
            ),
            (
                "Skin.ToggleSetting(enable_{}_background)".format(f),
                "Skin.ToggleSetting(show_{}_background)".format(f),
                1,
            ),
            (
                "<visible>!Skin.HasSetting(enable_{}_background)</visible>".format(f),
                "<visible>Skin.HasSetting(show_{}_background)</visible>".format(f),
                1,
            ),
        )
    ],
}


def _invert_widget_labels(text: str) -> str:
    """Mirror skin_transforms.invert_widget_labels for golden parity."""
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


def _normalize_golden(name: str, text: str) -> str:
    text = text.replace(UPSTREAM_ID, SKIN_ID)
    if name == "Variables.xml":
        # 1.0.39: the view-picker image variable is deleted (the same
        # transform the build applies), not normalized pair-by-pair.
        text = drop_settings_views_variable(text, path="golden " + name)
    if name == "Font.xml":
        # 1.0.47: the lyrics font files are repointed at NotoSans (the same
        # transform the build applies) since fonts/lyrics/ was trimmed.
        text = repoint_lyrics_fonts(text, path="golden " + name)
    for old, new, count in NORMALIZE.get(name, []):
        found = text.count(old)
        assert found == count, (
            "golden {}: normalization anchor {!r} occurs {}x, expected {}x".format(
                name, old[:80], found, count
            )
        )
        text = text.replace(old, new)
    text = _invert_widget_labels(text)
    return _COMMENT_RE.sub("", text)


@pytest.mark.parametrize("name", GOLDEN_FILES)
def test_golden_parity(built, name):
    golden = (GOLDENS / "xml" / name).read_text(encoding="utf-8")
    actual = (built.tree / "xml" / name).read_text(encoding="utf-8")
    expected = _normalize_golden(name, golden)
    actual = _COMMENT_RE.sub("", actual)
    assert actual == expected, "{} diverges from the hardware-verified golden".format(
        name
    )
