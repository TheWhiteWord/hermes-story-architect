# Entity identity — the `id` / `slug` / `entity_id` problem

**Status: a position is agreed (2026-09-28), nothing is built.**

Raised 2026-09-28. This file exists because the id/slug question was about to
be answered by assertion. It is deliberately not a fix. Everything below is
either measured against the repo or explicitly marked as unverified, so the
next keeper can tell which is which — the lesson from the last three wrong
diagnoses in `bugs.md` was that a confident story with no measurement behind it
is worse than no story.

**Where it landed.** The id is generated (`secrets.token_hex(4)`), never
supplied by the agent, stored in the DB *and* in every note's frontmatter, and
the title is the only user-facing name — dashboard, payload, and filename. See
**The synthesis** at the end for the full statement, the two questions still
open, and the rough size. The reasoning is in the parts below, in the order it
happened — including the two positions that were **wrong and later overturned**
(Part A′'s first cost figure, and Part B's rejection of title filenames), kept
because the reasoning is what shows why the answer changed.

Scope: one question. *What is an entity's identity, and where is it written?*
Everything about ids, slugs, filenames and the display name. B6 and B12 are
separate defects and stay in `bugs.md`; this file may reference them but does
not own them.

---

## The deployment constraint (stated 2026-09-28, changes the arithmetic)

**The plugin is not deployed. Every project in existence is a test artefact** —
the two fixtures and the one project in the live plugin folder. Nothing anyone
depends on is stored in a Story Architect database, and no real user has ever
authored through these tools.

Two consequences, and they pull in opposite directions:

1. **Any schema or data change can be a one-time script.** It does not have to
   be a migration inside the plugin, it does not have to be idempotent, it does
   not have to handle a database written by a previous version, and it can be
   deleted once it has run. This removes the single biggest cost from every
   option below — options that looked expensive because of migration handling
   are now just a script.

2. **Compatibility code that exists only to serve an earlier build is now
   unjustifiable.** It was defensible while a real project might have been
   created by an older version. See "What the constraint makes deletable"
   below — this is now a concrete cleanup item, not a philosophical one.

Point 2 is the more valuable half and it is easy to miss, so it is recorded
here rather than left implicit.

### Measured: no database in existence needs any of it

Every `story.db` on the machine, excluding the plugin's own install copies:

| database | soft-delete cols | `drafts` table | entities | number fields stored as a string |
|---|---|---|---|---|
| `tests/fixtures/save-the-children` | ✅ | absent | 29 | **0** |
| `tests/fixtures/save-the-children` (installed copy) | ✅ | absent | 29 | **0** |
| `/media/theww/AI/TWW/…/browser-verification-test` | ✅ | absent | 37 | **0** |

So there is nothing to migrate. Both fixtures were last written by a build that
already had the current schema, and the one bug that motivated a whole
compatibility layer — B10, `act_count` stored as `'3'` — has left no bad data
behind in either.

### What the constraint makes deletable

Three pieces of live code exist **only** to tolerate a database written by an
earlier build. With no such database, they are complexity guarding nothing:

- **`core/db.py:125-134` `ensure_soft_delete_columns`** — adds `is_deleted` /
  `deleted_at` to a table that lacks them. Called on every `get_db`
  (`db.py:84`). The docstring says why: "any project created by an earlier
  build has no such column". There are no such projects. **The columns are in
  `SCHEMA_SQL`; a fresh project gets them.**
- **`core/db.py:149-160` `ensure_drafts_table`** — same argument, for the
  `drafts` table. **Neither existing database has one**, because drafts are
  transient.
- **`core/db.py:302-325` `_coerce_number`, the read half.** The docstring is
  explicit that it exists because "databases written before any write-side fix
  already hold the wrong type, and a write-side fix alone leaves every existing
  project broken while looking complete". Measured above: **zero** such rows
  exist. The write-side fix (`writes.py:270-274`) is the one that matters and
  it stays.

This is the same ladder rung as everywhere else: the best code is the code never
written. These three were written to serve a constraint that no longer exists.

**Not deleting any of it yet** — it is a behaviour change to every read path,
and the sequencing question below should be answered first.

### What the constraint unlocks for the questions below

- **Q1 (arc_beat composite) gets cheaper.** Making the composite id the value
  the agent supplies directly removes the string-slicing in three places
  (`story_export.py:164`, `:256`, and the reconstruction in
  `story_import.py:302-303`). That needed a data migration, which is now a
  one-time script. **This option is newly affordable and was written off too
  early.**
- **Q5 (hard rename vs alias) is settled by measurement, not preference.**
  Zero open drafts in both real projects, and drafts are transient. Hard
  rename, no alias.
- **Q3 (`type` vs `entity_type`) is unaffected** — it was never a data
  question, only a naming one.

---

## The problem as stated

The agent names an entity three different ways depending on which tool it is
calling, and a fourth way in the vocabulary the tools teach it:

| where | name | source |
|---|---|---|
| `story_draft` create op | `slug` | `tools/story_draft.py:51` |
| `story_draft` edit op | `entity_id` | `tools/story_draft.py:54` |
| `story_draft` delete op | `entity_id` | `tools/story_draft.py:55` |
| `story_draft` reorder op | `ordered_ids` | `tools/story_draft.py:57` |
| `story_retrieve` | `id` | `tools/story_retrieve.py:28` |
| `story_describe` (as a field) | `id` | `core/constants.py` schemas |
| the entity's own key, in the DB | `id` | `entities.id` |
| the exported filename | `{id}.md` | `tools/story_export.py:171` |
| the skill's own gloss | "`id` is the `slug` argument" | `skills/…/SKILL.md` |

