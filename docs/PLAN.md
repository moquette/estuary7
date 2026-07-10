# Estuary 7 - fork-by-build the MOD V2 skin as a standalone project

## Context

Today the fleet installs the third-party skin `skin.estuary.modv2` (b-jesch/Kodinerds,
~94MB, auto-updated on boxes DIRECTLY from repo.kodinerds.net) and our add-on
`script.tony7bones.modv2plus` rewrites 50+ of its files at runtime (9 shipped XMLs +
a 42-file `[B]` sweep + Font.xml), with a boot service, markers, version sentinels,
and a wedge-defense shell to survive upstream clobbers. After the 1.8.0 bold sweep,
"patch" is a fiction: we maintain a fork and apply it on every box at boot.

The original patch-vs-fork decision (recorded in
`docs/playbooks/modv2plus-dev-cycle-and-lessons.md:24-42`) was right at the time, but
two facts have flipped it:

1. **Divergence**: 50+ files rewritten, one opinionated look, master switch rarely used.
2. **Upstream is dormant for our fleet**: b-jesch's development moved to Kodi 22
   ("Piers"); the Omega branch our Kodi-21 fleet tracks is maintenance-only. "Ride
   upstream for free" now mostly delivers unreviewed changes landing on the fleet with
   a stock-flash window: risk, not fixes.

The playbook itself names the chosen path: "Fork-by-build (the hybrid to remember if
we ever reconsider): keep our changes as deltas, apply them at build time to the
latest MOD V2, ship the result as our own rebranded skin."

**Owner decision (2026-07-10):** fork-by-build, as a NEW standalone repository at
`~/Code/moquette/estuary7` - a learning project that owns the skin build end-to-end.
tony7bones.github.io remains the distribution channel. End state: all runtime patch
machinery deleted; skin updates come only from us.

**Verified enablers** (do not re-litigate):

- The proxy engine already supports large external zips: `release_asset://` handling at
  `addons/repository.tony7bones/lib/repository.py:137,322-334` + plain-https asset URLs,
  streamed in 16KB chunks - so the ~94MB zip lives in GitHub Release assets, never in git.
- License: upstream is **GPL-2.0 (code) + CC-BY-SA-4.0 (artwork)** - a rebranded fork is
  permitted with attribution + license retained. (The playbook's "MIT" note at line 42
  is WRONG and gets corrected in Phase 6.)
- `repository.kodinerds` must stay installed on boxes (pinned in the base closure,
  `_tools/test_modular_setup.py:542`, and serves script.skinshortcuts +
  image.resource.select), so keeping the same skin id would be a permanent version race.
  **New id: `skin.estuary7`** (from the project name; display "Estuary 7", provider
  credits b-jesch / Guilouz / Team Kodi).

## What does NOT change during this project

The fleet keeps running overlay 1.8.0 (just shipped, hardware-verified). Nothing
regresses while phases 0-4 proceed; boxes are only touched in Phase 5, one at a time,
each with a one-command rollback.

---

## Phase 0 - Scaffold the estuary7 project (first work session there)

Create `~/Code/moquette/estuary7`:

- `git init` (branch `main`), `.gitignore` (`build/`, `upstream-cache/`, `__pycache__/`,
  `.pytest_cache/`, `dist/`)
- `CLAUDE.md` - project instructions: what the repo is, the build contract, the
  relationship to tony7bones.github.io (distribution) and the fleet, the license
  obligations (GPL-2.0 + CC-BY-SA-4.0, attribution file), pin-by-SHA policy
- `docs/PLAN.md` - this plan carried over as the project's phase log (the repo is where
  planning continues, per owner)
- `LICENSE` / `ATTRIBUTION.md` - GPL-2.0 text + credits (b-jesch, Guilouz, Team Kodi)
- `README.md` - what Estuary 7 is, honest provenance
- Groundwork checks (read-only):
  - Pin the upstream: identify the exact commit SHA on b-jesch/skin.estuary.modv2
    `Omega` branch that matches the live skin (diff against the Office box copy at
    `/sdcard/.../addons/skin.estuary.modv2/`); record in `skin_build.lock`
  - Verify the proxy's `request()` (`addons/repository.tony7bones/lib/utils.py`)
    follows GitHub's 302 redirect for release-asset downloads; if not, use the
    `release_asset://` API form instead of plain URLs

## Phase 1 - Build pipeline (the heart of the project, ~2-3 days)

In estuary7:

