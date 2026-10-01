# Phase 1 — Fix the create-path corruption; one dict→row function

**Phase 1 of 7.** No phase starts before the previous one is done. See `INTEGRATION.md`.
No dependencies. Independent of every decision in `PLAN.md`.

## What is wrong

`relations_for_insert` (`core/entity.py:442`) unwraps a `{scene_id, description}` entry
only for two kinds:

```python
if kind in ("plot_setup", "plot_payoff"):
    to_id = item.get("scene_id", ""); note = item.get("description", "")
else:
    to_id = str(item); note = ""
```

Executed against current code:

```
plot_setup  -> to_id='s1'                      ok
plot_crisis -> to_id="{'scene_id': 's2', …}"   dict repr as to_id, note lost
plot_climax -> to_id="{'scene_id': 's3', …}"   dict repr as to_id, note lost
plot_payoff -> to_id='s4'                      ok
```

A plot **create** writes corrupt rows for `crisis` and `climax`. The row points at a
nonexistent scene slug and the prose is discarded.

## Verified: three write paths, three behaviours

| path | site | crisis/climax |
|---|---|---|
| create | `entity.py:428-459` | **corrupt** |
| edit | `writes.py:388-400` | correct |
| import | `story_import.py:504-515` | correct |

Undetected because `tests/test_field_coverage.py:456` asserts `plot_crisis` survives only
through the **edit** path. There is no create-path coverage for these fields.

## What to do

1. Extract one function in `core/entity.py`:
   ```python
   def relation_entry(item) -> tuple[str, str]:
       """(to_id, note) from a relation field entry — dict or bare slug."""
   ```
   It must handle both shapes, because the same loop serves `character_scene`
   (list of plain slugs, `entity.py:222`) and the plot role lists (list of dicts).
2. Route all three call sites through it: `entity.py:443`, `writes.py:390`,
   `story_import.py:507`.
3. Delete the per-kind special case at `entity.py:442`. There is no reason for one kind to
   behave differently from its four siblings.

## Detail found during verification

The three copies **already disagree** on the missing-key default:

- `entity.py:443` — `item.get("scene_id", "")` → empty, row skipped
- `writes.py:390` — `beat.get("scene_id", str(beat))` → the dict repr, row written pointing
  at garbage
- `story_import.py:507` — `beat.get("scene_id", "")` → empty, row skipped

So a malformed entry is dropped on two paths and written as garbage on the third. The
shared function picks **empty** (skip the row): a relation row naming a scene that was not
identified is not a fact worth storing. Low impact, resolved here rather than escalated.

## Legacy / obsolete code to clear

- The `if kind in ("plot_setup", "plot_payoff")` branch at `entity.py:442` — deleted, not
  generalised. It is the bug.
- `tests/test_write_shape.py:92` asserts a string `setups` writes no relations. Keep — it
  is the guard for the shape check.

## Tests

- **New, required:** a plot **create** with `crisis`/`climax` dict entries writes rows whose
  `to_id` is the scene slug and whose `note` is the description. This is the regression test
  for the bug; it fails today.
- **Extend:** `tests/test_write_shape.py` to cover the malformed-entry case (missing
  `scene_id`) on all three paths, asserting consistent skip behaviour.
- **Do not** weaken `tests/test_field_coverage.py:456`. It is correct; it is just not
  covering the create path.

## Notes

- No backward-compat shim. The old per-kind branch is removed, not kept behind a flag.
- Phase 3 adds `plot_complication`, which this function will then serve too. Write it
  role-agnostic now; do not name it after a role.

## Checklist

- [x] `relation_entry()` exists in `core/entity.py`, handles dict and bare-slug
- [x] `entity.py`, `writes.py`, `story_import.py` all call it; no local copies left
- [x] `grep 'scene_id' core/ tools/` shows no per-kind unwrap logic anywhere
- [x] Create-path regression test added and **fails without the fix**
- [x] Malformed-entry behaviour consistent across all three paths
- [x] `tests/test_write_shape.py` extended; `test_field_coverage.py:456` untouched
- [x] Full suite green
- [x] No compat shim, alias, or legacy branch left behind

## Implementation report

**Done.** Suite: 959 passed (was 950; +9 new: 4 parametrised create-path roles, 1
no-dict-repr guard, 3 malformed-entry paths, 1 bare-slug guard).

