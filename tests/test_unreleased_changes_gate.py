"""The unreleased-changes gate: build inputs that moved at a released version.

Exercises tools/check_unreleased_changes.classify(), which is pure precisely so
this suite never shells out to git or touches the network.

The hole being closed (2026-07-25 pipeline audit): the publish job is idempotent
by tag, so a fix committed WITHOUT bumping our_version builds, tests green,
publishes nothing, reaches zero boxes, and nothing goes red anywhere. This repo
is the more exposed of the two, because it has no separate release script that
fails closed the way the add-on's tools/release.sh does: CI on push to main is
the only path that ever cuts a release here.

The deliberately-permitted case is test_dirty_is_a_warning_not_a_failure: the
default must not block a push, because batching several commits into one later
release is the normal workflow and a gate that fought it would be bypassed.

test_source_paths_cover_every_build_input is the load-bearing one. If a future
build input is added to build_skin.py and not to SOURCE_PATHS, the gate goes
quietly blind to it, which is worse than not having the gate.
"""

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "tools" / "check_unreleased_changes.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_unreleased_changes", MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_unreleased_version_is_clean(mod):
    """A version with no tag yet is the normal pre-release state, not a problem."""
    state, message = mod.classify("1.0.79", has_tag=False, changed=[])
    assert state == "unreleased"
    assert "no v1.0.79 tag yet" in message


def test_released_and_unchanged_is_clean(mod):
    """The genuine idempotent no-op: tag exists, no build input moved."""
    state, message = mod.classify("1.0.78", has_tag=True, changed=[])
    assert state == "clean"
    assert "no build input changed" in message


def test_build_input_changed_at_released_version_is_dirty(mod):
    """The actual failure the audit found, and the whole reason this gate exists."""
    state, message = mod.classify(
        "1.0.78", has_tag=True, changed=["tools/skin_transforms.py"]
    )
    assert state == "dirty"
    assert "reach NO box" in message
    assert "tools/skin_transforms.py" in message


def test_dirty_is_a_warning_not_a_failure(mod):
    """Batching is the real workflow, so the default must never block a push."""
    assert mod.main([]) == 0


def test_version_comes_from_the_lock(mod, tmp_path):
    lock = tmp_path / "skin_build.lock"
    lock.write_text(json.dumps({"our_version": "1.2.3", "upstream_sha": "abc"}))
    assert mod.read_version(str(lock)) == "1.2.3"


def test_real_lock_parses(mod):
    """The gate is worthless if it cannot read this repo's own lock file."""
    version = mod.read_version()
    assert version, "no our_version parsed from the live skin_build.lock"
    assert version[0].isdigit()


def test_source_paths_cover_every_build_input(mod):
    """Guard against the gate silently going blind when a build input is added.

    build_skin.py resolves its inputs from module-level ROOT-relative constants.
    Every one of those that is a committed source path must be watched, or a
    change to it would ship unnoticed at an already-released version.
    """
    build_skin = (ROOT / "tools" / "build_skin.py").read_text(encoding="utf-8")

    # The constants that name committed inputs, as opposed to generated output
    # (BUILD_DIR, DIST_DIR) or a gitignored fetch cache (CACHE_DIR).
    expected = {
        "LOCK_FILE": "skin_build.lock",
        "ASSETS_DIR": "assets",
    }
    for const, path in expected.items():
        assert f"{const} = ROOT /" in build_skin, (
            f"{const} vanished from build_skin.py; re-check SOURCE_PATHS"
        )
        assert path in mod.SOURCE_PATHS, f"{path} is a build input but is not watched"

    # The transform code itself is an input: it rewrites the upstream tree. Named
    # files, NOT the tools/ directory. Watching all of tools/ made this gate count
    # ITSELF as a build input, so it warned about its own arrival on the day it
    # shipped (2026-07-25). A gate that is wrong on day one is one people learn to
    # ignore, which is worse than not having it.
    assert "tools/build_skin.py" in mod.SOURCE_PATHS
    assert "tools/skin_transforms.py" in mod.SOURCE_PATHS
    assert "tools" not in mod.SOURCE_PATHS, (
        "watch named files, not the whole tools/ dir: the gate would flag itself"
    )
