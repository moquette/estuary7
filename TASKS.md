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
- [ ] **Phase 5 - Fleet migration**: modv2plus 2.0.0 one-shot migrator
      (disarmed first), box-by-box, rollback = one skin switch.
- [ ] **Phase 6 - Retirement + docs**: retire modv2plus, correct the playbook's
      wrong "MIT" license note (upstream = GPL-2.0 code + CC-BY-SA-4.0 art).

## Menu-reset incident (1.0.2x, RESOLVED 2026-07-12)

"Reset main menu settings" did not restore items the user had disabled/hidden in
the Customize main menu editor - only a full Apple TV reboot did. Root-caused and
fixed on the bench ATV (192.168.1.162) after a multi-session, ~2-day dig. Two
independent bugs:

1. **tvOS xbmcvfs vs real-path split** - the reset cleaned menu files via
   `xbmcvfs` on `special://` paths, but skinshortcuts reads/writes them with
   real `translatePath` + Python `open`/`ETree`, and on tvOS the two APIs see
   different bytes in-session. The reset now uses real-path `os`/`open`.
2. **Stuck `skinshortcuts-isrunning` on Window(10000)** - survives ReloadSkin
   and addon toggles, only a reboot clears it; a stale True makes every rebuild a
   no-op. The reset now clears it.

Fixed in 1.0.23 (reset), 1.0.24 (blank Videos editor/tile icon: overrides
`videos` labelID was `DefaultAddonVideo.png` -> `icons/sidemenu/videos.png`),
1.0.25 (removed the temporary diagnostics). Live TV/Radio kept visible via
seeded `donthidepvr=true`. FULL WRITEUP + prevention checklist:
`docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md`. Also captured in
`CLAUDE.md` (Runtime gotchas). These fixes ship to the ATV via the proxy; the
6-box fleet is untouched (still Phase 5-gated).

## Bench state (Office Fire TV 192.168.7.162)

- Since 2026-07-10 (1.0.1 tweak round): Estuary 7 ACTIVE; BOTH
  `script.tony7bones.modv2plus` AND `skin.estuary.modv2` DISABLED (deliberate
  end-state soak - the fork standing with zero overlay machinery). Both stay
  INSTALLED: modv2plus 1.8.0 is the future Phase 5 migrator, and the MOD V2
  skin dir keeps the applied overlay + .baks frozen (disabled add-ons do not
  auto-update, so no Kodinerds clobber is possible). Rollback = re-enable
  both, switch skins - seconds, no downloads. The other six boxes keep
  everything enabled until Phase 5.

## Deferred / revisit later

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

## Standing constraints

- The fleet stays on overlay 1.8.0 until Phase 5; nothing here touches boxes
  before then.
- Every phase: implement -> test -> gate -> QA -> real-device verify -> document
  -> commit. No hardware claim without proof.
