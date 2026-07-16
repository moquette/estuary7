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

## Post-launch hardening, 1.0.28-1.0.54 (current: 1.0.54 RELEASED 2026-07-15)

- **1.0.54 (2026-07-15) - select opens the OSD on live TV (tvOS)** - owner
  report while watching live IPTV on the ATV: 'single select does not work
  on iptv... nothing happens. maybe is on video or movies'. Diagnosis over
  JSON-RPC against the live stream: upstream maps Siri select (button 5) to
  Pause in FullscreenVideo, but the channel reports canseek=false /
  canchangespeed=false (no timeshift), so Kodi silently swallows Pause - a
  dead button on live TV, while movies pause fine. Fix: one button-5=OSD
  line in the keymap seed's FullscreenLiveTV section (consulted FIRST while
  a PVR channel plays), matching Fire OS where select shows the OSD in
  fullscreen video. Movies/shows keep select=Pause via the FullscreenVideo
  fallback; Fire TV untouched (tvOS-gated writer + SiriRemote-scoped
  mappings). Playbook table updated; selfheal tests pin exactly one id-5
  override inside the live section.

- **1.0.53 (2026-07-15) - REVERT of 1.0.51/1.0.52: Home exit animations
  removed, Home.xml back to stock bytes.** Owner report: 'you broke my
  settings button animation' - the window-level WindowClose slide/fade
  fired on EVERY exit from Home (Settings included, adding 400ms of
  blocked render loop to all Home navigation) while NEVER playing for
  the video handoff it targeted. Root cause, proven from Omega source
  by the architecture agent: Kodi FORCE-CLOSES any window whose
  successor is WINDOW_FULLSCREEN_VIDEO (GUIWindow.cpp:379-380,
  `forceClose |= nextWindowID == WINDOW_FULLSCREEN_VIDEO`), skipping
  the WindowClose animation queue entirely - unpatchable from skin XML
  on the close path. LESSON: window-level WindowClose animations can
  never animate a hand-off INTO fullscreen video, and they tax every
  other exit. If Apple Elegance round 2 is ever revisited, the only
  viable mechanism (source-verified) is: keymap sets a skin bool ->
  Conditional animations on ALL top-level Home groups slide/fade the
  UI out over the live video layer -> a skin timer (Timers.xml) fires
  `FullScreen` + `Skin.Reset` after ~1s. Risks documented in the agent
  report (timer 1s granularity; input lands on invisible Home during
  the window). OWNER DECISION REQUIRED before any retry.

- **1.0.52 (2026-07-15) - the Home exit becomes a SLIDE-OUT (tvOS)** -
  owner reaction to 1.0.51's dissolve: imperceptible ('it just
  disappears... borrow slide-out animations instead of recreating the
  wheel'). Diagnosis: the 260ms fade + 6% zoom DID run but reads as a
  cut over an instantly-visible video surface. Replaced with the skin's
  own slide idiom (sine tween, like the sidebar glide): the whole Home
  UI slides down (0,1080) and fades over 400ms, easing in - a visible
  curtain-drop into the show. Still tvOS-gated; Fire OS stock.

