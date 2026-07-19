"""The vendored skinshortcuts includes must be a CURRENT pristine capture.

`build_skin.check_contracts()` already gates the vendored
`assets/xml/script-skinshortcuts-includes.xml` on the sha256 of the shipped menu
DATA. That guard is necessary but not sufficient: it only proves the DATA has
not moved since someone last wrote the baseline down. It cannot tell a genuine
re-capture apart from a hash refresh, so a baseline edited "because the change
is byte-invariant" silently re-blesses a stale capture. That is exactly how the
1.0.33 capture survived into 1.0.66 while the baseline was refreshed at 1.0.55,
1.0.56 and 1.0.57.

These tests look at the CONTENT of the capture instead, and are pinned to the
two defects the stale capture actually shipped - both of them first-paint
visible to the owner:

  * 111 item icons flattened to `addtile.png`, because the capture predates the
    DATA that gives those items real icons and `shortcuts/overrides.xml` maps
    the `DefaultShortcut.png` fallback onto the add-item tile.
  * 38 `System.HasPVRAddon` visible conditions, which hide Live TV and Radio on
    a box with no PVR client - the opposite of the always-visible stock
    behaviour that `donthidepvr=true` exists to guarantee.

A pristine build of the shipped DATA produces zero of each.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_skin  # noqa: E402

VENDORED = build_skin.ASSETS_DIR / "xml" / "script-skinshortcuts-includes.xml"


@pytest.fixture(scope="module")
def includes_text() -> str:
    return VENDORED.read_text(encoding="utf-8")


@pytest.fixture
def data_dir(built) -> Path:
    """The shipped menu DATA, from the session's transformed tree.

    Deliberately NOT ROOT/"build"/"tree": that path is a gitignored build
    artifact, so reading it makes the test pass or fail on whatever the last
    local build happened to leave behind, and fail outright on a clean checkout
    or in CI. The `built` fixture is the canonical shipped tree.
    """
    return built.tree / "shortcuts"


def test_capture_has_no_pvr_visibility_conditions(includes_text):
    """Live TV and Radio must not be gated on a PVR client being installed.

    `donthidepvr=true` is the only lever that keeps them visible like stock, and
    the boot service plus Home's seedPVR onload both set it. A capture taken
    before that setting was true bakes the hiding condition into the shipped
    first paint, where no runtime seed can reach it.
    """
    hits = includes_text.count("System.HasPVRAddon")
    assert hits == 0, (
        "vendored includes carries {} System.HasPVRAddon condition(s): it was "
        "captured with donthidepvr unset, so Live TV/Radio are hidden on first "
        "paint. Re-capture from a pristine build with donthidepvr=true.".format(hits)
    )


def test_capture_does_not_flatten_icons_to_the_add_item_tile(includes_text):
    """No menu item may render the add-item placeholder as its icon.

    `overrides.xml` rewrites the `DefaultShortcut.png` fallback to
    `extras/icons/addtile.png`. Items whose DATA declares a real icon never hit
    that fallback in a current build, so any addtile icon in the capture means
    the capture predates the DATA.
    """
    hits = includes_text.count("addtile.png")
    assert hits == 0, (
        "vendored includes flattens {} icon(s) to addtile.png: it predates the "
        "shipped menu DATA, so those items render the generic add-item tile on "
        "first paint. Re-capture from a pristine build.".format(hits)
    )


# Icons the stale 1.0.33 capture flattened to addtile.png and a pristine build
# of the shipped DATA resolves correctly. Each is declared by a submenu DATA
# file that the `group=mainmenu` build instantiates, so each MUST appear
# literally in the capture. Deliberately not derived from every *.DATA.xml:
# Home's onload runs buildxml with group=mainmenu only, so powermenu.DATA.xml
# is never instantiated and its icons are legitimately absent from this file
# (true of the stale capture and the pristine one alike - not a regression).
_RESOLVED_SUBMENU_ICONS = (
    "icons/lastseen.png",
    "DefaultVersions.png",
    "LibrarySettings.png",
    "DefaultCinema.png",
    "DefaultNextUp.png",
)


def test_capture_carries_the_real_icons_the_shipped_data_declares(
    includes_text, data_dir
):
    """Positive counterpart: distinctive DATA icons must survive into the capture.

    Guards the failure mode where a capture is emptied or truncated rather than
    stale - `addtile.png` would be absent then too, and the negative checks
    above would both pass on a file with no icons at all.
    """
    declared = set()
    for data in sorted(data_dir.glob("*.DATA.xml")):
        for icon in re.findall(
            r"<icon>([^<]+)</icon>", data.read_text(encoding="utf-8")
        ):
            # $VAR icons resolve at runtime and are not literal in the capture.
            if not icon.startswith("$VAR["):
                declared.add(icon)
    assert declared, "no icons found in shipped DATA - fixture path is wrong"

    unknown = [i for i in _RESOLVED_SUBMENU_ICONS if i not in declared]
    assert not unknown, (
        "expected icon(s) no longer declared by any shipped DATA file: {}. "
        "Update _RESOLVED_SUBMENU_ICONS deliberately, do not delete the "
        "check.".format(", ".join(unknown))
    )

    missing = [i for i in _RESOLVED_SUBMENU_ICONS if i not in includes_text]
    assert not missing, (
        "shipped menu DATA declares icon(s) that never reach the vendored "
        "capture: {}. The capture is stale, empty, or was built against "
        "different DATA.".format(", ".join(missing))
    )
