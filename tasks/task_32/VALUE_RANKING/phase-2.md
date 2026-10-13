# Phase 2 — The `value` entity type

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §3 and §6 step 2.
Depends on: **Phase 1** (not required technically, but keep order — Phase 1 lands the helper; this phase is independent of it).

A new entity type, one per value: `{name, p, c, cd, nn, note}`. Schemas move off the plot onto first-class `value` entities. Follow the `arc_beat` wiring pattern exactly — it is the most recent leaf entity type and touches the same ~8 files.

## Verification of the plan against code (done)

Every registry point a new entity type must be added to, confirmed:

| File | Point | arc_beat reference |
| --- | --- | --- |
| `core/constants.py` | `ENTITY_LABELS`, `ENTITY_SCHEMAS` | `constants.py:58`, `:259` |
| `core/entity.py` | `ENTITY_COLUMN_MAP`, `_RELATION_FIELDS`, `standard_sections`, `value_problems` enum block | `entity.py:287,340,478,82` |
| `core/writes.py` | parent/ref validation in `create_entity` | `writes.py:184` |
| `tools/story_export.py` | `_FOLDERS`, per-type branch in the walk, `_frontmatter_for` | `export.py:378,226` |
| `tools/story_import.py` | `_import_all` walk, `_columns_for` branch, `_extra_for` skip-set | `import.py:239,432,490` |
| `tools/story_retrieve.py` | `_resolve` query (default branch already handles a plain `type+id`) | `retrieve.py:73` |
| `tools/story_describe.py` | none — enum-driven off `ENTITY_SCHEMAS` | auto |

- **Storage model — CONFIRMED sound.** A value is a flat leaf: `name` is a column, `p/c/cd/nn/note` are plain scalars → `extra`. No relations, no parent. `columns_for_insert` (`entity.py:504-547`) handles an empty `ENTITY_COLUMN_MAP` entry fine (everything non-column goes to `extra`). Map only `name → name`; the rest land in `extra` automatically.
- **One inconsistency found — id vs name. LOW impact.** The plan says "the id is the slug of the name," but `story_draft` create takes an **explicit `id`** (`story_draft.py:51-56`); there is no auto-slugging anywhere in the write path. **Resolution (low impact, no design change):** keep the explicit-id create path, and add a value create validation that requires `id == slug(name)` (lowercased, hyphenated). Enforces the plan's invariant without building a slugging feature the rest of the system does not have. Import must apply the same rule.

## Schema (`core/constants.py`)

```python
"value": {
    "name": {"type": "string", "default": "", "optional": False,
             "description": "The value, named by its positive pole (e.g. 'trust'). One value per entity."},
    "p":  {"type": "string", "default": "", "optional": False, "description": "Positive: the ideal word (ladder rung p)."},
    "c":  {"type": "string", "default": "", "optional": False, "description": "Contrary: opposite word (rung c)."},
    "cd": {"type": "string", "default": "", "optional": False, "description": "Contradictory: direct negation (rung cd)."},
    "nn": {"type": "string", "default": "", "optional": False, "description": "Negation of negation (rung nn)."},
    "note": {"type": "string", "default": "", "optional": True, "description": "Optional: what this value means."},
}
```

- [ ] `ENTITY_LABELS["value"] = "Value"`.
- [ ] Fields ordered `name, p, c, cd, nn, note` — matches the plan's table; retrieve/export emit in this order.
- [ ] `VALUE_LADDER` (`constants.py:29`) already names the four rungs — reference it in the descriptions, do not restate the meanings.

## Tasks

