# Task 30 — Structure for the `hermes-story-architect` skill

Stage: **structure only**. Folder tree, file names, and the scope of each file.
No content drafted. Each file gets its own later stage.

Source of truth is the code at the time of writing (`tools/*.py` SCHEMAs,
`core/constants.py`, `core/entity.py`, `core/scene_content_lint.py`), with
`task_30/tool_note.md` and `task_30/sections.md` as raw material only.

This structure was **audited against the code**, not only reasoned about:
`task_30/structure-audit.md` records the checks, the one real hole it found (the
dashboard was in no file), and the two false alarms it produced. Re-run it
before adding to the tree.

---

## 1. The governing constraint: a tool that knows something wins

Eleven tools sit permanently in the model's context with rich `description`
strings and JSON Schemas. `story_describe` emits the full `ENTITY_SCHEMAS`
dictionary — every field, type, default, `optional`, `sub_fields`,
`is_reference`, `stored_as`, and the computed/read-only marker.

**Rule:** if a tool already reports it, the skill points at the tool and says
nothing more. Field names, field types, which fields are required, the shape of
`relationship.perspectives` and `plot.setups`, the op grammar, the tool
parameters — **none of that is a reference file.** Duplicating it creates a
second source of truth that rots on the next schema change.

Verified: `relationship.perspectives.sub_fields` is emitted by
`story_describe` today (`_entity_schemas` copies every schema key; the older
"sub_fields are dropped" note in `tool_note.md` is stale). A reference file
describing that shape would be documenting a fixed bug.

The same test was applied to the section vocabulary, and it failed — so the
tool was fixed rather than the file written. `story_describe` now emits
`standard_sections` per type, because those names are a **closed set**:
`core/writes.py` rejects an edit key that is not a field, a relation, or a
standard section, so an agent guessing a name loses the whole write. Nothing
else in the tool surface reported them.

What survives the filter is the knowledge **no tool emits**: what belongs in
each section, the dramatic model behind the fields, the craft of using them, and
the failure modes that are invisible in a JSON response. A tool can report a
name; only a person can say what goes in it.

### Theory and implementation are different folders, not a filter

Dramatic theory and this system's encoding of it are both needed, and mixing
them in one file is what makes a reference unusable: the reader cannot tell
whether a statement is a fact about stories or a decision this codebase made,
so they either re-learn McKee or trust our field names as though they were
dramatic truth. **So they are separated by folder, not filtered by a rule.**

The test, when writing any line:

| | `theory/` | `craft/` and `model/` |
|---|---|---|
| Answers | "what is a value / a beat / a climax?" | "what does *this system* call it, and what did we decide?" |
| Speaks about | stories | entities, fields, sections, tools |
| Changes when | the theory changes | the schema changes |
| If it were wrong | the writing is wrong | the data is wrong |

A line goes in `theory/` if a screenwriter working in another tool would still
find it true. It goes in `craft/` or `model/` if it would be false or
meaningless over there.

Measured on the archived material, the split is not close — which is why the
seam is worth a folder rather than a paragraph:

| Source | Lines | System-specific | McKee citation |
|---|---|---|---|
| `values.md` §1–6, §9, §10 | ~120 | 2 | 14 |
| `values.md` §8, §11–12 (field table, charge encoding) | ~180 | 60 | 1 |
| `plot.md` schema/derivation/coverage | ~120 | 14 | 0 |
| `plot.md` structural spectrum, main-plot theory | ~110 | 0 | 0 |
| `sections.md` "Theory Foundation" blocks (10 types) | ~57 | 0 | — |

Note the last row: `sections.md` already keeps theory and implementation apart,
per entity type — a *Theory Foundation* list, then an FM-fields list, then a
*Section Map* saying which informs which. That document is the precedent for
this split, and the tree adopts its discipline at folder level.

**Both folders are linked from SKILL.md, and the theory file for an entity is
the pointer to its implementation.** That is the whole point of the
distinction: an agent deciding how to write a scene reads the theory, then the
decision our system made about it, and never has to guess which is which.