**Three names for one value, plus a prose bridge between two of them.** The
bridge sentence is the diagnostic: a tool that needs to *explain* that `id` and
`slug` are the same string is telling you the two names should not both exist.
That sentence appears in `story_describe`'s own description
(`tools/story_describe.py:118`) and in the skill.

Alongside it, a second axis of the same problem: **`type` vs `entity_type`** in
the same op list. `create` uses `type`, `edit`/`delete`/`reorder` use
`entity_type`. `core/drafts.py:524` papers over it with
`op.get("entity_type") or op.get("type", "")`.

---

## What the id actually IS, measured

**The id is the markdown filename.** This is the load-bearing constraint and
it is not obvious from the tool surface. Verified in code:

- `tools/story_export.py:171` — `_write_note(project_path / folder / f"{entity_id}.md", …)`
- `tools/story_import.py:279` — `slug = note.stem`
- `tools/story_import.py:302-303` — arc beats reconstruct `f"{char_slug}-{beat_id}"`
  from the directory name plus the file stem
- `tools/story_import.py:70` — the "at risk" diff matches DB ids against
  `f.stem` of the note files

Measured on both real projects:

```
save-the-children          29 entities   17 note files match their id
browser-verification-test  37 entities   36 note files match their id  (1 never exported)
```

So the identity of an entity, its filename, and its id are **one thing**, not
three that happen to agree. Any change to the id is a change to the vault.

### The id is globally unique already

`core/writes.py:129-143` checks `SELECT type FROM entities WHERE id=?` and
rejects, with a message that names the conflicting type:

> `Id 'kael' is already used by a character. Entity ids are unique across all
> types — choose a different slug for this scene.`

Uniqueness across all types is enforced by the primary key and checked
defensively before the insert. There is no uniqueness *design* problem here.
This is worth stating plainly because the original framing assumed there was.

### Every real id is already a descriptive slug

From the two real projects, every single one:

```
scene        central-room-day      garden-dream      the-door-closes
location     the-central-room      the-garden-dream
character    dr-elena-voss         the-administrator
act          act-1
arc_beat     kael-1                mira-the-leap
relationship kael-the-administrator
```

Not one opaque identifier, because the LLM writes them. The ids are already
doing the job a "dramatic intent" id was supposed to do.

### The dashboard already has the convention being proposed

The proposal was "make the dashboard use its own display field instead of the
id". It already does. Across `src/dashboard/js/`:

```js
scenes.js:58          s.title || s.id
entity-panels.js:8    act.title || act.id
entity-panels.js:13   seq.title || sid
entity-panels.js:51   data-hermes-send="… '${act.title || act.id}'?"
entity-panels.js:67   num ? `${num}. ${s.title || s.id}` : (s.title || s.id)
statistics.js:215     a.title || a.id
core.js:63            s.title = s.title || s.id   // ensure title exists
```

**id is the key, `title`/`name` is the display, the id is only ever a
fallback.** The proposed change is the existing behaviour. Whether the
fallback should exist at all is a separate, much smaller question (an entity
with an empty title currently renders its id, which is fine).

---

## The proposal, assessed

The proposal had three parts. Assessed separately, because they do not have
the same answer.

### Part 1 — "stop the LLM providing ids; generate unique ids on create"

**Rejected on the evidence, not on principle.** Three reasons:

1. **It does not fix the stated problem.** The problem is three *names* for one
   value. Generating the value differently does not reduce the number of names.
   The confusion an agent has is "is this argument called `slug` or `id`", not
   "is this string meaningful".

2. **It costs the vault.** An opaque id means `arcs/kael/a3f9c2.md`. The round
   trip still works — `story_import` reads the stem and rebuilds the composite
   — but the markdown vault becomes a directory of meaningless filenames. The
   export tool's stated purpose is to "publish the project as readable notes"
   (`tools/story_export.py:10-12`). Opaque ids contradict that purpose
   directly. A vault of `a3f9c2.md` files is not a readable note.

3. **It removes a capability rather than fixing a defect.** An LLM-authored id
   is self-documenting in every place the id surfaces: the load payload, the
   export filename, a `parent_id` in a relation row, a filename in an error
   message. `the-door-closes` and `a3f9c2` are equally valid primary keys;
   only one of them tells the reader what the scene is. Nothing in the
   evidence shows this capability causing harm.

There is a legitimate weaker version of this: **the LLM should not have to
invent a globally unique string across all ten types**, and it can collide with
itself. That is real, it is already handled with a clear error, and it is a
*usability* observation rather than a correctness one. If it is worth acting
on, the cheap version is to scope uniqueness to `(type, id)` — but that is a
data-model change affecting the primary key and every reader, and nothing
measured here says it is needed. **Not recommended without a concrete failure
to point at.**

### Part 2 — "id is the universal way to call an entity; no more double ways"

**This is the real defect, and it is a rename.** Four names collapse to one.
No stored value changes, so no data migration and no change to the vault.

### Part 3 — "the dashboard should use its own field"

**Already true.** See above. No work.

---

## Open questions, still to be answered

Not yet investigated. Listed so the next step is unambiguous.

- [x] **Q1. Does the arc_beat composite id survive a rename, and should the
      composite simply *be* the id?** **Round trip verified correct today.**
      `columns_for_insert` (`core/entity.py:291-294`) builds
      `{character}-{slug}` from a beat slug the agent supplies; export
      re-derives the beat part by string-slicing
      `entity_id[len(parent_id)+1:]` (`story_export.py:164`, again at `:256`).
      Measured on four character/slug pairs — `kael`+`first-doubt`,
      `dr-elena-voss`+`the-choice`, `kael`+`1`, `the-administrator`+`kael-1` —
      and all four slice back to exactly the beat slug that went in. So the
      round trip is **not** currently broken.
      **Still open:** the derivation is duplicated in three places and depends
      on the character id being an exact prefix, which holds by construction
      today and would break silently if that changed. Under the deployment
      constraint this is now affordable to fix (a one-time script, not a
      migration), and making the composite the id the agent supplies directly
      would delete all three sites. **Decide after Q2.**

