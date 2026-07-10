# Design intent - what Estuary 7 must look like, and why

## THE FIRST MANDATE (owner, 2026-07-10)

**Estuary 7 keeps the look and feel AS CLOSELY AS POSSIBLE to ORIGINAL (stock)
Estuary - with thin fonts everywhere.** That is the objective; everything else
is subordinate to it.

What this means in practice:

- **Stock Estuary is the visual reference, not MOD V2.** MOD V2 is the code
  base we build from (for its functional mods), but whenever a visual choice
  arises - a weight, a size, a color, a layout detail - the answer is:
  whatever original Estuary does, rendered thin.
- **Every visual deviation from stock Estuary must be DELIBERATE and listed**
  (the curated set at the bottom of this file: wordmark, trimmed menu, gear
  order, Outline HD weather, plain backgrounds, top-bar weather). Anything MOD
  V2 changed visually that is NOT on that list is a candidate to revert toward
  stock during transform work - flag it, ask the owner, do not silently keep it.
- **Thin fonts everywhere** is the one place we go beyond stock: stock Estuary
  already has zero bold binds in its Default fontset, and we ALSO kill the
  synthetic bold vectors (style tags, [B] markup) so nothing renders bold at
  all.

## The origin (so the taste survives context loss)

On 2026-07-10, tvOS purged ATV2's Kodi caches and the box fell back to the
STOCK Estuary skin bundled inside the app. The owner's reaction, verbatim:
"I love the fonts... thin and very clear system wide", "this is great for my
eyes", "it feels very sharp and modern", and then the directive:
"I do not want bold ANYWHERE."

That moment became THE FIRST MANDATE above: original Estuary's look and feel,
as closely as possible, thin everywhere. When in doubt about ANY visual
decision, the answer is: whatever stock Estuary renders. Stock Estuary's
Default fontset contains ZERO bold binds - every `*_title` id and
`font_MainMenu` is NotoSans-Regular; emphasis is done by size, not weight.

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

## The deliberate deviations from stock Estuary (the COMPLETE list)

Per THE FIRST MANDATE, these are the ONLY intended visual departures from
original Estuary. Anything else MOD V2 changed visually is a candidate to
revert toward stock - flag it during transform work, ask the owner:

- Thin clock; crisp white nav wordmark
- Thin side navigation (font13/font12 on all four left-hand nav columns)
- Outline HD weather icons; top-bar weather
- Plain Power/Settings/Search backgrounds
- Gear-menu reorder; trimmed six-item home menu (skinshortcuts)
- MOD V2's FUNCTIONAL mods (PVR integration, widgets, custom windows) stay -
  the mandate is about look and feel, not features

One opinionated look, no look toggles (the runtime master switch dies with
the overlay; revert = switch skins).

## Flagged deviations awaiting an owner decision

Found during transform/verify work per the rule above (flag, ask, never
silently keep):

- **Upstream "ESTUARY MOD V2" logo artwork in the SkinSettings window**
  (bottom-left wordmark texture; also elsewhere upstream binds it). Found in
  Phase 3 device verify - see
  `docs/verification/phase3/FINDINGS.md` Finding 3. MOD V2 branding, not on
  the deviation list. Options: swap for an Estuary 7 mark, revert to stock
  Estuary's artwork, or drop the image. Candidate 1.0.1 transform.
