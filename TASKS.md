# TASKS

Estuary 7 - fork-by-build of skin.estuary.modv2 for the Tony.7.Bones fleet.
Full phase plan + locked decisions: `docs/PLAN.md`. Project rules: `CLAUDE.md`.

## Phase status

- [x] **Phase 0 - Scaffold + groundwork** (2026-07-10, commit `13b7ebd`). Upstream
      pinned at `8d9b2c7c` = 21.4+omega.4, verified byte-identical to the fleet's
      stock skin via the Office box `.bak` snapshots; tarball sha256 in
      `skin_build.lock`. Proxy `request()` 302-following live-verified (plain
      release-asset URLs work). NOTE: upstream Omega head is ALREADY 21.4+omega.5 -
      the rebase to it is a deliberate exercise AFTER the baseline ships.
- [x] **Phase 1 - Build pipeline** (2026-07-10). `tools/skin_transforms.py`
      (15 anchored fail-loud file edits + rebrand + 46-file [B] sweep +
      Font.xml Estuary-weights + baked opt-out defaults), `tools/build_skin.py`
      (sha256-verified fetch, transform, ship-contract checks, deterministic
      zip; `--check` double-builds and byte-compares), `assets/` (16 shipped
      skinshortcuts files + wordmark, seeded from the goldens), `tests/`
      (70 passing: anchors incl. mutation/fail-loud, golden parity vs the
      1.8.0 bytes, no-bold contracts, baked-default contracts, rebrand,
      determinism). dist zip sha256 in `skin_build.lock`. NOTE for Phases 4/5:
      skinshortcuts reads `<skinid>.properties` ONLY from its addon_data - the
      re-keyed copy shipped at `shortcuts/skin.estuary7.properties` must be
      seeded by Setup's `_install_skin` (Phase 4) / the migrator (Phase 5);
      the DATA files ARE consumed natively as skin defaults.
- [x] **Phase 2 - First release + hosting** (2026-07-10). Public repo
      `moquette/estuary7` (owner decision: moquette, not tony7bones - no
      tony7bones GitHub credentials on this machine; transfer later is safe,
      GitHub redirects). Release v1.0.0 with the 94MB zip asset; anonymous
      download sha256-verified against the build. tony7bones.github.io:
      `addons/hosted/skin.estuary7/` metadata + repository.json entry (zip
      template -> the release asset URL), shipped via proxy release 2.2.7.
      End-to-end verified through the REAL proxy engine: full 98,631,598-byte
      stream sha256-matches the build, live addons.xml lists skin.estuary7
      1.0.0 with the full requires closure, icon/fanart resolve.
- [x] **Phase 3 - Device verify** (2026-07-10, Office Fire TV 192.168.7.162).
      Estuary 7 1.0.0 installed alongside MOD V2 (adb push + boot rescan +
      SetAddonEnabled), switched live, screencap parity vs the 1.8.0 overlay
      baseline: home (six thin items, wordmark, thin clock, top-bar weather
      w/ outline icon, plain shortcut icons), widgets, gear order, thin
      SkinSettings nav + our "Estuary 7" category/toggle/breadcrumb, PVR
      regular headers, Classic-list power menu. Live-skin greps: zero [B],
      zero bold binds, zero non-lyr style-bold. Survived restart; reverted to
      MOD V2 in one switch (overlay intact) - rollback exercised BOTH ways.
      CONFIRMED on hardware: fresh skin shows menu but NO widgets until the
      skinshortcuts properties is seeded into addon_data (seed + hash drop +
      restart fixed it) - Phase 4 setup / Phase 5 migrator MUST do this.
      FLAGGED for owner: upstream "ESTUARY MOD V2" logo artwork still shows in
      the SkinSettings window corner (cosmetic; candidate 1.0.1 transform).
      Box end state: MOD V2 + overlay 1.8.0 active (modv2plus updated from
      1.6.3 via push), Estuary 7 installed alongside. ATV by-eye check CLOSED
      2026-07-10: owner installed 1.0.1 on the ATV via Install-from-repository
      (the first real repo-path install - proxy resolved, release asset
      streamed on tvOS) and verified the look by eye. Phase 3 fully complete.
