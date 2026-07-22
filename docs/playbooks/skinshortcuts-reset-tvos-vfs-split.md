# Playbook: the "Reset main menu" that only a reboot could fix (tvOS VFS split)

Status: RESOLVED in skin.estuary7 1.0.23 (real-path reset) + 1.0.27 (Videos
icon; the 1.0.24 attempt was wrong and was reverted - see the Videos section
below). Later rounds extended the reset/refresh design: 1.0.65 (tvOS DATA
durability reconcile) and post-1.0.65 (immediate on-demand refresh), both
documented at the end of this file. This document exists so nobody burns days
on it again.

## TL;DR (read this first)

On **tvOS (Apple TV)**, a Kodi Python script that manipulates files under
`special://profile`, `special://masterprofile`, or `special://skin` with
**`xbmcvfs`** does NOT reliably affect the same bytes that another component
reading via **`xbmcvfs.translatePath()` + Python `open()`/`ElementTree`** sees.
They resolve to the same logical path but observe different content in-session.

`script.skinshortcuts` reads and writes its menu data with **real filesystem
paths** (`ETree.parse(path)`, `tree.write(path)`, where `path` is a
`translatePath`'d absolute path). Our old reset "cleaned" the menu with
`xbmcvfs.delete` / `xbmcvfs.copy` on `special://` paths. It reported success,
every `xbmcvfs`-based check confirmed the file was clean, and the builder kept
reading the un-cleaned real file. Only a full reboot (which flushes the split)
ever made the reset appear to work.

**Rule: when a skin script must delete/copy/write files that skinshortcuts (or
any Python `open`-based consumer) will read, use `xbmcvfs.translatePath(...)`
plus the `os`/`open` API, never `xbmcvfs` on the `special://` form. And verify
file state with the SAME API the consumer uses, not with `xbmcvfs.File`.**

## Symptom

- User disables/hides a main-menu item in the "Customize main menu" editor.
  The item disappears (correct).
- User clicks **Reset main menu settings** and confirms.
- The item does NOT come back on screen. The editor still shows it disabled.
- A full power-cycle of the Apple TV brings the stock menu back. Nothing short
  of a reboot does (ReloadSkin, switching skins, disabling/re-enabling
  `script.skinshortcuts` all fail).

## Why it looked impossible

Everything on disk looked clean while the menu stayed broken:

- `xbmcvfs.File('special://masterprofile/.../mainmenu.DATA.xml').readBytes()`
  parsed to a games shortcut with **no `<disabled>`** element.
- A substring check for `<disabled>` on the same `special://` path returned
  False.
- The shipped skin default and the skinshortcuts bundled default were both
  clean.
- Yet `DataFunctions().get_shortcuts('mainmenu', ...)` in a fresh RunScript
  process returned the games node **with `<disabled>True</disabled>`**, so
  `build_element` baked `<visible>False</visible>` into
  `script-skinshortcuts-includes.xml` and the tile stayed hidden.

Because skinshortcuts can only ever copy/read a `<disabled>` element (it never
synthesizes one, verified across all of gui.py/datafunctions.py/xmlfunctions.py),
a fresh process returning `<disabled>` means the file it opened still had it. The
file it opened was NOT the file our `xbmcvfs` checks and reset touched.

## The smoking-gun diagnostic

A helper action (`menuProbe`) that reported skinshortcuts' own resolved path
constants and parsed the file at those exact real paths, in the same run as the
`get_shortcuts` call:

```
DATA_PATH   = /private/var/mobile/Containers/Data/Application/<UUID>/Library/Caches/Kodi/userdata/addon_data/script.skinshortcuts/
MASTER_PATH = (same)
rawfile[data]   games_disabled = True      # ET.parse(real path)  -> DISABLED
rawfile[master] games_disabled = True
getshortcuts_games_disabled     = True
```

while, at the same instant:

```
xbmcvfs.File('special://profile/.../mainmenu.DATA.xml')       <disabled> = False   # CLEAN
xbmcvfs.File('special://masterprofile/.../mainmenu.DATA.xml') <disabled> = False   # CLEAN
```

Same logical file, two APIs, opposite content. That is the whole bug for the
"clean file, disabled result" half.

## Root cause (two independent bugs, both needed fixing)

1. **tvOS `xbmcvfs` special:// vs real-path split.** skinshortcuts uses real
   paths (Python `open`/`ETree`); our reset used `xbmcvfs` special:// ops, which
   on tvOS did not update the file the builder reads. `xbmcvfs.delete` returned
   `True` without removing the real file; `xbmcvfs.copy` did not overwrite the
   real file. So the disabled copy survived every reset.

2. **Stuck `skinshortcuts-isrunning` build guard.** `build_menu`
   (xmlfunctions.py:60-63) returns immediately if
   `Window(10000).getProperty('skinshortcuts-isrunning') == 'True'`. Window
   10000 (Home) properties **survive `ReloadSkin()` and addon disable/enable;
   only a Kodi restart clears them.** If any build was interrupted between
   setting the flag (line 63) and clearing it (lines 99/118), every subsequent
   rebuild is a silent no-op, which is exactly why "only a reboot fixed it."

## The fix (scripts/helpers.py `resetMenu`, injected by tools/skin_transforms.py)

The reset now, in order:

1. Clears the stuck guards on Window(10000): `skinshortcuts-isrunning`,
   `skinshortcuts-loading`, and the edit caches.
2. Resolves the **real** paths with `xbmcvfs.translatePath(...)` and wipes every
   `*.DATA.xml` / `*.properties` / `*.hash` in BOTH the profile and masterprofile
   `addon_data/script.skinshortcuts/` dirs with `os.remove` (not
   `xbmcvfs.delete`).
3. Deletes the baked `special://skin/xml/script-skinshortcuts-includes.xml` on
   the real path (missing includes forces `shouldwerun` to True).
4. Copies the skin's `shortcuts/*.DATA.xml` defaults into `addon_data` with plain
   `open(...,'rb')/open(...,'wb')` on real paths.
5. Seeds `donthidepvr=true` (see the Live TV/Radio note below).
6. Clears `skinshortcuts-isrunning` again, sets `skinshortcuts-reloadmainmenu`,
   and fires the canonical
   `RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&group=mainmenu)`.

Verified on the bench Apple TV: disable Games, Reset, Games returns on screen
in-session, no reboot. `get_shortcuts` reads clean. (The IP recorded here
originally, `192.168.1.162`, is not on the fleet's `192.168.7.0/24` subnet and
could not be reconciled with any known box - it is removed rather than left as
a target someone might contact. Do not restore an IP here without confirming
it. The office Fire TV `192.168.7.162` HANDS-OFF rule this paragraph used to
cite was LIFTED 2026-07-21; that box is a normal target.)

## Prevention checklist (for any future skin-side file work on tvOS)

- [ ] Never assume `xbmcvfs` on a `special://` path and Python `open()` on
      `translatePath(special://...)` see the same bytes on tvOS. For files a
      Python consumer will read, do the delete/copy/write with `os`/`open` on the
      `translatePath` result.
- [ ] Verify results with the SAME API the consumer uses. If skinshortcuts reads
      with `ETree.parse(realpath)`, verify with `ETree.parse(realpath)`, not with
      `xbmcvfs.File(special://...)`.
- [ ] Any menu rebuild that "should have happened but didn't": suspect a stuck
      `skinshortcuts-isrunning` on Window(10000). Clear it before firing a build.
      It is not cleared by ReloadSkin or an addon toggle, only by a reboot or an
      explicit `clearProperty`.
- [ ] `xbmcvfs.delete` can return `True` on a file that still exists on tvOS, and
      `xbmcvfs.copy` may not overwrite an existing destination. Do not trust their
      return values for the "the file is now clean" conclusion.

## Related: the blank Videos icon (attempted 1.0.24, REALLY fixed 1.0.27)

Separate but found during the same incident. `shortcuts/overrides.xml` mapped the
`videos` labelID icon to `DefaultAddonVideo.png`, which renders blank in the menu
editor and on the tile (unlike the `livetv`/`radio` overrides whose `Default*`
icons exist). skinshortcuts applies that override on top of the data icon, so the
shipped `icons/sidemenu/videos.png` (present in Textures.xbt) never showed.

**The 1.0.24 fix - repointing the override at `icons/sidemenu/videos.png` - was
WRONG and was REVERTED. Do not reinstate it.** ANY `<icon labelID="videos">`
override that resolves to a SKIN image draws BLANK in the editor: skinshortcuts'
`gui.py` calls `setArt({'icon': 'icon'})` with the literal string `'icon'`
whenever `skinHasImage` is True. Repointing at a skin image swapped one blank
for another. `livetv`/`radio` survive only because their `Default*` overrides are
NOT skin images.

**The shipped fix (1.0.27) is two changes, both in `tools/skin_transforms.py`:**

1. `_edit_overrides` REMOVES the `videos` override line entirely, so the entry
   falls back to the DATA icon `icons/sidemenu/videos.png`.
2. That path exists in MOD V2's `Textures.xbt` as a REDRAWN film-reel, and Kodi's
   loader checks the bundle BEFORE loose files - so `shadow_videos_texture`
   renames the bundled entry in place to `icons/sidemenu/__videos_shadowed__.png`.
   The XBTF name field is a fixed 256-byte null-padded slot, so the rewrite
   touches no frame offsets and needs no offset math; the build stays
   deterministic. Kodi then falls back to the loose stock Estuary `videos.png` that
   `build_skin.add_assets` ships at `media/icons/sidemenu/videos.png`.

Net: no override in play, editor icon fixed, and the glyph matches original
Estuary per THE FIRST MANDATE. `check_contracts` fails the build if either half
regresses (missing loose file, or the bundle entry still present).

## Related: Live TV / Radio always-visible

Stock Estuary shows Live TV and Radio always; skinshortcuts hides them without a
PVR backend by injecting `System.HasPVRAddon`. Numeric window ids do NOT dodge it
(skinshortcuts normalises them back at build time). The only lever is
skinshortcuts' `donthidepvr` setting, seeded to true by the boot service
(`scripts/services.py`) and the reset helper. See the `tools/skin_transforms.py`
FILE_EDITS comment.

## Instrumentation used (removed in 1.0.25)

To root-cause this, temporary helper actions were injected and later stripped:
`menuProbe` (report skinshortcuts path constants + parse them with ET), `writeTest`
(prove the skin xml dir is writable and the includes deletable), `menuDump`
(parse DATA + includes item-by-item), `fileHas` (substring check via xbmcvfs).
If this recurs, re-add a `menuProbe`-style action first: reporting the real
resolved paths and reading them the way skinshortcuts does is what cracked it.

## 1.0.65: Customize edits now SAVE + PERSIST on tvOS (the DATA durability reconcile)

1.0.64 fixed the hash/includes freeze but left the tvOS write/guard split
unaddressed, so Customize Main Menu edits still failed to stick on Apple TV.
Re-derived from Kodi Omega source (`TVOSFile.cpp`, `TVOSNSUserDefaults.mm`,
encoded in `tests/fake_kodi_storage.py`):

- A `*.xml` under `userdata` is shadowed by an NSUserDefaults KEY. `xbmcvfs`
  read/exists are KEY-FIRST (POSIX only as a fallback WHEN NO KEY EXISTS),
  `xbmcvfs` write is KEY-ONLY, and the POSIX copy lives in a purgeable cache.
- skinshortcuts SAVES the menu with `ElementTree.write` (plain POSIX) and READS
  it back with `ETree.parse` (plain POSIX) behind an `xbmcvfs.exists` GUARD
  (`datafunctions.py:178-180`). The freshest edit is always on POSIX; the DURABLE
  store is the key.

Two failure modes: (1) a stale key from an earlier era (EZM++-restored box)
shadows the fresh POSIX edit for every `xbmcvfs` consumer; (2) after a cache purge
only the key survives and skinshortcuts (a POSIX reader) reverts to the shipped
default.

Fix: the tvOS-only `syncMenu` helper action (`_SYNC_MENU_ACTION` in
`tools/skin_transforms.py`), fired from Home's onload BEFORE the buildxml. Per
`*.DATA.xml` it reconciles the layers so the user's FRESHEST edit wins (POSIX when
present): push fresh POSIX bytes into the durable key (de-shadow + register so the
edit survives a purge), and re-materialize POSIX from the durable key when the
cache was purged. It NEVER deletes a copy, skips empty/unparseable data
(no corruption propagation), is byte-preserving (no `ETree` re-serialize, so the
hash never churns), and fires its own `buildxml` (guard cleared first) only when a
layer actually changed. Strict no-op on Fire TV / desktop and on a consistent box
with no pending edit. This obeys the core lesson above: skinshortcuts always reads
POSIX, so POSIX is what we keep correct for it; the key write is a durability
sidecar, never something we make skinshortcuts read.