- **1.0.51 (2026-07-15) - 'Apple Elegance' round 1: Home dissolves into
  fullscreen video (tvOS ONLY)** - owner request after living with the
  1.0.50 back-at-Home flow: the hard cut into fullscreen TV should be a
  transition. Two window-level WindowClose animations on Home.xml (fade
  100->0 + zoom 100->106 centered, 260ms sine/out): the whole Home UI
  dissolves and swells toward the viewer as it hands off to the video -
  upstream faded only some background groups, cutting the menu layer.
  BOTH animations carry condition=System.Platform.TVOS (owner directive:
  'the office TV is firetv which shouldn't be touched') - Fire OS keeps
  stock timing, verified by redeploying the gated build to the bench.
  WindowOpen untouched. Golden parity mirrors the insert. 106 tests +
  determinism green. Owner feels the motion on the bedroom ATV after
  the repo update; timing/zoom are one-number tunables for iteration.

- **1.0.50 (2026-07-15) - back at Home returns to the playing video
  (tvOS)** - owner live-tested 1.0.49 on the ATV and it WORKED (back
  from fullscreen kept Family Guy playing through the guide and Home),
  but one more back at Home hit upstream's OTHER Siri mapping: back on
  Home opens the Favourites browser - a blank blue screen on a box with
  no favourites. Owner expectation: back at Home while something plays
  returns to fullscreen. The keymap gains a <Home> section mapping
  button 6 to FullScreen (a no-op when nothing is playing, so idle
  Home-back does nothing instead of surprising). Seed test extended.
  106 tests + determinism green; owner verified LIVE on the ATV (back
  through guide and Home with Family Guy playing; Home-back and double
  play/pause return to fullscreen). Fire TV isolation hardware-proven
  (empty keymaps dir on the office box at 1.0.50). FULL WRITEUP - the
  stock-Kodi contrast, the JSON-RPC-vs-physical-button diagnosis
  method, button-id reference, delivery, revert, maintenance:
  docs/playbooks/tvos-siri-remote-firetv-parity.md (also linked from
  CLAUDE.md and DESIGN.md).

- **1.0.49 (2026-07-15) - Siri remote Fire TV parity for live TV (tvOS
  keymap via the boot service)** - owner-reported: on tvOS, backing out
  of fullscreen live TV STOPS playback; on Fire TV it keeps playing.
  RECON (empirical, both boxes): inside Kodi both platforms keep playing
  (JSON-RPC 'back' proved it live on the ATV); the killer is Kodi's
  SHIPPED customcontroller.SiriRemote.xml, which maps the back/menu
  button (6) to STOP inside FullscreenVideo - and upstream had a reason:
  the Siri remote has NO button that returns to fullscreen (owner got
  stuck exactly there when the stream played in the background). Fix,
  BOTH halves: a userdata keymap (t7b-siriremote.xml) mapping button 6
  to Back in FullscreenVideo + FullscreenLiveTV, and double play/pause
  (21, upstream noop) to FullScreen as the return/toggle gesture; stop
  remains on hold-play/pause and in the OSD. DELIVERY: skins cannot
  ship keymaps, so the skin's boot service writes the file on tvOS
  boxes only (plain open() per the tvOS VFS lesson), idempotent
  (content-compare, reloadkeymaps only on change), strict no-op on
  Android/desktop. fake_kodi gains platform getCondVisibility; two new
  seed tests (tvOS write+idempotence, Android no-op). 106 tests +
  determinism green. Verification: ATV2 updates via the repo, then the
  owner presses back during live TV (playback should continue) and
  double-taps play/pause (fullscreen returns). Also this round: the
  bench debug overlay was disabled with a clean-exit settings flush.

- **1.0.48 (2026-07-15) - power menu order + capitalization - BENCH-
  VERIFIED + RELEASED** - owner refinements on 1.0.47: 'Customize Main
  Menu' now LEADS the power menu (above Skin Settings) and is title-cased
  via a literal label (owner asked; matches the adjacent 'Skin Settings';
  the localization loss is nil since 1.0.44 trimmed to English only). The
  power-menu contract test now pins the pair's order, actions, and the
  dialog.close-before-action rule for both items. Also: the bench box's
  debug overlay (owner-side, NOT the build) was disabled properly - the
  first attempt was silently discarded by a deploy force-stop (the
  settings-clobber class), the fix used Application.Quit for a clean
  settings flush. 104 tests + determinism green; screencap-verified.
  1.0.47 was never released standalone (superseded same hour by the
  order/case swap); ATV2 self-updated 1.0.39 -> 1.0.46 via the repo
  today, and gets 1.0.48 the same way.

- **1.0.47 (2026-07-15) - power-menu 'Customize main menu' + lyrics-font
  log-spam fix - BENCH-VERIFIED, not yet released** - (1) owner request:
  a second fork item in the power menu, directly below 'Skin Settings',
  in all three display modes: 'Customize main menu' (stock label 31306,
  loose extras/icons/controlpanel.png per the 1.0.29 tvOS icon rule)
  opening the skinshortcuts menu editor via
  RunScript(script.skinshortcuts,type=manage&group=mainmenu) -
  skinshortcuts is a hard manifest import, so no InstallAddon guard.
  Verified end to end on the bench: power menu shows Skin Settings /
  Customize main menu / Exit, and selecting it loads
  script-skinshortcuts.xml (log-proven; a first attempt LOOKED broken -
  landed in the Videos window - but was input interference, the clean
  retest passed). (2) Bench-caught 1.0.44 regression: trimming
  fonts/lyrics/ left the lyr* definitions binding missing files - ~40
  GUIFontManager::LoadTTF errors at EVERY skin load. New
  repoint_lyrics_fonts (called from transform_font_xml, mirrored in
  golden normalization) re-points the DEFAULT fontset's lyrics
  <filename>s at NotoSans-Regular; alternates stay byte-stock
  (test_nobold invariant), font-id inventory untouched. Verified: zero
  lyrics font errors on the post-deploy boot. NOTE: the bench box had
  Kodi's debug overlay enabled during this round (not by the build;
  owner-side) - handy for the log proofs, owner can disable in
  Settings > System > Logging.

