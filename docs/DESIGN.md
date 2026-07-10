# Design intent - what Estuary 7 must look like, and why

## The origin (so the taste survives context loss)

On 2026-07-10, tvOS purged ATV2's Kodi caches and the box fell back to the
STOCK Estuary skin bundled inside the app. The owner's reaction, verbatim:
"I love the fonts... thin and very clear system wide", "this is great for my
eyes", "it feels very sharp and modern", and then the directive:
"I do not want bold ANYWHERE."

**The target look is stock Estuary Omega's regular-weight typography, applied
to MOD V2's layout.** When in doubt about a weight decision, the answer is:
whatever stock Estuary renders. Stock Estuary's Default fontset contains ZERO
bold binds - every `*_title` id and `font_MainMenu` is NotoSans-Regular;
emphasis is done by size, not weight.

## The hard-won lesson: bold has THREE sources (a fontset fixes only one)

Learned across modv2plus 1.7.0 -> 1.8.0, the hard way:

1. **Bold font FILES** bound in Font.xml (`NotoSans-Bold.ttf` etc.).
   Fix: re-bind. NotoSans-Bold -> NotoSans-Regular (exact stock-Estuary parity
   for the ids MOD V2 emboldened); RobotoCondensed-Bold -> RobotoCondensed-Light
   for the four media-flag badges (family-internal, metric-safe - do NOT swap
   condensed to a normal-width face, glyph widths would overflow layouts).
2. **`<style>bold</style>` declarations** - FreeType SYNTHESIZES bold
   regardless of the bound file. The 1.7.0 file swap alone left headers bold
   because font10_bold/font12_bold/font37_bold carried style tags.
   Fix: remove the style on UI ids. EXCEPTION: the `lyr*` lyrics faces keep
   theirs (decorative overlay art, not UI chrome).
3. **Literal `[B]..[/B]` markup** baked into ~46 window XMLs - also synthetic
   bold, no fontset can override markup. This is where the PVR "Categories" /
   "Channel groups" headers lived.
   Fix: strip the markup from every XML at build time.

Invariant the tests must hold: **the font-id INVENTORY stays byte-identical to
upstream** - a control whose font id vanishes falls back SILENTLY to font13
(no error, wrong look forever). Only faces/styles/markup change, never ids.

The Arial / Arial Unicode MS / Economica fontsets are alternates nobody runs:
leave them stock.

## Verification checklist (device, not just tests)

Proven look on the Office Fire TV under overlay 1.8.0 (the goldens in
`tests/goldens/` are those exact bytes). Estuary 7 must match it:

- Home main menu labels: regular weight (was NotoSans-Bold 60)
- Settings tiles, list views: regular
- PVR channel list + "Categories" / "Channel groups" headers: regular
  (the markup vector - the one a font-only check misses)
- Media-flag badges: RobotoCondensed-Light
- Live-skin greps after install: zero `[B]` in xml/, zero `<style>bold` on
  non-`lyr*` ids in the Default fontset

## Everything else the fork carries (the pre-existing MOD V2++ look)

Thin clock, crisp white nav wordmark, thin side navigation (font13/font12 on
all four left-hand nav columns), Outline HD weather icons, plain
Power/Settings/Search backgrounds, gear-menu reorder, trimmed six-item home
menu, top-bar weather. One opinionated look, no look toggles (the runtime
master switch dies with the overlay; revert = switch skins).
