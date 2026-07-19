# Goldens - the proven desired bytes

Vendored from `script.tony7bones.modv2plus` **1.8.0** (the last overlay
release, hardware-verified on the Office Fire TV and ATV2 on 2026-07-10).
These are the AUTHORITATIVE reference for what the transforms must produce:

- `xml/` - the 9 shipped skin XMLs (incl. the no-bold Font.xml). LIVE:
  `tests/test_golden_parity.py` compares transform output against these,
  modulo the skin-id rename and the removed master-toggle plumbing.
- the wordmark PNG - LIVE: `tests/test_rebrand_and_assets.py` byte-compares
  the shipped `media/extras/logo-text-hires.png` against it.
- `skinshortcuts/` - ARCHIVE ONLY, referenced by no test and no build step.
  This is the fleet's OLD 14-item trimmed menu DATA plus the modv2plus-era
  `.properties` file. It does NOT describe what ships. Since the 2026-07-12
  owner directive the fork ships UPSTREAM's `shortcuts/` dir stock-aligned by
  `_edit_mainmenu`/`_edit_overrides`/`_edit_template`, and ships NO
  `.properties` file at all - `build_skin.check_contracts()` FAILS the build if
  one ever appears there again. A re-keyed copy of the properties file also
  sits unused at `assets/shortcuts/`. Do not "restore" either set into the
  build; that would revert an owner decision.

Vendored deliberately: modv2plus is RETIRED in Phase 6, so these bytes must
not be referenced across repos. Do not edit by hand - they are evidence, not
source. The source of truth for future changes is `tools/skin_transforms.py`.