- [x] **Q2. What exactly is broken *today*, in a live session? — ANSWERED
      2026-09-28: a silent wrong-entity write, reproduced.** Not confusion. The
      arc-beat composite id was resolved with `id LIKE '%-{slug}'`, so
      `edit_entity(..., 'arc_beat', 'the-choice', ...)` matched every character
      owning a beat of that label, took the first, and returned
      `success: true`. Two characters, same beat label, one silently wrong
      write. Fixed by D5 step 2.
      **So it was a high-severity fix, not an I-improvement** — and the
      question that was right to ask first was the one that found it. Note the
      answer came from *deliberately trying to make the agent get it wrong*,
      exactly as this entry proposed.

- [x] **Q3. Is `type` vs `entity_type` in scope? — NO, assessed 2026-09-28.**
      It looked like the same class of defect as `slug`/`id`, in the same op
      list. Measured, it behaves the opposite way in the one way that matters:
      **sending the wrong name fails immediately and legibly**
      (`ops[0] (create) is missing: type.`), where `slug` was *accepted and
      silently reinterpreted* — the thing D5 step 2 existed to kill.

      **And the naming is internally consistent across both key pairs.** After
      step 3, `create` takes `{type, id}` and the others
      `{entity_type, entity_id}` — a create names a *new* entity, the others
      refer to an *existing* one, and both pairs follow that rule. It is one
      convention applied twice, not one name split in two.

      Both shapes are already documented in the `ops` description, so there is
      no bridge sentence to delete either. **Left as is.** Written up in
      `bugs.md` under "Resolved by investigation" so the next reader does not
      re-raise it as the obvious loose end from step 3.

- [x] **Q4. What about `FIELDS_TO_SKIP = {"id", "type"}`? — RESOLVED by D5
      step 5, in the opposite direction to what this entry assumed.** The id is
      still skipped on the *write* path (correct: the write path is given the id
      as an argument, so a frontmatter copy would be a second source). But the
      id is now written to the *note* by export, for all ten types, and read
      back by import. So the id round-trips through the vault, and `story_describe`
      advertising `id` on four types while six had none is now moot — the note
      carries it either way. The "third naming problem" is gone.

      Original entry follows:

      **Q4. What about `FIELDS_TO_SKIP = {"id", "type"}`?** The write path
      silently discards a frontmatter `id` (`core/entity.py:279`,
      `core/writes.py:253`, `:442`), while `story_describe` advertises `id` as
      a non-optional field on four types (scene, sequence, act, arc_beat) and
      not on the other six. Measured: no type's `column_map` contains `id`, so
      the field can never be written anywhere. An agent that dutifully fills in
      `id` gets a silent no-op. **This is a third naming problem** and it is
      arguably the sharpest one — a field the schema requires and the writer
      throws away. Related to B6 but not the same: B6 is the false-positive
      finding, this is the silent-drop.

- [x] **Q5. Renamed argument vs alias — SETTLED, hard rename, no alias.**
      Measured: **both real projects have zero open drafts** (the `drafts`
      table is created on demand and both are transient), and drafts are
      short-lived by design. So the blast radius of a hard rename is a draft
      staged in the window between deploying the change and committing it.
      An alias would be permanent code guarding a window that lasts seconds.

- [x] **Q6. Do the reference docs need the same edit? — NO, and the question is
      moot.** `skills/story-editor` and `skills/story-loader` are **obsolete**,
      kept deliberately as reference material for the proper skill that is still
      to be written. So `story_create` / `story_edit` / the `slug` argument in
      them are not drift to be fixed — they are a document waiting to be
      replaced. Editing a corpse is not maintenance.

      Measured anyway, because the measurement is what the new skill needs:
      **18 occurrences across six files**, and the real tool surface is
      `story_admin, story_backup, story_dashboard, story_describe, story_draft,
      story_export, story_import, story_load, story_memory, story_resolve,
      story_retrieve, story_search`. `story_draft` also *stages* a batch and
      commits it, so the prose about how to create is stale as well as the name.
      Recorded in `bugs.md` under "Stale tool names in `skills/`" so it is not
      re-raised as a bug.

- [x] **Q11. If ids become uuids, what does the exported vault look like? —
      MOOT.** Step 4 (generated ids) was cancelled: relations are looked up by
      id, so a generated id costs three round trips per referenced entity, and
      the alternative is matching relations by name, which is the silent
      wrong-entity write. Ids stay agent-supplied and readable. The underlying
      product question stands for whoever proposes uuids later, and it is
      recorded below — the vault is for reading, not only for backup.

      Original entry follows:

      **Q11. If ids become uuids, what does the exported vault look like?**
      `characters/1a28e84f-a0a8-45bf-b163-7b5a6cd4f4bc.md`. The file is
      filename-safe and the round trip is intact, but the vault stops being
      browsable — which is the export tool's stated purpose
      (`story_export.py:10-12`, "publish the project as readable notes"). The
      `name`/`title` is in the frontmatter, so Obsidian's search still finds
      things; only the *file browser* degrades. **This is the one real cost of
      uuids and it is a product decision, not a technical one** — whether the
      vault is for reading or is only a backup. Not answerable from the code.

