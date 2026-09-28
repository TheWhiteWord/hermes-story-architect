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

## Step 1 — delete the compatibility shims — **BUILT, with two corrections**

**Two of the three were safe. One was not, and checking first is what caught
it.** The plan below originally called all three deletions and claimed the test
suite was a sufficient check. Both statements were wrong, and the corrections
are recorded here rather than quietly applied.

### Correction 1 — `drafts` was the ONLY table not in `SCHEMA_SQL`

```
tables SCHEMA_SQL creates: ['entities', 'relations', 'sections']
tables DRAFTS_SQL creates: ['drafts']
```

`ensure_drafts_table` was not merely redundant — it was the **sole creator** of
the table. Deleting it as written broke draft staging on every fresh project,
and **no test caught it**, because every test uses a fixture whose database the
shim had already prepared.

Two tests guarded it, not one. `test_legacy_db_migration.py` and
`test_drafts.py` ("Guard 7"), both constructing a database from before draft
staging existed. **I had not read either file before writing this plan.**

### Correction 2 — `_coerce_number` is NOT legacy, it is load-bearing

`create_project` **does not coerce** `number` fields; only `edit_entity` does
(the write-side fix at `writes.py:270-274`). Measured:

```
create_project with act_count='5'  ->  stored: '5'  type=str
   get_dashboard_data: OK, act_count=5        <- only because _coerce_number ran
edit_entity with act_count='5'     ->  stored: 5   type=int
```

So the read half is the **only** thing standing between a string `act_count`
and `max('3', 3)` taking the dashboard down — the original B10 symptom, still
reachable. The justification for deleting it was "zero string-in-number rows
exist", which is true of the *fixtures* and irrelevant: `create_project` writes
one on demand.

**Kept.** The real defect is the asymmetry, and the honest fix is to make
`create_project` coerce like every other write path — one call, at the same
place `edit_entity` does it. Filed as a new entry rather than smuggled in here.

### What was actually deleted

| | |
|---|---|
| `DRAFTS_SQL` | folded into `SCHEMA_SQL` — it is a table like any other, and `create_schema` is called by `create_project` (`writes.py:45`), `create_entity` (`:119`) and `story_import` (`:157`) |
| `ensure_drafts_table` | deleted, and its call removed from `get_db` |
| `ensure_soft_delete_columns` | deleted as a function; the two `ALTER TABLE` lines inlined into `get_db`, which every caller reaches first — including read-only tools, the ones that never call `create_schema` |
| `_coerce_number` | **kept** — see Correction 2 |

`core/db.py`: **49 lines deleted, 26 added.** Net −23.

### Tests

- `test_legacy_db_migration.py` — the drafts test **deleted**; the other two
  kept (one guards a *column*, which `ALTER TABLE` is still needed for; one
  guards a fresh folder). The module docstring now says why the drafts half
  went and why the column half stayed.
- `test_drafts.py` — "Guard 7" **replaced**, not just deleted, with
  `test_drafts_table_exists_on_a_fresh_project`: a real `create_project()`
  database has the table and staging works against it. That is the case that
  can actually happen, and it would fail if the shim were removed without
  moving `DRAFTS_SQL`.
- `test_soft_delete.py` — two tests rewritten off the deleted function onto
  `get_db`, which is where the repair lives. `test_migration_is_idempotent`
  now asserts the columns appear exactly once after two opens, rather than
  calling a function twice.

**Suite: 891 → 890.** One test removed and one added, net −1, and the two
rewritten ones now exercise the real path.

---


## Step 2 — drop the arc_beat composite id — **BUILT 2026-09-28** ← *fixed a reproduced bug*

**The suite did not drop:** 892 before, 892 after. But it went through 57
failures first, and the shape of those is the useful part.