- **1.0.46 (2026-07-15) - weather icons BAKED IN + Skin Settings declutter -
  BENCH-VERIFIED, not yet released** - two owner directives in one version:
  (1) "Can the outline icons be our default weather icons baked in? e.g. no
  extra downloads": braz's Outline HD set (CC BY 3.0, Erik Flowers'
  weather-icons; vendored into assets/weather/ from
  bryanbrazil/resource.images.weathericons.outline-hd @5644804, tarball
  sha256 0c92d66..., 49 PNGs = FanartCode 0-47 + na, LICENSE.txt ships at
  extras/weather/LICENSE.txt, credited in ATTRIBUTION.md) now ships AT
  upstream's stock special://skin/extras/weather/ default path (add_assets
  replaces the dir the 1.0.44 trim used to delete); all 5 default texture
  sites are skin-local (the Includes.xml rewrite is GONE - upstream's path
  stands - and Includes_Home's 4 fallbacks now point local); the outline-hd
  import LEFT the manifest (ship-contract check inverted to assert its
  absence + the baked na.png present). The Artworks pane's weather-icon
  pack CHOOSER stays (generic resource-type filter; a user-picked installed
  pack still overrides the baked default). (2) Extras/Home menu declutter:
  the splash CLUSTER (Enable Splash Screen toggle 503 + gated sub-rows
  504/505), the "Enable themes" toggle (506, artless since the 1.0.44
  trim), and the "Kodi/Distribution Logo" chooser (10023, "It should only
  be Kodi") all leave Skin Settings; stale flags keep being honored by
  their consumers, and the office box was verified to carry NONE. Gates:
  104 tests (weather test rewritten for the baked inventory; golden parity
  gains a reverse weather pair + three block-deletion pairs replacing the
  splash/themes rename pairs; ShowSplashScreen/EnableThemes REPLACEMENT
  counts re-baselined) + determinism green. Bench: pushed 5 changed files
  - the new extras/weather dir (50 files), verified live: top-bar weather
    icon renders from the BAKED set, Extras pane has no splash/themes rows,
    Home menu pane opens at "Minimize main menu" with no logo chooser.
    RELEASED 2026-07-15: GitHub release v1.0.46 (created owner-side ~8min
    after the commit - the catalog work published it; asset sha256
    download-verified IDENTICAL to the lock) with notes bundling
    1.0.44-1.0.46, and the hosted metadata bumped in the shared repo by
    the catalog commit 381d3fa ('feat(catalog): ship estuary7 1.0.46').
    1.0.44 and 1.0.45 were never released standalone; the fleet jumps
    1.0.43 -> 1.0.46.

- **1.0.45 (2026-07-15) - pvr.artwork dependency dropped - BENCH-VERIFIED,
  not yet released** - owner-approved after a full binding audit: the
  `script.module.pvr.artwork` import leaves the manifest entirely (it had
  been optional since 2026-07-10). Evidence: the office bench NEVER had the
  module installed and nobody noticed - every one of the skin's ~80
  pvr.artwork references is defensive (AddonIsEnabled-guarded RunScripts in
  the PVR next-up popup; emptiness-guarded Window(Home).Property(PVR.
  Artwork.*) reads everywhere else), so the skin renders stock PVR labels
  without it. KEPT: all skin XML guards byte-for-byte (upstream parity,
  zero cost), the SkinSettings "PVR Artwork" toggle (one-click InstallAddon
  opt-in), and the hosted mirror in tony7bones.github.io that serves it.
  KEPT: resource.images.weathericons.outline-hd (owner asked - it is
  load-bearing: 5 active texture refs for the deliberate Outline HD look,
  and it resolves from Kodi's OFFICIAL repo, zero hosting burden).
  FLAG FOR THE STATIC-CONVERSION CREW (shared repo, not touched here):
  bootstrap `_install_skin` still direct-extracts pvr.artwork (+ its
  requests/simplecache deps) on fresh installs - that step can be removed
  now that the skin neither requires nor imports it. Gates: 104 tests
  (rebrand test flipped to assert the import ABSENT) + determinism green.
  Bench: manifest-only delta pushed, Kodi restarted, skin enabled + active
  on 1.0.45 - on a box that never had the module, the exact scenario the
  removal serves.

- **1.0.44 (2026-07-15) - trim round two - BENCH-VERIFIED, not yet
  released** - full-tree audit (sizes + reference greps + live box-settings
  checks), owner-approved item by item. Zip 26.2MB -> 20.9MB, tree 37M ->
  29M. TRIM_PATHS gains 24 entries: extras/weather (196K, zero refs since
  the Outline HD switch), fonts/NotoSans-Bold.ttf (356K, zero refs since
  the no-bold rebind), xml/Custom_1120_SourcesDialog.xml (dead since Media
  sources moved to Skin Settings), extras/epg-genres (4.9MB - the EPG
  genre-artwork mode; owner: "no one uses it"; the sidebar genre-colors
  cycle drops mode 20190 via `_edit_includes_mediamenu` so it cannot be
  selected into blankness, and stale 20190 values reset on the next click),
  fonts/lyrics (844K karaoke faces; Font.xml keeps the lyr* id inventory),
  5 seasonal theme art dirs (936K; the EnableThemes machinery stays,
  background.jpg + t7b-splash.jpg survive), and 14 non-English locales
  (~860K; en_gb ships, Kodi falls back to it anyway). DELIBERATELY KEPT
  (audited, referenced): extras/patterns (pattern13 renders unconditionally
  in dialogs), extras/backgrounds (the opt-in shortcut-background toggles),
  extras/home-images, Textures.xbt (repack = high risk, low reward),
  alternate fontsets (prior decision), resources/ screenshots. Gates: 104
  tests (new `test_trim_round_1044`: survivors present, cycle rewired,
  lyr ids intact) + determinism green. Bench round: pushed the 2 changed
  files AND rm -rf'd the 24 trimmed paths on-device (adb pushes never
  delete; repo-path updates replace the whole addon dir so the fleet needs
  no such step), device tree 29M matches the build; home + PVR guide
  screencap-verified clean. Pending: release on owner word.

- **1.0.43 (2026-07-15) - POV search toggle renamed and moved - BENCH-
  VERIFIED, not yet released** - owner refinement on 1.0.42: the toggle is
  now "Enable POV search" and sits just above "Enable background of 'Power
  options' shortcut" (anchor: upstream radiobutton 10006) instead of below
  the Search-background pair. Setting name unchanged (`use_pov_search`), so
  boxes keep their state across the update. 103 tests + determinism green;
  golden parity mirror updated. Bench-verified: toggle rendered at the new
  position, still ON from the owner's testing. RELEASED 2026-07-15: GitHub
  release v1.0.43 (asset sha download-verified), proxy metadata bumped
  (single-file commit 92750cd; synced the shared repo first - the other
  crew had pushed 2d5f46d in the interim), raw URL confirmed 1.0.43,
  office proxy cache busted.

- **1.0.42 (2026-07-15) - POV search toggle - BENCH-VERIFIED, not yet
  released** - owner-designed via interview before any code: "Use POV
  search" (radiobutton 1104, Home menu pane after the Search-shortcut
  background pair, visible only while plugin.video.pov is installed AND
  enabled, default OFF = zero settings writes). ON = the home Search popup
  (Custom_1107_SearchDialog) swaps its four provider items for POV's four
  search entries - Movies / TV Shows / People / Movies Collection (TMDb),
  labels and search_history routes read live from the box's POV
  navigator.search menu; each opens POV's search-history page (owner
  decision). Wiring: new `_edit_searchdialog` (FILE_EDITS 23 -> 24) gates
  each stock item on `![use_pov_search + AddonIsEnabled(pov)]` and appends
  the four POV items with the affirmative - the popup always shows exactly
  four entries, and a vanished POV falls back to stock silently (panel
  items re-evaluate visibility live; no include conditions anywhere).
  Gates: 103 tests (new `test_pov_search_toggle_wired`; anchors count and
  golden parity updated) + determinism green. Bench round (office Fire TV,
  screencap-verified end to end): stock popup with toggle off; toggle
  rendered in place and flipped via the real GUI; popup showed POV's four
  entries; selecting Movies opened POV's search page (NEW SEARCH...).
  Toggle left ON on the bench box per owner testing. RELEASED 2026-07-15
  (owner: "deploy", carrying the unreleased 1.0.41 with it): GitHub release
  v1.0.42 (asset sha256 download-verified against the lock), proxy metadata
  bumped (tony7bones.github.io 8d6bacf - a SINGLE-FILE commit; the static-
  conversion crew's work had just landed as 5d8fe81 and local was synced
  before touching anything, per the owner's "folks working on the repo"
  heads-up), raw URL confirmed serving 1.0.42, office proxy cache busted.
  v1.0.41 was never released standalone - its tag/commit exist but the
  fleet jumps 1.0.40 -> 1.0.42. atv2 and the fleet update through the repo
  at the owner's leisure.

