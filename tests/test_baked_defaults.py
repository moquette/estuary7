"""Baked-defaults contracts: a FRESH box (zero settings writes) renders the
Tony.7.Bones look, and every toggle now opts back toward stock.

Independent of the transform tables on purpose: these greps assert the END
STATE of the whole xml/ tree, so a typo mirrored between a transform and its
golden normalization still gets caught here.
"""

from __future__ import annotations

import pytest

# Flags the retired runtime overlay used to WRITE; after the inversion not a
# single reference may survive anywhere in the shipped tree.
RETIRED_FLAGS = [
    "show_weatherinfo",
    "EnableSplashScreen",
    "DisableThemes",
    "hide_recordingchannels",
    "hide_searches",
    "hide_allchannels",
    "hide_audioaddons",
    "hide_gameaddons",
    "hide_imageaddons",
    "enable_power_background",
    "enable_settings_background",
    "enable_search_background",
]

# Their opt-out/opt-in replacements (flag, minimum expected references).
REPLACEMENT_FLAGS = [
    ("hide_weatherinfo", 4),  # 3 includes + the toggle
    ("ShowSplashScreen", 5),  # Startup(2) + Timers + Settings reset + toggle
    ("EnableThemes", 7),  # 6 theme expressions + the toggle
    ("show_recordingchannels", 2),
    ("show_searches", 2),
    ("show_allchannels", 2),
    ("show_audioaddons", 2),
    ("show_gameaddons", 2),
    ("show_imageaddons", 2),
    ("show_power_background", 4),  # 2 variables + selected/onclick/visible... >= 4
    ("show_settings_background", 4),
    ("show_search_background", 4),
    ("show_system_info_overlay", 3),  # Home gate + toggle selected/onclick
]


def _xml_corpus(built) -> dict:
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted((built.tree / "xml").glob("*.xml"))
    }


@pytest.fixture(scope="module")
def corpus(built):
    return _xml_corpus(built)


@pytest.mark.parametrize("flag", RETIRED_FLAGS)
def test_retired_flag_gone(corpus, flag):
    hits = [name for name, text in corpus.items() if flag in text]
    assert not hits, "{} still referenced in {}".format(flag, hits)


@pytest.mark.parametrize("flag, minimum", REPLACEMENT_FLAGS)
def test_replacement_flag_wired(corpus, flag, minimum):
    total = sum(text.count(flag) for text in corpus.values())
    assert total >= minimum, "{} referenced {}x, expected >= {}".format(
        flag, total, minimum
    )


def test_power_menu_defaults_to_classic_list(corpus):
    includes = corpus["Includes.xml"]
    assert includes.count('<expression name="PowerMenuList">') == 1
    # The vestigial bool survives ONLY inside the style picker's SelectBool.
    total = sum(
        text.count("Skin.HasSetting(powermenu_list)") for text in corpus.values()
    )
    assert total == 0
    remaining = {
        name: text.count("powermenu_list")
        for name, text in corpus.items()
        if "powermenu_list" in text
    }
    assert remaining == {"SkinSettings.xml": 1}, remaining
    # Every former powermenu_list condition now rides the expression.
    users = [name for name, text in corpus.items() if "$EXP[PowerMenuList]" in text]
    assert sorted(users) == [
        "DialogButtonMenu.xml",
        "DialogNotification.xml",
        "Includes.xml",
    ]


def test_weather_icons_default_to_outline_hd(corpus, built):
    joined = "".join(corpus.values())
    assert "resource.images.weathericons.default" not in joined
    assert joined.count("resource://resource.images.weathericons.outline-hd/") >= 5
    addon = (built.tree / "addon.xml").read_text(encoding="utf-8")
    assert '<import addon="resource.images.weathericons.outline-hd"' in addon


def test_no_runtime_settings_writers_shipped(built):
    """Nothing in the shipped tree writes our defaults at runtime - the whole
    point of the fork. (The skin's own scripts may Skin.SetBool for USER
    choices; our retired flags must not be among them.)"""
    for py in sorted((built.tree / "scripts").glob("*.py")):
        text = py.read_text(encoding="utf-8")
        for flag in RETIRED_FLAGS:
            assert flag not in text, "{} writes {}".format(py.name, flag)
