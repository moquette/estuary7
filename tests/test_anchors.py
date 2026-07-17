"""Anchor contract: every transform fails LOUD when upstream drifts."""

from __future__ import annotations

import pytest

import skin_transforms
from skin_transforms import TransformError


def test_transform_tree_summary(built):
    """The pinned upstream matches every anchor; the counts are properties of
    the pin and must change only with a deliberate rebase."""
    assert len(built.summary["edited"]) == len(skin_transforms.FILE_EDITS) == 25
    # 18, not 24: six files' only upstream-id references were RunScript
    # helper calls, which now use the file path instead of the addon id.
    assert built.summary["renamed"] == 18
    assert built.summary["runscript"] == skin_transforms.RUNSCRIPT_SITES == 15
    assert built.summary["swept"] == 46  # the [B] sweep's known blast radius


@pytest.mark.parametrize("rel, edit", sorted(skin_transforms.FILE_EDITS.items()))
def test_missing_anchor_fails_loud(rel, edit):
    """Every per-file edit raises TransformError (naming the file) on a text
    that carries none of its anchors - a rebased upstream can never ship a
    silent partial transform."""
    with pytest.raises(TransformError) as exc:
        edit("<window></window>", rel)
    assert rel in str(exc.value)


def test_double_transform_fails_loud(built):
    """Transforming an already-transformed file is drift, not a no-op."""
    text = (built.tree / "xml" / "Home.xml").read_text(encoding="utf-8")
    with pytest.raises(TransformError):
        skin_transforms.FILE_EDITS["xml/Home.xml"](text, "xml/Home.xml")


def test_rebrand_requires_exact_upstream_header():
    with pytest.raises(TransformError):
        skin_transforms.rebrand_addon_xml('<addon id="something-else">', "1.0.0")


def test_font_transform_requires_default_fontset():
    with pytest.raises(TransformError):
        skin_transforms.transform_font_xml("<fonts></fonts>")