- [x] **Phase 4 - Setup/library/tests** (2026-07-10, tony7bones.github.io
      077a60a + release e564b78: library 1.9.0 + bootstrap 2.3.0). SKIN_ID ->
      skin.estuary7; the Skin layer direct-extracts the fork from its GitHub
      release asset (version from the hosted metadata), selects the remaining
      closure (skinshortcuts + image.resource.select) explicitly, seeds the
      skinshortcuts properties into addon_data (+hash drop), and no longer
      installs modv2plus on fresh boxes. skin_done = installed + active.
      Fork-resilience pinned: the skin installs/activates even on a bare repo
      index. Snapshot regenerated; 1295 tests + ruff green. Real-device proof
      of the fresh-box path deliberately deferred to Phase 5 (a full fresh
      provision would wipe the bench; the migrator run IS the live exercise).
- [x] **Phase 5 - Fleet migration**: DROPPED as a project (owner decision
      2026-07-15). No modv2plus 2.0.0 migrator will be built. Boxes switch to
      Estuary 7 MANUALLY, one at a time, at leisure (one skin switch via the
      repo; rollback = one switch back). `script.tony7bones.modv2plus` is
      DEPRECATED effective immediately: no further releases or investment;
      its boot service keeps already-patched MOD V2 boxes working until each
      box is switched. Context: the fleet's distribution is converting to a
      static repo - plan lives in the fleet meta-repo,
      `~/Code/moquette/kodi/docs/static-repo-and-tailscale.md` - and no
      longer gates on this migration.
- [ ] **Phase 6 - Retirement + docs**: retire modv2plus once the last box has
      left MOD V2; correct the playbook's wrong "MIT" license note (upstream =
      GPL-2.0 code + CC-BY-SA-4.0 art).

## Menu-reset incident (1.0.2x, RESOLVED 2026-07-12)

"Reset main menu settings" did not restore items the user had disabled/hidden in
the Customize main menu editor - only a full Apple TV reboot did. Root-caused and
fixed on the bench ATV (`192.168.1.162` as recorded at the time) after a
multi-session, ~2-day dig. **FLAGGED (2026-07-14 doc audit): this IP is on a
different subnet than every other documented box on this network (Office Fire TV
`192.168.7.162`, the Mini `192.168.7.2`, the bench Apple TV later identified as
`192.168.7.183` - see `tony7bones.github.io/docs/incident-2026-07-14-ezmpp-restore-wiped-custom-menu-tvos.md`,
which independently caught the SAME box being misidentified by IP, `.220` vs the
real `.183`). This looks like a `7`/`1` transposition typo, not a re-verified
fact - left as originally recorded rather than silently corrected; treat
`192.168.1.162` here as unverified.** Two independent bugs:

1. **tvOS xbmcvfs vs real-path split** - the reset cleaned menu files via
   `xbmcvfs` on `special://` paths, but skinshortcuts reads/writes them with
   real `translatePath` + Python `open`/`ETree`, and on tvOS the two APIs see
   different bytes in-session. The reset now uses real-path `os`/`open`.
2. **Stuck `skinshortcuts-isrunning` on Window(10000)** - survives ReloadSkin
   and addon toggles, only a reboot clears it; a stale True makes every rebuild a
   no-op. The reset now clears it.

Fixed in 1.0.23 (reset), 1.0.24 (first attempt at the blank Videos editor/tile
icon: repointed the overrides `videos` labelID to `icons/sidemenu/videos.png` -
WRONG, ANY skin-image override still draws blank), 1.0.25 (removed the temporary
diagnostics), 1.0.27 (the real Videos-icon fix, local-Kodi-verified: REMOVE the
override entirely - the skinshortcuts editor blanks any skin-image override
because gui.py setArt uses the literal string 'icon' - AND ship ORIGINAL
Estuary's film-strip `videos.png` by shadowing MOD V2's bundled `Textures.xbt`
entry in place so Kodi falls back to the loose stock copy; Kodi checks the xbt
bundle BEFORE loose files, so a same-name loose override alone is a no-op).
Live TV/Radio kept visible via seeded `donthidepvr=true`. FULL WRITEUP +
prevention checklist:
`docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md`. Also captured in
`CLAUDE.md` (Runtime gotchas). These fixes ship to the ATV via the proxy; the
6-box fleet is untouched (still Phase 5-gated).