Verified before relying on the archived field table: checked against
`core/constants.py`, only `project` and `character` carry their own value word;
`act`, `sequence`, `scene` and `arc_beat` inherit, and the charge/`shift`/`y`
fields sit where the table says. The archived material is a valid source for
both folders — it just has to be split along this line.

---

## 2. Proposed tree

```
skills/hermes-story-architect/
├── SKILL.md
└── references/
    ├── theory/                    ← pure dramatic theory, no fields, no tools
    │   ├── values.md
    │   ├── character-and-arc.md
    │   ├── scene-and-beat.md
    │   ├── structure-and-plot.md
    │   └── world-and-place.md
    ├── model/                     ← this system's vocabulary
    │   ├── entity-sections.md
    │   ├── value-system.md
    │   └── story-memory.md
    ├── craft/                     ← our decisions, in the act of writing
    │   ├── project-design.md
    │   ├── scene-design.md
    │   ├── character-and-arc.md
    │   ├── plot-and-structure.md
    │   └── world-and-place.md
    └── mechanics/                 ← how to read and write without losing data
        ├── screenplay-format.md
        │   └── samples/
        │       ├── scene-content-good.md
        │       └── scene-content-broken.md
        ├── staging-changes.md
        ├── reading-the-project.md
        ├── dashboard.md
        ├── ids-and-links.md
        └── project-lifecycle.md
```

Four folders, one question each:

