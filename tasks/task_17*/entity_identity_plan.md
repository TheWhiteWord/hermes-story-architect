# D5 implementation plan — entity identity

**Written 2026-09-28. Nothing here is built.** The design is settled and
recorded in `entity_identity.md`; this file is the order to build it in, and
why that order.

**Baseline: 889 tests pass** (`.venv/bin/python -m pytest tests/ -q`, 35.5s).
Every step below must leave that number at 889 or higher. No step may be
committed with a red suite.

**The governing constraint** (from `entity_identity.md`): the plugin is not
deployed and every project is a test artefact, so a data change is a one-time
script, not a migration inside the plugin. That is what makes step 5 affordable
and it is why nothing here needs a compatibility layer.

---

## Why this order

The work is **not** one change. It is four independent ones with a dependency
between two of them, and two of them are *fixes for bugs already reproduced*
rather than refactors:

| # | change | depends on | fixes a live bug? |
|---|---|---|---|
| 1 | delete the 3 compat shims | — | no |
| 2 | drop the arc_beat composite id | — | **yes** — the wrong-entity write |
| 3 | `slug` → `id` on the op vocabulary | — | no (B6 is separate) |
| 4 | generate the id | 2 | no |
| 5 | id into frontmatter, filenames by title | 4 | no |

**Steps 1 and 2 go first** for one reason: they are the only two that fix a
reproduced defect, and both are deletions. Landing them before anything else
means the diff that follows is purely structural, and a regression in the
refactor is not confused with a regression in a fix.

**Step 4 must follow step 2.** Generating an id while `columns_for_insert` still
composites `{character}-{slug}` produces the 73-char id measured in Part A″ — a
worse artefact than either the old composite or a clean uuid. Drop the composite
first, then generate.

**Step 5 is last** because it is the only one that changes the *file* layout,
and because it needs step 4 to have landed: a frontmatter id is only meaningful
if there is a generated id to put in it.

---

## Step 1 — delete the compatibility shims

**Why first:** they are complexity guarding a constraint that no longer exists,
they are independent of everything else, and the test suite is a sufficient
check.

Measured across every `story.db` on the machine: all three real databases
already carry `is_deleted`/`deleted_at`, **none** has a `drafts` table, and
**zero** number-typed fields are stored as a string.

| delete | where | why it is dead |
|---|---|---|
| `ensure_soft_delete_columns` | `core/db.py:125-134`, called at `:84` | every real DB has the columns; `SCHEMA_SQL` gives them to a fresh one |
| `ensure_drafts_table` | `core/db.py:149-160`, called at `:78` | no real DB has the table; drafts are transient |
| the read half of `_coerce_number` | `core/db.py:302-325`, used at `:346` and `:1328` | zero string-in-number rows anywhere. **Keep the write-side fix** at `writes.py:270-274` — that is the one doing real work. |

**Check:** the suite passes at 889, and `save-the-children` still imports,
exports and re-imports (`test_round_trip.py` covers exactly that).

**Risk:** low, and the failure mode is loud — a missing column raises
`no such column` immediately on the first read, which is what these shims were
written to prevent. A test that passes while a shim was needed would be a test
that never reads the column.

---

## Step 2 — drop the arc_beat composite id  ← *fixes a reproduced bug*

**Why:** this is a live, silent, wrong-entity write. Two characters each own an
arc beat labelled "The Choice"; `edit_entity(..., "arc_beat", "the-choice", …)`
resolves through `writes.py:689`'s `id LIKE '%-{slug}'` fallback, matches the
first row, and **edits the wrong beat while returning `success: true`**.

| change | where |
|---|---|
| `columns["id"] = slug`, not `f"{char}-{slug}"` | `core/entity.py:290-294` |
| drop the `LIKE '%-{slug}'` fallback from the lookup | `core/writes.py:682-693` |
| drop the `id[len(parent_id)+1:]` slice in export (×2) | `story_export.py:164`, `:256` |
| arc-beat notes get an `id` in frontmatter; the beat slug comes from it | `story_export.py:254-264` |
| the import fallback `fm.get("id", note.stem)` stays | `story_import.py:302` — already correct |

**The character link is unaffected:** it lives in the `parent_id` column, which
is set from `fm["character"]` independently of the id. Nothing references the
composite.

**Check:** a test that creates two arc beats with the same label under
different characters, edits one **by its full id**, and asserts the other is
untouched. Plus the existing arc tests. The `save-the-children` fixture has 11
composite-id beats, so the fixture ids change — `test_round_trip.py:61` asserts
`arcs/kael/1.md` and will need updating to whatever the new layout is.

**This step is worth doing even if nothing else is.** It is a bug fix, it is
small, and it is a prerequisite for step 4 being clean.

---

## Step 3 — one name for the op argument

**Why here:** purely mechanical, touches no data, and it is what makes the
vocabulary honest. Independent of steps 1, 2 and 4 — it could land first.

