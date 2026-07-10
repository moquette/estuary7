# Estuary 7

A fork-by-build of the Kodi skin [Estuary MOD V2](https://github.com/b-jesch/skin.estuary.modv2)
(Omega branch) for the Tony.7.Bones fleet: one opinionated look - thin,
sharp, Estuary-weight fonts everywhere ("no bold anywhere"), a trimmed home
menu, crisp wordmark, reordered settings, Outline HD weather icons - applied
at **build time** to a **pinned upstream commit** and shipped as a complete
skin, `skin.estuary7`.

This replaced a runtime patch add-on that rewrote 50+ skin files on every box
at boot. Same look, zero runtime machinery: what we build is what runs,
byte-for-byte.

## How it works

```
skin_build.lock                 # pinned upstream SHA + version + zip sha256
tools/skin_transforms.py        # every customization as an anchored, fail-loud transform
tools/build_skin.py             # fetch pinned upstream -> transform -> deterministic zip
tests/                          # anchor tests, golden parity, no-bold contracts
```

Rebasing onto a newer upstream = bump the SHA in `skin_build.lock` and
rebuild; any transform whose anchor no longer matches fails the build by name.

## Distribution

Built zips are published as GitHub Release assets here and served to the
fleet by the Tony.7.Bones repository proxy
([tony7bones.github.io](https://github.com/tony7bones/tony7bones.github.io)).

## Provenance and license

This is honest derived work: Estuary by phil65/Team Kodi, MOD by Guilouz,
Omega maintenance by b-jesch. Code GPL-2.0, artwork CC-BY-SA-4.0 - see
`LICENSE` (upstream's, verbatim) and `ATTRIBUTION.md`.
