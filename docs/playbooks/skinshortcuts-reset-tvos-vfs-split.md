# Playbook: the "Reset main menu" that only a reboot could fix (tvOS VFS split)

Status: RESOLVED in skin.estuary7 1.0.23 (real-path reset) + 1.0.24 (Videos
icon). This document exists so nobody burns days on it again.

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

Verified on the bench ATV (192.168.1.162): disable Games, Reset, Games returns
on screen in-session, no reboot. `get_shortcuts` reads clean.

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

## Related: the blank Videos icon (fixed 1.0.24)

Separate but found during the same incident. `shortcuts/overrides.xml` mapped the
`videos` labelID icon to `DefaultAddonVideo.png`, which renders blank in the menu
editor and on the tile (unlike the `livetv`/`radio` overrides whose `Default*`
icons exist). skinshortcuts applies that override on top of the data icon, so the
shipped `icons/sidemenu/videos.png` (present in Textures.xbt) never showed. Fix:
`tools/skin_transforms.py` `_edit_overrides` repoints the override at
`icons/sidemenu/videos.png`.

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