- **1.0.41 (2026-07-15) - the Movies & TV Shows label opt-out, DONE RIGHT -
  BENCH-VERIFIED, not yet released** - owner asked for the withdrawn 1.0.40
  sub-toggle back, now that the architecture allows it: "Do not apply labels
  to Movies & TV Shows" (radiobutton 1103 under "Show labeled tiles", beside
  the PVR sub-option, visible only while the parent is on; writes
  `hide_video_tile_labels`, default OFF = the shipped 1.0.40 look,
  zero settings writes). ON = the fork fade + label hide per item on DBType
  movie/set/tvshow/season/episode, leaving the clean poster; music/genre/
  category labels unaffected. Safe where the first attempt failed: the gate
  is a third `<visible>` term on the fork's OWN fade/label controls - the
  poster art renders identically either way, so no include-condition split
  exists to desynchronize. Ship delta vs 1.0.40: SkinSettings.xml +
  Includes_Home.xml + addon.xml. Gates: 101 tests (new
  `test_video_label_optout_toggle_wired`: 12 gated controls, SkinSettings
  sole writer, Includes_Home+SkinSettings sole readers) + determinism green;
  golden parity mirrors the toggle insert. Bench round (office Fire TV):
  cleared the STALE `hide_video_tile_labels=true` left in the box's
  addon_data settings.xml by the morning's withdrawn attempt (edited while
  Kodi was STOPPED, per the settings-clobber playbook), then verified all
  three states by screencap: default OFF = 1.0.40 look pixel-parity; flag ON
  = clean bare posters on movie tiles; and the REAL GUI path - focused the
  1103 toggle in Skin Settings, Input.Select via JSON-RPC - flipped labels
  back live, no reload. NOTE for the fleet: any box that ran the withdrawn
  morning build may carry the same stale flag; harmless on 1.0.39/1.0.40
  (nothing reads it), but 1.0.41 will honor it - those boxes would boot
  with movie labels hidden until the toggle is flipped once. Only the
  office bench ever ran it (flag now cleared there).

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
