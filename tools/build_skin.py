"""Build skin.estuary7 from the pinned upstream: fetch, transform, package.

Usage:
    python3 tools/build_skin.py            # build dist/skin.estuary7-<ver>.zip
    python3 tools/build_skin.py --check    # build twice, byte-compare zips

The pin lives in skin_build.lock ({upstream_sha, upstream_tarball_sha256,
our_version, zip_sha256}). The tarball is cached in upstream-cache/ and its
sha256 is verified on EVERY build - a mismatch is a hard error, never a
warning. Packaging is deterministic (sorted paths, 1980-01-01 timestamps,
0644 perms - the same discipline as tony7bones.github.io's generate_repo.py),
so two builds of the same lock are byte-identical and the recorded zip_sha256
is meaningful.

Post-transform contract checks run inside every build; a violation fails the
build. They are a subset of the pytest suite - the tests remain the real gate.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import skin_transforms  # noqa: E402
from skin_transforms import SKIN_ID, UPSTREAM_ID, TransformError  # noqa: E402

LOCK_FILE = ROOT / "skin_build.lock"
CACHE_DIR = ROOT / "upstream-cache"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
ASSETS_DIR = ROOT / "assets"

TARBALL_URL = "https://github.com/{repo}/archive/{sha}.tar.gz"

SKIN_README = """# Estuary 7

The Tony.7.Bones fleet skin for Kodi 21 (Omega): the look and feel of
original Estuary with thin fonts everywhere, built from Estuary MOD V2.

This zip is produced by an automated build from a pinned upstream commit
plus anchored transforms - see the source repository for the build pipeline,
license (GPL-2.0 code, CC-BY-SA-4.0 artwork), and full attribution:

    https://github.com/moquette/estuary7

Credits: Estuary MOD V2 by Guilouz, adapted for Kodi 21 (Omega) by PvD /
b-jesch (Kodinerds); Estuary by phil65 and Piers (Team Kodi).
"""


def read_lock() -> dict:
    return json.loads(LOCK_FILE.read_text(encoding="utf-8"))


def write_lock(lock: dict) -> None:
    LOCK_FILE.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_tarball(lock: dict) -> Path:
    """Return the verified pinned tarball, downloading it if absent."""
    sha = lock["upstream_sha"]
    tarball = CACHE_DIR / "{}.tar.gz".format(sha)
    if not tarball.is_file():
        CACHE_DIR.mkdir(exist_ok=True)
        url = TARBALL_URL.format(repo=lock["upstream_repo"], sha=sha)
        print("fetching {}".format(url))
        with urllib.request.urlopen(url) as resp, open(tarball, "wb") as out:
            shutil.copyfileobj(resp, out)
    actual = sha256_file(tarball)
    expected = lock["upstream_tarball_sha256"]
    if actual != expected:
        raise SystemExit(
            "FATAL: upstream tarball sha256 mismatch\n  expected {}\n  actual   {}\n"
            "The pin and the bytes disagree - refusing to build.".format(
                expected, actual
            )
        )
    return tarball


def extract_tree(tarball: Path, dest: Path) -> Path:
    """Extract the tarball's single top-level dir to dest/<SKIN_ID>."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(tarball, "r:gz") as tar:
        tar.extractall(dest, filter="data")
    (entry,) = list(dest.iterdir())  # exactly one top-level dir, or fail loud
    tree = dest / SKIN_ID
    entry.rename(tree)
    return tree


def add_assets(tree: Path) -> None:
    """Ship the wordmark, artwork, and provenance docs.

    The home menu is UPSTREAM MOD V2's default (owner directive 2026-07-10):
    the fork ships NO custom skinshortcuts menu, so upstream's shortcuts/
    (full default mainmenu.DATA.xml + overrides.xml widget defaults) stands
    unmodified. This also retires the skinshortcuts-properties seed - stock
    upstream needs none. The fleet's old trimmed menu lives on in assets/
    shortcuts/ (unused by the build) if it is ever wanted per-box.
    """
    extras = tree / "media" / "extras"
    extras.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ASSETS_DIR / "media" / "extras" / "logo-text-hires.png",
        extras / "logo-text-hires.png",
    )
    # Skin-selection artwork: ORIGINAL Estuary's icon + fanart + the 8
    # screenshots (Team Kodi, vendored from xbmc/xbmc Omega), replacing MOD
    # V2's branded set (owner decision 2026-07-10 - stock look everywhere).
    # MOD V2's screenshots/ dir is removed; the rebranded addon.xml points at
    # the flat resources/screenshot-0N.jpg names instead.
    for name in ("icon.png", "fanart.jpg"):
        shutil.copyfile(ASSETS_DIR / "resources" / name, tree / "resources" / name)
    shutil.rmtree(tree / "resources" / "screenshots", ignore_errors=True)
    for shot in sorted(ASSETS_DIR.glob("resources/screenshot-*.jpg")):
        shutil.copyfile(shot, tree / "resources" / shot.name)
    (tree / "README.md").write_text(SKIN_README, encoding="utf-8")
    shutil.copyfile(ROOT / "ATTRIBUTION.md", tree / "ATTRIBUTION.md")


