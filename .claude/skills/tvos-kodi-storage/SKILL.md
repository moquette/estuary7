---
name: tvos-kodi-storage
description: >-
  Field guide to why Apple TV (tvOS) Kodi storage behaves nothing like the
  fleet's Fire TVs, for the Tony.7.Bones project (skin.estuary7,
  script.ezmaintenanceplusplus, tony7bones repo). Load BEFORE writing, deleting,
  reading, backing up, or restoring ANY file under special://profile /
  special://userdata / addon_data on Apple TV, and ALWAYS when a bug is
  "saves/works on Fire TV but not Apple TV." Triggers on: Apple TV, atv1, atv2,
  tvOS, NSUserDefaults, Caches purge, xbmcvfs vs open, "file exists but won't
  read", menu/settings revert on restart, duplicate File Manager entries, blank
  image, skinshortcuts menu-save, EZM++ restore reverts custom menu.
---

# tvOS Kodi storage: the fleet's Apple-TV-only hazard

The two Apple TVs (`atv1`, `atv2` = 192.168.7.183) store Kodi's `userdata/*.xml`
in a place the five Fire TVs do not. Code that saves fine on Fire TV can silently
fail to persist on Apple TV. Every repeated data-loss burn in this project traces
to this. Verified line-by-line against `github.com/xbmc/xbmc`, branch **Omega**.

## RULE ZERO

- **The filesystem is not the store on tvOS.** A `.xml` under `userdata` is shadowed by a durable NSUserDefaults key; the disk file is a purgeable cache copy.
- **"Fixed" = verified on an Apple TV**, not in code. No adb on tvOS - verify via JSON-RPC (port 9090) or the Xcode/`devicectl` route.

## The mechanism (source-cited)

`xbmc/filesystem/FileFactory.cpp`:

```cpp
#if defined(TARGET_DARWIN_TVOS)
  if (CTVOSFile::WantsFile(url)) return new CTVOSFile();
#endif
  return new CPosixFile();
```

`CTVOSFile::WantsFile` (`xbmc/platform/darwin/tvos/filesystem/TVOSFile.cpp`) is true iff:
`ext == "xml"` AND basename NOT `customcontroller.SiriRemote*` AND path under `<home>/userdata` (any depth). Such a file is **vectored** - shadowed by a gzip NSUserDefaults key.

Routing for a vectored file (the whole bug surface):

| Op                                | Where it lands on tvOS                 |
| --------------------------------- | -------------------------------------- |
| `xbmcvfs` read / `xbmcvfs.exists` | KEY first; POSIX only if no key exists |
| `xbmcvfs` write                   | KEY ONLY (gzip); disk untouched        |
| `xbmcvfs.delete`                  | drops the KEY only; POSIX file stays   |
| `open()` / `os` / `ElementTree`   | POSIX ONLY; never sees/creates a key   |

Two facts that decide almost every case:

1. **The KEY is durable; the POSIX file (in `Library/Caches`) is purgeable by tvOS at any time.** A POSIX-only write survives the session but can vanish on the next app kill.
2. **Kodi never reconciles key <-> POSIX.** A stale key silently shadows a fresh POSIX write, and vice-versa.

