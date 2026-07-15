"""Stock view switching (1.0.39): the MOD V2 view-picker dialog is gone.

The dialog (Custom_1131) existed to show preview thumbnails this build trims
(extras/views); with them missing it rendered its MOD V2 splash-art fallback.
The fork restores stock Estuary's single Viewtype cycle button and drops the
dialog, its image-lookup variable, and the splash art.
"""

from __future__ import annotations

import build_skin
import skin_transforms


def test_stock_viewtype_button(built):
    """The media sidebar carries exactly stock Estuary's Viewtype button
    (label 31023, Container.NextViewMode) and neither MOD V2 button remains."""
    text = (built.tree / "xml" / "Includes_MediaMenu.xml").read_text(encoding="utf-8")
    assert text.count(skin_transforms._VIEW_BUTTON_STOCK) == 1
    assert 'id="60511"' not in text
    assert "ActivateWindow(1131)" not in text
    assert "$LOCALIZE[31347]" not in text


def test_views_variable_deleted(built):
    """Variables.xml no longer references the trimmed extras/views thumbnails
    or the MOD V2 splash art (the picker's image-lookup variable is gone)."""
    text = (built.tree / "xml" / "Variables.xml").read_text(encoding="utf-8")
    assert "SettingsViewsImagesVar" not in text
    assert "extras/views" not in text
    assert "themes/splash.png" not in text


def test_picker_dialog_and_splash_are_trimmed():
    """The dialog XML and the splash art ship nowhere: both are TRIM_PATHS
    entries (trim_payload deletes them fail-loud; check_contracts gates the
    zip on their absence)."""
    assert "xml/Custom_1131_SettingsViews.xml" in build_skin.TRIM_PATHS
    assert "extras/themes/splash.png" in build_skin.TRIM_PATHS


def test_no_other_window_1131_callers(built):
    """No shipped XML can open the deleted dialog."""
    for xml in sorted((built.tree / "xml").glob("*.xml")):
        if xml.name == "Custom_1131_SettingsViews.xml":
            continue  # the definition itself; deleted by trim_payload
        assert "ActivateWindow(1131)" not in xml.read_text(encoding="utf-8"), xml.name
