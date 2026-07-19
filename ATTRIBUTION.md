# Attribution

Estuary 7 (`skin.estuary7`) is a build-time fork of **Estuary MOD V2**
(`skin.estuary.modv2`), rebuilt from a pinned upstream commit with the
Tony.7.Bones customizations applied at build time. It exists because of the
work of others:

- **Estuary** - the original Kodi skin by **phil65 and Team Kodi**
- **Estuary MOD V2** - the MOD by **Guilouz**, Matrix+ continuation by **PvD**
- **Omega maintenance** - **b-jesch** (the pinned upstream source:
  <https://github.com/b-jesch/skin.estuary.modv2>, `Omega` branch)
- **Weather icons** (`extras/weather/`, the skin's baked-in default set) -
  **Outline HD Weather Icons** by **braz** (vendored from
  <https://github.com/bryanbrazil/resource.images.weathericons.outline-hd>,
  commit `5644804`), based on the **weather-icons** project by
  **Erik Flowers** (<http://erikflowers.github.io/weather-icons/>). Licensed
  **Creative Commons Attribution 3.0** (the pack's LICENSE.txt ships
  alongside the icons at `extras/weather/LICENSE.txt`).

## Licenses (inherited, unchanged)

- Code: **GNU General Public License v2.0**
- Artwork: **Creative Commons Attribution-ShareAlike 4.0**

See `LICENSE` (upstream's license file, kept verbatim). This repository is
public to satisfy GPL source availability. The complete corresponding source is
three things, and all three are required to reproduce the shipped zip
byte-for-byte:

1. the pinned upstream commit (`upstream_sha` + `upstream_tarball_sha256` in
   `skin_build.lock`),
2. the transforms and build in `tools/`, and
3. the vendored assets in `assets/` (the wordmark, the stock Estuary
   icon/fanart/screenshots and Videos glyph, the Outline HD weather set with
   its LICENSE.txt, the splash art, and the pre-built skinshortcuts includes).

The build is deterministic (`python3 tools/build_skin.py --check` builds twice
and byte-compares), so anyone can reproduce the published release asset from
these three inputs.

Upstream copyright headers in skin files are never removed by the build.