## Post-launch hardening, 1.0.28-1.0.40 (current: 1.0.40 RELEASED 2026-07-15, live on the office bench)

Bench-driven fixes shipped after the 1.0.1 stock-alignment round, none yet a
formal PLAN.md phase (Phase 5 fleet migration has not started - these all
landed on the bench box(es) ahead of it). In order:

- **1.0.28/1.0.29** - added a Skin Settings item to the power menu (all three
  display modes) + a System-page toggle to swap the Games tile for it. 1.0.29
  fixed a same-day tvOS CRASH: 1.0.28's menu item pointed at a bundle-relative
  `Textures.xbt` icon, which killed Kodi the instant the power menu opened on
  Apple TV (fine on macOS). Fixed by repointing at the shipped loose
  `special://skin/extras/icons/skinsettings.png`, matching every other working
  power-menu item.
- **1.0.30** - trimmed the install payload ~70% (86MB -> 25MB) by dropping
  `extras/views` (view-picker preview thumbnails only) and the unused
  `ArialUnicodeMS.ttf` (23MB, no fontset references it), cutting the Apple TV's
  install black-screen window.
- **1.0.31** - stopped the boot service from forcing an extra
  `skinshortcuts-reloadmainmenu` nudge on top of the natural first-boot rebuild
  (redundant, and the one reload MOD V2 itself never did).
- **1.0.33** - closed the first-launch black-flash/revert/reset/reboot cluster:
  ships pre-built skinshortcuts includes + a matching on-device hash so first
  Home load skips the rebuild+`ReloadSkin` entirely (re-seeds on a version
  mismatch, so upgrades are covered too); clears the stuck
  `skinshortcuts-isrunning` guard on every Home load; seeds `donthidepvr` before
  the first build. Hardware-verified on the bench Apple TV.
- **1.0.35** - matched stock Estuary's System-page tile grid metrics (centered
  4-column layout, corrected focus-highlight size) - the redesigned System page
  had drifted from stock's cell/highlight geometry. Hardware-verified.