- [ ] **Q7. Should the compat deletions happen before, with, or after the
      rename?** Three independent changes are now on the table: the argument
      rename, the arc_beat composite (Q1), and deleting the three compat
      pieces. Doing them in one commit makes the diff unreviewable and means a
      regression in any one is hard to attribute. Doing the deletions first
      means the rename sits on a simpler base. **Recommend: deletions first,
      as their own commit with the test suite as the check** — they are
      independent of naming, and if one of them breaks a reader, finding out
      before the rename is cheaper. Not decided; this is a sequencing opinion,
      not a finding.

---

## What a fix would look like, if one is approved

Recorded so the size is known before committing to it. **Not a proposal.**

The change is confined to the *argument names the agent types*. Stored values,
the DB schema, the exported filenames and the vault are untouched.

| site | from | to |
|---|---|---|
| `core/drafts.py:27` | `("type", "slug", …)` | `("type", "id", …)` |
| `core/drafts.py:425` | `op["slug"]` | `op["id"]` |
| `core/drafts.py:472` | `op.get("slug")` | `op.get("id")` |
| `core/drafts.py:527` | `op.get('slug', '')` | `op.get('id', '')` |
| `tools/story_draft.py:51` | schema text | schema text |
| `story_describe.py:118` | bridge sentence | **deleted** |
| `SKILL.md` | bridge sentence | **deleted** |
| `tests/` | 27 `"slug"` op-key sites, 9 `slug=` call sites | updated |

Plus, if Q3 is in scope: `type` → `entity_type` throughout, which retires the
`or op.get("type", "")` fallback at `core/drafts.py:524`.

Estimate: roughly 40 sites, most of them mechanical. The `slug=` keyword
arguments in `core/writes.py` are a separate question — those are Python
function parameters, not the agent-facing vocabulary, and renaming them is
cosmetic. **Leave them** unless there is a reason not to: the ladder says fix
what the agent sees, not what a developer types.

## Proposal 2 (2026-09-28) — remove the id burden; titles name the files

A second, more ambitious proposal: the agent should not create an id at all.
The system generates one. And the **filenames should be the title**, so the
division of function is clean — *id for data manipulation and retrieval, title
for everything user-facing.*

The division of function is right and worth keeping. Two of the three parts are
supported by the evidence; one is not. Assessed separately.

### Part A — "remove the burden to create an id from the agent" — **SOUND, and cheap**

The agent already supplies the display field on create (`name` for six types,
`title` for three, `label` for arc_beat — all landing in the single `name`
column). So the id can be *derived* from a value the agent is already passing,
with no new field and nothing new to ask for:

```
agent sends   {op: create, type: scene, frontmatter: {title: "The Door Closes", …}}
system derives id = "the-door-closes"   (slugified from the title, once)
```

The agent's burden drops to **zero** — it never types an id again. The id is
generated, uniqueness is the existing check at `writes.py:129-143` plus whatever
collision rule is chosen, and the agent cannot get it wrong because it never
supplies it. This is a strict improvement over today, where the agent invents a
globally-unique-across-ten-types string and is told to retry on collision.

**This is the part that should be built.** It is a rename plus a derivation in
one place (`columns_for_insert`), and under the deployment constraint the
existing ids need no migration at all — nothing has to read the old ones.

### Part B — "titles name the files" — **NOT SUPPORTED, and it breaks references**

This is where the measurement goes against the proposal. The filename is not a
display convenience; **it is the definition of the id**, because
`story_import` rebuilds the database from filenames
(`story_import.py:279` — `slug = note.stem`). So a title-keyed filename makes
the id *derived from a mutable field*, and ids are what everything else points
at.

**The retitle failure, traced through the real code:**

```
step 1  character id='kael', name='Kael'
        export → characters/Kael.md                    (title-keyed)
step 2  the author renames the character: name='Kael Renamed'
        export → characters/Kael Renamed.md
        the id in the database is STILL 'kael'
step 3  the DB is lost, story_import runs, reads the stem: 'Kael Renamed'
        every parent_id, relation and `extra` link still saying 'kael'
        now points at an id that does not exist. SILENTLY.
```

`scene.title`'s own description invites exactly this: *"Display name (freely
editable)"*. So the retitle is not an edge case, it is the advertised use of
the field. **Measured under the current scheme, the same edit is a non-event:**
the file stays `kael.md` and the id cannot drift from the file that defines it.

**And titles are not unique.** `save-the-children` contains two arc beats both
named **"The Choice"** (one under `kael`, one under `dr-elena-voss`). A
title-keyed filename needs a collision policy for a case that already exists in
the reference corpus — and a case-folding policy, since `The Choice` /
`the choice` collide on macOS and Windows.

**"Title" is also not one field.** Already three words for one job: `name` (6
types), `title` (3), `label` (1). The DB column is `name` for all ten, so the
*vault* is the only place the three words appear — and it is the one place with
no schema to reconcile them.

The full list of things a title-keyed vault would need: a slugifier, a
collision policy, a case-folding policy, a retitle policy (rename the file, or
leave a stale one), byte-length limits, reserved Windows names, and unicode
normalisation. **That is a slugifier with extra steps — and Part A already
buys the slugifier**, by deriving the id from the title once at creation and
then never touching it again.

### Part A′ — "we don't need to derive the id, we can use a UUID" (2026-09-28)

Correct, and simpler than the slugifier Part A implied. `uuid.uuid4()` is
stdlib, collision-free by construction, and needs no collision policy at all —
which retires Q8 outright. The agent still never supplies an id, so the burden
removal of Part A is preserved.

**Everything mechanical already works.** Measured, not assumed:

