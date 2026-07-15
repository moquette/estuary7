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


_POSTER_EMPTY = (
    "[String.IsEmpty(ListItem.Art(poster)) + "
    "String.IsEmpty(ListItem.Art(tvshow.poster)) + "
    "String.IsEmpty(ListItem.Art(season.poster)) + "
    "String.IsEmpty(ListItem.Art(animatedposter))]"
)


def test_labeled_poster_tiles_render_poster_plus_label(corpus):
    """1.0.40: in labeled mode, poster-art home tiles render the clean
    full poster with a fork label BELOW it; the square InfoWallMusicLayout
    chrome is per-item gated to no-poster items so the two layers never
    stack (the owner-rejected double-poster). The split rides group
    visibility, never include conditions (load-time, no item context)."""
    ih = corpus["Includes_Home.xml"]
    # 2 itemlayout + 2 focusedlayout no-poster wraps (Widget, WidgetListPoster).
    assert ih.count("<visible>" + _POSTER_EMPTY + "</visible>") == 4
    # 8 poster labels (year/no-year x focused/unfocused x 2 includes) + 4
    # fade bands + the 2 focused poster-present InfoWallMovieLayout groups.
    assert ih.count("<visible>!" + _POSTER_EMPTY + "</visible>") == 14
    # The label rides the poster's bottom 70px on the skin's fade texture
    # (full strength, 150px tall per owner taste), at the stock label height
    # (bench screenshot-compared): 4 sites x (1 fade at top 220 + 2 label
    # variants at top 300), upstream baseline zero.
    assert ih.count("overlays/overlayfade.png") == 4
    assert ih.count("<top>220</top>") == 4
    assert ih.count("<top>300</top>") == 8
    # The ITEMLAYOUTS carry an unconditioned InfoWallMovieLayout
    # (self-gating on art): generic Widget and WidgetPanelPoster ship it
    # that way upstream, WidgetListPoster gets its condition dropped by the
    # fork. The unlabeled-mode conditioned form survives only in the three
    # focusedlayouts (Widget, WidgetListPoster, WidgetPanelPoster - stock),
    # and the labeled poster-present form is the two fork groups counted
    # above.
    assert ih.count('<include content="InfoWallMovieLayout">') == 3
    assert (
        ih.count(
            '<include content="InfoWallMovieLayout" '
            'condition="Skin.HasSetting(hide_tile_labels)">'
        )
        == 3
    )
    # The withdrawn per-item toggle attempt left no remnants.
    joined = "".join(corpus.values())
    assert "tile_unlabeled" not in joined
    assert "hide_video_tile_labels" not in joined


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