- **1.0.36/1.0.37/1.0.38 - the tvOS restore self-heal + boot-loop saga
  (2026-07-14).** Cross-linked with the EZ Maintenance++ incident
  `tony7bones.github.io/docs/incident-2026-07-14-ezmpp-restore-wiped-custom-menu-tvos.md`
  (that repo owns the root-cause writeup; this is the skin-side summary):
  - **1.0.36** - the boot service now self-heals a main menu orphaned by an
    EZM++ restore: if skinshortcuts DATA exists only as an NSUserDefaults key
    (not on disk), it reads the key back through `xbmcvfs`, writes it to disk
    with plain `open()` (the API skinshortcuts itself reads with), drops the
    stale hash, and lets skinshortcuts rebuild the menu from the owner's own
    data. It also stopped seeding a hash over an already-customized menu
    (which had been silently reverting the menu to stock on every skin version
    bump, fleet-wide, restore or not).
  - **1.0.37** - purges the now-redundant NSUserDefaults keys the self-heal (or
    an earlier bad restore) leaves behind, so each file goes back to being one
    coherent on-disk entity (no duplicate File Manager entry, no stale key
    shadowing the disk copy, tvOS defaults budget freed). Guarded so it only
    ever purges a key whose POSIX copy is confirmed present first.
  - **1.0.38 - REGRESSION FOUND AND FIXED SAME DAY.** 1.0.36's hash-drop rule
    was too broad: it dropped skinshortcuts' hash whenever the box had ANY
    `*.DATA.xml` on disk, which is true of every box that has ever built a
    menu - not just a just-healed one. skinshortcuts then saw no hash on
    every boot, rebuilt, reloaded the skin, wrote a fresh hash, which the next
    boot deleted again: **a permanent every-boot rebuild loop on all 7 boxes,
    Fire TV included, not just Apple TV.** Fixed by narrowing the drop to
    exactly the boot that just re-materialized menu DATA out of
    NSUserDefaults (self-limiting: heals once, never loops). Also corrects the
    1.0.37 purge's safety reasoning against Kodi Omega source: `xbmcvfs.delete()`
    on a userdata `*.xml` CANNOT delete the POSIX file on tvOS (`CTVOSFile::Delete`'s
    POSIX-delete fallback is unreachable for files dispatched to it - it drops
    the key and reports success either way); the purge's actual safety property
    is structural (it only calls delete on a path whose disk copy it already
    confirmed), not the reachable-fallback story the 1.0.37 comment originally
    claimed. New tests: `tests/fake_kodi_storage.py` (a two-layer tvOS fake -
    NSUserDefaults keys + a real POSIX tree - representing "key exists, disk
    file gone", which the old dict-based fake could not express) +
    `tests/test_services_selfheal.py` (9 tests: healthy/orphaned/post-heal/
    virgin/skin-bump/purge boots on tvOS and Android; the healthy-boot case
    fails on the pre-fix guard). 95 tests + determinism green.
  - **Verified live (2026-07-14 doc audit):** office Fire TV
    (`192.168.7.162`) confirmed via direct JSON-RPC query -
    `skin.estuary7` reports version `1.0.38`. The task record states the
    bench Apple TV (`192.168.7.183`, friendlyname now reports `atv2`) is also
    on 1.0.38, alongside EZ Maintenance++ `2026.07.14.1`; that box was asleep
    (unreachable over JSON-RPC) at the time of this audit, so its version was
    not independently re-confirmed here.
- **1.0.39 (2026-07-15)** - replaced the MOD V2 view-picker dialog with stock
  Estuary view cycling, and removed the MOD V2 splash/poster art. The dialog
  (`Custom_1131_SettingsViews.xml`, opened from the media sidebar's "View"
  button) existed to show per-view preview thumbnails; 1.0.30 trimmed those
  (`extras/views`, 49MB), leaving the dialog rendering its
  `extras/themes/splash.png` fallback - the "MOD V2 poster" the owner reported.
  Now the sidebar carries exactly stock Estuary Omega's single Viewtype button
  (label 31023, `Container.NextViewMode` cycle, verified against xbmc/xbmc
  Omega `Includes_MediaMenu.xml`), the dialog XML and splash art are TRIM_PATHS
  entries, and the dead 92-line `SettingsViewsImagesVar` block is deleted from
  Variables.xml (new `_delete_block` fail-loud helper; the golden-parity test
  normalizes via the same shared function). Forced views (Skin Settings) use
  Kodi's built-in select dialog and are unaffected; `extras/views.xml` (the
  view-id definitions `services.py` reads) still ships. New
  `tests/test_viewpicker.py` (4 contracts: stock button bytes, no
  `ActivateWindow(1131)` anywhere, variable gone, trims present). 99 tests +
  determinism green. Hardware-verified BOTH bench boxes same day: office Fire
  TV (adb push + boot rescan) and atv2 (install-from-zip over the KodiShare
  NFS source, driven end-to-end via JSON-RPC); owner confirmed the sidebar
  cycles views with no dialog and no poster on atv2. Kodi GUI gotcha learned:
  the file-browser dialog serves stale in-memory directory listings for
  already-browsed NFS paths - drop new zips into a not-yet-browsed subfolder
  (`apps/`) or reboot Kodi first.