- `tools/skin_transforms.py` - every customization as an **anchored transform** that
  FAILS LOUD when its anchor is missing (upstream drift = build error, not silent
  wrongness - this kills the recorded "Nexus-era Home.xml shipped onto Omega" bug class):
  1. Rebrand: addon.xml (id `skin.estuary7`, our version scheme starting 1.0.0, news,
     provider, keep the `<requires>` closure + add outline-hd weather icons); global
     rename of `skin.estuary.modv2` in `RunScript(...)`/paths
  2. Bold sweep: port `sweep_bold_markup` (tony7bones.github.io
     `addons/script.tony7bones.modv2plus/default.py:164-206`) over ALL XMLs at build time
  3. Font.xml: the Estuary-weight rewrite (NotoSans-Bold to Regular for `*_title` +
     `font_MainMenu`; RobotoCondensed-Bold to Light flags; `<style>bold</style>`
     neutralized on UI ids) - regenerated from stock each build
  4. The 9-file tweaks (overlay gate, wordmark, gear-menu order, clock, our Skin
     Settings category with per-item toggles - the master Apply/Restore toggle is
     REMOVED; revert UX = switch skin to stock MOD V2 from Kodinerds)
  5. Bake defaults into XML conditions (the opt-out `!Skin.HasSetting()` house pattern)
     so a fresh box needs ZERO settings writes; retarget the weather-icon fallback to
     Outline HD
  6. Ship the 17 skinshortcuts menu files inside the skin's `shortcuts/` dir
     (skin-provided defaults; they are skin-agnostic except the one `.properties` file);
     loose media into `media/extras/`
- `tools/build_skin.py` - fetch pinned upstream tarball (verify sha256 against
  `skin_build.lock`), run transforms, package **deterministically** (reuse the zip
  discipline from tony7bones.github.io `_tools/generate_repo.py:121-160`: sorted paths,
  1980 timestamps; build twice + byte-compare; record `zip_sha256` in the lock)
- `tests/` - pytest: per-transform anchor tests, golden-parity check (the transformed
  9 files must be semantically identical to the currently shipped modv2plus copies,
  modulo id rename + removed master-toggle plumbing - copy those goldens in as
  fixtures), determinism test, no-`[B]`/no-style-bold sweep contracts (port from
  `_tools/test_modv2plus.py`)
- Rebase story, made real: bump the SHA in `skin_build.lock`, rebuild; anchor failures
  enumerate exactly what upstream changed.

## Phase 2 - First release + hosting (~1 day)

- Create the public GitHub repo (`moquette/estuary7`; public is required for GPL
  source availability AND anonymous asset downloads), push.
  **Owner decision (2026-07-10):** moquette, not tony7bones - the tony7bones
  GitHub user's credentials are not on this machine (gh CLI + SSH both auth as
  moquette). A later transfer to tony7bones is safe: GitHub redirects git,
  release, and asset URLs after a transfer.
- `gh release create v1.0.0` + upload `skin.estuary7-1.0.0.zip` as the asset
- In tony7bones.github.io: `addons/hosted/skin.estuary7/{addon.xml,icon.png,fanart.jpg}`
  (small, in-tree) + `repository.json` entry (asset_prefix pointing at the raw hosted
  path; zip pointing at the estuary7 release-asset URL) - the manifest is baked, so
  this is a **proxy release via `release.py --proxy`**
- Verify end-to-end: the zip 200s through a local proxy instance

## Phase 3 - Device verify (~1-2 days)

Office Fire TV (192.168.7.162): install Estuary 7 ALONGSIDE the overlaid MOD V2,
switch with the hardened `activate_skin`
(`addons/script.module.tony7bones/lib/tony7bones/system.py:145` - reuse verbatim, do
not reimplement), screencap-parity every documented tweak (gate overlay, wordmark,
clock, fonts incl. PVR headers, six-item menu, weather icons, gear order, our
category). Reboot cycles. ATV2 by eye (tvOS cannot screenshot).
Rollback: switch back to `skin.estuary.modv2` - the overlay is still installed and its
service still re-applies.

## Phase 4 - Setup/library/tests in tony7bones.github.io (~2-3 days)

- Flip `SKIN_ID` at `setup/skin.py:55` + `bootstrap/default.py:247` (probes import from
  skin.py); `_install_skin` direct-extracts the Estuary 7 zip from the release URL
  (proxy-invisible to the closure resolver, same pattern as modv2plus today), then
  installs skinshortcuts/image.resource.select/outline-hd/pvr.artwork as now; the
  activate-LAST orchestrator seam stays untouched
- Probes simplify: `skin_done` = installed + active (drop `_modv2plus_fully_applied`)
- Tests: `test_setup_skin.py`, `test_setup_probes.py`, `EXPECTED_NET_INSTALLED`
  (`test_modular_setup.py:532`), `test_no_fork.py`, `modular_setup_snapshot.json`