- **theory/** — what a value, a beat, a climax *are*. True of any story, in any
  tool. Speaks about stories; never names a field.
- **model/** — what this system calls those things. The vocabulary the agent
  needs before it can act: sections, the value encoding, memory.
- **craft/** — what we decided, and how to apply it while writing. The bridge:
  where theory meets a specific entity and a specific decision.
- **mechanics/** — how to read and write without losing data.

**theory/ and craft/ are deliberately paired by name.** Same basename, two
folders: `theory/scene-and-beat.md` is what a scene is, `craft/scene-design.md`
is what this system does about it. The pairing is the navigation — SKILL.md
links to both, and each craft file names its theory file as the reason behind
the decision. A reader who lands in either one is one link from the other, and
never has to guess whether a statement is McKee or us.

The names are not all identical pairs, and deliberately: where theory and craft
genuinely cover different ground (`values.md` ↔ `value-system.md`,
`scene-and-beat.md` ↔ `scene-design.md`), the names say so rather than forcing
a false symmetry.

`samples/` sits under the one reference that needs worked examples. It is a
folder only where a parent earns it; the other three stay flat.

---

## 3. Scope of each file

Each line states what the file owns **and what it must not restate**.

### SKILL.md  (always loaded, target < 150 lines)

| Holds | Not in it |
|---|---|
| Purpose, and when to trigger | Any field name or type |
| The common loop: orient → understand → propose → confirm | Op grammar (`story_draft`'s schema has it) |
| Hard rules: every write goes through a draft; never commit unconfirmed; relay `preview_md` verbatim; propose, the human decides | The section vocabulary and the field names (`story_describe` has both) |
| When a fact belongs in memory, in one line — a decision, a direction, an open question, something that must not be contradicted | The four categories in full, the limits, the mutations |
| Tool routing: 11 tools, one line each — which question it answers | How a value charge is read |
| Pointer table to every reference file with its trigger, **paired theory → implementation** | Screenplay syntax; any dramatic theory |
| Ask before acting; never invent ids or slugs | |

### references/theory/

Pure dramatic theory. The test each line must pass: **a screenwriter working in
a different tool would still find it true.** No field names, no section
headings, no tool names, no "in this system". Where theory needs to point at an
implementation, it links to the `craft/` or `model/` file — one direction only.

**`values.md`** — what a value is and what it does: chargeable conditions rather
than moral judgements, the canonical value list, the P/C/CD/NN escalation
schema, and the dialectical progression (protagonist and antagonist as opposing
sides of one argument, beats as its turns, climax as its resolution). Why a
scene turns and an arc moves. From `values.md` §§1–6, 9–10. *Not in it:* the two
tracks, the charge fields, how `y` is derived — that is
`model/value-system.md`, and the link from here is how the agent knows the
difference.

> **This file belongs to no single entity type, and that is deliberate.** The
> other four theory files each serve named types; this one serves the *value
> track*, whose fields sit on six of them — `story_value_at_open/_close` on
> `project`, `value_at_open/_close` on `act` and `sequence`, the same plus
> `shift` and `y` on `scene`, and the `character_value_*` pair on `character`
> and `arc_beat`. An audit of the tree will therefore flag it as the one theory
> file with no owner. It is the shared substrate, not an orphan: split by type
> it would be duplicated six times, and the whole point of the two-track rule is
> that the track crosses types. Referenced from `model/value-system.md` and
> `craft/scene-design.md`.

**`character-and-arc.md`** — true character revealed only through choice under
pressure; depth as internal plus surface-vs-core contradiction; the three
conflict levels; desire as conscious and unconscious; the gap between
expectation and reality; what a beat is (action → gap → choice → shift) and what
an arc beat adds. Relationships as the crucible of revelation, subtext,
polarization, dramatic irony. From the Character, Arc Beat and Relationship
*Theory Foundation* blocks in `sections.md`, plus `values.md` §5 and §10.

**`scene-and-beat.md`** — a scene as story in miniature: action through
conflict in continuous time and space that turns a value-charged condition. The
scene-objective against the super-objective, conflict levels, beats as
action/reaction exchanges, the scene analysis (conflict → opening value → beats
→ closing value → turning point), and the dilemma as a choice between
irreconcilable goods. The seven dramatic roles. From the Scene *Theory
Foundation* block.

**`structure-and-plot.md`** — the hierarchy by scale of value change (beat →
scene → sequence → act → story), and what makes an act climax an absolute and
irreversible reversal. Sequence as hinge point. Plot as a designed pattern, the
four subplot types and what each does to the main plot, the structural spectrum
(Classical / Miniplot / Antiplot), and the inciting incident. From the Project,
Sequence, Act and Plot *Theory Foundation* blocks, plus `plot.md`'s spectrum.

**`world-and-place.md`** — setting as dramatic function rather than backdrop;
the world as antagonist and as cosmology; internal laws a story must obey once
set; values and power as the friction points for arcs; mood as emotional
register; the image system; creative limitation as the source of originality.
From the Location and World *Theory Foundation* blocks.

### references/model/

**`entity-sections.md`** — what belongs in each standard section, and when. The
tool now reports the *names* (`story_describe` emits
`standard_sections` per type, and they are a closed set the write path
enforces), so this file is not a vocabulary lookup — it is the expansion of
those names. For each section: the question it answers, what a filled one looks
like versus an empty placeholder, and the judgement of what to do when the
author has not decided. A new entity type adds a block here, not a new tool
call. *Not in it:* the section names themselves (`story_describe`), the theory
behind each section (that is `theory/`), and field names (`story_describe`).

**`value-system.md`** — how this system encodes value. The two tracks: the
story's value word lives on the project, the character's on the character, and
nothing derives one from the other. Containers inherit the word and charge it
per-entity; `shift` and `y` are never inherited. The charge words, the field
table by scope, and why a scene cannot open a second theme. The theory these
fields encode is `theory/values.md`. *Not in it:* the field names themselves
(`story_describe` carries them), and McKee.

**`story-memory.md`** — the four memory categories and, more importantly, *when
one belongs there*: a decision the user made, a direction for the story, an open
question, a fact that must not be contradicted. Memory is how a fact outlives the
conversation, so the failure mode is silence — the agent decides something in
chat and the next session starts blind. Also: one entry is one rule, never prose;
`story_load` returns the whole memory plus a live `usage` meter against a
**shared** 3000-character budget (300 per entry), so a full memory forces a
consolidation decision rather than a silent failure. The three mutations are
exact-match: `remove` and `replace` need the entry's complete existing text, so
read before writing. *Not in it:* the action and category parameters, the
limits (both are in the tool schema and in `story_load`'s own response), and the
continuity-checking method — see below.

### references/craft/

Where theory meets a decision. Each file names its `theory/` counterpart in its
first paragraph, so the agent can always get from "what our system decided" to
"why that is defensible" in one hop. Each states a decision *this codebase*
made, or a judgement the agent cannot make from the entity in front of it.

**`scene-design.md`** — what a scene needs before it is worth staging: a turn,
not an event. How opening and closing charge relate to the turn point, what to
put in each scene section when the author has not decided it, and how a scene's
role in the larger structure is expressed. Pairs with `theory/scene-and-beat.md`.

**`character-and-arc.md`** — building a character: identity, desire,
contradiction, the gap; and how a character arc differs from the story's value
arc, which is the second track and never a mismatch. Where a beat's four
elements go when the author has given three of them. Pairs with
`theory/character-and-arc.md`.

**`plot-and-structure.md`** — the act/sequence/scene hierarchy in practice, main
vs sub, where a climax belongs at each level, and what a plot's setups, crisis,
climax and payoffs are *for* as a set. Pairs with `theory/structure-and-plot.md`.

**`world-and-place.md`** — world rules as the antagonist in practice, values and
power as friction points, mood and image system, and what a `variant_of` variant
is for. That last one is purely ours — no theory behind it, only a decision.
Pairs with `theory/world-and-place.md`.

**`project-design.md`** — shaping the story itself, before there are characters
or scenes to write. The `project` entity is where premise, spine, controlling
idea, the value arc and the structure choice live, and it is the one type with
no craft file — the audit caught that `craft/` was organised by task while
`project` had no task. What this system decided about that work: only `name` is
required and the other nineteen fields fall back to defaults, so a project can
be created nearly empty and filled as the thinking happens; nothing on it is
computed, so every field is a judgement the user makes rather than something
the system derives. The judgement is in the *order* — a premise that is not yet
a spine, a spine with no controlling idea, a structure chosen before the value
is known. **A project cannot be drafted** (see `mechanics/project-lifecycle.md`),
so this is the one creative step that does not go through the review loop, and
that makes it the step most worth being careful about. Pairs with
`theory/structure-and-plot.md`.

### references/mechanics/

**`screenplay-format.md`** — Fountain syntax for `scene.Content`. The single
most expensive silent failure in the system: a cue written inline renders as a
wall of prose, and a missing leading heading makes the scene vanish from the
script entirely with no error anywhere. `core/scene_content_lint.py` catches
only the missing opening heading — the rest of the format is on the author.
*Samples live in `samples/`*, not inline.

**`staging-changes.md`** — the write path as the agent experiences it: staging
is inert, restaging replaces the proposal and reports the delta, one batch per
decision, reading `validation` findings before asking for confirmation, and
never passing a `commit` error straight through. *Not in it:* the op grammar —
`story_draft`'s schema declares every op kind's fields, so it is tool knowledge
and §1 sends it there. That leaves five behaviours; if the schema covers them
too, the file may not earn its own place. Decide when it is written.

**`reading-the-project.md`** — which `story_load` view answers which question,
and how to read what comes back. The routing decision is a judgement the tool
description cannot make for you: five views, each built for a different question,
and picking the wrong one costs a second call. The base view needs `project` and
nothing else — the other six parameters are view-scoped and optional — and it
returns the structure, the project row and the full story memory, so it is both
the first call of a session and the cheapest way to read what has been decided.
*Not in it:* the parameter list, the tree shape, or the old index format (that
surface is `story_load`'s now).

**`dashboard.md`** — the surface the human actually looks at. Eight views
(story, character web, relationships, scenes, locations, plots, worlds, script)
and what each one answers, so the agent can tell the user what a change did to
the shape of their story rather than only what it did to a field. Two things
the agent cannot guess and this states: the plugin **opens the dashboard by
itself** after a successful commit (a `post_tool_call` hook dispatches it), so
calling `story_dashboard` unprompted is noise; and **scene order is the
screenplay** — `core/screenplay.py` assembles scenes in order into one script,
which is the whole reason `reorder` exists. *Not in it:* the dashboard's own
UI, or the statistics it computes.

**`ids-and-links.md`** — slug conventions for new entities, what a
reference-valued field expects, which fields are computed and must never be
written, and the `is_reference` flag as the tie-breaker. *Not in it:* the
field-by-field list (`story_describe`).

**`project-lifecycle.md`** — the operations outside the draft path:
`create_project`, `list_projects`, `restore`, `purge`, `backup`, `export`, and
the destructive `import` with its dry-run-first rule. This exists because these
are the calls that lose work, and the agent needs the ordering (back up before
import) more than the parameters.

`create_project` is the one that is not administrative. **A project cannot be
drafted** — `story_draft` refuses a `project` op outright, because a project
that does not exist has no database to hold the draft. So the first creative act
in the plugin bypasses the review loop that protects every other write, and
there is no preview to show the user before it lands. It is also forgiving in
the other direction: only `name` is required and the other nineteen fields fall
back to schema defaults, so a project can be created nearly empty and filled in
later through ordinary drafts. That combination — the one unprotected step, and
the one with the most room to start small — is what the file has to make the
agent think about. *Not in it:* parameter lists.

### Dropped: `craft/continuity-review.md`

No tool runs a continuity check, so the file would have been the agent inventing
a method and then reporting its own invention as a finding. A finding with no
cited field is a guess, and a skill that teaches guessing is worse than no
skill.

Continuity is not abandoned, though — it is *recorded* rather than *audited*.
The `continuity_warnings` memory category is the durable half: a fact that must
not be contradicted, written once and returned by every later `story_load`. That
covers what the review file would have claimed authority over, using a mechanism
that already exists, and it does not ask the agent to invent findings. Add the
audit back when a tool can run one.

---

## 4. Distribution rules

1. **One aspect per file.** A file that needs a second subject becomes two
   files, each linked from SKILL.md.
2. **SKILL.md links to every file directly** — one hop. Sub-folders organise
   for humans; they never form a chain the agent has to traverse. The guide's
   partial-read warning is the reason: a file two links deep may never be
   opened. The theory↔implementation pair is not a chain — both files hang off
   SKILL.md, side by side.
3. **No code blocks in SKILL.md or in references.** Worked examples live in a
   `samples/` folder, read when the agent needs the shape rather than the rule.
4. **A fact lives in exactly one file.** When a rule is needed in two places,
   the second is a pointer.
5. **A tool that knows it wins.** If `story_describe` or a field's own
   description reports it, it is not a reference file. See §1.
6. **Theory never names a field; implementation always names its theory.** The
   one direction is the whole separation. A `craft/` or `model/` file that
   states a decision links to the `theory/` file that makes it defensible; a
   `theory/` file that needs to point at an implementation links outward once
   and never imports the vocabulary back.
7. **Every reference opens with what it covers**, and with a table of contents
   past ~100 lines, so a partial read still shows the scope.

---

## 5. Open questions

1. **Should this be one skill or several?** The guide's argument for splitting is
   domains rarely needed together. Here every task needs the same loop and the
   same write path, so one skill with a reference tree is the honest reading.
   Splitting would only save context on the files a given task skips — which
   the tree already does. Confirm one skill.
2. ~~**How much dramatic theory survives?**~~ **Settled by decision, not by
   measurement.** Both halves are kept, in separate folders: `theory/` holds
   what is true of any story, `craft/` and `model/` hold what this system
   decided. My earlier measurement (§1) is what showed the seam is real — it
   is not the reason for the split. The test for each line is now "would a
   screenwriter in another tool still find this true?", and the link runs one
   way only: implementation names its theory, never the reverse.
3. ~~**Does `continuity-review.md` earn its place now?**~~ Dropped. Continuity
   is recorded through the `continuity_warnings` memory category instead of
   audited by an invented method; see §3.
4. ~~**Do the `tool_note.md` workarounds become reference files or code fixes?**~~
   Settled: they were code fixes, and they are done. `story_draft`'s schema
   now declares every op kind's fields, built from the same tables
   `validate_ops` enforces, so there is nothing for a skill to document.
5. **Tree depth.** Three folders is a bet that the model folder and the craft
   folder stay roughly equal. If `craft/` keeps splitting, the tree needs a
   second level there.