- **1.0.40 (2026-07-15) - HARDWARE FAIL, WITHDRAWN SAME DAY (never released;
  nothing committed)** - first attempt at the owner-requested "Show labeled
  tiles" sub-option "Do not apply labels to Movies & TV Shows" (radiobutton
  1103 below the PVR-info sub-option, visible only while the parent is on).
  The attempt made label visibility PER-ITEM: a new `$EXP[tile_unlabeled]`
  (global flag OR sub-toggle + ListItem.DBType in movie/set/tvshow/season/
  episode) textually swapped into all 496 layout sites reading
  `Skin.HasSetting(hide_tile_labels)`. All local gates were green (100 tests,
  golden parity mirrored, determinism) but it FAILED on the office Fire TV:
  with the sub-toggle on, movie tiles dropped the label but kept the LABELED
  art geometry - a smaller inset thumb with dark side borders superimposed on
  the poster (owner-observed + screencap-confirmed). ROOT CAUSE: upstream
  gates labeled-vs-unlabeled through THREE mechanisms - control `<visible>`
  (re-evaluated per item, per frame), itemlayout/focusedlayout `condition`
  attributes, and `<include condition>` (resolved ONCE at window load with NO
  ListItem context). A per-item expression can only ever flip the first kind,
  so the DBType terms were false at the structural sites (include picks the
  labeled InfoWallMusicLayout in e.g. WidgetPanelPoster's focusedlayout) while
  the per-item sites flipped - one tile rendered a MIX of both modes. LESSON:
  any skin-setting condition that upstream uses inside `<include condition>`
  can never become per-item; scoping must stay STATIC (whole-widget), decided
  per widget-layout include, not per tile. Bench box rolled back to the 1.0.39
  xml set same hour (adb push + restart, JSON-RPC-confirmed 1.0.39, screencap
  parity); the orphaned `hide_video_tile_labels` guisettings bool is inert
  under 1.0.39. SUPERSEDED same day: on seeing the bench, the owner redefined
  the ask - keep the labels, kill the "double poster" and the dark side bars
  (see the second 1.0.40 entry below). The sub-toggle work was fully reverted
  (git checkout; no remnants, guarded by the new end-state test).
- **1.0.40 (2026-07-15, second take) - LABELED POSTER TILES FIXED, BENCH-
  VERIFIED SAME DAY (not yet committed/released)** - owner redefined the ask
  after the withdrawn sub-toggle attempt: keep labels, remove the doubled
  poster and the dark side bars on home widget tiles. DIAGNOSIS (bench,
  screencap + JSON-RPC art dump): every widget row on the box instantiates
  the generic 'Widget' include (skinshortcuts personal-widget rows; POV
  plugin items DO carry poster art), whose ITEMLAYOUT stacks
  InfoWallMovieLayout (full-bleed poster) under the labeled
  InfoWallMusicLayout chrome - upstream forgot the mutually exclusive
  condition its own focusedlayout and WidgetListPoster carry. And the
  intended labeled design itself is a 316x316 aspect-keep thumb over a dark
  panel: portrait posters get dark side bars. Both owner-rejected. FIX
  (tools/skin_transforms.py, `_edit_includes_home`): in the generic Widget +
  WidgetListPoster 486 layouts, wrap the InfoWallMusicLayout/Progress run in
  a per-item group visible only when ALL poster art keys are empty (the same
  split InfoWallMovieLayout uses internally), add a fork label riding the
  poster's bottom 70px (font12 textbox at top 300, year per the stock
  hide_pubyear pair) on a dark fade band (overlays/overlayfade.png, full
  strength, 150px tall at top 220 - owner-tuned live on the bench: 70 CC ->
  100 FF -> 150 FF), restore InfoWallMovieLayout to labeled focusedlayouts
  via a per-item poster-present group, and drop WidgetListPoster's
  itemlayout load-time condition (the include self-gates on art). WidgetPanelPoster
  untouched (no stacking bug; Animation_FocusBounce anchor excludes it).
  Music/genre/category tiles byte-identical. Per-item logic rides GROUP
  VISIBILITY ONLY - the first take's include-condition lesson. Ship delta vs
  1.0.39: Includes_Home.xml + addon.xml only. Gates: 100 tests (new
  test_labeled_poster_tiles_render_poster_plus_label end-state contract) +
  determinism green. Bench-verified on the office Fire TV (adb push +
  restart, JSON-RPC 1.0.40 confirmed, screencaps each round): POV movie rows
  render clean single posters, label on the fade band at the poster bottom,
  focused tile = poster + focus frame + label, no doubling, no side bars;
  owner watched live and tuned the fade twice ("nice!"). RELEASED 2026-07-15
  (owner: "deploy"): commit 7b56720, GitHub release v1.0.40 (asset sha256
  download-verified against the lock), proxy metadata bumped
  (tony7bones.github.io f795516, raw URL confirmed serving 1.0.40), office
  proxy cache busted via the update endpoint. The office box already runs
  the identical bytes via the bench pushes; atv2 and the fleet update
  through the repo at the owner's leisure. The fade-look revisit stays an
  open task (see Deferred) - any change ships as 1.0.41+.
