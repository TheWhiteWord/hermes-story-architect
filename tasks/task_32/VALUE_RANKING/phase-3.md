# Phase 3 — Export/import the single `values.md`

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §3 ("all values are one file, `values.md`, at the project root, with one entry per value") and §6 step 3.
Depends on: **Phase 2** (the `value` entity type must exist). Runs against a project that may still carry `plot.value_schemas` — this phase does not touch them (that is Phase 4).

## Design decision (locked)

Values serialize as **one file `values.md` at the project root**, one entry per value. This deliberately departs from the one-note-per-entity folder model every other type uses (`values/*.md`), per the plan's literal wording and the user's confirmed choice. The cost is a small bespoke serializer + parser; the benefit is one file a writer reads whole. Reuse `_write_note`/`frontmatter` for the write, but the file is a concatenation of per-value frontmatter blocks, so the parser is custom.

## Verification against code (done)

- **Root-level files already exist and work.** `story_export` writes `project.md` and `.story/memory.md` at the root with `_write_note` (`export.py:218-224`). A root `values.md` is the same shape.
- **The stale-manifest sweep handles a root file.** `_export_all` returns absolute paths in `written`; the sweep at `export.py:108-125` stores project-relative paths and unlinks any previous path no longer written. Adding `values.md` to `written` makes it swept correctly — no change to the sweep.
- **Import entry point is an explicit ordered walk.** `_import_all` (`import.py:228-239`) calls `_import_project`, then each `_import_folder`, then `_import_arcs`. Add `_import_values(conn, project_path)` **after `_import_project` and before the folder walks**, so values exist before scenes (Phase 4's turn validation reads value entities).
- **`_diff` (the destructive-import guard) must know about values.** It scans fixed folders (`import.py:71-72`) for markdown ids to decide which DB entities are "at risk." A `value` entity has no folder note, so it would be wrongly reported as destroyable. Add the value ids parsed from `values.md` to `markdown_ids` so the guard stays quiet for values.

## Entry format for `values.md`

One YAML frontmatter block per value, separated by `---`, in `id` order. Body (the `## Definition`/`## Notes` sections) rides under each block.

```markdown
---
id: trust
name: trust
p: open
c: wary
cd: deceived
nn: exploited
note: Whether the system tells them the truth.
---

## Definition

[prose]

---
id: loyalty
name: loyalty
p: ...
```

- Field order `id, name, p, c, cd, nn, note` — same as the schema; skip empty `note`.

## Tasks

### T3.1 — Export (`tools/story_export.py`)
- [x] In `_export_all`, collect all `type='value'` rows (already in `entity_rows`, `ORDER BY type, id` → values come out in id order).
- [x] Do **not** route values through the per-note walk (`_filename`/`_write_note` per entity). Instead: build the concatenated `values.md` text and write it once at `project_path / "values.md"` via `_write_note` with an **empty** frontmatter dict and the blocks as the body (mirror how `memory.md` is written at `export.py:222`).
  - **Deviation (found in testing):** `_write_note` with an empty dict emits a leading `--- {} ---` wrapper block, which the parser then has to skip. The file is a concatenation of blocks that already carry their own fences, so `values.md` is written directly (`values_path.write_text`) rather than through `_write_note`. Same one-write shape, no wrapper.
- [x] Add the path to `written` so the manifest/sweep tracks it. When there are **zero** values, write an empty `values.md` (a stable, present file — the importer treats missing/empty as "no values").
- [x] Per value: frontmatter `{id, name, p, c, cd, nn, [note]}`, body = its two sections joined (`## Definition`/`## Notes`, only non-empty ones), matching the section body assembly at `export.py:206-216`.
- [x] Preserve declaration order of the ladder words (p/c/cd/nn) — `_write_note` already writes with `sort_keys=False`. (`_value_block` renders via `frontmatter.dumps(..., sort_keys=False)`.)

### T3.2 — Import (`tools/story_import.py`)
- [x] New `_import_values(conn, project_path)`: read `values.md`; split into frontmatter blocks; for each, insert a `value` entity via `_insert_entity`/`_columns_for("value", ...)`.
  - [x] Splitting: `_iter_value_blocks(text)` walks the `---` fences and `yaml.safe_load`s each block's frontmatter (frontmatter only parses the first block of a concatenation). A block whose `id`/`name` is missing is refused, in `_insert_sections`'s message style.
  - [x] Run the Phase 2 `validate_value` checks so a hand-edited `values.md` is refused exactly as the write path refuses it (distinct words, id==slug(name), name uniqueness — validate_value opens its own read connection so it sees the values already inserted this pass).
  - [x] Empty or missing `values.md` → no values, no error.
- [x] Call `_import_values` in `_import_all` **right after `_import_project`**, before scenes.
- [x] `_columns_for("value", ...)`: `name` from `fm["name"]`, `p/c/cd/nn/note` via `_extra_for`.
- [x] `_extra_for` skip-set for `value`: `{"name", "id"}`.
- [x] `_diff`: parse `values.md` ids and union into `markdown_ids` so the at-risk guard does not flag values. Reuses `_iter_value_blocks`.

### T3.3 — Tests (`tests/test_values_export_import.py`, new)
- [x] **Round-trip:** a project with ≥3 values (incl. one with a `note`, one without) → `story_export` writes `values.md` → fresh DB → `story_import` → entities match id/name/p/c/cd/nn/note exactly, order preserved.
- [x] Values import **before** scenes — asserted by watching the import walk (values before scenes).
- [x] Empty `values.md` (or absent) imports clean.
- [x] A `values.md` block with duplicate words is refused on import with the Phase 2 message.
- [x] `story_export` re-run is idempotent (manifest unchanged, no stale sweep of `values.md`).

## Cleanup / legacy
- [x] None. This phase is additive; `plot.value_schemas` removal is Phase 4.

## Checklist
- [x] Export writes one root `values.md`, one frontmatter block per value, tracked in manifest/sweep
- [x] Import parses `values.md`, validates each value, runs before scenes
- [x] `_diff` knows value ids (no false at-risk)
- [x] Round-trip + edge-case tests green
- [x] Full suite at baseline (1142 pass, 0 failed)

## Notes for the implementer
- **Depends on Phase 2** (entity + `validate_value` + `_columns_for`/`_extra_for` value branch). Not parallel with Phase 2 — it consumes what Phase 2 defines. Parallel-safe with Phases 1 and 5/6 (different regions).
- The bespoke block split is the one non-reused piece. Keep it in `story_import.py` beside `_import_project`/`_import_folder`; export side reuses `_write_note`. If the split grows past ~15 lines, factor a tiny `_iter_value_blocks(text)` helper used by both import and `_diff` so the parser lives once.

## Final brief (implementation complete)

`values.md` export/import is wired end to end. Export writes one root file (id order, `note` only when present, empty-but-present for a value-less project); import parses it with the same block reader `_diff` uses, runs `validate_value` per block so a hand-edited file is refused like a draft, and runs before scenes so a value exists before a turn can name it.

**The one deviation from the plan.** The plan said to write `values.md` through `_write_note` with an empty frontmatter dict, "mirroring how memory.md is written." Testing showed `_write_note({})` emits a leading `--- {} ---` wrapper (PyYAML writes an empty mapping rather than nothing), which the concatenated-block format cannot absorb — the parser would have to skip it. Since the blocks already carry their own fences, `values.md` is written directly with `write_text`. Same one-write shape, same manifest/sweep tracking; no wrapper.

**Where the parser lives.** `_iter_value_blocks` (import.py) is the single block reader — `_import_values` and `_diff` both call it, so the parser exists once. It splits on `---` fences and `yaml.safe_load`s each block's frontmatter; `frontmatter` itself only parses the first block of a concatenation, which is why the split is bespoke. Export's `_value_block` (export.py) renders one block via `frontmatter.dumps(..., sort_keys=False)`, keeping the schema's p/c/cd/nn order.

**Guards.** `validate_value` is Phase 2's own check, called per block — distinct words, id==slug(name), and name uniqueness (it opens a read connection, so it sees values already inserted this pass, making the uniqueness rule hold across the file). `_diff` unions the parsed ids into `markdown_ids`, so an exported value is never falsely reported as database-only.

**Tests.** `tests/test_values_export_import.py` (17 tests): export shape/order/optional-note/manifest, exact round-trip incl. sections and retrieve field order, values-before-scenes (asserted by watching the walk — the fixture's turn still names a plot schema, so a value-naming turn is Phase 4), empty/absent file, refusals (duplicate word, id≠slug, duplicate name), idempotence + delete-sweep, and the `_diff` guard. Full suite: **1142 passed, 0 failed** (1096 baseline + 17 new + Phase 2's tests already counted; the phase notes' "2 pre-existing failures" no longer appear).

**Skipped:** `plot.value_schemas` / turn-schema wiring to the value entity (Phase 4), per the deferral. Nothing else deferred.