### T2.1 — Constants and validation (`core/constants.py`, `core/entity.py`)
- [ ] Add `value` to `ENTITY_LABELS` and `ENTITY_SCHEMAS` (above).
- [ ] `standard_sections("value")` → `["Definition", "Notes"]` (a value is a definition + note; no relation/arc sections).
- [ ] New validator `validate_value(project_path, fm)` in `core/entity.py`:
  - [ ] `name` non-empty.
  - [ ] **Four distinct words:** `p/c/cd/nn` all non-empty and pairwise distinct (case-insensitive) — this is the plan's "four distinct words" rule, same check as `validate_scene_value_turns`'s inline branch (`entity.py:953-957`). Reuse that logic if it factors cleanly; else duplicate the 3-line check.
  - [ ] **Name uniqueness (case-insensitive, trimmed):** no other `value` entity whose `name` equals this one — the plan's "a value has one schema wherever it is used." Query `SELECT id, name FROM entities WHERE type='value' AND is_deleted=0`.
  - [ ] **id == slug(name):** the low-impact resolution above.
- [ ] Add the `value` enum/shape block to `value_problems` (`entity.py:42+`) so both write and import run the same checks.

### T2.2 — Write path (`core/writes.py`)
- [ ] In `create_entity`, after the generic id-collision check, for `entity_type == "value"` call `validate_value` **before** INSERT. A refused create writes nothing.
- [ ] In `edit_entity`, for `value` re-run `validate_value` on the merged frontmatter (renaming a value must keep `id == slug(name)` and re-check name uniqueness/distinct words). Check how `edit_entity` merges (`writes.py:408-414` region) and hook beside the scene `value_turns` re-check at `writes.py:475-476`.

### T2.3 — Retrieve / describe / export / import wiring
- [ ] **Retrieve:** default `_resolve` branch (`retrieve.py:73-75`) already returns a value by `type+id`. Add nothing — **skip a lookup-by-name fallback (YAGNI)**, the id IS the slug of the name.
- [ ] **Describe:** automatic via `ENTITY_SCHEMAS` (`story_describe.py:111`). Verify `story_describe(entity_type='value')` lists all six fields + the two sections.
- [ ] **Export / import — DEFERRED to Phase 3.** Values do NOT use the per-note folder model. They serialize as a **single `values.md` at the project root** (design decision, see Phase 3). Do **not** add `value` to `_FOLDERS` or the export note walk. Only Phase 3 wires the file. This phase wires constants + validation + write path + retrieve + describe only.

### T2.4 — Tests (`tests/test_value_entity.py`, new)
- [ ] Create a value with four distinct words → succeeds; retrieve returns all fields in schema order.
- [ ] Create with duplicate words (e.g. `p == c`) → refused, message names the rungs.
- [ ] Create with `id` not equal to `slug(name)` → refused.
- [ ] Create two values whose names differ only by case/whitespace → second refused (uniqueness).
- [ ] Edit that renames → `id` must follow the new slug or the edit is refused.
- [ ] `story_describe(entity_type='value')` lists `name,p,c,cd,nn,note` and sections `Definition,Notes`.

## Cleanup / legacy
- [ ] None in this phase — `plot.value_schemas` still exists and is removed in Phase 4. Do not touch it here. (Create/edit of a value is additive.)

## Checklist
- [ ] `value` in ENTITY_LABELS, ENTITY_SCHEMAS, standard_sections, value_problems
- [ ] `validate_value`: name, four distinct words, name uniqueness, id==slug(name)
- [ ] create + edit both validate; refused write stores nothing
- [ ] retrieve/describe wired; export/import DEFERRED to Phase 3
- [ ] new test file green; full suite at baseline (1096 pass + the 2 pre-existing failures)

## Notes for the implementer
- **Parallel-safe with Phase 1.** No shared file region beyond additive constants. **Phase 3 owns all `values.md` file I/O** — this phase leaves export/import alone so the single-file decision has one home.
- The `validate_value` distinct-words check and `validate_scene_value_turns`'s inline check (`entity.py:953-957`) encode the same rule. If you can factor one shared `assert_four_distinct_words(words)` helper, do it — it retires a duplicate when Phase 4 deletes the inline path.