- Library + bootstrap ship via `release.py` lockstep as usual

## Phase 5 - Fleet migration (~1-2 days elapsed, box-by-box)

- Ship `script.tony7bones.modv2plus` **2.0.0** as a one-shot MIGRATOR (boxes already
  auto-update it): if Estuary 7 active, stay inert; else download+extract the fork zip,
  rescan+settle+enable, copy `addon_data/skin.estuary.modv2/settings.xml` to
  `addon_data/skin.estuary7/`, write the re-keyed skinshortcuts `.properties`, restore
  stock MOD V2 files from `.bak`s, remove sentinels, then `activate_skin(skin.estuary7)`
  gated on GUI-idle
- Stage it: 2.0.0 ships DISARMED (manual `migrate` argv only); drive each box via
  ADB/JSON-RPC (tvOS via devicectl + the RunScript bridge), verify per box; then 2.1.0
  arms auto-migrate as the sweep-up net
- Rollback per box: one skin-switch back to stock MOD V2 (Kodinerds still serves it);
  2.0.0 keeps the overlay apply code intact as the escape hatch until all 7 confirm

## Phase 6 - Retirement + docs (~1-2 days)

- Retire modv2plus (proxy manifest removal via proxy release; `EXPECTED_NET_INSTALLED`
  - `test_no_fork.py` updated)
- tony7bones.github.io docs: rewrite the playbook decision record (patch to fork, WHY,
  and the license correction MIT to GPL-2.0 + CC-BY-SA-4.0), CLAUDE.md skin section,
  TASKS.md track record; estuary7 `docs/PLAN.md` phase log kept current throughout
- New release loop documented: estuary7 `build_skin.py`, then `gh release`, then bump
  the hosted addon.xml in tony7bones.github.io, then boxes auto-update

## Verification (per the house workflow, every phase)

- estuary7: its own pytest suite green + double-build determinism before any release
- tony7bones.github.io: full `pytest _tools/ -q` + ruff + regen gates on every change
- Real-device verify before every fleet-facing step (Office box first, always);
  screenshots + kodi.log; no "fixed in code" claims without hardware proof
- Phase 5 is the only fleet-exposed phase; one box at a time, rollback = one skin switch

## Key decisions locked

| Decision                    | Choice                                                                    |
| --------------------------- | ------------------------------------------------------------------------- |
| Architecture                | Fork-by-build (deltas applied at build time to pinned upstream)           |
| Home                        | NEW standalone repo `~/Code/moquette/estuary7` (owner directive)          |
| Skin id / name              | `skin.estuary7` / "Estuary 7" (new id - no Kodinerds version race)        |
| Upstream pin                | Commit SHA on b-jesch Omega branch, in `skin_build.lock` (no usable tags) |
| Hosting                     | GitHub Release assets on the estuary7 repo (no git bloat, no 100MB limit) |
| Versioning                  | Ours, from 1.0.0                                                          |
| Master switch               | Removed; revert = switch to stock MOD V2 via Kodi's skin chooser          |
| Runtime machinery end state | Deleted (service, markers, sentinels, sweep, shell)                       |

Estimated total: ~8-12 working days across both repos, fleet exposed only in Phase 5.
First concrete step on approval: Phase 0 scaffold of `~/Code/moquette/estuary7`.

---

## Phase 0 - COMPLETE (2026-07-10)

Scaffold created (git, CLAUDE.md, LICENSE verbatim from upstream, ATTRIBUTION,
README, this plan). Groundwork results:

- **Upstream pinned:** `8d9b2c7c304c6f0226cd40e24819061c6165a6ec` = 21.4+omega.4.
  Evidence: addon.xml + the stock `.bak` snapshots of Home.xml, Font.xml,
  Includes_PVR.xml, DialogPVRChannelGuide.xml on the Office Fire TV all
  md5-match this commit. Tarball sha256 in `skin_build.lock` (97MB).
- **Upstream has already moved:** Omega head is 21.4+omega.5 (`15e10710`).
  The fleet has NOT received it yet - live proof of the unreviewed-update
  hazard the fork eliminates. The omega.4->omega.5 rebase is the fork's first
  deliberate exercise AFTER the baseline ships, not part of the baseline.
- **Redirect check PASSED:** the proxy's `request()`
  (tony7bones.github.io `addons/repository.tony7bones/lib/utils.py:50`)
  follows GitHub's cross-host 302 (github.com -> codeload.github.com, status
  200, streaming read OK). Plain https release-asset URLs are usable in
  `repository.json`; `release_asset://` stays as fallback.

