# Task 30 — Structure audit against the code

Run after the tree was designed, to test it rather than re-read it. Every claim
below was checked by executing the code, not by reading the design doc.

Method: a script per concern, each stating an assumption and returning whether
the code supports it. Two assumptions failed. Both were traced to their cause
before acting, because a failing check is not the same as a wrong design.

---

## 1. Confirmed

| Assumption | Result |
|---|---|
| Every one of the 10 entity types has a home in the tree | holds — no type unaccounted for |
| `reorder` works on scene and sequence only | holds — `REORDERABLE_TYPES = ('scene', 'sequence')` |
| All 10 types report a non-empty section list | holds — after 1dfe241 |
| `story_load` has the five views the file claims | holds — `arc, story_value, dramatic_elements, relationship, unfilled` |
| The scene-content lint catches only a missing opening heading | holds — an inline cue `ELIAS: You could have telephoned.` returns one finding, and it is about the heading, not the cue |
| `fountain_validator` is not on the write path | holds — nothing in `core/writes.py` imports it |
| `is_reference` is emitted where it matters | holds — scene reports `location, sequence_id, act_id, characters` |
| `story_admin` really has restore and purge | holds — all five actions present |

## 2. The one real hole: the dashboard is in no file

**`grep` over the whole design doc: zero mentions of `dashboard`, `preview
pane`, `desktop_preview`, `screenplay view`, or `statistics`.**

The tree was built from the tools and the entity types, and the dashboard fell
between them. It is not a minor surface:

- Eight views — `story, graph, relationships, scenes, locations, plots, worlds,
  script` — which is what the human actually looks at.
- `story_dashboard` is a registered tool whose description tells the agent to
  pass the URL to `desktop_preview`. That instruction lives only in the schema.
- The plugin auto-opens it: `__init__.py` registers a `post_tool_call` hook that
  dispatches `story_dashboard` after a successful commit. The agent never asks;
  the dashboard appears as a side effect of writing.

So the agent populates a surface it has no model of, and — the part that
mattered — nothing in the tree said that **scene order is what produces the
screenplay**. `core/screenplay.py` assembles scenes in order into one script,
which is the entire reason `reorder` exists.

Added `mechanics/dashboard.md` — but scoped down hard, and the first draft was
wrong. See §3.

## 3. The dashboard file is two facts long, not a view guide

The first scope for `dashboard.md` was the eight views and what each one
answers, on the reasoning that the agent should be able to tell the user what a
change did to the shape of their story. That is wrong on the same rule the rest
of the tree is built on: **the views are derived from the entities.** The
character web is built from relationships, the arc graph from arc beats, the
statistics from value charges, the view list from what exists. The agent already
knows all of it from what it has staged — documenting the views would be a
second source of truth for something computed, and would go stale the moment a
view changed.

What survives is what is *not* derivable from the data, because it is a property
of the plumbing rather than of the story:

1. The plugin opens the dashboard by itself after a commit, so an unprompted
   `story_dashboard` call is noise.
2. Scene order is the screenplay.

Two facts, and both are needed — the first stops the agent doing something
useless after every commit, the second is the reason a user moving a scene is
making a decision about a film. Everything else about the dashboard is the
user's to look at, and the file says so rather than describing it.

The general form of this, worth keeping: **a derived surface does not need a
reference file, it needs a note that it is derived.** The same test that removed
the field names and the section vocabulary removes the view list.


## 4. A file that looks orphaned but is not: `theory/values.md`

The audit flagged that `values.md` is the one theory file with no owning entity
type. It is not orphaned — it is the shared substrate. The value track's fields
appear on six types:

    project      story_value_at_open, story_value_at_close
    act          value_at_open, value_at_close
    sequence     value_at_open, value_at_close
    scene        value_at_open, value_at_close, shift, y
    character    character_value_at_open, character_value_at_close
    arc_beat     character_value_at_open, character_value_at_close, shift, y

No single type owns the value, so no single theory file should. **The doc must
say this**, or a reader auditing the tree later will reach the same conclusion
and either delete the file or invent a redundant pair. Recorded as a note on
`theory/values.md` rather than left to be re-derived.

## 5. A second hole: `project` had no craft file

Found by asking what the *task*-organised folders covered, rather than what the
entity types covered. The first audit checked that all ten types had a theory
home and reported clean — but `craft/` is organised by what you are doing, not by
type, and `project` had no task. `grep` over the doc: `premise` 0, `spine` 0,
`controlling idea` 0, `structure_type` 0, `logline` 0.

The theory was covered — `theory/structure-and-plot.md` claims the Project
*Theory Foundation* block, and it has one. The craft was not: nothing anywhere
said how a story gets shaped before there are characters to write.

**Added `craft/project-design.md`.** What the code says about that work:

- Only `name` is required. The other nineteen fields fall back to schema
  defaults, so a project can be created nearly empty and filled as the thinking
  happens.
- Nothing on `project` is computed. Every field is a judgement the user makes
  rather than something the system derives — so unlike a character, there is no
  part of it the agent can fill in on the user's behalf.

## 6. The finding behind that: one creative step has no review loop

Verifying the above turned up something the tree had not stated anywhere.
**A project cannot be drafted:**

    stage(proj, [{"op": "create", "type": "project", ...}])
    -> DraftError: ops[0]: projects cannot be drafted.
       Call story_admin(action="create_project") directly.

The reason is structural — a project that does not exist yet has no database to
hold the draft. So `story_admin(action="create_project")` is the one creative
write in the plugin that lands with no `preview_md` and no confirmation, while
every character, scene and plot goes through the loop.

Verified the other side of it too, because the asymmetry could have been worse
than it is: once created, the project is editable through the ordinary draft
loop (`edit` on `entity_type: "project"` stages and previews normally), and
`story_admin(create_project)` with only `{name}` succeeds. So the exposure is one
call at the very start, not a permanently unguarded entity.

This belongs in `mechanics/project-lifecycle.md` as the reason to be careful
there, and it is the strongest argument for `craft/project-design.md` — the step
with no preview is the step where the user most needs to be asked rather than
assumed.

## 7. Two false alarms, and why

Worth recording so the same checks are not re-run.

**"memory is not in the base view"** — the check grepped `tools/story_load.py`
for the string `memory` and found none. False: `story_load` does not import it,
but its `view is None` branch calls `get_project_summary`, which does. Confirmed
by running it — the base view returns
`['acts', 'characters', 'confirmation', 'loaded', 'memory', 'plots', 'project',
'worlds']`. The grep looked in the wrong file.

**"base view takes only `project`"** — reported `extra: []`, which read as a
schema problem. The check subtracted a hardcoded parameter list from the real
one and got nothing; the check was malformed, not the schema. The real answer:
`required: ['project']`, and the other six parameters are view-scoped and
optional. `mechanics/reading-the-project.md` should say exactly that.

The lesson is the boring one: a failing assertion is a question, not a verdict.
Both of these looked like design holes and neither was.