**What changed**

| file | change |
|---|---|
| `core/entity.py:219` | new `relation_entry(item) -> (to_id, note)`, role-agnostic |
| `core/entity.py:455` | create loop now `to_id, note = relation_entry(item)` |
| `core/writes.py:389` | edit loop now `target, note = relation_entry(beat)` |
| `writes.py:324` | import added to the local `.entity` import |
| `tools/story_import.py:5,507` | `from core.entity import relation_entry`; import loop routes through it |
| `tests/test_write_shape.py:97-185` | regression + malformed-entry + bare-slug tests |

The `if kind in ("plot_setup", "plot_payoff")` branch is gone, not generalised.
No shim, no alias. `str()` coercion on both returned values, so a non-string
`scene_id` cannot reach the `to_id` column untyped.

**Verified against the spec, not assumed**

- `git stash` on `core/entity.py` alone → crisis/climax/no-dict-repr fail; with
  the fix, all pass. The regression test genuinely pins the bug.
- `grep scene_id core/ tools/`: only three remain — `constants.py` (schema
  `sub_fields`, correct), `story_export.py:177` and `story_retrieve.py:121`
  (both **write** `{scene_id, description}` on the read side). Both construct the
  shape, neither unwraps it. No per-kind logic anywhere.
- Missing-key default is **empty/skip** on all three paths, as the spec decided.
  This changed one behaviour: edit previously wrote `beat.get("scene_id",
  str(beat))` — the dict repr as `to_id`. That was the garbage-row path and is
  now a skip. No test depended on it.

**Assumptions checked, none required a change**

- `relation_entry` is called only where `kind` is in scope for the
  non-list branch too; the non-list branch (`variant_of`) never touches it and
  does not need to — a single string, not a relation entry.
- `story_import.py` imports `core.entity` at module top. Other tools
  (`story_export`, `story_retrieve`) already do exactly this, so it is the
  established convention, not a new coupling.
- `tests/test_write_shape.py:92` (the string-writes-no-rows guard) kept as-is.

## NOTES

- **`db.py:1095-1107` is a fourth copy of the same normalisation**, in
  `story_load`'s reader: it rebuilds `{scene_id, description}` from rows and has
  a `b["to_id"]` / `str(b)` branch. Not a bug today (it is the read direction and
  its default matches), but it is duplication phase 2's `PLOT_ROLES` work should
  look at. Not touched here — out of scope for a bugfix phase.
- **`db.py:374` and `story_load.py:205` both name a local `scene_id`** in a
  loop variable that is an entity id, not a scene slug of a relation entry.
  Cosmetic, not a defect. Noted so a future grep for `scene_id` does not read
  them as violations.
- **Pre-existing:** `test_field_coverage.py:456` remains edit-path-only. Phase 6
  owns the create-path coverage audit across every relation field; this phase
  added coverage for plot beats specifically.

## Final brief — phase 1

**Phase gate met.** The corruption is closed on every path that can write a
relation row, and it is closed in one place, so no fourth path can reintroduce
it. Phase 1 lands on its own merit: it is a live data-corruption fix with no
dependency on any decision in `PLAN.md`, and phases 2–4 all get cheaper for it.

**Why it was invisible.** `plot_crisis` and `plot_climax` had exactly one test
each, and both went through `edit_entity` — the one path that was already
correct. The create path had no coverage for any plot beat. The defect was not
missed so much as *unreachable from the suite*.

**What a successor inherits**

- `relation_entry()` is the single dict→row unwrap. It is role-agnostic and
  unnamed after a role, so phase 3's `plot_complication` and phase 4's five-kind
  `plot_roles` need no change here. Give it a new caller; do not add a second
  unwrap beside it.
- One convention changed: a relation entry with no usable `scene_id` is
  **dropped**, on all three paths. Skip, do not store a guess.
- `str()` on both returned values. Keep it — a non-string `scene_id` must never
  reach `to_id` untyped.

**For phase 2.** The remaining duplication is `db.py:1095-1107` (the reader-side
copy of this same normalisation) plus the eight sites `task_02` already lists.
That is the whole of the remaining work for a `PLOT_ROLES` source; nothing new
turned up here.

**Confidence:** verified by execution, not inspection. Suite 959/959 green;
the regression demonstrated red-then-green by stashing the fix.