Log fingerprint (stock): `NSUSerDefaults: compressed .../userdata/<name>.xml from <n> to <m>` (xbmc #25939). **Fire OS / Android has NO shadow** - `xbmcvfs` and `open()` agree there.

## The canonical failure: skinshortcuts menu edits don't save on Apple TV

`script.skinshortcuts` 2.0.3 **writes** the menu with `ElementTree.write(path)` = POSIX
(`gui.py`/`nodefunctions.py`), but **guards its read** with `xbmcvfs.exists(path)` = key-first
(`datafunctions.py:178`, then `ETree.parse(path)` on POSIX at `:180`). On tvOS:
`mainmenu.DATA.xml` is vectored, so the edit lands only on the purgeable POSIX copy; the
durable key is never updated. The read-guard misses it (falls through to the shipped
default menu -> item "gone" in Customize), and even when it doesn't, a Caches purge on
restart loses the edit -> the menu reverts to stock. This is Apple-TV-only; it saves on
Fire TV.

## Fix patterns (pick ONE lane per file; never straddle)

- **All-VFS (only lane that persists across a Caches purge):** write with `xbmcvfs.File(path,'w')` so `SetKeyDataFromPath` updates the durable key; read/guard/delete with `xbmcvfs`. Use this when the durable copy must survive app kill (menus, settings).
- **All-POSIX + kill the shadow:** do every op with `os`/`open` on `translatePath`'d real paths AND `xbmcvfs.delete(special://...)` to drop the stale key so VFS falls through to POSIX; then verify with the SAME API the consumer uses. Used by the `resetMenu` helper (estuary7 `tools/skin_transforms.py`). Content stays in purgeable Caches, so durability rides on re-persistence.
- **Reconcile / syncMenu (mid-session, non-destructive):** on Home onload before `buildxml`, for each vectored DATA/properties file: read POSIX bytes (skip if empty/unparseable), and when `os.path.exists(real) and not xbmcvfs.exists(real)`, write those bytes back through `xbmcvfs.File(special,'w')` to register the durable key, then re-assert POSIX. NEVER delete; byte-preserving (do not re-serialize - it churns skinshortcuts' hash into a rebuild loop). Clear the stuck `skinshortcuts-isrunning` guard first; chain `buildxml` yourself (RunScript is async).

Second, separate tvOS gotcha: a stuck `Window(10000).Property(skinshortcuts-isrunning)="True"` survives `ReloadSkin`/addon toggle and no-ops every `build_menu` until a reboot. Clear it before any build (the onload already does).

## Do NOT

- Trust `xbmcvfs.delete`/`copy` return values as proof the POSIX file changed.
- Verify a POSIX write with `xbmcvfs.File` (or vice-versa) - verify with the consumer's API.
- Re-serialize a data file a consumer hashes (rebuild loop).
- `os.remove` the user's ONLY menu copy; materialize/reconcile, never wipe, unless the shipped default is the intended result (that is `resetMenu`, a distinct action).
- Vector everything to keys - the ~500 KB NSUserDefaults budget will terminate the app.

## Research + verify checklist

1. Read Kodi source: `FileFactory.cpp`, `TVOSFile.cpp`, `TVOSNSUserDefaults.mm` on branch Omega. Confirm `WantsFile`, the Open/Exists/Write/Delete asymmetry, `translatePathIntoKey`.
2. Classify the add-on's I/O: unzip `~/Code/moquette/kodi/repo/addons/hosted/script.skinshortcuts/script.skinshortcuts-2.0.3.zip`; grep `xbmcvfs` / `open(` / `ElementTree` / `translatePath`; label every read/write/exists by lane.
3. Model + test against `~/Code/moquette/kodi/estuary7/tests/fake_kodi_storage.py` (source-derived split).
4. On-device (required before "fixed"): JSON-RPC 9090 - `Files.GetDirectory` the addon_data dir, `Addons.GetAddonDetails` for versions; if possible compare `xbmcvfs.exists(path)` vs `os.path.exists(translatePath(path))` after a save (mismatch = split confirmed). Office Fire TV 192.168.7.162 is HANDS-OFF without explicit permission.

## Companion docs

- `~/Code/moquette/kodi/repo/.claude/skills/kodi-storage-map/SKILL.md` - exhaustive per-OS file map.
- `~/Code/moquette/kodi/estuary7/docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md` - the field write-up of this split.
- `~/Code/moquette/kodi/ezmpp/CLAUDE.md` - the tvOS backup/restore/wipe rules (nsud/nsub two-layer capture; a key SHADOWS the disk, `xbmcvfs.delete` drops only the key, Kodi never re-materializes).
- The `tvos-expert` agent (this project) - dispatch it for any Apple TV storage/persistence bug.
