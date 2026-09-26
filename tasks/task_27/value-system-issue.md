# Task 27 — Story value vs character value: two different things

**Status: built and verified.** Phases 1–5, 4.5 and 6 are implemented; 671 tests
passing. The field table below is what shipped — read it, not the decisions
section, which records how the design was reached. Implementation order and
every verification are in `implementation-plan.md` (same folder).
**Origin:** reviewing `story_load` view output against the live project
`browser-verification-test` (title: *Save the Children*). Commits `48ac493`,
`4c0a0f5`, `35ed290` on `dev` — 625 tests passing at time of writing.

---

## The problem

The plugin has one concept called "value" and applies it at two scopes that
mean different things.

**Story value** — the thematic exploration the whole work is about. A story
about *Trust*. Every container declares which value it is exploring and what
charge it opens and closes at.

**Character value** — what a specific person's arc explores. Kael explores
*Freedom*. Related to the story's *Trust* (it happens in its lens, and shapes
it), but **not the same thing** and not derivable from it. A protagonist's arc
may, but need not, run on the main value.

Today the schema does not distinguish these. Worse, the field names actively
invite the error: containers use `value` while characters use `arc_value`, so
the prefix reads as "the character's value, derived from the story's" — the
opposite of the intent.

### Evidence from the live project

```
project        value = Trust        positive → ironic
  act-1        value = Trust        positive → negative
    seq-discovery      Trust        positive → negative
      central-room-day    Trust     positive → negative
      central-room-night  Trust     negative → positive   ← the mainline turns
      the-core-day        Trust     positive → positive
  act-2        value = (unset)
    seq-confrontation  (unset)
      garden-day        Hope       positive → mixed      ← a second value
      garden-dream      Hope       positive → negative
      the-door-closes   Freedom    negative → positive   ← a third value
```

```
kael   arc_value = Freedom   negative → positive    ← the PROTAGONIST, not on Trust
mira   arc_value = Trust     negative → positive    ← on the same value as the story
```

Three concrete symptoms:

1. **The protagonist's arc is on a different value from the story's.** Nothing
   in the data records that `Freedom` is being explored *through the lens of*
   `Trust`, or how it affects it.

2. **`act-2` and its sequence are unset while its three scenes carry values.**
   This is drift: a container that does not name a value, containing scenes
   that run three different ones. Nothing detects or reports it.

3. **Scene-level `value` is ambiguous.** Is `garden-day: Hope` a story-level
   sub-theme, or Mira's/Kael's character value leaking into the story thread?
   The schema cannot say, and `view='story_value'` currently presents it as the
   latter without knowing.

---

## Root cause in the schema

| | story scope | character scope |
|---|---|---|
| origin | project `value` / `value_at_open` / `value_at_close` | character `arc_value` / `arc_value_at_open` / `arc_value_at_close` |
| per container | act / sequence / scene `value` + open/close | beat has **nothing** |
| continuous | **nothing** | beat `y` (−1…+1), `shift` ("positive → mixed") |
| graph | **none** | `src/dashboard/js/graph/arc-graph.js` plots beats |

**The asymmetry is the finding.** The character arc has a plottable curve; the
story value has only discrete words and cannot be graphed. And a character's
progression is unmeasurable at the only level where it actually happens —
6 beats exist, **none carries a value charge**. The character's arc is an
endpoint summary on the character entity with nothing in between.

---

## Decisions taken

1. **One vocabulary, scope distinguishes.** Same value words (`Trust`,
   `Freedom`), same charge words. The field name says whose arc it is. No
   separate naming scheme, and nothing named in a way that implies one derives
   from the other.

2. **`arc_beat` carries the per-character charge**, using the same field names
   as the character (scope is already carried by the entity type). The
   character's open/close are the *promise* — where this journey must start and
   end. The beats are the *path*, allowed to wobble, because the wobble is the
   drama.

3. **The story/character correspondence is NOT stored.** This was the
   correction that redirected the whole task. There is no field, no relation,
   no prose section for it, and deliberately no formula.

   The correspondence is a **process of revision**: write a scene, record the
   story value and each character's value *independently*, then evaluate
   against the existing shape. A beat that does not land on the character's
   declared close is a signal that the design needs adjusting — sometimes by
   rewriting scenes, sometimes by reshaping the arc itself. You keep shaping
   until both shapes hold.

   Encoding it as a relation would make a judgement look like a fact. The
   plugin's job is to make both sides visible at the same moment so the balance
   can be judged — not to compute it.

