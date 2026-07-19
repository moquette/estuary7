---
name: tvos-kodi-storage
description: >-
  POINTER ONLY. The canonical tvOS Kodi storage field guide lives at
  ~/Code/moquette/kodi/.claude/skills/tvos-kodi-storage/SKILL.md and covers this
  whole meta-tree including this repo. Read that file. Load BEFORE writing,
  deleting, reading, backing up, or restoring ANY file under special://profile /
  special://userdata / addon_data on Apple TV, and ALWAYS when a bug is
  "saves/works on Fire TV but not Apple TV." Triggers on: Apple TV, atv1, atv2,
  tvOS, NSUserDefaults, Caches purge, xbmcvfs vs open, "file exists but won't
  read", menu/settings revert on restart, duplicate File Manager entries, blank
  image, skinshortcuts menu-save, EZM++ restore reverts custom menu.
---

# POINTER: this skill lives at the meta root

**Canonical file:**
`~/Code/moquette/kodi/.claude/skills/tvos-kodi-storage/SKILL.md`

Read it. The NSUserDefaults shadow model, the vectoring rules, the fix patterns,
the do-not list and the research/verify checklist are all there and only there.

## Why this is a pointer and not a copy

This repo used to carry a full duplicate of that guide. On 2026-07-18 an edit to
the meta-root copy silently made the two diverge, and it was caught only by an
incidental `diff`. Nothing enforces that two copies of a skill stay in sync.

This project has already paid for exactly this failure mode: the add-on source
was hand-synced between two repos for weeks, the copies drifted, and the stale
one kept receiving the real fixes while the other rotted.

A pointer cannot drift.

**Do not restore the full text here.** If the guide needs changing, change the
canonical file at the meta root. Every checkout in this fleet lives under
`~/Code/moquette/kodi`, so that path always resolves.
