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

- Thin clock; crisp white nav wordmark, centered ◆KODI in the blade like
  original Estuary (conditional +70 slide when the menu is full; the lone
  diamond re-centers over the icon column when minimized - MOD V2 default)
- Thin side navigation (font13/font12 on all four left-hand nav columns)
- Outline HD weather icons; top-bar weather. Since 1.0.46 the icons are
  BAKED IN (owner directive 2026-07-15: "no extra downloads"): braz's
  Outline HD set (CC BY 3.0, Erik Flowers' weather-icons; credited in
  ATTRIBUTION.md) is vendored at extras/weather/ and every default
  weather-icon path is skin-local - the outline-hd resource-pack import is
  gone from the manifest. The WeatherIcons pack chooser still overrides
  the default when a user picks an installed pack.
- Plain Power/Settings/Search backgrounds
- Gear-menu reorder. HOME MENU (owner directive 2026-07-12): ships STOCK
  Estuary's default item set/order and stays fully editable (skinshortcuts).
  The shipped default (shortcuts/mainmenu.DATA.xml) keeps Live TV/Radio
  ALWAYS-visible like stock by seeding skinshortcuts' `donthidepvr=true` (boot
  service + reset helper); numeric window ids do NOT work (skinshortcuts
  normalises them back and injects System.HasPVRAddon). The Videos item uses
  ORIGINAL Estuary's film-strip icon, not MOD V2's redrawn film-reel (1.0.27):
  upstream's `<icon labelID="videos">` override is REMOVED (any skinshortcuts
  icon override that resolves to a skin image draws BLANK in the menu editor -
  its gui.py setArt uses the literal string 'icon'; livetv/radio survive because
  their Default* overrides are not skin images), and because Kodi's loader
  checks Textures.xbt BEFORE loose files, the build renames the bundled
  icons/sidemenu/videos.png entry in place (shadow_videos_texture) so Kodi falls
  back to the loose stock videos.png the build ships at
  media/icons/sidemenu/videos.png (vendored from xbmc/xbmc). "Reset main menu
  settings" restores this default - see
  docs/playbooks/skinshortcuts-reset-tvos-vfs-split.md for the tvOS reset fix.
- System page (Settings.xml) redesigned back toward stock Estuary (owner
  directive 2026-07-10, bench-verified on the Office Fire TV): upstream's
  single scrolling 5-column panel becomes a stock-style 4x3 grid - a fixed
  top utility row (File manager, Add-ons, System info, Event log), a
  "Settings" divider, then one non-scrolling block of eight tiles. Skin
  Settings takes the slot upstream gave Games (games are unused on the
  fleet and stock only shows that tile conditionally). No scrollbar.
- MOD V2's "Media sources" quick-launcher leaves the System page and moves
  into Skin Settings > Extras as an "Add media sources" section (header +
  Videos/Music/Pictures/Games file-browser buttons) directly above the
  Debug section. The Custom_1120 dialog is now unreferenced (harmless dead
  weight; the buttons open the file browsers directly).
- Boot splash: NO splash on a fresh box (owner directive 2026-07-12: the
  flag is a plain opt-in `ShowSplashScreen`), and since 1.0.46 there is NO
  Skin Settings switch for it either (owner directive 2026-07-15: the
  Extras pane loses the "Enable Splash Screen" toggle and its two gated
  splash-background sub-rows). Startup.xml still honors a ShowSplashScreen
  a box set before the toggle vanished; the splash art, when enabled, is
  the owner's background.jpg (extras/themes/t7b-splash.jpg). (History: the
  1.0.32 round had restored a default-ON splash; 2026-07-12 flipped it to
  opt-in; 1.0.46 removed the switch.)
- Skin Settings declutter (owner directives 2026-07-15, 1.0.46): the
  "Enable themes" toggle is gone (1.0.44 trimmed the seasonal art, so it
  could only enable artless themes; the EnableThemes expressions stay
  inert), and the Home menu pane's "Kodi/Distribution Logo" chooser is
  gone ("It should only be Kodi" - the fork ships the stock Kodi wordmark
  and offers no LibreELEC/CoreELEC variants; the MenuLogo* bools stay
  unset so the default renders).