The durability write was originally gated on the pending-edit flag - superseded
by the flag-free redesign below. The purge-recovery is gated on the unambiguous
`xbmcvfs.exists && !os.path.exists` state (only a surviving key can make exists
True while POSIX is gone). Coverage: `tests/test_syncmenu_tvos.py` execs the REAL
payload against the two-layer fake.

## Post-1.0.65: immediate on-demand refresh (the 4-agent panel findings, 2026-07-17)

1.0.65 shipped the reconcile but edits STILL did not render immediately. A
2-QA + 2-architect panel traced the full trigger graph and found four defects;
all four are fixed together (this section describes the current design):

1. **The power-menu "Customize Main Menu" entry had NO rebuild trigger at all**
   (all platforms - the primary owner-visible bug). The editor is a dialog
   opened OVER a still-loaded Home; closing a dialog never re-fires Home's
   `<onload>`, the only rebuild producer. Upstream never hits this because its
   sole editor entry is behind the SkinSettings WINDOW (whose close path
   re-inits Home). Four releases (1.0.62-1.0.65) fixed the consumer side and
   missed the missing producer. Fix: the `customizeMenu` helper wrapper - it
   launches the editor, waits for the deterministic close signal
   (`Window(10000).Property(skinshortcuts)` is stamped exactly once after
   `doModal()` returns, on save AND cancel; skinshortcuts.py:351), then if
   `skinshortcuts-reloadmainmenu` is set: on Fire OS/desktop it clears the
   stuck `isrunning` guard and fires ONE buildxml directly; on tvOS it arms
   `t7b_chainbuild` and spawns ONLY `syncMenu`, which fires the one build
   strictly after reconciling - never build-and-reconcile as two parallel
   RunScripts (a mid-session purge would make syncMenu WRITE POSIX while the
   build reads it). The durable key also registers immediately this way,
   not at the next Home load.

