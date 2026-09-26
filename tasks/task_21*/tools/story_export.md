# story_export — VERIFY (P2)

`tools/story_export.py` (231 lines) · `tests/test_round_trip.py`

## What it does
DB → Markdown: one `.md` per entity, frontmatter denormalized from columns + `extra` + `relations`, prose from `sections`. Also writes `project.md` and `.story/memory.md`.

The most intricate tool, and the one you rated as probably fine. Read-only, it mostly holds up.

## Findings

1. **Never deletes stale files.** If an entity is deleted via `story_edit`, its `.md` survives the next export. `story_import` will then happily re-create it. **Delete and export do not compose** — the exact inverse operation is missing. Highest-value fix here.
2. **Variable shadowing in the plot-beat loop** (line 76–82): `rows` is reassigned inside the loop over `rows`. It works because the outer `fetchall()` already completed, but it's a trap for the next edit.
3. **Section order is `ORDER BY rowid`** (line 86) — insertion order, not a defined section order. After an upsert-via-`story_edit`, ordering follows creation history. A stable order needs an explicit ordinal or ordering by `standard_sections()`.
4. **`_frontmatter_for` is a 9-branch if-chain** where `core.entity.columns_for_insert` already encodes the inverse mapping. Two directions of the same mapping, independently maintained — the same class of duplication as `story_import`.
5. **`arc_beat` composite-id derivation is repeated three times** (lines 103, 191, and again in `_columns_for` on the import side). One helper.
6. **`memory.md` write is nested inside the project-entity branch** (line 99–100), so it only happens if a project entity row exists. If the DB somehow lacks one, memory is silently never exported. Low probability, trivially fixed by hoisting.
7. **Only `character` filters `computed` fields out of `extra`** (line 127). Other entity types export computed fields verbatim if they somehow reached `extra`. Asymmetric.
8. **Round-trip is tested** (`test_round_trip.py`, `test_memory_export.py`) — good. The test presumably doesn't cover delete-then-export, which is why #1 survives.

## Work
1. Delete the `.md` for entities no longer in the DB (or write into a clean temp tree and swap). Pairs with `story_import`'s wipe semantics.
2. Hoist the `memory.md` write.
3. Stable section ordering.
4. Rename the shadowed `rows`; extract the arc-beat-id helper.
5. Apply the `computed` filter to all entity types, not just `character`.

## Note on the inverse-mapping duplication (#4)
Worth deciding once: should export derive frontmatter from `ENTITY_SCHEMAS` generically (one data-driven function) instead of a per-type if-chain? It would be shorter and self-updating. The counter-argument is that export's output *is* the Markdown contract that humans and existing vaults depend on — a generic emitter could change field order or emit fields the old notes never had. **I'd leave the if-chain and add a round-trip test per entity type** rather than risk changing the Markdown contract. Flagging it as a deliberate non-change, not an oversight.
