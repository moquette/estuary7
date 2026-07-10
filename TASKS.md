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
- [ ] **Phase 1 - Build pipeline** (NEXT): `tools/skin_transforms.py` (anchored,
      fail-loud transforms: rebrand to skin.estuary7, [B] sweep, Font.xml
      Estuary-weights, the 9-file tweaks, baked defaults, in-skin shortcuts) +
      `tools/build_skin.py` (fetch pinned tarball, transform, deterministic zip,
      double-build byte-compare) + `tests/` (anchor tests, golden parity against
      the shipped modv2plus 1.8.0 resources in
      `~/Code/moquette/tony7bones.github.io/addons/script.tony7bones.modv2plus/resources/xml/`,
      no-bold contracts).
- [ ] **Phase 2 - First release + hosting**: public GitHub repo, `gh release`
      v1.0.0 asset, hosted metadata + repository.json entry + proxy release in
      tony7bones.github.io.
- [ ] **Phase 3 - Device verify**: Office Fire TV side-by-side skin switch,
      screencap parity of every tweak; ATV by eye.
- [ ] **Phase 4 - Setup/library/tests** in tony7bones.github.io (SKIN_ID flip,
      probes simplify, EXPECTED_NET_INSTALLED).
- [ ] **Phase 5 - Fleet migration**: modv2plus 2.0.0 one-shot migrator
      (disarmed first), box-by-box, rollback = one skin switch.
- [ ] **Phase 6 - Retirement + docs**: retire modv2plus, correct the playbook's
      wrong "MIT" license note (upstream = GPL-2.0 code + CC-BY-SA-4.0 art).

## Standing constraints

- The fleet stays on overlay 1.8.0 until Phase 5; nothing here touches boxes
  before then.
- Every phase: implement -> test -> gate -> QA -> real-device verify -> document
  -> commit. No hardware claim without proof.
