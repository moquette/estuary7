"""The year must survive on PLUGIN-BACKED movie listings (1.0.72).

Owner-reported, 2026-07-19: with an EMPTY video library the home Movies item
falls through to the Videos window on `plugin://plugin.video.pov/...`. Posters
and titles drew; the year did not.

Two INDEPENDENT causes, both fixed and both guarded here. Bench-reproduced on
a plugin-backed movie list in the Videos window, not a home widget row:

1. LIST view (`View_50_List.xml`) has no year token of its own; its second
   column is `ListLabel2Var`, whose every year branch is gated on
   `String.IsEqual(Container.SortMethod,$LOCALIZE[556])` (sorted by Title). A
   plugin listing arrives sorted otherwise - the bench reproduction came up
   sorted by Date - so every year branch falls through to the plain
   `ListItem.Label2` tail and the row shows a title with no year. This is NOT
   a plugin:// gate, so relaxing gates would never have reached it.

2. `WallThumbsLayout` (defined in `View_54_InfoWall.xml`, consumed by
   `View_504_ThumbsWall.xml` and `View_505_ThumbsInfoWall.xml`) draws the
   library case as title + right-aligned year, each carrying
   `!String.StartsWith(Container.FolderPath,plugin://)`, then swaps in ONE
   centered title-only label for plugin paths and artists.

`test_no_plugin_gate_on_year_labels` is the mutation-checked guard: it walks
the real control tree of every shipped view and fails if a layout's year
labels are ALL gated off on plugin paths - the exact state that produced this
bug.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

# Upstream's gate, in the only form that HIDES content on a plugin path.
PLUGIN_GATE = "!String.StartsWith(Container.FolderPath,plugin://)"
YEAR_TOKEN = "ListItem.Year"


def _views(tree: Path) -> list[Path]:
    return sorted((tree / "xml").glob("View_*.xml"))


def _year_controls(path: Path) -> dict[str, list[tuple[str, bool]]]:
    """Year-printing controls, grouped by the LAYOUT BLOCK they live in.

    Grouping matters. The invariant cannot be per file: View_54 also prints a
    year in `WallViewLabels` (the side info pane, never gated), which would
    mask a fully-gated tile layout and let this guard pass while the tiles
    show nothing. The unit that actually renders a row or tile is the
    enclosing `<include name="...">` definition (or itemlayout /
    focusedlayout), so each is judged on its own.

    Walks the parsed tree rather than scanning text, so a `<visible>`
    belonging to a neighbouring control is never mistaken for this one's
    (views 503 and 503_21x9 both place an ungated year label a few lines
    below a gated control, and a text scan reads those as gated). Ancestor
    gates count: a gate on an enclosing group hides the label just as
    effectively as one on the label itself.
    """
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    parents = {child: parent for parent in root.iter() for child in parent}

    def block_of(node) -> str:
        while node is not None:
            if node.tag in ("itemlayout", "focusedlayout"):
                return node.tag
            if node.tag == "include" and node.get("name"):
                return node.get("name")
            node = parents.get(node)
        return "<root>"

    found: dict[str, list[tuple[str, bool]]] = {}
    for control in root.iter("control"):
        labels = [
            (child.text or "") for child in control if child.tag in ("label", "label2")
        ]
        if not any(YEAR_TOKEN in text for text in labels):
            continue
        node, gated = control, False
        while node is not None:
            if any(
                child.tag == "visible" and PLUGIN_GATE in (child.text or "")
                for child in node
            ):
                gated = True
                break
            node = parents.get(node)
        found.setdefault(block_of(control), []).append(
            (" | ".join(labels).strip(), not gated)
        )
    return found


def test_wallthumbs_plugin_label_carries_the_year(built):
    """`WallThumbsLayout`'s plugin-path label prints title AND year.

    Split on `hide_pubyear` (a SHOW toggle despite the name: true = year
    shown) so the owner's switch still governs it, mirroring the tvshows pair
    in the same file. Artists keep a plain label - no year, no empty "( )".
    """
    text = (built.tree / "xml" / "View_54_InfoWall.xml").read_text(encoding="utf-8")
    with_year = (
        "<label>$INFO[ListItem.Label]$INFO[ListItem.Year, (,)]</label>\n"
        "\t\t\t\t<font>font25_title</font>\n"
        "\t\t\t\t<align>center</align>"
    )
    assert with_year in text, "the plugin-path tile label lost its year"
    assert (
        "<visible>String.StartsWith(Container.FolderPath,plugin://) + "
        "!Container.Content(artists) + Skin.HasSetting(hide_pubyear)</visible>" in text
    )
    # The title-only label survives for artists and for hide_pubyear off.
    assert (
        "<visible>[String.StartsWith(Container.FolderPath,plugin://) + "
        "!Skin.HasSetting(hide_pubyear)] | Container.Content(artists)</visible>" in text
    )


def test_wallthumbs_consumers_are_the_expected_views(built):
    """Pin who actually renders `WallThumbsLayout`.

    The fix lives in View_54 but View_54's OWN tiles carry no per-item label
    (bench-confirmed: InfoWall labels only the focused item, in the side
    pane). The layout is consumed by the ThumbsWall views, and that is where
    the tile-level year change lands. If this set changes, the bench proof
    for this fix no longer describes the shipped surface.
    """
    consumers = sorted(
        p.name
        for p in _views(built.tree)
        if "WallThumbsLayout" in p.read_text(encoding="utf-8")
    )
    assert consumers == [
        "View_504_ThumbsWall.xml",
        "View_505_ThumbsInfoWall.xml",
        "View_54_InfoWall.xml",
    ], consumers


def test_list_view_year_on_plugin_movie_paths(built):
    """`ListLabel2Var` gains a plugin-path movie-year branch.

    It must sit AFTER the sort-method-Title branches (those stay authoritative
    for a Title-sorted list) and BEFORE the generic `ListItem.Label2` tail,
    and it must be scoped to plugin + movies + hide_pubyear + a non-empty
    year so it can never blank a Label2 that had content.
    """
    text = (built.tree / "xml" / "Variables.xml").read_text(encoding="utf-8")
    branch = (
        '<value condition="String.StartsWith(Container.FolderPath,plugin://) + '
        "Container.Content(movies) + Skin.HasSetting(hide_pubyear) + "
        '!String.IsEmpty(ListItem.Year)">$INFO[ListItem.Year]</value>'
    )
    assert branch in text, "ListLabel2Var lost its plugin-path movie-year branch"

    appearances = '<value condition="!String.IsEmpty(ListItem.Appearances)">'
    tail = '<value condition="!String.StartsWith(ListItem.Label2,0.00)'
    assert text.index(branch) < text.index(appearances) < text.index(tail)

    sort_title = "String.IsEqual(Container.SortMethod,$LOCALIZE[556])"
    assert text.rindex(sort_title) < text.index(branch), (
        "the plugin-year branch must not pre-empt the sort-method-Title branches"
    )


def test_no_plugin_gate_on_year_labels(built):
    """No layout may hide ALL of its year labels on plugin paths.

    THE guard for this bug class. The invariant is per LAYOUT BLOCK, not per
    control: upstream deliberately partitions the tile layout into a library
    branch and a plugin branch, so the library-side year labels keep their
    `!String.StartsWith(...)` gate and SHOULD. What must never happen again is
    a layout whose year labels are ALL gated off on plugin paths.

    Mutation-checked: re-adding upstream's gate to the plugin label (the
    1.0.72 fix) turns this red and names View_54_InfoWall.xml:WallThumbsLayout.
    """
    offenders = {}
    for view in _views(built.tree):
        for block, controls in _year_controls(view).items():
            if controls and not any(visible for _, visible in controls):
                offenders["{}:{}".format(view.name, block)] = [
                    label for label, _ in controls
                ]
    assert offenders == {}, (
        "every year label is hidden on plugin paths, so a plugin-backed movie "
        "list shows no year (the owner's empty-library Movies surface): "
        "{}".format(offenders)
    )


def test_guard_is_wired_to_the_real_views(built):
    """The guard is meaningless if it inspects nothing.

    Proves the walker actually finds year-printing controls in the shipped
    tree, so a future refactor that renames or relocates the views cannot
    leave `test_no_plugin_gate_on_year_labels` vacuously green.
    """
    views = _views(built.tree)
    assert len(views) >= 15, views

    seen = {v.name: sum(len(c) for c in _year_controls(v).values()) for v in views}
    assert seen.get("View_54_InfoWall.xml", 0) >= 3, seen
    assert sum(seen.values()) >= 5, seen
