# Phase 3 device-verify findings - Office Fire TV, 2026-07-10

Estuary 7 **1.0.0** (zip sha256 `8c77c853fb1a...`, see `skin_build.lock`)
verified on the instrumented bench box (192.168.7.162, Fire TV, Kodi 21
Omega), driven over adb + JSON-RPC. Baseline = MOD V2 + overlay 1.8.0,
captured in the SAME session on the SAME box minutes before the switch.
Committed record: `TASKS.md` Phase 3 entry and `docs/PLAN.md` Phase 3 log.

Screenshots here are the evidence, downscaled to 1280px JPEG for the repo;
parity judgments were made against the full-resolution originals during the
session.

## Parity checklist (DESIGN.md verification list -> evidence)

| Check                                                                                             | Result                     | Evidence                                                                                                          |
| ------------------------------------------------------------------------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Home: six-item menu, regular weight                                                               | PASS                       | `baseline-home.jpg` vs `e7-home-widgets.jpg`                                                                      |
| Nav wordmark (hi-res white, extras/logo-text-hires.png)                                           | PASS                       | same pair                                                                                                         |
| Thin clock + top-bar weather + Outline HD icon                                                    | PASS                       | same pair                                                                                                         |
| Plain Power/Settings/Search (no backgrounds, baked default)                                       | PASS                       | same pair                                                                                                         |
| Home widgets (Recently added / Last watched / Files / Update library)                             | PASS after properties seed | `e7-home.jpg` (gap) vs `e7-home-widgets.jpg` (fixed)                                                              |
| Gear menu order: Skin settings first, Media sources demoted                                       | PASS                       | `baseline-settings.jpg` vs `e7-settings.jpg`                                                                      |
| SkinSettings nav column thin (font13)                                                             | PASS                       | `e7-skinsettings.jpg`                                                                                             |
| Our category: "Estuary 7", System Info overlay toggle, breadcrumb, NO master toggle               | PASS                       | `e7-ourcategory.jpg`                                                                                              |
| PVR channel list: regular weight, layout parity                                                   | PASS                       | `baseline-pvr.jpg` vs `e7-pvr.jpg` (pixel-parity incl. the item-index column, which is NOT ShowPVRChannelNumbers) |
| Power menu: Classic list on a FRESH skin (PowerMenuList expression bake)                          | PASS                       | `e7-powermenu.jpg`                                                                                                |
| Boot: no splash (opt-in ShowSplashScreen bake), boots to Home                                     | PASS                       | observed on restart; skin persisted                                                                               |
| Live-skin greps: zero `[B]` in xml/, zero bold binds + zero non-lyr style-bold in Default fontset | PASS                       | adb greps on the installed skin, session log                                                                      |
| Revert = one skin switch back to MOD V2, overlay intact                                           | PASS                       | `reverted-home.jpg`                                                                                               |

## Finding 1 - skinshortcuts properties MUST be seeded (hardware-confirmed)

Fresh Estuary 7 renders the six-item menu (the skin-shipped `shortcuts/` DATA
defaults ARE consumed) but **no widgets**: the Movies pane showed Kodi's
"library empty" prompt (`e7-home.jpg`). Cause, predicted in Phase 1 from the
skinshortcuts source: `<skinid>.properties` is read ONLY from
`addon_data/script.skinshortcuts/`, never from the skin.

Fix validated on the box: push `assets/shortcuts/skin.estuary7.properties` to
`addon_data/script.skinshortcuts/skin.estuary7.properties`, delete
`skin.estuary7.hash`, restart. Widgets then match the baseline exactly
(`e7-home-widgets.jpg`).

**Consequence: Phase 4's `_install_skin` and Phase 5's migrator MUST perform
this seed + hash drop.** On truly fresh boxes the modv2plus-era unprefixed
DATA files in addon_data will not exist either; the skin's shipped defaults
cover the menu itself (proven here), the properties seed covers the widgets.

## Finding 2 - the skin-switch confirm race, reproduced live

The first `Settings.SetSettingValue(lookandfeel.skin, skin.estuary7)` went
live, then script.skinshortcuts' FIRST menu build for the new skin ended in a
ReloadSkin that destroyed the "Keep this skin?" confirm (window 10100) before
it could be accepted; Kodi treated that as No and reverted
(`switch-confirm.jpg` shows the mid-build blank home in Estuary 7 dress).
This is the exact race `tony7bones.system.activate_skin` hardens against.

Bench workaround (this Kodi build exposes NO ExecuteBuiltin over JSON-RPC, so
`SendClick(11)` is not reachable remotely): wait until the new skin's
`xml/script-skinshortcuts-includes.xml` exists (first build done), re-assert
the setting, poll `Window.IsVisible(10100)` every 250ms, then
`Input.Right` + `Input.Select` (confirm focus defaults to No; Yes is control
11 to its right). Held through the settle window both directions.

**Consequence: Phase 5 keeps using the in-Kodi `activate_skin` verbatim, as
already locked in the plan. The remote recipe above is bench tooling only.**

## Finding 3 - upstream MOD V2 logo artwork survives in SkinSettings (FLAGGED)

The Skin Settings window shows upstream's "ESTUARY MOD V2" wordmark artwork
in the bottom-left (`e7-skinsettings.jpg`, also visible in
`e7-ourcategory.jpg`). It is a skin-internal texture the rebrand transforms
never touched. Per DESIGN.md this is MOD V2 branding NOT on the deliberate
deviation list, so it is flagged for the owner: candidate 1.0.1 transform
(swap for an Estuary 7 mark, or drop the image). Decision pending.

## Finding 4 - fleet auto-update lag (operational note)

The bench box was found running modv2plus 1.6.3 although 1.7.0/1.8.0 shipped
earlier the same day; Kodi's repo-update cadence had not picked them up.
Pushed 1.8.0 directly (adb + boot rescan) so the baseline was the proven
1.8.0 overlay. Worth remembering in Phase 5 rollout timing: "shipped" is not
"on the boxes" until Kodi's updater has cycled (or the box is driven).

## Box end state / open items

- Box: MOD V2 + overlay 1.8.0 active (fleet-standard), Estuary 7 1.0.0
  installed alongside + enabled, properties seeded (inert under MOD V2),
  modv2plus at 1.8.0.
- OPEN: ATV by-eye check (tvOS cannot screenshot) - owner's call.
- OPEN: Finding 3 decision (MOD V2 logo artwork in SkinSettings).
