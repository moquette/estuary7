"""No-bold contracts (THE FIRST MANDATE): all three bold vectors dead.

1. bold font FILES     - Default fontset binds no *-Bold face
2. <style>bold</style> - neutralized on UI ids (lyrics faces excepted)
3. [B]..[/B] markup    - stripped from every window XML

Plus the silent-fallback invariant: the font-id inventory is byte-identical
to upstream (a vanished id falls back to font13 with no error), and the
alternate fontsets nobody runs stay stock.
"""

from __future__ import annotations

import re

import skin_transforms


def _default_fontset(text: str) -> str:
    start = text.find('<fontset id="Default"')
    end = text.find("<fontset id=", start + 1)
    assert start != -1 and end != -1
    return text[start:end]


def _font_blocks(segment: str):
    for block in re.findall(r"<font>.*?</font>", segment, re.DOTALL):
        name = re.search(r"<name>([^<]+)</name>", block)
        yield name.group(1), block


def test_no_bold_markup_anywhere(built):
    for xml in sorted((built.tree / "xml").glob("*.xml")):
        text = xml.read_text(encoding="utf-8")
        for tag in skin_transforms.BOLD_MARKUP:
            assert tag not in text, "{} still carries {}".format(xml.name, tag)


def test_no_bold_faces_in_default_fontset(built):
    segment = _default_fontset(
        (built.tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    )
    assert "NotoSans-Bold.ttf" not in segment
    assert "RobotoCondensed-Bold.ttf" not in segment
    # The re-bound faces actually ship with the skin.
    fonts = built.tree / "fonts"
    assert (fonts / "NotoSans-Regular.ttf").is_file()
    assert (fonts / "RobotoCondensed-Light.ttf").is_file()


def test_style_bold_only_on_lyrics_faces(built):
    segment = _default_fontset(
        (built.tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    )
    keepers = [
        name for name, block in _font_blocks(segment) if "<style>bold</style>" in block
    ]
    assert keepers, "the decorative lyrics faces must keep synthetic bold"
    assert all(name.startswith("lyr") for name in keepers), keepers


def test_font_id_inventory_identical_to_upstream(built, upstream_tree):
    ours = skin_transforms.font_id_inventory(
        (built.tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    )
    stock = skin_transforms.font_id_inventory(
        (upstream_tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    )
    assert ours == stock


def test_alternate_fontsets_stay_stock(built, upstream_tree):
    """Arial / Arial Unicode MS / Economica are alternates nobody runs."""
    ours = (built.tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    stock = (upstream_tree / "xml" / "Font.xml").read_text(encoding="utf-8")
    assert (
        ours[ours.find('<fontset id="Arial"') :]
        == stock[stock.find('<fontset id="Arial"') :]
    )
