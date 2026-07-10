"""Packaging determinism: same tree -> byte-identical zip.

The full pipeline determinism (fetch + transform + package, twice) is the
build gate: `python3 tools/build_skin.py --check`.
"""

from __future__ import annotations

import zipfile

import build_skin
from skin_transforms import SKIN_ID


def test_package_twice_is_byte_identical(built, tmp_path):
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    build_skin.package(built.tree, a)
    build_skin.package(built.tree, b)
    assert a.read_bytes() == b.read_bytes()


def test_zip_layout_and_fixed_timestamps(built, tmp_path):
    path = tmp_path / "skin.zip"
    build_skin.package(built.tree, path)
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert names == sorted(names)
        assert all(n.startswith(SKIN_ID + "/") for n in names)
        assert "{}/addon.xml".format(SKIN_ID) in names
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in zf.infolist())
