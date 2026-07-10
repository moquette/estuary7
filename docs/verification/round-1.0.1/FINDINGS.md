# 1.0.1 stock-alignment round - Office Fire TV, 2026-07-10

Seven owner-directed tweaks toward THE FIRST MANDATE, each cycle:
transform + tests + bench push + owner eyes-on. Zip sha256 in
`skin_build.lock`; full narrative in `docs/PLAN.md` (1.0.1 round).

| #   | Tweak                                                                                                                                | Evidence                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| 1   | Custom "Estuary 7" settings tab removed; toggle moved to General below "Disable zoom effect" as "Show system info on Settings focus" | `e7-101-cat-order.jpg` (toggle visible in pane; no 11th category)           |
| 2   | System-info overlay skin line reads "Estuary 7" + own version                                                                        | owner-verified on the TV                                                    |
| 3   | Skin Settings categories in stock Estuary order (General first, opens on General)                                                    | `e7-101-cat-order.jpg`                                                      |
| 4   | MOD V2 wordmark removed from SkinSettings + media-menu blade                                                                         | `e7-101-skinsettings-nologo.jpg`, `e7-101-blade-nologo.jpg`                 |
| 5   | Skin-chooser artwork = original Estuary icon/fanart (vendored, Team Kodi)                                                            | byte-asserted in tests; owner-verified                                      |
| 6   | Header bullet chips (frame/puce.png) removed at all 8 sites, labels flush                                                            | `e7-101-nobullets-home.jpg`                                                 |
| 7   | Skin no longer lists under Program add-ons                                                                                           | `still-listed.jpg` (before); JSON-RPC executable-node listing clean (after) |

Final state: `e7-101-final-home.jpg` - clean 1.0.1 full-tree install.

## Finding: <provides> cannot hide a script extension from Program add-ons

Kodi's `addons://sources/executable/` browser node (which feeds the home
"Program add-ons" widget row and the add-on browser section) buckets ANY
add-on carrying an `xbmc.python.script` extension by TYPE - an empty
`<provides></provides>` only cleans content queries
(`Addons.GetAddons(content=executable)`), proven live on the bench. The
working fix: ship NO script extension (stock Estuary ships none) and invoke
the helper bridge by file path - `RunScript(special://skin/scripts/helpers.py,...)`

- at all 15 call sites. helpers.py is addon-context-free, verified live
  (Home's onload getKodiSetting populated its window property).

## Bench soak state at round close

Estuary 7 1.0.1 active (clean full-tree install of the release bytes).
`script.tony7bones.modv2plus` and `skin.estuary.modv2` both DISABLED but
installed - frozen rollback (re-enable + switch, no downloads), no
auto-update clobber possible while disabled. This is the fleet's intended
end-state, soaking on the bench ahead of Phase 5.