---

## Resolved

- **Where the correspondence lives:** nowhere in the data. It is the writing
  process. Recorded here so it is not re-litigated or re-encoded.
- **Naming:** `story_value*` on the story side, `character_value*` on the
  character side. Parallel, neither implying derivation from the other.
- **Beat granularity:** beats get the charge; the character keeps the promise.

### The three questions, now closed

**4. `y` is not redundant, and `shift` is not a duplicate of the charge pair.**
Three different kinds of data, all kept:

| | what it is | example |
|---|---|---|
| `value_at_open`/`_close` | a measurement on the charge scale | `positive → negative` |
| `y` | the sampled point a curve is drawn through | `-0.3` |
| `shift` | the dramaturgical reading, in the story's language | `suspicious doubt → active defiance` |

The charge pair is instrumentation; `shift` is the finding, and it is the one a
writer actually uses. `y` is the only one of the three that can be
interpolated, which is why `arc-graph.js` plots it. All three survive.

**Correction to an earlier proposal in this file:** `shift` was briefly
proposed for deletion as a duplicate of the charge pair. It is not one. The
storytelling reading and the scale reading carry different information, and
losing `shift` loses the dramatic interpretation of every turn.

**5. The story side gets `shift` and `y` too — and it is a real gap, measured.**
Against the live DB, *no story container has either field*:

```
project  story_value=Trust  open=positive  close=ironic   shift=None  y=None
act-1    story_value=Trust  open=positive  close=negative  shift=None  y=None
act-2    (unset)                                          shift=None  y=None
all 7 scenes                                              shift=None  y=None
all 6 arc_beat  y=0.2/-0.3/0.6/0.4…  shift='positive trust → suspicious doubt'
```

The reading and the curve existed only on the character side. That is the
asymmetry, stated as a measurement rather than an argument.

**6. Inheritance: the value word is stated once and inherited downward.**

- `project` states the story's value word. It is the only place.
- `act` / `sequence` / `scene` **inherit** it. No value word field.
- `character` states its own value word. The only place on that side.
- `arc_beat` **inherits** from its character. No value word field.

The charge pair, `shift` and `y` are per-entity everywhere. A charge is a
property of *this* scene, *this* beat — it is not inherited, because that is
where the story turns.

**Consequence, accepted:** the three live scenes carrying a second value lose
it — `garden-day`/`garden-dream` (`Hope`) and `the-door-closes` (`Freedom`).
That is symptom 3 resolving correctly: a character's value was recorded in a
story container. The `Hope` thread becomes a character value on Mira. A
genuine subplot needing its own theme is a `plot` concern, deferred — no field
until that case actually arrives.

### Field table (as shipped)