- **`_check_slug` accepts it.** It strips hyphens then tests `isalnum`, and a
  uuid4 is hex — `1a28e84f-a0a8-45bf-b163-7b5a6cd4f4bc` passes unchanged. No
  change to the validation.
- **It is filename-safe.** No `/`, no `\`, no `:`, 36 chars against a 255-byte
  limit. And case-insensitive collisions are impossible in practice.
- **The arc_beat composite still round-trips.** With a uuid parent,
  `export`'s slice `entity_id[len(parent_id)+1:]` recovers the beat uuid
  exactly — verified by parsing the sliced string back as a `UUID`. So Q1's
  string-slicing is *not* made worse by uuid ids.

**What it costs, measured on the real fixture.** Ids appear **90 times** in one
`story_load` payload for `save-the-children` (29 as node ids, 39 in
`parent_id`/`location_id`/`extra`, 22 across relation rows):

| | id chars in payload | payload | share |
|---|---|---|---|
| readable slugs | 372 | 4,142 | 9.0% |
| uuid4 | 1,044 | 4,142 | 25.2% |

**+672 chars, ~+168 tokens per `story_load`, +16% of the payload.** Real and
measurable — and note this is the *entire* id cost, not a rounding error
against it. But the payload this came from was itself the result of a redesign
whose stated purpose was removing ~12.9k tokens, so 168 is **1.3% of that
saving**. It is a cost worth naming, not a cost that decides the question.

**One real casualty: the arc_beat composite id becomes 73 characters.**

```
{parent_uuid}-{beat_uuid} = 1043da66-f7aa-4f52-a049-8a2e4b34dfe7-eeef6b33-…-942071d317bb
```

which is also the filename. It works, but a 73-char arc-beat filename is where
"the vault is readable" starts to strain, and it is a direct consequence of
composing two uuids. **If uuids are adopted, arc beats should stop composing
and just take their own uuid**, with the character link living in the
`parent_id` column where it already does. That is a simplification, not extra
work — the composite exists only to make the *filename* self-describing, which
is exactly the thing a uuid gives up.

**And one deletion it enables:** `writes.py:689`'s `id LIKE '%-{slug}'`
fallback for arc_beat lookups can never match a uuid, so it becomes dead code
under uuids. It is currently load-bearing for the wrong-entity bug already
found (two beats named "The Choice" — an edit silently hit the wrong one), so
**removing it is a fix, not a regression.**

**Ladder note, recorded not proposed:** the cost scales with id *length*, not
with "uuid-ness". A 6-hex short id would cost a sixth of uuid4 and still be
collision-free at this scale. Stating it so the choice is made knowingly — but
uuid4 is a stdlib one-liner and a short id is a hand-rolled generator, so
**uuid4 is the right rung unless the token cost is later shown to matter.**

**What uuid4 does *not* fix:** it does not reduce the number of *names*. Part A
still needs the rename (`slug` → `id` on the create op) for the vocabulary to
be consistent. Uuids fix who supplies the value; the rename fixes what it is
called. **Both, and they are independent.**

### What a generated id does and does not change — measured

**The agent stops supplying an id. The corpus does not have to stop having
readable ones.** These are separable, and conflating them is what would make
step 4 expensive. `entities.id` is a TEXT primary key; relations, `parent_id`
and every `extra` link store whatever string is there. A fixture built by hand
with `kael` as its id works unchanged under a code path that generates ids for
whatever the agent creates.

Measured cost of converting the fixtures as well:

```
kael 272 · act-1 88 · mira 72 · central-room-day 54 · the-central-room 45
seq-discovery 25 · the-resistance 9 · dr-elena-voss 8
= 493 occurrences across 25 test files
```

plus the markdown fixture, where **the filename is the id** — 20 note files and
11 arc beats keyed `parent-child`, all asserted by path in `test_round_trip.py`.

**Recommendation, now recorded in the build plan: do not convert them.** A test
saying `edit_entity(..., "kael", ...)` states its intent; the same test saying
`"95b392b8"` states nothing. The fixtures are the readable case and they
exercise the same code. One new test asserting distinctness and a retry covers
the generated case — that is the whole cost, against 493.

**What does change, necessarily:** the uniqueness error at `writes.py:132-143`
tells the caller to *"choose a different slug"*, which stops making sense the
moment the caller is not choosing one.

---

### Part A″ — how long does the id need to be? (2026-09-28)

`uuid4()` is 36 chars mostly out of habit, not necessity. Shorter stdlib
options, measured:

| generator | sample | chars | bits | P(collision @ 1000 entities) |
|---|---|---|---|---|
| `secrets.token_hex(3)` | `f04956` | **6** | 24 | 2.0% — 1 in 50 projects |
| `uuid4().hex[:8]` | `763adb02` | 8 | 32 | 0.008% — 1 in 12,000 |
| `secrets.token_hex(4)` | `95b392b8` | 8 | 32 | 0.008% |
| `uuid4().hex` | `8d575722b9e441cc…` | 32 | 128 | never |
| `uuid4()` | `f3e3db8b-f3b7-4d17-…` | 36 | 122 | never |

1000 entities is generous — the largest real project here has **37**. At 37 the
24-bit option is nowhere near a problem. `uuid4().hex[:8]` drops the hyphens
too, which is 4 chars saved for free.

**Cost against the real payload** (90 id appearances, 4,142-char `story_load`):

| | id chars | vs today | payload |
|---|---|---|---|
| readable slug (today) | 372 | — | — |
| **6-char** | 540 | +168 (~+42 tokens) | +4.1% |
| **8-char** | 720 | +348 (~+87 tokens) | +8.4% |
| 32-char | 2,880 | +2,508 | +60% |
| 36-char `uuid4()` | 3,240 | +2,868 (~+717 tokens) | +69% |

So the earlier "+168 tokens for uuid4" figure was wrong by 4× — I had costed 36
chars against 372 total, without counting that ids appear 90 times, not 29.
**The honest range is +42 to +87 tokens for a short id, versus +717 for
`uuid4()`.** Corrected here because the number was load-bearing in the
recommendation.

**A collision is caught, not silent — measured.** Forced one by stubbing the
generator to always return the same value:

```
first create:    OK
colliding create: REFUSED — Id '…' is already used by a character.
                  Entity ids are unique across all types.
