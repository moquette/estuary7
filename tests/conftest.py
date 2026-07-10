"""Shared fixtures: one pristine upstream extract and one transformed tree
per session (the extract is ~97MB, so both are session-scoped)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_skin  # noqa: E402
import skin_transforms  # noqa: E402

GOLDENS = ROOT / "tests" / "goldens"


@pytest.fixture(scope="session")
def lock():
    return build_skin.read_lock()


@pytest.fixture(scope="session")
def upstream_tree(lock, tmp_path_factory) -> Path:
    """The pinned upstream, pristine."""
    tarball = build_skin.ensure_tarball(lock)
    return build_skin.extract_tree(
        tarball, tmp_path_factory.mktemp("upstream") / "tree"
    )


@pytest.fixture(scope="session")
def built(lock, tmp_path_factory) -> SimpleNamespace:
    """The fully transformed tree + assets, exactly as build_skin ships it."""
    tarball = build_skin.ensure_tarball(lock)
    tree = build_skin.extract_tree(tarball, tmp_path_factory.mktemp("built") / "tree")
    summary = skin_transforms.transform_tree(tree, lock["our_version"])
    build_skin.add_assets(tree)
    return SimpleNamespace(tree=tree, summary=summary, lock=lock)