`shift` and `y` were later moved off `project` / `act` / `sequence` and left only
on `scene` and `arc_beat` — see [Revision 2](#revision-2--shift-and-y-are-scene-and-beat-only)
in `implementation-plan.md`. A `y` at act level could only be a prediction about
scenes that do not exist yet.

| scope | value word | charge | reading | curve |
|---|---|---|---|---|
| `project` | `story_value` | `story_value_at_open` / `_close` | — | — |
| `act` / `sequence` | *inherited* | `value_at_open` / `value_at_close` | — | — |
| `scene` | *inherited* | `value_at_open` / `value_at_close` | `shift` | `y` |
| `character` | `character_value` | `character_value_at_open` / `_close` | — | — |
| `arc_beat` | *inherited* | `character_value_at_open` / `_close` | `shift` | `y` |

`shift` and `y` are unprefixed on both sides on purpose: the prefix is only
needed where the ambiguity lives — the *identity* of the value. Each entity
carries exactly one value track, so its shift and its charge have only one
possible owner. The beat already works this way today.

The character carries no `shift`/`y`: it is the promise (where the arc must
start and end), not a sampled point. The beats are the path.

**Still open — one question, one default.** Whether a subplot can carry its own
value word. Default: no field until a real case appears; `plot` is the home if
it does.

**Deferred refinement, deliberately not designed.** The `story_value` view may
later include each character's value shape alongside the scene's story value.
Scene level keeps the story value — settled. Whether the view *also* shows the
per-character shape is a refinement to address after the main issue is solved
cleanly, not a reason to weaken the field table now.

**No migration function ships in the plugin.** See below.

---

## Migration: done once, by hand, never as code

The plugin is **not deployed**. Every project that exists — live and in-repo —
is a test project, and test data is worth less than a clean codebase. So:

- **No `_migrate_*` function** in `core/db.py`.
- **No backward-compatible reader.** Readers accept exactly one key name, so a
  stale key fails loudly instead of being silently tolerated forever.
- **No dual-write**, no deprecation shim, no "accept either key" branch.

Order of operations for the renames:

1. Back up each DB beside its project.
2. Rename the key in the schema (`core/constants.py`) and validators
   (`core/entity.py`).
3. Rename it in the **`.md` notes** *and* `.story/index.yaml` — every project
   and every test fixture. A DB-only rename silently reverts on the next
   `story_import`, because import rebuilds the DB from Markdown.
4. Grep the whole tree, `tests/fixtures/` included, for the old name. A fixture
   still carrying it reproduces the old behaviour and the regression reads as
   unfixed.
5. Re-import each project and read the values back. A rename that looks fine in
   the DB proves nothing until an import cycle has run over it.

**The one migration function already in the code is a different case, and stays
for now.** `core/db.py` `ensure_soft_delete_columns()` is called from both
`create_schema` and `get_db`. It is a **column** migration, not a data rename:
`CREATE TABLE IF NOT EXISTS` silently leaves an existing table alone, so a
project created by an earlier build has no `is_deleted` column and every reader
filtering on it dies with "no such column". It is a structural repair, not a
compatibility layer, and it is called from `get_db` because that is the one
function every read path routes through.

Once the plugin is deployed, every project comes from the current build and it
has no case to serve — delete it then, for the same reason a retained-but-
useless migration is a schema lie. The pre-soft-delete test databases still
exist today, so it is load-bearing and stays.

---

## Scope

Touches, when it happens: `core/constants.py` (schema), `core/entity.py`
(validators), `core/db.py` (backfill + reads), `tools/story_load.py`
(`story_value` and `arc` views), `src/dashboard/js/graph/arc-graph.js`, and a
skill that does not exist yet. Multi-session change.

**Suggested sequence:** schema and backfill first, so the data can hold the
distinction — then the views, then the skill. Do not start with the views; they
will encode a guess.

**Renames to perform (no backward-compatible reader, per the deployment rule):**

| from | to | where |
|---|---|---|
| `project.value` | `project.story_value` | schema, db, notes, `index.yaml` |
| `project.value_at_open` / `_close` | `story_value_at_open` / `_close` | same |
| `character.arc_value` | `character.character_value` | schema, db, notes, `index.yaml` |
| `character.arc_value_at_open` / `_close` | `character_value_at_open` / `_close` | same |
| `act`/`sequence`/`scene` `.value` | *field removed* (inherited) | schema, db, notes, `index.yaml` |

Added: `shift` + `y` on `act`/`sequence`/`scene`; `character_value_at_open` /
`_close` on `arc_beat`.

The `value_at_open`/`_close` names on `act`/`sequence`/`scene` are **unchanged**
— they are already scope-free, and the charge words are shared vocabulary. Only
the value *word* moves, and only where it is stated.

**Migration data:** live project `browser-verification-test` (1 project, 2 acts,
2 sequences, 7 scenes, 2 characters, 6 beats); the `save-the-children` test
fixture; every `.story/index.yaml`. A DB rename alone silently reverts on the
next `story_import`, because import rebuilds from the `.md` files — rename in
the notes **and** `index.yaml`. Backup alongside:
`.story/story.db.pre-valuekey-migration`.

**Known wrong today, deliberately left:** `view='story_value'` reads scene
`value`, which is where the conflation is visible. It currently presents
Kael's `Freedom` and the `Hope` thread as story-value threads. Once the field is
removed there is nothing to misread, so the view needs no filtering logic — the
bug cannot survive the change. Left in place until then so the problem stays
concrete while it is designed.

## Test project

`browser-verification-test` (title: *Save the Children*), at
`/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test`.
Contains the exact case this task is about: a protagonist on a different value
from the story, a second value thread, and an unset act containing both.

DB backup from the earlier `value_open` → `value_at_open` data rename:
`.story/story.db.pre-valuekey-migration`
