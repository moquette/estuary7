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
    """Ship the wordmark, artwork, provenance docs, pre-built menu, and splash.

    The home menu is UPSTREAM MOD V2's shortcuts/ dir, stock-ALIGNED by the
    transforms - NOT a fork-authored menu and NOT untouched upstream (owner
    directive 2026-07-10: ship stock Estuary's item set/order). add_assets
    copies NOTHING into shortcuts/; the edits are anchored transforms in
    tools/skin_transforms.py: _edit_mainmenu moves Disc into stock's slot and
    drops the LibreELEC/CoreELEC entries, _edit_overrides removes the "videos"
    icon override, _edit_template rewrites the widget-pane animation. Upstream's
    overrides.xml widget defaults otherwise stand, which is what retires the
    skinshortcuts-properties seed (check_contracts fails the build if a
    .properties file ever ships again). The fleet's old 14-item trimmed menu
    lives on in assets/shortcuts/ - referenced by NO build step and NO test,
    kept only as an archive if it is ever wanted per-box.

    1.0.32 additionally ships the PRE-BUILT skinshortcuts includes
    (xml/script-skinshortcuts-includes.xml, into every res folder) so the menu
    renders INSTANTLY on first boot (shouldwerun()'s "includes file exists"
    check passes, so nothing has to build before the first paint). The boot
    service seeds NO hash (1.0.64: the seed reported "menu up to date" while
    blind to the owner's addon_data edits, so Home main-menu edits never
    persisted). With no hash on disk the first real build - deferred one boot by
    Home's onload past the keep-skin dialog - writes a REAL hash from the owner's
    actual DATA, and every later edit self-heals via a hash mismatch. Also ships
    the restored startup splash (extras/themes/t7b-splash.jpg = the owner's
    background.jpg). check_contracts() gates both (byte-equality, res-coverage,
    and a provenance staleness guard for the includes).
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
    # Baked-in default weather icons (owner directive 2026-07-15, 1.0.46:
    # "no extra downloads"): braz's Outline HD set - CC BY 3.0, based on Erik
    # Flowers' weather-icons; vendored into assets/weather/ from
    # bryanbrazil/resource.images.weathericons.outline-hd @5644804 (tarball
    # sha256 0c92d66fa19019eb309a0fede552ee77eb39708e428c4ab531248e0ddeb61d68)
    # with its LICENSE.txt alongside, credited in ATTRIBUTION.md. Replaces
    # upstream's skin-local set IN PLACE so stock Estuary's
    # special://skin/extras/weather/ default path serves the owner's chosen
    # look with no resource-pack download; the WeatherIcons pack chooser
    # still overrides it when a user picks an installed pack.
    weather = tree / "extras" / "weather"
    shutil.rmtree(weather)
    shutil.copytree(ASSETS_DIR / "weather", weather)
    # Stock Estuary's Videos glyph (Team Kodi, vendored from xbmc/xbmc): a loose
    # media file that Kodi falls back to because the transform shadows MOD V2's
    # redrawn videos.png entry inside Textures.xbt. THE FIRST MANDATE (match
    # stock) + no skinshortcuts editor blank (see _edit_overrides).
    stock_videos_dst = tree / "media" / "icons" / "sidemenu" / "videos.png"
    stock_videos_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ASSETS_DIR / "media" / "icons" / "sidemenu" / "videos.png", stock_videos_dst
    )
    shutil.rmtree(tree / "resources" / "screenshots", ignore_errors=True)
    for shot in sorted(ASSETS_DIR.glob("resources/screenshot-*.jpg")):
        shutil.copyfile(shot, tree / "resources" / shot.name)
    # Pre-built skinshortcuts menu: shipping the generated includes means
    # skinshortcuts' shouldwerun() "includes file exists" check passes on first
    # launch, so the menu renders INSTANTLY - nothing has to build before the
    # first paint. The boot service seeds NO hash (see _SERVICES_SEED): the first
    # real build is deferred one boot by Home's onload past Kodi's "keep this
    # skin?" dialog (so its ReloadSkin cannot silently revert the skin), then
    # writes a REAL hash from the owner's actual DATA and every later edit
    # self-heals. Captured pristine from a live build; re-capture when menu DATA
    # changes (the provenance test fails loud).
    inc_dst = tree / "xml" / "script-skinshortcuts-includes.xml"
    inc_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS_DIR / "xml" / "script-skinshortcuts-includes.xml", inc_dst)
    # Boot splash background (owner-supplied). The splash is restored on by
    # default (see _edit_startup) and points at this image.
    splash_dst = tree / "extras" / "themes" / "t7b-splash.jpg"
    splash_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS_DIR / "extras" / "themes" / "t7b-splash.jpg", splash_dst)
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
    if "resource.images.weathericons.outline-hd" in addon:
        problems.append("addon.xml: outline-hd import survived the 1.0.46 bake-in")
    if not (tree / "extras" / "weather" / "na.png").is_file():
        problems.append("baked weather icons missing: extras/weather/na.png")
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
    # The stock Videos glyph must ship loose AND the MOD V2 bundle entry must be
    # shadowed, or Kodi renders the film-reel (bundle wins over loose files).
    loose_videos = tree / "media" / "icons" / "sidemenu" / "videos.png"
    if not loose_videos.is_file():
        problems.append("media/icons/sidemenu: missing stock videos.png")
    xbt = tree / "media" / "Textures.xbt"
    if not xbt.is_file():
        problems.append("media: Textures.xbt missing")
    elif any(
        name == skin_transforms._XBT_VIDEOS_PATH
        for name, _ in skin_transforms._xbt_entry_offsets(xbt.read_bytes())
    ):
        problems.append(
            "Textures.xbt: icons/sidemenu/videos.png still bundled "
            "(shadow failed - MOD V2 film-reel would win over the loose stock icon)"
        )
    # Payload trim must have run (keeps the install small; see TRIM_PATHS).
    for rel in TRIM_PATHS:
        if (tree / rel).exists():
            problems.append("payload not trimmed: {}".format(rel))
    # Pre-built menu must ship (byte-identical) in EVERY <res> folder addon.xml
    # declares, or the first-launch rebuild+ReloadSkin reappears. And the vendored
    # includes must still match the shipped menu DATA (provenance) or it is stale.
    import json as _json
    import re as _re

    vendored_inc = (
        ASSETS_DIR / "xml" / "script-skinshortcuts-includes.xml"
    ).read_bytes()
    addon_text = (tree / "addon.xml").read_text(encoding="utf-8")
    res_folders = set(_re.findall(r'<res\b[^>]*\bfolder="([^"]+)"', addon_text)) or {
        "xml"
    }
    for folder in sorted(res_folders):
        inc = tree / folder / "script-skinshortcuts-includes.xml"
        if not inc.is_file():
            problems.append("res {!r}: missing pre-built includes".format(folder))
        elif inc.read_bytes() != vendored_inc:
            problems.append(
                "{}: includes differ from the vendored capture".format(folder)
            )
    prov = _json.loads(
        (ASSETS_DIR / "xml" / "includes.provenance.json").read_text(encoding="utf-8")
    )
    for rel, want in prov["data_sha256"].items():
        f = tree / rel
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        if got != want:
            problems.append(
                "menu DATA changed ({}): re-capture "
                "assets/xml/script-skinshortcuts-includes.xml from a pristine "
                "Kodi build, then regenerate includes.provenance.json".format(rel)
            )
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


# Bulk MOD V2 ships that the fleet does not need. Dropping it shrinks the ~86MB
# install (and the Apple TV's long black-screen install) by roughly two thirds.
# Fail loud if a target vanishes (upstream drift), never silently ship bloat.
TRIM_PATHS = (
    # 49MB of view-layout PREVIEW thumbnails, formerly shown in the MOD V2
    # view-picker dialog (Custom_1131). Since 1.0.39 nothing references them:
    # the picker itself is trimmed below and its Variables.xml image-lookup
    # variable is deleted by the transforms. Forced views (Skin Settings) use
    # Kodi's built-in select dialog and never showed these.
    "extras/views",
    # The MOD V2 view-picker dialog. Unreachable since 1.0.39: the transforms
    # restore stock Estuary's single Viewtype cycle button (the dialog's only
    # ActivateWindow(1131) caller). With extras/views trimmed it could only
    # show its splash-art fallback (the "MOD V2 poster"). Custom windows load
    # by filename, so deleting the XML deletes the window.
    "xml/Custom_1131_SettingsViews.xml",
    # MOD V2's splash/poster art. Startup.xml uses our t7b-splash.jpg and the
    # view picker (its last consumer, via texture fallback + the deleted
    # Variables.xml fallthrough) is gone.
    "extras/themes/splash.png",
    # 23MB font used ONLY by the unused "Arial Unicode MS" alternate fontset
    # (the Default fontset uses NotoSans). Font.xml is left stock per the mandate
    # ("alternates nobody runs"); that alternate fontset would render with
    # fallback fonts if ever selected via Kodi's font picker.
    "fonts/ArialUnicodeMS.ttf",
    # ---- 1.0.44 trim round (owner-approved 2026-07-15, audit in TASKS) ----
    # (1.0.44 trimmed extras/weather as orphaned; 1.0.46 re-ships that dir
    # with the VENDORED Outline HD set instead - see add_assets - so it left
    # this list.)
    # Orphaned by the no-bold rebind: no fontset binds the Bold face anymore.
    "fonts/NotoSans-Bold.ttf",
    # Dead since MOD V2's Media sources tile left the System page: nothing
    # calls ActivateWindow(1120). Custom windows load by filename, so
    # deleting the XML deletes the window.
    "xml/Custom_1120_SourcesDialog.xml",
    # 4.9MB of EPG genre artwork, rendered only by the sidebar genre-colors
    # cycle's "genre artwork" mode - unused on the fleet (owner: "no one
    # uses it"). The transforms drop that mode from the cycle so it cannot
    # be selected into blankness; a stale genrecolors=20190 resets to
    # defined colors on the next cycle click.
    "extras/epg-genres",
    # Karaoke lyric faces, used only by the CU LRC Lyrics add-on overlays;
    # the fleet runs no lyrics add-on. Font.xml keeps the lyr* ids untouched
    # (the font-id inventory invariant); if lyrics ever return, those
    # overlays render in the fallback face instead of the decorative ones.
    "fonts/lyrics",
    # Seasonal theme art packs (owner: gone). The EnableThemes machinery
    # (toggle, expressions, picker) stays - it is opt-in default-off and
    # sheds only its artwork here.
    "extras/themes/christmas",
    "extras/themes/easter",
    "extras/themes/halloween",
    "extras/themes/palmweek",
    "extras/themes/valentine",
    # Non-English skin locales (14): the fleet is English; Kodi falls back
    # to en_gb strings for any missing locale anyway.
    "language/resource.language.cs_cz",
    "language/resource.language.de_de",
    "language/resource.language.es_es",
    "language/resource.language.fr_fr",
    "language/resource.language.he_il",
    "language/resource.language.hu_hu",
    "language/resource.language.it_it",
    "language/resource.language.nl_nl",
    "language/resource.language.pl_pl",
    "language/resource.language.pt_br",
    "language/resource.language.ru_ru",
    "language/resource.language.sk_sk",
    "language/resource.language.tr_tr",
    "language/resource.language.zh_cn",
)


def trim_payload(tree: Path) -> None:
    """Remove bulk assets the fleet does not need (TRIM_PATHS)."""
    for rel in TRIM_PATHS:
        target = tree / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.is_file():
            target.unlink()
        else:
            raise SystemExit(
                "FATAL: trim target missing (upstream drift): {}".format(rel)
            )


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
    trim_payload(tree)
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
