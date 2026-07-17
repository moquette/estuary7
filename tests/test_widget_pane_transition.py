"""Personal-widget pane transition (1.0.55).

Upstream keys the home widget-pane fade+slide on the focused item's `widget`
property CHANGING, so two menu items that both use owner-picked widgets
(widget=PersonalWidgetList/Panel) swap panes with NO transition. The build
gates each generated pane instance per item (skinshortcuts resolves
<skinshortcuts>visibility</skinshortcuts> to the item's submenuVisibility
condition) and replaces the shared Conditional include with the same effects
triggered on the group's own Visible/Hidden. Hardware evidence: office box
backups 2026-07-15 21:04 (distinct widgets - animated) vs 2026-07-16 04:56
(both PersonalWidgetList - cut), identical 1.0.54 skin bytes in both.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PANES = ("PersonalWidgetList", "PersonalWidgetPanel")

VISIBLE_EFFECTS = (
    '<effect type="fade" start="0" end="100" time="300" tween="sine" '
    'delay="300" easing="out" />',
    '<effect type="slide" start="320" end="0" time="400" delay="300" '
    'tween="cubic" easing="out" />',
)
HIDDEN_EFFECTS = (
    '<effect type="fade" start="100" end="0" time="300" tween="sine" easing="out" />',
    '<effect type="slide" start="0" end="320" time="300" tween="cubic" easing="out" />',
)


def _template(built) -> str:
    return (built.tree / "shortcuts" / "template.xml").read_text("utf-8")


def test_shared_pane_include_replaced(built):
    """The Conditional-keyed include (which cannot fire between two items of
    the SAME pane type) is gone from the template; the static per-widget panes
    in Home.xml keep theirs."""
    text = _template(built)
    assert "Visible_Right_Delayed_Home" not in text
    home = (built.tree / "xml" / "Home.xml").read_text("utf-8")
    assert home.count("Visible_Right_Delayed_Home") >= 8


def test_pane_instances_gated_per_item_with_stock_effects(built):
    """Each pane template block keeps its widget-type visible condition, gains
    the per-item visibility tag, and animates its own Visible/Hidden with the
    EXACT effects of Vis_FadeSlide_Right_Delayed_Home (plus the
    no_slide_animations fade fallback, mirroring Visible_Fade)."""
    text = _template(built)
    for pane in PANES:
        anchor = (
            "<visible>String.IsEqual(Container(9000).ListItem."
            "Property(widget),{})</visible>".format(pane)
        )
        assert text.count(anchor) == 1, pane
        block = text[text.index(anchor) : text.index(anchor) + 2200]
        assert "<skinshortcuts>visibility</skinshortcuts>" in block, pane
        assert (
            '<animation type="Visible" '
            'condition="!Skin.HasSetting(no_slide_animations)">' in block
        ), pane
        assert (
            '<animation type="Hidden" '
            'condition="!Skin.HasSetting(no_slide_animations)">' in block
        ), pane
        for eff in VISIBLE_EFFECTS + HIDDEN_EFFECTS:
            assert eff in block, (pane, eff)
        assert (
            '<animation effect="fade" time="300" '
            'condition="Skin.HasSetting(no_slide_animations)">'
            "VisibleChange</animation>" in block
        ), pane


def test_effects_stay_in_parity_with_the_pane_switch_include(built):
    """Drift guard: if upstream ever retunes Vis_FadeSlide_Right_Delayed_Home,
    this fails so the template copy is retuned with it (same feel on
    same-pane and cross-pane switches)."""
    anims = (built.tree / "xml" / "Includes_Animations.xml").read_text("utf-8")
    m = re.search(
        r'<include name="Vis_FadeSlide_Right_Delayed_Home">(.*?)</include>',
        anims,
        re.S,
    )
    assert m, "upstream include renamed or removed"
    upstream_effects = [e.strip() for e in re.findall(r"<effect [^>]*/>", m.group(1))]
    assert upstream_effects == list(VISIBLE_EFFECTS + HIDDEN_EFFECTS)


def test_vendored_includes_unaffected_by_the_template_edit(built):
    """The provenance premise for 1.0.55: the pristine (stock-menu) capture
    instantiates neither edited template block, so the vendored includes is
    byte-invariant under this edit. If a PersonalWidget* string ever shows up
    in the capture, the includes must be genuinely re-captured."""
    vendored = ROOT / "assets" / "xml" / "script-skinshortcuts-includes.xml"
    assert b"PersonalWidget" not in vendored.read_bytes()