| change | where |
|---|---|
| `("type", "slug", …)` → `("type", "id", …)` | `core/drafts.py:27` |
| `op["slug"]` → `op["id"]` | `core/drafts.py:425` |
| `op.get("slug")` → `op.get("id")` | `core/drafts.py:472` |
| `op.get('slug', '')` → `op.get('id', '')` | `core/drafts.py:527` |
| the ops description in the tool schema | `tools/story_draft.py:51` |
| **delete** the bridge sentence | `story_describe.py:118`, `SKILL.md` |

**Hard rename, no alias** — measured: zero open drafts in both real projects,
and drafts are transient, so the blast radius is a draft staged in the seconds
between deploy and commit. An alias would be permanent code guarding that.

**Leave `slug=` in the Python signatures** (`create_entity(project_path, type,
slug, …)`). Those are developer-facing, not the agent's vocabulary; renaming
them is cosmetic churn.

**Do NOT touch** `slug` meaning *project directory* — `projects/<slug>/`,
`story_resolve`, the `project` argument on every tool. Different concept,
different name, and `_check_slug`'s traversal defence is load-bearing there.

**Check:** 27 `"slug"` op-key sites and 9 `slug=` sites in `tests/`. Update
them. The suite at 889.

---

## Step 4 — generate the id

**Why after step 2:** compositing a generated id gives the 73-char artefact.

```python
# core/writes.py, in create_entity, replacing the slug parameter
import secrets
...
for _ in range(5):                       # 32-bit id: a collision is 1-in-12,000
    entity_id = secrets.token_hex(4)
    if not conn.execute("SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone():
        break
else:
    raise ValueError("Could not generate a unique id after 5 attempts")
```

`columns_for_insert` takes the generated id instead of the caller's slug. The
existing check at `writes.py:129-143` stays as the backstop and its message
needs rewriting — it currently says *"choose a different slug"*, which will no
longer make sense.

**`id` is then declared on all ten types** in `ENTITY_SCHEMAS` (currently four
have it) and **removed from `FIELDS_TO_SKIP`** (`entity.py:161`,
`writes.py:20`) so it round-trips instead of being silently dropped. This is
Q4's finding, fixed at the same time because both are the same missing field.

**Cost, measured:** +87 tokens per `story_load` (ids appear 90× in the payload;
+4.1% → +8.4%). Accepted deliberately, against +717 for `uuid4()`.

**Check:** create ten entities, assert ten distinct 8-char hex ids; assert a
forced collision is retried rather than raised. Suite at 889.

---

## Step 5 — id in frontmatter, filenames by title

**Why last:** it changes the file layout, and it needs a generated id to put in
the frontmatter.

| change | where |
|---|---|
| filename = the title, uniquified per folder by counter | `story_export.py:171` |
| write `id` into every note's frontmatter (all ten types) | `story_export.py:177-274` |
| read the id from frontmatter, fall back to the stem | `story_import.py:279` |
| the arc-beat filename uses its own id, not `{char}-{beat}` | `story_export.py:162-168` |
| `_diff` matches DB ids against frontmatter, not stems | `story_import.py:55-77` |
| the 4 dead-link fallbacks say "⚠ unresolved" | `entity-panels.js:70,165,364,78` |

**Counter policy:** `Kael.md`, then `Kael 2.md`. Needed because titles are not
unique — *"The Choice"* is two arc beats in `save-the-children` today.
Nothing references a filename, so this collision is cosmetic; an id collision
would be silent.

**`_diff` is the real work in this step** — it currently globs stems and would
have to open every note. Same function that already reads each file to import
it, one pass.

**This step will break tests that hardcode filenames.** Measured: 9 test files,
23 sites, including `test_round_trip.py:60-61` (`kael.md`, `arcs/kael/1.md`)
and `test_export_sweep.py`. Update them to look the file up by frontmatter id
rather than by name — which is also the behaviour the change is meant to
enable.

**The 4 dashboard sites are independent of everything above** and could be a
separate commit. They are a legibility fix, not a refactor.

**Check:** the round trip still closes — import → export → wipe → re-import
yields identical entities, sections and relations, **with the ids surviving**,
which is the property that was impossible before. That is the test that proves
this step.

---

## Explicitly not in this plan

- **B6 / B12** (`REQUIRED_FIELDS` and the enum placeholder defaults). Separate
  defects in `bugs.md`, separate fixes. B6 is arguably fixed *by* step 4, since
  an unsatisfiable `id` requirement disappears when the agent stops supplying
  the id — **verify that when step 4 lands** rather than assuming it.
- **Q2** — whether the naming caused a live mis-call. Still unanswered, and it
  does not gate this plan: steps 1, 2 and 5 are justified on their own merits
  (two fix reproduced bugs, one is a legibility fix), and steps 3 and 4 are
  wanted as a coherent whole regardless of severity.
- **A data migration for the fixtures.** The deployment constraint makes the
  existing ids convertible with a throwaway script if step 2 needs it. Not
  written until step 2 proves it needs one.
- **Renaming `title`/`name`/`label` in the schema** (Q10). The DB column is
  `name` for all ten types and the division of function is already true at that
  level. The vocabulary split is a docs problem.
