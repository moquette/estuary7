"""Golden parity: the transformed files must match the hardware-verified
modv2plus 1.8.0 bytes (tests/goldens/xml/), modulo the DOCUMENTED divergences.

The normalization applied to each golden below IS the divergence record:

  every file   - XML comments stripped from both sides (the goldens carry
                 patch-era marker comments; the fork needs none), and the
                 golden's skin id renamed (the fork is skin.estuary7).
  Settings.xml - the splash auto-disable writes the fork's opt-in flag.
  Includes.xml / Variables.xml / SkinSettings.xml / Home.xml
               - the runtime-written skin settings are baked as inverted
                 opt-out conditions (see skin_transforms module docstring).
  SkinSettings.xml
               - the master Apply/Restore toggle (radiobutton 1102) does not
                 exist in the fork; the category is named "Estuary 7", is no
                 longer gated on the retired modv2plus add-on, and the
                 category nav column is UNCONDITIONALLY thin (the golden
                 carried a dual thin/bold label pair driven by the runtime
                 t7b_patch_on mirror - plumbing the fork does not need).

Anything NOT normalized here that differs from the golden fails the test.
"""

from __future__ import annotations

import re

import pytest

from conftest import GOLDENS
from skin_transforms import SKIN_ID, UPSTREAM_ID

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
_GOLDEN_MASTER_TOGGLE = (
    '\t\t\t\t<control type="radiobutton" id="1102">\n'
    "\t\t\t\t\t<label>Tony.7.Bones MOD V2++</label>\n"
    "\t\t\t\t\t<include>DefaultSettingButton</include>\n"
    "\t\t\t\t\t<onclick>RunScript(script.tony7bones.modv2plus,toggle)</onclick>\n"
    "\t\t\t\t\t<selected>Skin.HasSetting(t7b_patch_on)</selected>\n"
    "\t\t\t\t</control>\n"
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

NORMALIZE = {
    "Home.xml": _WIDGET_INVERSIONS,
    "Settings.xml": [
        ("Skin.SetBool(EnableSplashScreen)", "Skin.Reset(ShowSplashScreen)", 1),
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
        (
            "[Window.IsVisible(shutdownmenu) + Skin.HasSetting(powermenu_list)]",
            "[Window.IsVisible(shutdownmenu) + $EXP[PowerMenuList]]",
            3,
        ),
    ],
    "Variables.xml": [
        ("Tony.7.Bones MOD V2++ settings", "Estuary 7 settings", 1),
        (
            '<value condition="Skin.HasSetting(powermenu_list)">$LOCALIZE[31427]</value>',
            "<value>$LOCALIZE[31427]</value>",
            1,
        ),
    ]
    + _BACKGROUND_INVERSIONS,
    "SkinSettings.xml": [
        (_GOLDEN_MASTER_TOGGLE, "", 1),
        ("Tony.7.Bones MOD V2++", "Estuary 7", 2),
        (
            "\t\t\t\t\t\t<visible>System.AddonIsEnabled(script.tony7bones.modv2plus)"
            "</visible>\n",
            "",
            1,
        ),
        (_GOLDEN_DUAL_ITEMLAYOUT, _FORK_SINGLE_ITEMLAYOUT, 1),
        (_GOLDEN_DUAL_FOCUSEDLAYOUT, _FORK_SINGLE_FOCUSEDLAYOUT, 1),
        (
            "<selected>!Skin.HasSetting(EnableSplashScreen) + "
            "String.IsEqual(Window(home).property(lookandfeel.startupaction),0)"
            "</selected>",
            "<selected>Skin.HasSetting(ShowSplashScreen) + "
            "String.IsEqual(Window(home).property(lookandfeel.startupaction),0)"
            "</selected>",
            1,
        ),
        (
            "!Skin.HasSetting(EnableSplashScreen)",
            "Skin.HasSetting(ShowSplashScreen)",
            2,
        ),
        (
            "Skin.ToggleSetting(EnableSplashScreen)",
            "Skin.ToggleSetting(ShowSplashScreen)",
            1,
        ),
        ("!Skin.HasSetting(DisableThemes)", "Skin.HasSetting(EnableThemes)", 1),
        ("Skin.ToggleSetting(DisableThemes)", "Skin.ToggleSetting(EnableThemes)", 1),
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


def _normalize_golden(name: str, text: str) -> str:
    text = text.replace(UPSTREAM_ID, SKIN_ID)
    for old, new, count in NORMALIZE.get(name, []):
        found = text.count(old)
        assert found == count, (
            "golden {}: normalization anchor {!r} occurs {}x, expected {}x".format(
                name, old[:80], found, count
            )
        )
        text = text.replace(old, new)
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