**What broke, and why it was not arc-specific.** The fixture's note files were
named after the beat number alone — `arcs/kael/1.md` — because the id used to
be reassembled from the directory. With that derivation gone, `_diff` matched
DB ids against stems that no longer corresponded, decided 11 entities were
"only in the database", and **refused to import**. Everything downstream
failed from a half-built database: the load view gained `orphaned_locations`
(the world links never made it in), the key-set assertions broke, round-trip
counts were wrong. 49 of the 57 were `story_import.py`.

**Bisected per file rather than guessed at** — each change stashed in turn:

```
without core/entity.py       55 failed
without core/writes.py       57 failed
without tools/story_export.py 57 failed
without tools/story_import.py  8 failed   <- the cause
```

**The conversion was in the markdown, not the database.** Renamed each note to
`{parent}-{stem}.md` with `id:` matching — `arcs/kael/1.md` →
`arcs/kael/kael-1.md` — which is **exactly what the fixture database already
held**. So there was no data migration at all, which is the deployment
constraint paying for itself a second time. Git tracked all 11 as renames.

After that, 9 failures remained, every one a test asserting the old
convention. Six were updated (`test_arcs`, `test_field_coverage` ×2,
`test_export_sweep`, `test_round_trip`, and the composite's own two).

**The class check came first and is in the entry.** Every other type resolves
by exact `(type, id)` against the PRIMARY KEY; duplicate names are harmless.
Only the `LIKE` branch looked up by anything else, and it is gone.

**Fixture conversion, run once, not committed as a script** — it was 11 renames
performed by a throwaway script, and the result is in the tree.

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

> **The agent's burden and the fixture's readability are separable.** A
> generated id is decided in step 4; whether the *fixtures and tests* keep
> readable ids is a separate question, and answering it wrongly turns a
> two-line change into a 493-occurrence rewrite. See "What step 4 does NOT
> have to touch" below — read it before starting.

**Why after step 2:** compositing a generated id gives the 73-char artefact
measured in Part A″ — a worse thing than either the old composite or a clean
uuid. Drop the composite first, then generate.

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

### What step 4 does NOT have to touch — measured, and it is the whole step

**A generated id is not the same thing as an unreadable id.** The agent stops
supplying one; nothing forces the *fixtures* to stop having readable ones. The
code is agnostic — `entities.id` is a TEXT primary key, and relations,
`parent_id` and every `extra` link store whatever string is there. A fixture
built by hand, with `kael` as its id, works unchanged under a code path that
generates ids for anything the *agent* creates.

So the two halves are separable:

| | what changes | size |
|---|---|---|
| **the code** | generate the id on create; stop requiring the agent to send one | ~10 lines, plus the uniqueness message |
| **the fixtures** | nothing, if they keep their readable ids | **0** |
| **the tests** | nothing, if the fixtures keep theirs | **0** |

**Measured cost of the alternative** — converting the fixtures to generated ids
too:

```
kael                 25 files, 272 occurrences
act-1                10 files,  88
mira                 15 files,  72
central-room-day     13 files,  54
the-central-room      8 files,  45
seq-discovery         8 files,  25
the-resistance        5 files,   9
dr-elena-voss         3 files,   8
                     ─────────────────────
                     493 occurrences across 25 test files
```

Plus the markdown fixture, where **the filename is the id** — 20 note files
(`dr-elena-voss.md`, `kael.md`, …) and 11 arc beats keyed `parent-child`. Every
one of those would need renaming, and `test_round_trip.py` asserts those exact
paths.

**Recommendation: do not convert the fixtures.** A test that says
`edit_entity(..., "kael", ...)` states its intent; the same test saying
`edit_entity(..., "95b392b8", ...)` states nothing. The fixtures are the
readable case, and they exercise the same code the generated case uses. If a
generated id ever needs testing, that is one new test asserting distinctness
and a retry — not a migration of the corpus.

**The one thing that must change either way:** the uniqueness error at
`writes.py:132-143` says *"choose a different slug"*, which stops making sense
the moment the agent is not choosing one.

**Check:** create ten entities, assert ten distinct 8-char hex ids; assert a
forced collision is retried rather than raised. Suite at 892.

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
