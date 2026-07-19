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
    ("ShowSplashScreen", 4),  # Startup(2) + Timers + System-page reset;
    # the Skin Settings toggle left in the 1.0.46 Extras declutter
    ("EnableThemes", 6),  # 6 theme expressions; toggle removed 1.0.46
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
    # The withdrawn 1.0.40 $EXP attempt left no remnants.
    joined = "".join(corpus.values())
    assert "tile_unlabeled" not in joined


def test_video_label_optout_toggle_wired(corpus):
    """1.0.41: 'Do not apply labels to Movies & TV Shows' (radiobutton 1103
    under 'Show labeled tiles') hides the fork poster fade + label on
    video-library items only, via per-item <visible> terms on the fork
    controls - never include conditions (the withdrawn first attempt's
    hardware lesson). Default off = the shipped 1.0.40 look untouched."""
    optout = (
        "![Skin.HasSetting(video_tile_labels_off) + ["
        "String.IsEqual(ListItem.DBType,movie) | "
        "String.IsEqual(ListItem.DBType,set) | "
        "String.IsEqual(ListItem.DBType,tvshow) | "
        "String.IsEqual(ListItem.DBType,season) | "
        "String.IsEqual(ListItem.DBType,episode)]]"
    )
    ih = corpus["Includes_Home.xml"]
    # Every fork fade (4) and label (8) control carries the gate.
    assert ih.count("<visible>" + optout + "</visible>") == 12
    # The sub-toggle: wired in SkinSettings.xml, visible only while the
    # parent labels toggle is on, and nothing else writes the flag.
    skinsettings = corpus["SkinSettings.xml"]
    assert "Skin.ToggleSetting(video_tile_labels_off)" in skinsettings
    assert "<selected>Skin.HasSetting(video_tile_labels_off)</selected>" in skinsettings
    writers = [
        name
        for name, text in corpus.items()
        if "Skin.ToggleSetting(video_tile_labels_off)" in text
    ]
    assert writers == ["SkinSettings.xml"], writers
    readers = sorted(
        name for name, text in corpus.items() if "video_tile_labels_off" in text
    )
    assert readers == ["Includes_Home.xml", "SkinSettings.xml"], readers


def test_retired_video_label_id_is_never_read(corpus):
    """1.0.71: `hide_video_tile_labels` is RETIRED and must appear nowhere in
    the built skin.

    The withdrawn first-take 1.0.40 published that id and wrote it `true`
    into addon_data; 1.0.41 later re-pointed the same id at live behaviour,
    so any box (or any EZ Maintenance++ backup zip) still carrying the stale
    value silently loses the title and year on its movie/TV widget tiles.
    A published name cannot be un-published, so the fork stops reading it
    instead - which makes every stale `true` in the wild inert forever,
    without writing to a single box's storage.

    If this test fails, someone has re-armed a live landmine. Pick a new
    name; never revive this one."""
    offenders = sorted(
        name for name, text in corpus.items() if "hide_video_tile_labels" in text
    )
    assert offenders == [], offenders


def test_pov_search_toggle_wired(corpus):
    """1.0.42: 'Use POV search' (radiobutton 1104, Home menu pane) swaps the
    home Search popup's four provider items for POV's four search entries.
    The toggle is visible only while plugin.video.pov is installed AND
    enabled, and every popup item re-checks the same condition live - POV
    vanishing falls back to the stock popup. Default off = stock popup,
    zero settings writes."""
    pov_on = "Skin.HasSetting(use_pov_search) + System.AddonIsEnabled(plugin.video.pov)"
    dialog = corpus["Custom_1107_SearchDialog.xml"]
    # Four stock items gated off in POV mode, four POV items gated on.
    assert dialog.count("<visible>![" + pov_on + "]</visible>") == 4
    assert dialog.count("<visible>" + pov_on + "</visible>") == 4
    # POV's exact search-history routes, one per entry.
    for action in ("movie", "tvshow", "people", "tmdb_collections"):
        assert dialog.count("mode=search_history&amp;action=" + action + "&amp;") == 1
    # The toggle: wired in SkinSettings.xml, POV-gated, sole writer.
    skinsettings = corpus["SkinSettings.xml"]
    assert "Skin.ToggleSetting(use_pov_search)" in skinsettings
    assert "<selected>Skin.HasSetting(use_pov_search)</selected>" in skinsettings
    writers = [
        name
        for name, text in corpus.items()
        if "Skin.ToggleSetting(use_pov_search)" in text
    ]
    assert writers == ["SkinSettings.xml"], writers
    readers = sorted(name for name, text in corpus.items() if "use_pov_search" in text)
    assert readers == ["Custom_1107_SearchDialog.xml", "SkinSettings.xml"], readers


def test_trim_round_1044(corpus, built):
    """1.0.44 trim round (owner-approved): dead weight is gone, the things
    that must survive it are still shipped, and the EPG genre-colors cycle
    no longer offers the trimmed 'genre artwork' mode. (Path absence itself
    is enforced by build_skin's ship-contract check over TRIM_PATHS; this
    pins the survivors and the cycle rewire.)"""
    tree = built.tree
    # Survivors adjacent to trimmed things.
    assert (tree / "language" / "resource.language.en_gb").is_dir()
    assert (tree / "extras" / "themes" / "background.jpg").is_file()
    assert (tree / "extras" / "themes" / "t7b-splash.jpg").is_file()
    assert (tree / "fonts" / "NotoSans-Regular.ttf").is_file()
    # The genre-artwork mode (20190) is gone from the sidebar cycle; the
    # remaining pair still cycles.
    mm = corpus["Includes_MediaMenu.xml"]
    assert "20190" not in mm
    assert mm.count("Skin.SetString(genrecolors,571)") == 1
    assert mm.count("Skin.SetString(genrecolors,1223)") == 3
    # Font.xml keeps the lyr* id inventory even though the faces are gone.
    assert "lyr" in corpus["Font.xml"]


def test_weather_icons_baked_default(corpus, built):
    """1.0.46: the Outline HD icons are VENDORED at extras/weather (CC BY
    3.0, credited in ATTRIBUTION.md) and every default weather-icon path is
    skin-local - no resource-pack import, no download on a fresh box. The
    WeatherIcons pack chooser still overrides when a user picks one."""
    joined = "".join(corpus.values())
    # No reference to any SPECIFIC icon pack survives; the Artworks pane's
    # pack CHOOSER keeps its generic resource-type filter (a user picking an
    # installed pack still overrides the baked default).
    assert "resource.images.weathericons.outline-hd" not in joined
    assert "resource.images.weathericons.default" not in joined
    assert joined.count("special://skin/extras/weather/") == 5
    addon = (built.tree / "addon.xml").read_text(encoding="utf-8")
    assert "weathericons" not in addon
    weather = built.tree / "extras" / "weather"
    icons = {p.stem for p in weather.glob("*.png")}
    # The complete Weather.FanartCode inventory: codes 0-47 plus na.
    assert icons == {str(n) for n in range(48)} | {"na"}
    assert (weather / "LICENSE.txt").is_file()


def test_no_runtime_settings_writers_shipped(built):
    """Nothing in the shipped tree writes our defaults at runtime - the whole
    point of the fork. (The skin's own scripts may Skin.SetBool for USER
    choices; our retired flags must not be among them.)"""
    for py in sorted((built.tree / "scripts").glob("*.py")):
        text = py.read_text(encoding="utf-8")
        for flag in RETIRED_FLAGS:
            assert flag not in text, "{} writes {}".format(py.name, flag)