2. **The tvOS onload raced its own reconcile.** `syncMenu` and the later-load
   buildxml were two ASYNC RunScripts with no ordering; the build could read
   DATA before the reconcile re-materialized it (baking the shipped default)
   and consume `reloadmainmenu` before syncMenu read it. Fix: the ordered
   chain - Home's onload sets `t7b_chainbuild` (later loads only, a
   SYNCHRONOUS builtin, before the spawn), the parallel onload buildxml is now
   `!System.Platform.TVOS`-gated, and syncMenu fires the one build strictly
   after reconciling. The chain fire lives in its own try block so a reconcile
   crash cannot strand the build; a helper crash leaves the marker set and the
   next Home load re-arms it. No marker is set on the first load per boot, so
   no build can fire inside the keep-skin dialog window (the AlarmClock defer
   still owns the first build on both platforms).

3. **The durability push was gated on a flag another thread consumes.**
   `shouldwerun` reads-AND-clears `skinshortcuts-reloadmainmenu` first thing,
   so the key-registration for a fresh keyless edit rode a 50/50 race. Fix:
   flag-free detection - `xbmcvfs.listdir` merges POSIX and key names WITHOUT
   dedupe (TVOSDirectory.cpp), so a name listed ONCE alongside a present POSIX
   file provably has no key. syncMenu registers the key from that structural
   signal and never touches `reloadmainmenu` except to SET it when the POSIX
   layer changed (re-materialize). That set is load-bearing: skinshortcuts
   2.0.3's `writexml` drops hash entries for files absent at build time
   (`if hexdigest:` - hash_utils returns None for a missing file), so a
   re-materialized DATA is INVISIBLE to the hash check and only the flag can
   trigger the rebuild. On-demand refresh must always ride the flag, never
   the hash.

