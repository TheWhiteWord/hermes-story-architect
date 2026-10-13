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
- [ ] In `_export_all`, collect all `type='value'` rows (already in `entity_rows`, `ORDER BY type, id` → values come out in id order).
- [ ] Do **not** route values through the per-note walk (`_filename`/`_write_note` per entity). Instead: build the concatenated `values.md` text and write it once at `project_path / "values.md"` via `_write_note` with an **empty** frontmatter dict and the blocks as the body (mirror how `memory.md` is written at `export.py:222`).
- [ ] Add the path to `written` so the manifest/sweep tracks it. When there are **zero** values, write an empty `values.md` (a stable, present file — the importer treats missing/empty as "no values").
- [ ] Per value: frontmatter `{id, name, p, c, cd, nn, [note]}`, body = its two sections joined (`## Definition`/`## Notes`, only non-empty ones), matching the section body assembly at `export.py:206-216`.
- [ ] Preserve declaration order of the ladder words (p/c/cd/nn) — `_write_note` already writes with `sort_keys=False`.

### T3.2 — Import (`tools/story_import.py`)
- [ ] New `_import_values(conn, project_path)`: read `values.md`; split into frontmatter blocks; for each, insert a `value` entity via `_insert_entity`/`_columns_for("value", ...)`.
  - [ ] Splitting: use `frontmatter.loads` on each `---`-delimited block, or split on `\n---\n` and `frontmatter.load` each. Reject a block whose `id`/`name` is missing with the same message style as `_insert_sections`.
  - [ ] Run the Phase 2 `validate_value`/`value_problems` checks so a hand-edited `values.md` is refused exactly as the write path refuses it.
  - [ ] Empty or missing `values.md` → no values, no error.
- [ ] Call `_import_values` in `_import_all` **right after `_import_project`** (`import.py:230`), before scenes.
- [ ] `_columns_for("value", ...)`: `name` from `fm["name"]`, `p/c/cd/nn/note` via `_extra_for`.
- [ ] `_extra_for` skip-set for `value`: `{"name", "id"}`.
- [ ] `_diff`: parse `values.md` ids and union into `markdown_ids` so the at-risk guard does not flag values. Reuse the same block parser.

### T3.3 — Tests (`tests/test_values_export_import.py`, new)
- [ ] **Round-trip:** a project with ≥3 values (incl. one with a `note`, one without) → `story_export` writes `values.md` → fresh DB → `story_import` → entities match id/name/p/c/cd/nn/note exactly, order preserved.
- [ ] Values import **before** scenes (a scene edit naming a value resolves) — assert by the import order or a scene whose turn names an existing value.
- [ ] Empty `values.md` (or absent) imports clean.
- [ ] A `values.md` block with duplicate words is refused on import with the Phase 2 message.
- [ ] `story_export` re-run is idempotent (manifest unchanged, no stale sweep of `values.md`).

## Cleanup / legacy
- [ ] None. This phase is additive; `plot.value_schemas` removal is Phase 4.

## Checklist
- [ ] Export writes one root `values.md`, one frontmatter block per value, tracked in manifest/sweep
- [ ] Import parses `values.md`, validates each value, runs before scenes
- [ ] `_diff` knows value ids (no false at-risk)
- [ ] Round-trip + edge-case tests green
- [ ] Full suite at baseline (1096 pass + the 2 pre-existing failures)

## Notes for the implementer
- **Depends on Phase 2** (entity + `validate_value` + `_columns_for`/`_extra_for` value branch). Not parallel with Phase 2 — it consumes what Phase 2 defines. Parallel-safe with Phases 1 and 5/6 (different regions).
- The bespoke block split is the one non-reused piece. Keep it in `story_import.py` beside `_import_project`/`_import_folder`; export side reuses `_write_note`. If the split grows past ~15 lines, factor a tiny `_iter_value_blocks(text)` helper used by both import and `_diff` so the parser lives once.
