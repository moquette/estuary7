# tvOS Siri remote: Fire TV parity for playback (1.0.49/1.0.50)

**Stock Kodi on Apple TV does NOT do this.** Out of the box, pressing the
Siri remote's back button during fullscreen video or live TV **stops
playback dead**, and there is no button that returns you to fullscreen once
video plays behind the GUI. Estuary 7 changes both, fleet-wide, with no
manual steps on any box. This document records the symptom, the diagnosis
method, the root cause in Kodi's source keymaps, the fix design, the
delivery mechanism, and the proof - so nobody relearns any of it.

## The symptom (owner report, 2026-07-15)

"IPTV plays in the background on Fire OS and tvOS does not." On a Fire TV,
backing out of fullscreen live TV drops to the guide/menus with the stream
still playing. On the Apple TV, the same press killed the stream.

## The diagnosis method (worth keeping)

The breakthrough was noticing that **Kodi's abstract input actions and the
physical remote's buttons are not the same thing**:

1. Sending the JSON-RPC `Input.Back` action to the Apple TV during
   fullscreen live TV exited to the GUI **with playback continuing** -
   identical to Fire TV. So the player logic is platform-agnostic; core
   Kodi was never the problem.
2. The owner's physical Siri remote back press stopped playback.
3. Therefore the Siri remote's back button must be mapped to a *different
   action* than "back" - a keymap issue, not a platform or player issue.

General lesson: **when a remote button misbehaves, compare it against the
equivalent JSON-RPC `Input.*` action.** If JSON behaves and the button does
not, the problem is in a keymap, not in Kodi's logic. JSON-RPC actions
bypass keymaps entirely.

Corollary discovered the same way: tvOS has **no app-level background
playback at all** (leaving the Kodi app suspends it entirely - an Apple
lifecycle rule Kodi's tvOS port does not work around with background-audio
entitlements or PiP). And Fire OS does not truly "play in the background"
when you leave the app either - it **pauses** (measured: player speed 0
after `KEYCODE_HOME`) and resumes where you left it. The only real
per-platform difference was the keymap.

## Root cause: Kodi's shipped Siri remote keymap

Kodi ships `system/keymaps/customcontroller.SiriRemote.xml` (verified
against the Omega branch of xbmc/xbmc). The relevant stock mappings:

| Context | Button 6 (back/menu) | Effect |
| --- | --- | --- |
| `<global>` | `Back` | normal navigation |
| `<FullscreenVideo>` | **`Stop`** | live TV / video DIES on back |
| `<Home>` | **`ActivateWindow(FavouritesBrowser)`** | back at Home opens Favourites - a blank blue screen on a box with no favourites |

And the gesture inventory shows why upstream chose `Stop`: **no button
returns to fullscreen.** Double play/pause (button 21) and double select
(button 22) are both mapped to `noop`. If back merely exited fullscreen,
stock users would strand playback behind the GUI with no way back - the
owner hit exactly that state during testing. Upstream's `Stop` is a
workaround for the missing return path, not a considered UX choice.

### Siri remote button-id reference (from the stock keymap)

| id | Physical input | id | Physical input |
| --- | --- | --- | --- |
| 1-4 | up/down/left/right | 12 | play/pause |
| 5 | select | 20 | hold play/pause (= Stop globally) |
| 6 | menu/back | 21 | double play/pause (stock: noop) |
| 7 | hold select (= ContextMenu / OSD) | 22 | double select (stock: noop) |
| 8-11 | swipes | 23-26 | pans |

## The fix (both halves - one alone is worse than none)

A userdata keymap, `userdata/keymaps/t7b-siriremote.xml`, overriding three
mappings. User keymaps take precedence over system keymaps per button and
window; everything not listed stays stock.