```

The primary key plus the check at `writes.py:129-143` both hold. **So the
failure mode of a short id is a failed create, never a corrupted database** —
which moves the question from "will it collide" to "does the create path retry".

It does not retry today. A collision would surface as an error the agent has to
handle, and it would have no way to know whether to retry or change something.
**A retry loop is therefore not optional if the id is short** — it is ~3 lines
inside `create_entity`, and it is the price of the 6 or 8 chars. `uuid4()` buys
its length with the *absence* of that loop.

**The hand-rolled option, rejected.** `base36(6)` yields ~31 bits in 6 chars,
better than `token_hex(3)`'s 24. It needs `random.choice` in a loop — hand-rolled
code to save **zero** characters over a stdlib call. The ladder rejects it.

### Part B′ — "the filename does not need to be the id; it can be the title" (2026-09-28)

**Correct, and Part B's earlier rejection does not apply any more.** The reason
Part B failed was specific: *the filename is the definition of the id*, so
keying the filename on a mutable field made the **id** derive from the title,
and a retitle orphaned every reference. **Once the id is generated and stored,
that chain is broken** — the id is no longer derived from anything, so deriving
it from the filename is no longer a hazard. The objection was valid and is now
void. Recorded rather than deleted, because the reasoning is what shows why.

**The coupling is one field, and it is already half-migrated.** Measured — which
exported note types carry `id` in their frontmatter today:

| carries `id` in frontmatter | does not |
|---|---|
| `scene`, `sequence`, `act`, `arc_beat` | `project`, `character`, `location`, `world`, `plot`, `relationship` |

So the export side already writes the id into the note for the four types whose
schema declares an `id` field. **The other six simply never had the field
declared** — which is Q4's finding (a schema that advertises `id` on four types
and not six) arriving from the other direction.

**What import would have to change — three sites, and two are nearly free:**

- `story_import.py:279` — `slug = note.stem` → `slug = fm.get("id") or note.stem`.
  **One line.**
- `story_import.py:302` — `beat_id = fm.get("id", note.stem)`. **Already reads
  the frontmatter first.** Only the fallback's meaning changes.
- `story_import.py:60-70` (`_diff`) — globs `f.stem` to decide which DB entities
  are at risk. Would have to read each note's frontmatter instead. **The real
  work**, but it is the same function that already opens every file to import
  it, and it is one pass.

Plus: **add `id` to the export frontmatter for the six types that omit it**, so
every note is self-describing. That is the same schema change Q4 asks for, done
once.

**The retitle failure, re-tested under the new scheme.** Renaming a character
moves the file; the `id` in the frontmatter does not move; import reads the
frontmatter; the id is stable; every reference still resolves. **The failure I
demonstrated for Part B does not occur here.** That is the whole difference, and
it is entirely due to the id no longer being derived.

**What still needs a rule: filename uniqueness.** Measured against both real
projects — `save-the-children` has **1 collision among 27 files**: two entities
named *The Choice* both want `arc/the choice.md`. (Arc beats nest under
`arcs/{character}/` in the real layout so the parent disambiguates them, but two
characters or two plots sharing a name would collide, and that is legitimate —
*"The Stranger"* twice.)

**This is a much easier problem than id uniqueness, and that is the point.**
Nothing references a filename. A collision can be resolved by appending a
counter (`The Choice.md`, `The Choice 2.md`) and nothing breaks, because the id
lives in the frontmatter and is unaffected. By contrast an **id** collision
would be silent — every relation points at the id. So a generated id plus
title-keyed filenames moves the collision problem from the one place where
collisions are dangerous to the one place where they are cosmetic.

**So the position is now:**

- **id:** generated, `secrets.token_hex(4)`, stored in the DB *and* in every
  note's frontmatter. Never derived from anything.
- **filename:** the title, for humans. Unique within its folder, by counter if
  needed. Re-derived on every export, so a retitle renames the file and nothing
  else.
- **dashboard:** the title, which it already prefers — and, per the audit
  below, the id stays exactly where it is being used as a *key*.

**Every user-facing surface is the title, and the id is invisible unless you go
looking** — with one exception the audit found and the synthesis records: a
*broken* link has no title to show, so the dashboard says "unresolved" instead
of printing an id. That is the division of function asked for. It is a real
change to export and import, not a rename.

**Still open, and it is a product question (Q11, now sharper):** the exported
vault becomes readable again — `characters/Kael Renamed.md` — which *fixes* the
degradation a generated id would otherwise cause. That is a point in favour.
The cost is that a hand-edited filename in the vault no longer renames the
entity, and the id in the frontmatter becomes the authority instead. **That is
the right way round** (a file rename should not silently rename a character and
orphan its references), but it is a behaviour change for anyone who has been
using the vault as the source of truth.

---

**DECIDED 2026-09-28: `secrets.token_hex(4)`** — 8 chars, 32 bits. 32 bits is
where a collision stops mattering (1 in 12,000 projects at 1000 entities), it
is 4× cheaper per `story_load` than `uuid4().hex`, and the retry loop it
requires is ~3 lines inside `create_entity` and is worth having anyway. The
table below is kept as the record of the choice.

| | `secrets.token_hex(4)` (8 chars) | `uuid4()` (36 chars) |
|---|---|---|
| agent burden | zero | zero |
| collision | caught, retried | impossible |
| retry loop needed | **yes, ~3 lines** | no |
| cost per `story_load` | +87 tokens | +717 tokens |
| vault filename | `95b392b8.md` | `f3e3db8b-f3b7-….md` |
| vault browsable (Q11) | no | no |

**Both retire the same problems.** Neither is blocked by anything measured. The
difference is 630 tokens per `story_load` against ~3 lines of retry logic.

**Recommend `secrets.token_hex(4)`** — 32 bits is the point where a collision
becomes a non-event (1 in 12,000 projects), the retry loop is small and is
needed anyway for robustness, and 87 tokens is a fair price for ids that are
half the length of `uuid4().hex`. **But this is the one id decision where the
ladder does not settle it**, because both rungs are defensible and the
trade-off is tokens against three lines of code. Recorded as a choice to make,
not made.

---

## Dashboard audit — what actually shows an id, and what must not change

Recorded 2026-09-28 so the "title everywhere" decision does not sweep the
dashboard. **The rule: an id is a key everywhere except the specific fallbacks
listed below, and those fallbacks are the only thing that should change.**

### The distinction that matters

47 sites in `src/dashboard/js/` interpolate an id into a template string. Only
**three kinds** of those are display:

| kind | example | change? |
|---|---|---|
| **a key** — inside `onclick="…('${id}')"`, `data-id=`, or a `.find(x => x.id === y)` | `scenes.js:55` `data-id="${s.id}"` | **NO.** This is the id doing its job. |
| **a fallback** — `title \|\| id`, shown only when the title is empty | `scenes.js:58` `${s.title \|\| s.id}` | **These are the ones to look at.** |
| **a dead link** — rendered when the entity was *not found* | `entity-panels.js:70` `` `<span>${sid}</span>` `` | **Yes — this is the real defect.** |

The middle and the third are what "id used instead of title" actually means.
The first must not be touched, and a blanket find-and-replace would break it.

### The `title || id` fallbacks (16 sites)

All of the form `x.title || x.id` or `x.heading || x.id`, across
`scenes.js`, `entity-panels.js`, `panel-manager.js`, `statistics.js`,
`arc-graph.js`. **These are already correct** — the title is preferred and the
id only appears when there is no title. With generated ids the fallback becomes
*less* useful (an opaque `95b392b8` is worse to read than `kael` was) but it is
not *wrong*, and it is the right behaviour for an untitled entity.

**Recommendation: leave all 16 as they are.** They are not "id used instead of
title" — they are title with a last-resort fallback, which is correct. Changing
them would mean deciding what to show for an entity with no title at all, which
is a different question and has no answer better than the id.

### The dead-link fallbacks (4 sites) — this is the actual finding

These render a **raw id as visible text** precisely when the lookup *failed*:

| site | code | when |
|---|---|---|
| `entity-panels.js:70` | `` return sid ? `<span class="tag tag-scene">${sid}</span>` : '' `` | scene id not in `DASH.story.scenes` |
| `entity-panels.js:165` | `` return `<span class="tag tag-scene">${ref}</span>` `` | same, for arc-beat scene refs |
| `entity-panels.js:364` | `` return sid ? `<span class="tag tag-scene">${sid}</span>` : '' `` | same, in the plot panel |
| `entity-panels.js:78` | `` `<span class="relationship-name">${rel.with}</span>` `` | the *other* character not found |

**This is what a generated id makes worse.** Today a dangling reference shows
`the-door-closes`, which a human can read and match by eye. With an 8-char hex
id it shows `95b392b8` — opaque, unmatched, and impossible for a user to act on.
And the condition is a *broken link*, so the user is already looking at a
problem; the label is where they need it to be legible.

**The right fix is not "use the title" — the entity was not found, so there is
no title to use.** The right fix is to say so:

```js
return `<span class="tag tag-scene tag-missing" title="No entity with id ${sid}">⚠ unresolved</span>`
```

The id moves into the `title` attribute (still available for debugging, no
longer the visible label) and the user sees that the link is broken. **This is a
genuine improvement over both the current behaviour and anything title-based**,
and it is the only dashboard change this decision implies.

### Sites that must NOT change

- **Every `onclick="DASH.showScenePanel('${id}')"`** — 12+ occurrences. The id
  is the lookup key; a title would break the lookup, and titles are not unique
  (*"The Choice"* is two beats).
- **`data-id="${s.id}"`** (`scenes.js:55`) — DOM identity for selection.
- **Every `.find(x => x.id === y)`** — matching, not display.
- **`sceneIds` / `scene_ids`** passed to the renderer — structural.
- **`DASH.story.*.id` in the payload** — the load contract; unchanged.

### Net dashboard change

**One thing: the four dead-link fallbacks above.** Everything else in
`src/dashboard/js/` keeps using the id as a key, which is correct and is the
whole reason the id exists.

Recorded because "make everything use titles" is the kind of instruction that,
applied literally to this directory, breaks every click handler in the app.

---

## The synthesis

**Built. See `entity_identity_plan.md`** for the step-by-step record.

| step | outcome |
|---|---|
| 1 — delete two compatibility shims | done |
| 2 — drop the arc_beat composite id | **done — fixed a reproduced silent wrong-entity write** |
| 3 — one name for the entity id | done |
| 4 — generate the id | **cancelled** — costs three round trips per referenced entity |
| 5 — filenames by title, id in the frontmatter | done |

**892 tests, unchanged throughout.** The investigation's own questions are
answered: Q2 (a live mis-call, reproduced), Q4 (resolved by step 5, the
opposite way to what was assumed), Q6 (moot — the skills are obsolete, kept as reference),
Q11 (moot, step 4 is cancelled). Q3 (`type` vs `entity_type`) is still open and
is the obvious next piece of the same class.

**What this investigation got wrong, kept because it is the useful part:** the
`id` vs `slug` verdict. Every measurement in it was correct and the conclusion
was not — see the reversed entry in `bugs.md`. Measuring precisely what the
code does does not establish that it *should* do that, and "a missing bridge"
is not a defence of two names.
Baseline: 889 tests pass, and no step may commit with fewer.

> **The id is generated, stored, and never derived from anything. The title is
> the user-facing name — in the payload and in the exported filename, and in
> the dashboard wherever the entity was found. Where the lookup *failed*, the
> dashboard says so rather than showing an id.**

This is the agreed position as of 2026-09-28. It supersedes the earlier
"the filename is the id" framing in every place below, and the reasoning for
each part is in Parts A′/A″ (generation), B′ (filenames) and the dashboard
audit.

| | today | after |
|---|---|---|
| who supplies the id | the agent, as `slug` | nobody — `secrets.token_hex(4)` |
| what the op argument is called | `slug` / `entity_id` / `id` | `id`, everywhere |
| where the id lives | the filename | the DB **and** every note's frontmatter |
| the filename | `kael.md` | `Kael Renamed.md` |
| dashboard: entity found | `title \|\| id` | `title \|\| id` — **unchanged** |
| dashboard: entity *not* found | the raw id, as if it were a name | **"⚠ unresolved"**, id in a tooltip |
| dashboard: click handlers, `data-id`, `.find()` | the id | **the id — unchanged** |
| a retitle | moves nothing | renames one file, nothing structural |

**What is settled:** the generator (`secrets.token_hex(4)`), that the agent
supplies no id, that the op argument is `id`, that the id lives in frontmatter
as well as the DB, that filenames are titles, and — per the dashboard audit —
that **the dashboard's use of the id as a key is not touched at all.**

**What is NOT settled, and is a product judgement, not a measurement:**

- **[ ] Q11. Is the vault for reading, or only a backup?** Title-keyed
      filenames *improve* browsability — `characters/Kael Renamed.md`. The
      cost is that a hand-edited filename no longer renames the entity; the
      frontmatter `id` becomes the authority. That is the safer direction (a
      file rename should not orphan a character's references) but it *is* a
      behaviour change for anyone treating the vault as source of truth.
- **[ ] Q2 is still the gate.** No live mis-call caused by the naming has been
      reproduced. This remains an improvement to schedule deliberately rather
      than a defect to fix urgently — **unless the id-generation and
      frontmatter work is wanted on its own merits**, which is a legitimate
      reason to proceed.

**Rough size, for planning only — not a plan:**

| change | where |
|---|---|
| generate the id in `create_entity`, with retry | `core/writes.py` |
| drop the arc_beat composite; the character link is already `parent_id` | `core/entity.py:290-294`, `core/writes.py:682-693` |
| `id` declared + written on all ten types | `core/constants.py`, `core/writes.py` (`FIELDS_TO_SKIP`) |
| `slug` → `id` on the create op | `core/drafts.py` (4 sites), `tools/story_draft.py` |
| delete the two bridge sentences | `story_describe.py:118`, `SKILL.md` |
| export: write `id` everywhere, name files by title | `tools/story_export.py` |
| import: read the id from frontmatter | `tools/story_import.py:60-70, 279, 302` |
| update 27 `"slug"` op-key sites in tests | `tests/` |

Two of these — dropping the arc composite and deleting the `LIKE '%-{slug}'`
fallback — are **fixes for the wrong-entity bug already reproduced**, not
chores.

---

## The one decision that is already safe

Independent of everything above, and supported by the measurements in this
file:

**`slug` should keep meaning exactly one thing — a project directory name.**
`projects/<slug>/`, `story_resolve.resolve_project`, the `project` argument on
every tool ("Project slug or path"). That is a real, separate concept from an
entity's id, it *is* a filesystem path (so `_check_slug`'s traversal defence
is load-bearing there), and it should not be renamed to `id` as part of this
work. Conflating the two is how the vocabulary got confusing in the first
place.

---

## How this was verified

Every measurement above is reproducible. The probes are throwaway scripts,
not committed tests, because no fix is approved yet and a test would imply a
contract that has not been decided.

- id↔filename coupling: read `story_export.py:171`, `story_import.py:70,279,302`;
  counted matching note files in both real projects (17/29 and 36/37).
- uniqueness: read `writes.py:129-143`.
- real ids: `SELECT id, type, name FROM entities` on both projects.
- dashboard convention: grepped `title || …id` across `src/dashboard/js/`.
- arc_beat composite: called `columns_for_insert` directly on four
  character/slug pairs and re-derived the export slice for each.
- open drafts: `get_db` on both projects, `SELECT * FROM drafts` — zero rows.
- test surface: counted `"slug"` / `"entity_id"` / `slug=` across `tests/*.py`.
- schema `id` field: dumped which types declare it, and confirmed no
  `ENTITY_COLUMN_MAP` entry maps `id` anywhere.
- **compat code vs real data:** walked every `story.db` on the machine
  (excluding the plugin's install copies) and for each checked soft-delete
  columns, the presence of a `drafts` table, and every number-typed schema
  field for a string value. Three real databases, **all clean on all three
  counts.** This is the measurement behind "What the constraint makes
  deletable".
