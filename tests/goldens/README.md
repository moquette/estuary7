# Goldens - the proven desired bytes

Vendored from `script.tony7bones.modv2plus` **1.8.0** (the last overlay
release, hardware-verified on the Office Fire TV and ATV2 on 2026-07-10).
These are the AUTHORITATIVE reference for what the transforms must produce:

- `xml/` - the 9 shipped skin XMLs (incl. the no-bold Font.xml). Phase 1's
  golden-parity tests compare transform output against these, modulo the
  skin-id rename and the removed master-toggle plumbing.
- `skinshortcuts/` - the menu DATA + properties set (ships in the fork's
  `shortcuts/` dir; the `.properties` file gets re-keyed to skin.estuary7).
- the wordmark PNG (`media/extras/` in the fork).

Vendored deliberately: modv2plus is RETIRED in Phase 6, so these bytes must
not be referenced across repos. Do not edit by hand - they are evidence, not
source. The source of truth for future changes is `tools/skin_transforms.py`.
