"""The select dialog's footer line.

Upstream spends that line on "N items - 1/1", a count the user can get by
looking at the list. An add-on may take it over PER ROW by setting the
ListItem property `ezm.footer`, which is how EZ Maintenance++ shows the backup
path while Backup is highlighted and the restore path while Restore is.

The contract these tests hold: the takeover is opt-in and per item, the stock
count is hidden only while a row supplies a footer, and no other add-on's
select dialog changes at all.
"""

from __future__ import annotations

PATH = "xml/Includes_DialogSelect.xml"
PROP = "Container(3).ListItem.Property(ezm.footer)"


def _select_xml(built):
    return (built.tree / "xml" / "Includes_DialogSelect.xml").read_text(
        encoding="utf-8"
    )


def test_the_footer_follows_the_highlighted_row(built):
    """The label reads the property off the FOCUSED item of list 3.

    Container(3).ListItem is the focused row, so the line changes as she moves
    without the add-on redrawing anything. A plain ListItem.Property here would
    resolve against whatever container the window last focused, which is how
    this lands blank on a real box while passing a file-content test."""
    xml = _select_xml(built)
    assert "<label>$INFO[{}]</label>".format(PROP) in xml


def test_the_footer_is_flush_left_under_the_row_text(built):
    """Left 40 is not a guess: list 3 sits at left 20 and its row label adds
    another 20 (DefaultSimpleListLayout2), so the path starts on the same
    column as the item labels above it. A right-aligned footer under a
    left-aligned list reads as a stray caption."""
    xml = _select_xml(built)
    footer = xml.split("<label>$INFO[{}]</label>".format(PROP))[0]
    block = footer[footer.rindex('<control type="label">') :]
    assert "<left>40</left>" in block
    assert "<align>left</align>" in block
    assert "<width>1160</width>" in block, "a long nfs:// path needs the full width"


def test_the_stock_item_count_survives_for_every_other_dialog(built):
    """The takeover must be OPT-IN. Every select dialog in Kodi shares this
    layout, so the stock count has to stay exactly as upstream drew it (right
    aligned, left 925, width 275) and merely yield when a row carries the
    property. Deleting it, or moving it, is a skin-wide regression shipped for
    one add-on's benefit."""
    xml = _select_xml(built)
    stock = xml.split("<label>$VAR[SelectLabel]</label>")[0]
    block = stock[stock.rindex('<control type="label">') :]
    assert "<left>925</left>" in block
    assert "<align>right</align>" in block


def test_the_two_labels_are_mutually_exclusive(built):
    """Exactly one line is drawn at a time: the count hides while a row
    supplies a footer, and returns when none does. Both visible at once would
    overprint the count on top of a long path."""
    xml = _select_xml(built)
    assert "<visible>String.IsEmpty({})</visible>".format(PROP) in xml
    assert "<visible>!String.IsEmpty({})</visible>".format(PROP) in xml


def test_the_footer_variable_is_left_stock(built):
    """SelectLabel stays upstream's item-count variable. An earlier attempt
    folded the property into the VARIABLE, which silently changed the footer
    of every dialog in the skin that uses it. The conditional belongs on the
    controls, where its blast radius is one label."""
    variables = (built.tree / "xml" / "Variables.xml").read_text(encoding="utf-8")
    marker = '<variable name="SelectLabel">'
    body = variables[variables.index(marker) : variables.index(marker) + 700]
    assert "ezm.footer" not in body