Next: Phase 1, the build pipeline (`tools/skin_transforms.py` + `tools/build_skin.py` + tests).

---

## Phase 1 - COMPLETE (2026-07-10)

The pipeline builds `dist/skin.estuary7-1.0.0.zip` (94MB, sha256 recorded in
`skin_build.lock`); `--check` double-builds byte-identically; 70 tests green.

What shipped, and the decisions made inside the phase:

- **Transforms** (`tools/skin_transforms.py`): 15 per-file anchored edit
  functions + addon.xml rebrand + global id rename (24 files) + [B] sweep
  (46 files - matching the patch era's known blast radius) + the Font.xml
  Default-fontset rewrite (11 NotoSans-Bold and 5 RobotoCondensed-Bold
  re-binds, 3 UI style-bold neutralized, lyrics faces kept, id inventory
  byte-identical - all counts asserted). Every anchor miscount raises
  TransformError naming the file.
- **Baked defaults**: every skin setting the runtime overlay wrote is now an
  inverted opt-out/opt-in condition, so a fresh box needs zero writes:
  `show_weatherinfo`->`hide_weatherinfo`, `EnableSplashScreen`->opt-in
  `ShowSplashScreen`, `DisableThemes`->opt-in `EnableThemes`,
  `enable_*_background`->`show_*_background`, six widget `hide_*`->`show_*`,
  power menu Classic-list default via a new `PowerMenuList` expression (the
  three `powermenu_*` bools and their SelectBool picker survive untouched;
  `ShowPVRChannelNumbers` needed no bake - unset already means hidden).
  Weather icons: the four `weathericons.default` fallbacks + the top-bar
  texture retarget to Outline HD, and addon.xml gains the
  `resource.images.weathericons.outline-hd` import (floor 0.0.1; Kodinerds
  serves it to the fleet already).
- **Our Skin Settings category**: item 11 + grouplist 1100 with the header
  and the System Info overlay toggle only. The master Apply/Restore toggle,
  its display mirror (`t7b_patch_on`), the dual thin/bold nav labels, and the
  `System.AddonIsEnabled(script.tony7bones.modv2plus)` gate are all gone.
- **Assets** (`assets/`): the 15 menu DATA files + the properties file
  re-keyed to `skin.estuary7.properties` + the wordmark PNG, seeded from
  `tests/goldens/` (which stay pristine as test fixtures; a test asserts
  byte-parity between the two). Upstream's `overrides.xml`/`template.xml`
  and untouched DATA files survive alongside ours.
- **skinshortcuts finding (matters in Phases 4/5)**: verified against the
  Omega `script.skinshortcuts` 2.0.3 source: group DATA files ARE read from
  the skin's `shortcuts/` dir as defaults, but `<skinid>.properties` is read
  ONLY from `addon_data/script.skinshortcuts/`. The shipped re-keyed
  properties file is therefore inert until Setup's `_install_skin` (Phase 4)
  or the 2.0.0 migrator (Phase 5) copies it into addon_data. Phase 3 device
  verify must check the menu builds correctly from DATA-only on a fresh box
  (widget defaults may fall back to `overrides.xml`).
- **Golden parity** (`tests/test_golden_parity.py`): transform output equals
  the hardware-verified 1.8.0 bytes for all 9 files; the per-file
  normalization table in that test IS the documented divergence record
  (marker comments, id rename, master-toggle removal, baked-default
  inversions). A one-byte mutation test proved the gate bites.
- **Ship contracts in the build itself**: no [B], no upstream id (ATTRIBUTION
  excepted), rebranded addon.xml, outline-hd import, properties + wordmark
  present - violations fail the build before packaging.

Next: Phase 2, first release + hosting (public repo, v1.0.0 release asset,
proxy release in tony7bones.github.io).

---

## Phase 2 - COMPLETE (2026-07-10)

- **Repo**: `https://github.com/moquette/estuary7`, public, main pushed.
  Owner decision recorded above (moquette, not tony7bones - credentials).
- **Release**: `v1.0.0` with `skin.estuary7-1.0.0.zip` (94MB) as the asset.
  Anonymous download verified byte-identical to the build
  (sha256 `8c77c853fb1a...`, matches `skin_build.lock`).
- **Hosting**: tony7bones.github.io `addons/hosted/skin.estuary7/`
  (addon.xml with the screenshot list stripped - the proxy would 404 the
  unhosted PNGs - plus `resources/icon.png` + `resources/fanart.jpg`, which is
  where the engine resolves `asset_prefix + <relative asset path>`), and the
  repository.json entry with
  `zip: https://github.com/moquette/estuary7/releases/download/v{version}/{id}-{version}.zip`.
  Shipped as **proxy release 2.2.7** (release.py --proxy: bump, regen, tag,
  push, live Pages verify, KodiShare mirror sync - all green).
- **End-to-end proof, engine-level** (not just curl): instantiated the actual
  `lib/repository.py` Repository against the shipped manifest and (a) streamed
  the full zip - 98,631,598 bytes, sha256 matches the build; (b) generated
  `addons.xml` lists `skin.estuary7 1.0.0` with the complete requires closure
  incl. `resource.images.weathericons.outline-hd`; (c) addon.xml / icon /
  fanart all 200 via the live hosted path.
- Fleet impact: additive only. Boxes' proxies self-update to 2.2.7 and start
  SERVING Estuary 7; nothing installs it until Phase 3 (bench box, manually).

Next: Phase 3, device verify on the Office Fire TV (192.168.7.162): install
Estuary 7 alongside the overlaid MOD V2, switch with the hardened
`activate_skin`, screencap-parity every documented tweak, reboot cycles,
fresh-box menu-widget check (the skinshortcuts properties caveat), ATV by eye.

---

## Phase 3 - COMPLETE on the bench box (2026-07-10); ATV by-eye still open

Office Fire TV (192.168.7.162), driven over adb + JSON-RPC. The box was found
mid-playback (live TV); owner approved interrupting.

**Install path used (bench equivalent of Phase 4's direct-extract ritual):**
adb push of the built tree into `.kodi/addons/` + Kodi restart (boot rescan
registers new local add-ons, disabled) + `Addons.SetAddonEnabled`. Found the
box still on modv2plus 1.6.3 (auto-update lag); pushed 1.8.0 the same way and
its boot service re-applied, giving the true 1.8.0 overlay baseline first.

**The skin-switch confirm race, reproduced live:** the first
`Settings.SetSettingValue(lookandfeel.skin)` went live, then skinshortcuts'
first-build ReloadSkin destroyed the "Keep this skin?" confirm -> auto-revert
(the exact failure `activate_skin` hardens against; JSON-RPC exposes no
ExecuteBuiltin on this build, so the bench can't call it). Once the includes
file existed (build done ~10s), the re-asserted switch + fast poll +
Input.Right/Input.Select accept held. Phase 5 must keep using the in-Kodi
`activate_skin` (SendClick(11) + quiescence wait), which handles all of this.

**Parity, screencapped against the same-session 1.8.0 baseline:** home (six
thin menu items from our shipped DATA, hi-res wordmark, thin clock, top-bar
weather with outline icon, plain shortcut icons), gear order (Skin settings
first), thin SkinSettings nav with the "Estuary 7" category (System Info
overlay toggle off, "Estuary 7 settings" breadcrumb, no master toggle), PVR
channel list regular-weight and pixel-parity with baseline, power menu =
Classic list on a fresh skin ($EXP[PowerMenuList] bake proven). Live-skin
greps on device: zero `[B]` across xml/, zero bold face binds and zero non-lyr
`<style>bold</style>` in the Default fontset. Survived a Kodi restart
(booted straight into Estuary 7, no splash). Reverted to MOD V2 with one
switch; overlay look intact - rollback exercised in BOTH directions.

**Hardware-confirmed finding (drives Phases 4/5):** on the fresh skin the
six-item menu renders but the Movies pane showed "library empty" - NO widgets

- until `skin.estuary7.properties` was seeded into
  `addon_data/script.skinshortcuts/` (+ hash drop + restart), after which the
  widget row matched the baseline exactly. The seed is MANDATORY in Phase 4's
  `_install_skin` and Phase 5's migrator (and on truly fresh boxes the
  modv2plus-era unprefixed DATA files won't exist either - the skin's shipped
  `shortcuts/` defaults cover the menu itself, as proven here).

**Flagged for owner (DESIGN.md rule - not on the deviation list):** the
SkinSettings window shows upstream's "ESTUARY MOD V2" logo artwork
(bottom-left). Cosmetic, skin-internal texture; candidate transform for a
1.0.1 (swap or drop the logo). Decision pending.

**Box end state:** MOD V2 + overlay 1.8.0 active (fleet-standard), Estuary 7
1.0.0 installed alongside and enabled, properties seeded (inert while MOD V2
is active). ATV2 by-eye check remains open - tvOS cannot screenshot.

Next: Phase 4 - setup/library/tests in tony7bones.github.io (SKIN_ID flip,
`_install_skin` direct-extracts the Estuary 7 release zip + seeds the
skinshortcuts properties, probes simplify, EXPECTED_NET_INSTALLED).