| Context | Button | Stock | Ours | Why |
| --- | --- | --- | --- | --- |
| `FullscreenVideo` + `FullscreenLiveTV` | 6 (back) | Stop | `Back` | exit fullscreen with playback continuing - Fire TV parity |
| `Home` | 6 (back) | Favourites browser | `FullScreen` | back at Home returns to the playing video (owner expectation, found in live testing); `FullScreen` is a no-op when nothing plays, so an idle back at Home does nothing instead of surprising |
| `<global>` | 21 (double play/pause) | noop | `FullScreen` | the missing return-to-fullscreen gesture, from any window; free real estate |

Stopping playback remains available exactly where users expect it: hold
play/pause (button 20, stock `Stop`) and the OSD's stop button (hold
select opens the OSD in fullscreen).

Both `FullscreenVideo` and `FullscreenLiveTV` sections are written because
Kodi consults the live-TV-specific keymap section first when PVR content
plays fullscreen, then falls back to the video section.

## Delivery: the skin's boot service (skins cannot ship keymaps)

Kodi only loads keymaps from `userdata/keymaps/` and the system dir - a
skin cannot carry one. Estuary 7's boot service (`scripts/services.py`,
the same service that seeds the skinshortcuts settings at every start):

- runs on every Kodi start, on every box, before Home's onload
- **gated on `System.Platform.TVOS`** - a strict no-op on Android/desktop
- writes the keymap with plain `open()` (the tvOS xbmcvfs/POSIX split
  lesson: `docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md`)
- is **idempotent by content**: it compares the existing file's bytes and
  rewrites + fires `Action(reloadkeymaps)` only when the payload changed -
  so a keymap revision ships as a normal skin update and hot-applies at
  the next service run, and steady-state boots touch nothing
- logs `estuary7: wrote Siri remote keymap (Fire TV parity)` when it acts

**Revert path** (documented inside the file itself): delete
`userdata/keymaps/t7b-siriremote.xml` and run `Action(reloadkeymaps)` (or
restart Kodi). Stock behavior returns instantly.

## Fire TV isolation - three independent layers, hardware-proven

1. The platform gate: the writer only runs on tvOS. Pinned by
   `test_siri_keymap_not_written_on_android`.
2. The mapping scope: every override sits inside
   `customcontroller name="SiriRemote"` blocks, which apply only to input
   from a device Kodi identifies as a Siri remote. Fire TV remote input
   arrives through a different path entirely.
3. Hardware proof (2026-07-15): after deploying 1.0.50 to the office Fire
   TV, `userdata/keymaps/` was verified empty and the log had zero
   siriremote mentions.

## Verification record (2026-07-15, live on the bench ATV, tvOS)

Owner-driven, step by step, with the stream state confirmed over JSON-RPC
at each step:

1. Fullscreen live TV -> back: **guide showing, still playing**
2. back again: **Home, still playing**
3. back at Home (1.0.49): opened the blank Favourites browser - the gap
   1.0.50 closed
4. back at Home (1.0.50): **returns to fullscreen**
5. double play/pause from anywhere: **returns to fullscreen**

## Test coverage

`tests/test_services_selfheal.py` executes the real service payload
against the two-layer tvOS storage fake (`fake_kodi_storage.py`, which
gained platform-aware `getCondVisibility`):

- tvOS boot writes the keymap with the expected mappings and fires
  `reloadkeymaps`; a second boot of the same box changes nothing and does
  NOT fire a second reload (idempotence)
- an Android boot writes nothing and never touches keymaps

## Maintenance notes

- The keymap payload lives in `_SERVICES_SEED`
  (`tools/skin_transforms.py`). Changing it bumps the content, and every
  tvOS box self-updates its keymap at the next service run after the skin
  update. No box-side steps, ever.
- On an upstream Kodi rebase, re-check
  `system/keymaps/customcontroller.SiriRemote.xml` in the pinned xbmc/xbmc
  branch: if upstream renumbers buttons or changes the FullscreenVideo /
  Home sections, this table and the payload must follow.
- The keymap filename deliberately does NOT start with
  `customcontroller.siriremote` - tvOS's NSUserDefaults file layer
  special-cases that prefix (see `TVOSFile.cpp`), and staying clear of it
  keeps the file in ordinary POSIX handling.
