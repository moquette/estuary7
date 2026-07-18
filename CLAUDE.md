# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## MANDATORY: markdown house style

Before writing or editing ANY `.md` file in this tree, follow the
**`markdown-house-style`** skill at
`~/Code/moquette/kodi/.claude/skills/markdown-house-style/SKILL.md`. It is the
single standard for all five checkouts and every agent, with no exceptions.

Non-negotiable summary:

- No em dash, en dash, horizontal bar, robot emoji, or AI attribution anywhere.
  The plain hyphen `-` is always fine.
- Never begin a wrapped line with `+`, `-`, or `*`. CommonMark turns it into a
  list item and splits your paragraph.
- Never let an inline code span cross a line break. It strips the
  list-continuation indent and leaves the next agent editing a stale copy.
- Markdown is deliberately NOT auto-formatted here (removed from
  `~/.claude/hooks/auto-format` on 2026-07-18, because prettier's markdown
  printer relocates content between block containers). Do not add it back.

## READ FIRST: start at `TASKS.md`

**`TASKS.md` is this project's task index** and holds every open item: the two
owner-reported hardening issues from 2026-07-17, the deferred design items, the
flagged-but-unfixed upstream typos, and the full release history. Until
2026-07-18 this file did not point at it, so an agent reading only `CLAUDE.md`
was never routed to the tracker.

`docs/PLAN.md` is the phase plan and `docs/DESIGN.md` is the design intent;
both are still required reading before transform work. But neither is the open
task list. **`TASKS.md` is.**

Note the status contradictions recorded at the top of `TASKS.md` before you
trust any version number in this repo: the tracker's section headings, its
bench-state block, and its release entries disagree with each other about what
is current. `skin_build.lock` and `git log` are the load-bearing facts.

## HARD CONSTRAINT - the office Fire TV is hands-off

The office Fire TV at `192.168.7.162` is HANDS-OFF. Never adb, JSON-RPC, ping
or otherwise contact it without explicit per-instance owner permission. The
bedroom Fire TV at `192.168.7.84` is the sanctioned JSON-RPC target. Carry this
prohibition into any subagent prompt you write.

This supersedes the "instrumented bench" language further down in this file and
in `TASKS.md`, `docs/PLAN.md` and `docs/verification/phase3/FINDINGS.md`. Those
predate the rule and describe how the box WAS used; they are not authorization
to use it now.

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

**Distribution stays in the sibling repo** (remote
`tony7bones/tony7bones.github.io`, local checkout `~/Code/moquette/kodi/repo`;
the standalone path `~/Code/moquette/tony7bones.github.io` that older docs cite
DOES NOT EXIST, verified 2026-07-18)
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

## tvOS Siri remote behavior is FORK-AUTHORED, not stock

Stock Kodi on Apple TV stops playback when back is pressed in fullscreen
and has no return-to-fullscreen gesture. The fork's boot service writes a
userdata keymap on tvOS boxes (back keeps playback running; back-at-Home
and double play/pause return to fullscreen). Before touching the service,
the keymap payload, or diagnosing "remote misbehaves" reports, read
`docs/playbooks/tvos-siri-remote-firetv-parity.md` - including the
JSON-RPC-vs-physical-button diagnosis method that found it.

## Runtime gotchas (skinshortcuts + tvOS) - READ BEFORE TOUCHING THE RESET

The skin ships a `scripts/helpers.py` `resetMenu` action (injected by
`tools/skin_transforms.py`) that restores the stock skinshortcuts menu. Two
hard-won lessons, fully written up in
`docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md` (resolved 1.0.23/1.0.24):

- **tvOS `xbmcvfs` vs real-path split.** On Apple TV, `xbmcvfs` operations on
  `special://` paths do NOT reliably affect the same bytes that Python
  `open()`/`ElementTree` on the `translatePath`'d real path sees, IN-SESSION.
  `script.skinshortcuts` reads/writes its menu data with real paths, so any
  skin-side file work that skinshortcuts must observe (delete/copy/write of
  `addon_data/script.skinshortcuts/*` or the generated
  `xml/script-skinshortcuts-includes.xml`) MUST use `xbmcvfs.translatePath(...)`
  plus `os`/`open`, never `xbmcvfs` on `special://`. Verify with the SAME API the
  consumer uses. `xbmcvfs.delete` can return True on a file that still exists;
  `xbmcvfs.copy` may not overwrite. This cost ~2 days across multiple sessions.
- **Stuck `skinshortcuts-isrunning` guard.** `build_menu` no-ops if
  `Window(10000).Property(skinshortcuts-isrunning)=="True"`. That property
  survives `ReloadSkin()` and an addon disable/enable; only a reboot (or explicit
  `clearProperty`) clears it. A menu that "won't rebuild until a reboot" is this.
  Clear it before firing a build.

Also: `donthidepvr=true` (seeded by the boot service + reset) is the only lever
that keeps Live TV/Radio visible like stock - numeric window ids do NOT work
(skinshortcuts normalises them back and injects `System.HasPVRAddon`).

## House rules (inherited from the fleet's workflow)

- implement -> TEST -> gate -> adversarial QA -> REAL-DEVICE verify -> document
  -> only then commit/release. No "fixed in code" claims without hardware proof.
  (Historical note: the Office Fire TV 192.168.7.162 WAS the instrumented bench
  and most of the recorded verification came from it. It is now HANDS-OFF, see
  the constraint at the top of this file. tvOS boxes cannot screenshot. There
  is currently no designated replacement bench for this project; raise it with
  the owner rather than improvising a target.)
- No AI attribution anywhere; no em dashes in written deliverables.
- STALE, kept for context: "The fleet is exposed ONLY during the Phase 5
  migration (see docs/PLAN.md), one box at a time." **Phase 5 was DROPPED as a
  project by owner decision on 2026-07-15** (`TASKS.md:67-76`): boxes switch to
  Estuary 7 manually, one at a time, at leisure, and `script.tony7bones.modv2plus`
  is deprecated. `docs/PLAN.md` was never updated for that drop and still
  documents Phase 5 as live with a 2.0.0 migrator; do not build from it.
  Rollback is still always one skin-switch back to stock MOD V2
  (repository.kodinerds still serves it).