4. **resetMenu left stale NSUD keys behind.** The POSIX wipe cannot reach the
   key layer, so a Caches purge could resurrect the pre-reset menu through a
   surviving key (and the ~500KB NSUD budget only ever ratcheted up). Fix:
   after the wipe, a tvOS-gated `xbmcvfs.delete` of every listed `*.DATA.xml`
   key (`settings.xml` excluded - its key is the addon settings' durable
   copy). This is the ONE correct use of `xbmcvfs.delete` here: on tvOS it
   drops ONLY the key, never a POSIX file.

**Deliberate tradeoff (do not "fix"):** the reconcile dual-layers every
`*.DATA.xml` (POSIX + durable key). tvOS File Manager lists such files TWICE
(listdir does not dedupe) - that is the expected cosmetic side effect of
durability, NOT the incident-2026-07-08 duplicate-userdata corruption, which
was about EZM++ vectoring files it should not have. One coherent entity per
file still holds: both layers carry identical bytes after every reconcile.

Coverage: `tests/test_syncmenu_tvos.py` (ordered chain, flag-free
registration, crash resilience) and `tests/test_menu_triggers.py` (resetMenu
keydrop, purge-after-reset, customizeMenu wrapper) exec the REAL payloads
against the two-layer fake. Residual known windows (accepted): SkinSettings'
`onunload` buildxml can still race the Home-onload chain when leaving Skin
Settings (both converge; loser no-ops via hash); a Customize session longer
than the wrapper's 30-min poll ceiling falls back to the old
refresh-on-next-Home-init behavior for that one save.