def check_contracts(tree: Path) -> None:
    """Fail the build on any violated ship-contract (subset of the tests)."""
    problems = []
    for xml in sorted((tree / "xml").glob("*.xml")):
        text = xml.read_text(encoding="utf-8")
        for tag in skin_transforms.BOLD_MARKUP:
            if tag in text:
                problems.append(
                    "{}: bold markup {} survived the sweep".format(xml.name, tag)
                )
    for path in sorted(tree.rglob("*")):
        if (
            path.suffix in (".xml", ".py", ".po", ".md", ".properties")
            and path.is_file()
        ):
            if path.name == "ATTRIBUTION.md":
                continue  # provenance doc - naming the upstream id is the point
            if UPSTREAM_ID in path.read_text(encoding="utf-8", errors="ignore"):
                problems.append(
                    "{}: upstream id survived the rename".format(path.relative_to(tree))
                )
    addon = (tree / "addon.xml").read_text(encoding="utf-8")
    if 'id="{}"'.format(SKIN_ID) not in addon:
        problems.append("addon.xml: missing rebranded id")
    if "resource.images.weathericons.outline-hd" not in addon:
        problems.append("addon.xml: missing outline-hd dependency")
    # The home menu ships STOCK ESTUARY's item set/order (owner directive).
    # Live TV/Radio keep stock's named windows (TVChannels/RadioChannels) and
    # stay always-visible like stock because the boot service + reset helper seed
    # skinshortcuts' donthidepvr=true (numeric window ids do NOT help - they are
    # normalised back to the named windows at build time and injected anyway).
    menu = tree / "shortcuts" / "mainmenu.DATA.xml"
    if not menu.is_file():
        problems.append("shortcuts: mainmenu.DATA.xml missing")
    else:
        menu_text = menu.read_text(encoding="utf-8")
        for needed in ("ActivateWindow(TVChannels)", "ActivateWindow(RadioChannels)"):
            if needed not in menu_text:
                problems.append("mainmenu: {} missing (stock PVR item)".format(needed))
        for banned in ("ActivateWindow(10700)", "ActivateWindow(10705)"):
            if banned in menu_text:
                problems.append("mainmenu: {} - use the named window".format(banned))
    # donthidepvr must be seeded so the named-window PVR items are not hidden
    services = tree / "scripts" / "services.py"
    if not services.is_file():
        problems.append("scripts: services.py missing")
    elif "donthidepvr" not in services.read_text(encoding="utf-8"):
        problems.append("services.py: donthidepvr seed missing (PVR items would hide)")
    if (tree / "shortcuts" / "{}.properties".format(SKIN_ID)).is_file():
        problems.append("shortcuts: fork properties shipped (menu must be stock)")
    if not (tree / "media" / "extras" / "logo-text-hires.png").is_file():
        problems.append("media/extras: missing wordmark")
    if problems:
        raise SystemExit("FATAL: ship contracts violated:\n  " + "\n  ".join(problems))


def package(tree: Path, zip_path: Path) -> None:
    """Deterministic zip: sorted members, fixed 1980 timestamps, 0644 perms."""
    zip_path.parent.mkdir(exist_ok=True)
    members = []
    for path in tree.rglob("*"):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        members.append(
            (path, "{}/{}".format(SKIN_ID, path.relative_to(tree).as_posix()))
        )
    members.sort(key=lambda m: m[1])
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in members:
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def build_once(lock: dict, workdir: Path) -> Path:
    tarball = ensure_tarball(lock)
    tree = extract_tree(tarball, workdir)
    summary = skin_transforms.transform_tree(tree, lock["our_version"])
    print(
        "transformed: {} files edited, {} renamed, {} swept".format(
            len(summary["edited"]), summary["renamed"], summary["swept"]
        )
    )
    add_assets(tree)
    check_contracts(tree)
    zip_path = workdir.parent / "{}-{}.zip".format(SKIN_ID, lock["our_version"])
    package(tree, zip_path)
    return zip_path


def main(argv: list) -> int:
    lock = read_lock()
    if not lock.get("our_version"):
        raise SystemExit("FATAL: skin_build.lock has no our_version")

    try:
        if "--check" in argv:
            zips = []
            for n in (1, 2):
                zips.append(build_once(lock, BUILD_DIR / "check-{}".format(n) / "tree"))
            a, b = (z.read_bytes() for z in zips)
            if a != b:
                raise SystemExit("FATAL: double build is not byte-identical")
            print(
                "determinism check PASSED ({} bytes, sha256 {})".format(
                    len(a), sha256_file(zips[0])
                )
            )
            return 0

        zip_tmp = build_once(lock, BUILD_DIR / "tree")
        DIST_DIR.mkdir(exist_ok=True)
        zip_final = DIST_DIR / zip_tmp.name
        shutil.move(str(zip_tmp), zip_final)
        lock["zip_sha256"] = sha256_file(zip_final)
        write_lock(lock)
        print(
            "built {} (sha256 {})".format(
                zip_final.relative_to(ROOT), lock["zip_sha256"]
            )
        )
        return 0
    except TransformError as exc:
        raise SystemExit("FATAL: upstream drift - {}".format(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