- Labeled home widget tiles: poster items render POSTER + LABEL (owner
  directive 2026-07-15, bench-verified same day, 1.0.40). MOD V2's labeled
  tile design (InfoWallMusicLayout) is a square-fit thumb over a dark panel -
  a portrait poster fit into that square leaves dark side bars, and the
  generic 'Widget' include's itemlayout ALSO stacked it on top of
  InfoWallMovieLayout's full-bleed poster (upstream forgot the mutually
  exclusive condition its own focusedlayout and WidgetListPoster carry) - so
  our labeled default shipped a "double poster with side bars" the owner
  rejected. The fork splits the labeled tile PER ITEM in the generic Widget
  and WidgetListPoster layouts: items WITH poster art draw
  InfoWallMovieLayout's clean poster with the label riding the poster's
  bottom 70px (font12, year per the stock hide_pubyear split) on a dark fade
  band (overlays/overlayfade.png full strength, 150px tall, spanning the
  drawn poster width - darker and taller than InfoWallMovieLayout's
  episode-count band per owner taste, bench-tuned 2026-07-15); items WITHOUT
  (music, genres, categories) keep the stock square look byte-for-byte.
  1.0.41 adds an owner-requested opt-out: "Do not apply labels to Movies &
  TV Shows" (radiobutton 1103 under "Show labeled tiles", beside the
  PVR-info sub-option, default OFF). ON = the fork fade + label hide on
  video-library items (DBType movie/set/tvshow/season/episode) per item,
  leaving the clean poster; everything else keeps its label. Safe where the
  withdrawn first attempt was not: the gate rides `<visible>` terms on the
  fork's own controls - the poster art renders identically either way.
  WidgetPanelPoster keeps its stock design (labels on focus only, no
  stacking bug). ENGINEERING RULE (hardware-learned, see TASKS.md 1.0.40):
  the per-item split rides `<control type="group">` visibility - NEVER
  include conditions, which Kodi resolves once at window load with no item
  context.
- POV search (owner request 2026-07-15, 1.0.42; renamed/moved 1.0.43):
  "Enable POV search" (radiobutton 1104, Home menu pane, just above "Enable
  background of 'Power options' shortcut"; visible only while
  plugin.video.pov is installed AND enabled). ON =
  the home Search popup (Custom_1107) swaps its four provider items (local
  library / add-ons / YouTube / TheMovieDB) for POV's four search entries
  (Movies / TV Shows / People / Movies Collection (TMDb), each opening
  POV's search-history page) - same dialog design, different items. Every
  popup item re-checks the toggle AND System.AddonIsEnabled live, so a
  removed POV falls back to the stock popup silently. Default OFF = stock
  popup, zero settings writes.
- tvOS Siri remote: Fire TV parity for playback (owner directives
  2026-07-15, 1.0.49/1.0.50) - a deliberate BEHAVIORAL deviation from
  stock Kodi, which stops playback on back in fullscreen and offers no
  return-to-fullscreen gesture on the Apple TV. The fork's boot service
  writes a userdata keymap on tvOS boxes only: back exits fullscreen with
  playback continuing, back at Home and double play/pause return to
  fullscreen, stop stays on hold-play/pause and in the OSD. Full record,
  root cause, and maintenance notes:
  docs/playbooks/tvos-siri-remote-firetv-parity.md
- Personal-widget panes animate per ITEM (owner report 2026-07-16, 1.0.55) -
  a deliberate BEHAVIORAL deviation from upstream MOD V2, whose
  PersonalWidgetList/Panel template keys the pane fade+slide on the focused
  item's `widget` property CHANGING: two menu items that both carry
  owner-picked widgets (the fleet's Movies and TV Shows, both POV widget
  rows) swap panes with a hard cut, while a move to any other pane type
  animates. The fork gates each generated pane instance on its own item
  (submenuVisibility) and gives it upstream's Vis_FadeSlide_Right_Delayed_
  Home structure VERBATIM - a per-item-keyed Conditional (delayed fade +
  slide in from the right, reversing out on exit) plus the verbatim Hidden
  (1.0.56; the 1.0.55 Visible/Hidden translation lost the reversal and was
  owner-rejected). Same-pane and cross-pane switches measure identical on
  30fps frame analysis. Hardware-proven root cause and forensics: TASKS.md
  1.0.55/1.0.56 entries.
- MOD V2's FUNCTIONAL mods (PVR integration, widgets, custom windows) stay -
  the mandate is about look and feel, not features

One opinionated look, no look toggles (the runtime master switch dies with
the overlay; revert = switch skins).

## Flagged deviations and their decisions

- **addon.xml authorship line** (owner directive 2026-07-10, v1.0.3):
  `provider-name` is **Tony.7.Bones alone**. Upstream authors (Guilouz,
  PvD / b-jesch, phil65, Team Kodi) never consented to authorship billing, so
  they are credited as THANKS in `<description>` and `ATTRIBUTION.md`, never
  in the "by" line. Skin-info screenshots are original Estuary's (Team Kodi),
  not MOD V2's branded set.

Found during transform/verify work per the rule above (flag, ask, never
silently keep):

- **Upstream "ESTUARY MOD V2" logo artwork** (the `dialogs/logo.png`
  wordmark: SkinSettings bottom-left + the media-menu side blade). Found in
  Phase 3 device verify - see `docs/verification/phase3/FINDINGS.md`
  Finding 3. **DECIDED 2026-07-10: removed from BOTH windows** - stock
  Estuary shows nothing in either spot (verified against stock
  SkinSettings.xml and Includes_MediaMenu.xml: zero logo references).
  Bench-verified in the 1.0.1 round.
