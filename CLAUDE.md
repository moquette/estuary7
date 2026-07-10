# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What this repo is

**Estuary 7** (`skin.estuary7`) is a fork-by-build of the Kodi skin
`skin.estuary.modv2` (b-jesch / Kodinerds, Omega branch) for the Tony.7.Bones
fleet (Kodi 21 "Omega": 5 Fire TV boxes + 2 Apple TVs). This repo owns the skin
build end-to-end; it ships a complete, rebranded skin zip built from a PINNED
upstream commit plus our transforms. Nothing here runs on a box at runtime -
the entire point of this project is that the fleet's former runtime patch
machinery (`script.tony7bones.modv2plus`: boot service, markers, version
sentinels, [B] sweep, wedge-defense shell) gets DELETED once migration
completes.

**Distribution stays in the sibling repo** `~/Code/moquette/tony7bones.github.io`
(the virtual proxy `repository.tony7bones`): the built zip is uploaded as a
GitHub Release asset on THIS repo, and the proxy's `repository.json` points at
it (the proxy engine supports `release_asset://` and plain https zip URLs and
streams in chunks, so the ~94MB zip never enters git).

Full phase plan and decision record: `docs/PLAN.md`. **The design intent - what
the skin must LOOK like and why (the owner's font directive, the three bold
vectors, the verification checklist) - is `docs/DESIGN.md`; read it before any
transform work.** The proven desired bytes are vendored in `tests/goldens/`
(from overlay 1.8.0, hardware-verified). The patch-era lessons live in the
sibling repo's `docs/playbooks/modv2plus-dev-cycle-and-lessons.md`.

## The build contract

- **THE FIRST MANDATE: as close as possible to ORIGINAL (stock) Estuary, with
  thin fonts everywhere.** Stock Estuary is the visual reference, not MOD V2;
  every visual deviation must be on the deliberate list in `docs/DESIGN.md`.
  A MOD V2 visual change not on that list gets flagged to the owner, never
  silently kept.
- **Pin by SHA.** Upstream (b-jesch/skin.estuary.modv2, `Omega` branch) has no
  usable tags. `skin_build.lock` records `{upstream_sha, upstream_version,
our_version, zip_sha256}`. Rebase = bump the SHA, rebuild, review anchor
  failures.
- **Anchored transforms, fail loud.** Every customization in
  `tools/skin_transforms.py` asserts its anchor string exists in the upstream
  file. A missing anchor is a BUILD ERROR that names the file - never a silent
  partial ship. (The patch era once shipped a Nexus-era Home.xml onto an Omega
  skin; this contract is why that cannot recur.)
- **Deterministic packaging.** Sorted paths, 1980-01-01 zip timestamps (same
  discipline as the sibling repo's `_tools/generate_repo.py`). `build_skin.py`
  builds twice and byte-compares; the zip sha256 is recorded in the lock.
- **No bold anywhere** (owner directive): the build strips `[B]`/`[/B]` markup
  from every XML, rewrites Font.xml to Estuary weights (NotoSans-Regular for
  the `*_title` ids + `font_MainMenu`; RobotoCondensed-Light flags), and
  neutralizes `<style>bold</style>` on UI font ids (lyrics faces excepted).
- **Zero settings writes on a fresh box.** Defaults are baked into XML
  conditions (the opt-out `!Skin.HasSetting()` pattern); skinshortcuts menu
  defaults ship inside the skin's `shortcuts/` dir.

## License obligations (non-negotiable)

Upstream is **GPL-2.0 (code) + CC-BY-SA-4.0 (artwork)** - NOT MIT. This repo
must remain public (source availability), keep `LICENSE`, and credit b-jesch,
Guilouz, and Team Kodi in `ATTRIBUTION.md` and the skin's addon.xml. Never
strip upstream copyright headers.

## Commands

```bash
python3 tools/build_skin.py            # fetch pinned upstream, transform, package
python3 tools/build_skin.py --check    # build twice, byte-compare (determinism gate)
python3 -m pytest tests/ -q            # transform anchors, golden parity, sweep contracts
```

## House rules (inherited from the fleet's workflow)

- implement -> TEST -> gate -> adversarial QA -> REAL-DEVICE verify -> document
  -> only then commit/release. No "fixed in code" claims without hardware proof
  (Office Fire TV 192.168.7.162 is the instrumented bench; tvOS boxes cannot
  screenshot).
- No AI attribution anywhere; no em dashes in written deliverables.
- The fleet is exposed ONLY during the Phase 5 migration (see docs/PLAN.md),
  one box at a time; rollback is always one skin-switch back to stock MOD V2
  (repository.kodinerds still serves it).
