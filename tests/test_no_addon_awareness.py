"""The skin does not know EZ Maintenance++ exists.

Owner rule: Estuary has no backup feature and does not control EZM. A skin that
reads an add-on's ListItem property, references its id, or names it anywhere is
a coupling that ships in the skin zip and then rots the moment the add-on stops
setting it - which is exactly what 1.0.77 did.

This is the boundary held from the SKIN side, so it fails at build time here
rather than as dead markup on a box. Three strings, no allowlist: the built
tree carries none of them, in file contents or in path names.
"""

from __future__ import annotations

FORBIDDEN = ("ezm.", "ezmaintenance", "script.ezmaintenanceplusplus")


def _hits(tree):
    found = []
    for path in sorted(tree.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(tree).as_posix()
        blob = path.read_bytes()
        for needle in FORBIDDEN:
            if needle in rel:
                found.append((rel, needle, "path", 1))
            count = blob.count(needle.encode("utf-8"))
            if count:
                found.append((rel, needle, "content", count))
    return found


def test_built_tree_never_mentions_the_addon(built):
    hits = _hits(built.tree)
    assert not hits, "the skin must not know the add-on exists: {}".format(hits)