- **1.0.40 also fixes: rating badge ignored its toggle (2026-07-15,
  bench-verified)** - the owner disabled every media flag, yet a lone TMDB
  rating badge kept rendering at the screen corner on focused home tiles.
  Upstream bug: the flags dialog (Custom_1137) writes `show_tmdbflag` and
  every other flag in the MediaFlags bar checks its own opt-out setting, but
  the two rating MediaFlag sites (flags/tmdb.png + the use_imdblogo
  variant, Includes.xml) never got the term - ONLY the 5px spacer beside
  them honors it. Fix: `_edit_includes` prepends
  `!Skin.HasSetting(show_tmdbflag)` to both visible params; golden parity
  mirrors the pair. Verified live: badge gone with a POV tile focused.
  FLAGGED upstream typos found during diagnosis (not fixed, candidates for
  a later round): Custom_1137 line ~107 `!Skin.HasSetting(show_tmdbflag`
  (missing paren, breaks the use_imdblogo sub-toggle's visibility),
  Includes.xml `Skin.HasSetting(cinfodialog_rating)` (stray 'c' - the info
  dialog's tmdb rating reads a never-set flag), DialogFullScreenInfo
  `...AudioChannels)<"` (stray '<' in a visible param). The PVR widget bar's
  tmdb badge also lacks the show_tmdbflag gate (PVR items - separate site,
  not part of this fix).
- **1.0.40 also fixes: finish-time flag vanished in widget "More" lists
  (2026-07-15, bench-verified)** - with duration + aired-date + finish-time
  flags enabled, Home showed all three on a focused tile but the same
  widget's "More" plugin list showed only duration + date. Upstream bolted
  `!String.StartsWith(Container.FolderPath,plugin://)` onto ALL FOUR
  end-time flag groups (short + AM/PM variants in MediaFlags and
  MediaFlagsInfoDialogRight, Includes.xml) - no other flag carries it, so
  the bar goes inconsistent inside any plugin-browsed window. Fix:
  `_edit_includes` drops the term (count=4); the groups keep their real
  gates (end-time present, not a folder, show_mediaendtimeflag). Audited
  the other 27 plugin:// sites (View_54/503/504/505/506/507/53, Variables,
  DialogVideoInfo): all gate UNRELATED features (spoiler plots, artist
  variants, per-view panels) - untouched. Golden parity mirrors the pair.
  Verified live: POV Trending list now shows 1h51 / finish 1:20 PM /
  05/27/2026, matching Home.

## Bench state (Office Fire TV 192.168.7.162)

- Since 2026-07-10 (1.0.1 tweak round): Estuary 7 ACTIVE; BOTH
  `script.tony7bones.modv2plus` AND `skin.estuary.modv2` DISABLED (deliberate
  end-state soak - the fork standing with zero overlay machinery). Both stay
  INSTALLED: modv2plus (currently 1.8.0 in `tony7bones.github.io`) is the
  future Phase 5 migrator, and the MOD V2 skin dir keeps the applied overlay
  and its `.baks` frozen (disabled add-ons do not auto-update, so no Kodinerds
  clobber is possible). Rollback = re-enable both, switch skins - seconds, no
  downloads. The other six boxes keep everything enabled until Phase 5.
- **Current version (confirmed live 2026-07-15 via JSON-RPC):** `skin.estuary7`
  1.0.40 on the office Fire TV (192.168.7.162, bench-pushed bytes identical
  to release v1.0.40); atv2 (192.168.7.183) still on 1.0.39 pending a repo
  update at the owner's leisure; `script.ezmaintenanceplusplus` 2026.07.14.1.

## Deferred / revisit later

- **Labeled poster-tile look (1.0.40) - REVISIT (owner, 2026-07-15).** The
  poster+label-on-fade design is live on the office bench (fade at top 220,
  150px, full strength) and the owner paused tuning there ("let's pause for
  a moment here but make it a task to revisit this again"). Revisit the fade
  height/strength and overall tile look with the owner before cutting the
  1.0.40 release; the build, tests, and bench deploy loop are all in place
  (see the second 1.0.40 entry above - one-minute iteration cycle).

- **Phase 4/5 MUST handle the proxy's 1h manifest cache** (learned on the ATV
  2026-07-10): the proxy service caches its GENERATED addons.xml for an hour
  (LoadingCache TTL) and Kodi's "Check for updates" / full Kodi restarts do
  NOT reliably bust a bad/stale build - the deterministic refresh is the
  proxy's own update endpoint (`http://127.0.0.1:<port>/update`, exposed in
  the add-on menu as "Update repository", or
  `Addons.ExecuteAddon(repository.tony7bones, update_repository)`). Any
  repo-resolved install of skin.estuary7 right after a proxy release must hit
  that endpoint first or the skin may be invisible to the resolver.

- **Skin Settings category order**: revisit in a future round. The 1.0.1
  order (commit 6158a83) leads with stock Estuary's sequence (General, Home
  menu, Artworks, Music OSD, Video OSD) and appends MOD V2's extra panels
  (Library, PVR & Live TV, Colors, Extras, Necessary add-ons) in upstream
  relative order - the tail placement was a judgment call, not an owner
  decision. Reordering is safe anytime: panes gate on item ids, and the
  transform is one data table (`_CATEGORY_ORDER_STOCK` in
  `tools/skin_transforms.py`).
- **In-place "Remove this main menu item" on empty home pages** (owner wants it;
  deferred 2026-07-13 as skinshortcuts surgery). Stock Estuary shows, on each
  empty content panel, an `ImageWidget` call-to-action: "Enter files section" /
  "Enter add-on browser" (`button_onclick`) PLUS "Remove this main menu item"
  (`button2_onclick` -> `Skin.SetBool(HomeMenuNo<X>Button)`, string 31116), and
  each stock item is gated `<visible>!Skin.HasSetting(HomeMenuNo<X>Button)`. Ours
  keeps the ImageWidget + the "Enter files/add-on" button but sets
  `visible_2="false"` on every block (the Remove button is hidden) and strips
  `HomeMenuNo` entirely - because our menu is skinshortcuts-driven (container
  9000 = `RunScript(script.skinshortcuts,buildxml)`); the stock bool would flip
  something nothing reads and skinshortcuts would rebuild the item right back. To
  add it for us: re-point `button2_onclick` at a skinshortcuts item removal
  (delete the focused item from the shortcuts DATA + set reloadmainmenu + buildxml
  via a helpers.py action, NOT the HomeMenuNo bool), re-enable `visible_2`,
  relabel. Fragile (skinshortcuts menu surgery - the area behind the 1.0.2x reset
  saga); do it deliberately with real-device verify. Touch points: the
  `ImageWidget` params in `_edit_home` (`tools/skin_transforms.py`) + the
  helpers.py reset/rebuild pattern.

## Standing constraints

- The fleet stays on overlay 1.8.0 until Phase 5; nothing here touches boxes
  before then.
- Every phase: implement -> test -> gate -> QA -> real-device verify -> document
  -> commit. No hardware claim without proof.
