# Safeguard design — scene script format (answers a live-test question)

**Question raised 2026-09-28:** the only place the Fountain rules exist is
`skills/story-editor/references/screenplay-format.md`, and that skill has not
been written yet. Should there be a safeguard so malformed scene content
produces an error or advice — and it cannot hardcode a path to a skill that
does not exist yet?

**Answer: yes, and it must not name a skill path.** Recorded here as the
decision, so it is not relitigated when the skill is written.

**The rule to implement:** the finding states the problem and the fix in its
own words, and never references a file path. Something like

> `scene/the-last-watch`: 2 lines look like inline character cues ("ELIAS:",
> "MARA:") — Fountain wants a cue on its own line, ALL CAPS, with the dialogue
> indented beneath it.

is actionable without opening anything. A message that says "read
`skills/…/screenplay-format.md`" is actionable only if that file exists, is
loaded, and is found at that exact path — three ways to be wrong, and the
first two are certain to happen at some point (the skill is being renamed and
rewritten, and the reference is moving under the new
`skills/hermes-story-architect/` layout).

**Division of responsibility, which this settles:**

| concern | belongs in | why |
|---|---|---|
| teaching the format | the skill (prose) | an agent learning screenplay needs examples, not an error string |
| detecting the error | a **new** linter, called from `validate_shape` in `core/drafts.py` | it must run whether or not a skill is loaded |
| reporting the error | `story_draft`'s `validation` list | the agent is already told to relay this list |

**The new module does not modify `core/fountain_validator.py`.** That module
was built for script *import* — accepting a real, human-written screenplay —
and it is correct for that: permissive parsing is the right behaviour when the
input is someone else's finished work. Our case is the opposite, an agent
*writing* script from a documented format and needing to be told where it
departed. Parser vs linter, same input, opposite correct answer. So: a new
module, inspired by the existing one, and the existing one left intact for if
script import is ever built. **Two modules that both "validate Fountain" but
answer different questions is the naming trap of D2 repeating itself** — the
new one needs its own name, not a variant of the old one.

**The dashboard gets the second half.** Rendering malformed script as prose is
I1, and it is a separate fix: the dashboard should not assume its input is
well-formed. A renderer that falls back to `<pre>` when it cannot parse a scene
is more robust than one that assumes success — same lesson as B1 at a
different layer: do not trust that data arriving in a view was already checked.

**What this does not settle:** the new linter's name, and whether it reuses
`fountain_validator._classify_line` (probably — the *classification* of a line
is reusable, the *verdict* is not) or takes a simpler line of its own. Decide
when the fix is scheduled.

---

# Live-test bugs — found 2026-09-28

Defects found while live-testing `story_draft` / `story_admin` on project
`lighthouse-test`. **Not** skill instructions — agent-behaviour notes live in
`tool_note.md`. Each entry says what was observed, what is confirmed, and what
is still a guess.

**How to read these.** An agent writing the wrong data is not the finding —
it is the *symptom* of a design gap. A missing `sub_fields` in
`story_describe`, an undocumented list shape, two names for one concept: each
of those makes a particular mistake likely, and the mistake is the evidence
that the design is incomplete. So the entries below are written to answer
"what should change so the next agent does not walk into this", not "what did
the agent do wrong". Fixing the agent's behaviour without fixing the design
leaves the trap in place.

---

## Status index

Last reconciled **2026-09-28**, after **D5** closed (steps 1, 2, 3 and 5 built;
step 4 cancelled with its reason). Entries are not deleted when superseded — a
wrong diagnosis that vanishes is worth nothing — so the original text stays
under its correction. Two verdicts were reversed this round: the nine `extra`
links (D3) and `id` vs `slug`, which was recorded as "both correct in different
places" and was the wrong call.

## Where the bug-fix work stands (2026-09-28)

A sequence of live-test fixes is being landed one at a time, each with its own
analysis and its own commit, so any of them can be reverted independently.
**The test suite is the gate: 889 before this round, 892 now, and no fix may
land with fewer.**

| # | fix | state |
|---|---|---|
| 1 | **B6** — `REQUIRED_FIELDS` derived from the schema | **done, 891 pass** |
| 6 | **B12 + B12b** — placeholder defaults out of the data, and the title page says which slots are open | **done, 896 pass** — 10 false findings → 0 |
| 7 | **B15** — a lost check-then-insert race leaked `IntegrityError` to the user | **done, 897 pass** — found while investigating B1; 40/40 → 0/40 |
| 3 | **D5 step 1** — delete two compatibility shims | **done, 890 pass** — see the two corrections in the plan |
| 4 | **B13** — `number` coercion on every write path | **done, 892 pass** |
| 5 | **D5 step 2** — drop the arc_beat composite id | **done, 892 pass** — **fixed a reproduced silent wrong-entity write** |
| 5a | **D5 step 3** — one name for the entity id in the op vocabulary | **done, 892 pass** — `slug` now means only a project directory |
| 5b | **D5 step 4** — generate the id | **CANCELLED** — breaks one-batch creation; 3 round trips per reference |
| 6 | **D5 step 5** — filenames by title, id in the frontmatter | **done, 892 pass** — the id/title division, and a round trip that no longer loses data |

**B6 and B12 are the same lesson applied twice**: the schema already knew the
answer and a hand-maintained list beside it had drifted. B6 fixes the
required-field list; B12 fixes the placeholder defaults the enum check then
misreads. D5 is the third instance — three names for one value, held together
by prose bridges.

The D5 investigation, its two overturned positions, and the build order are in
`entity_identity.md` and `entity_identity_plan.md`.

### Fixed

| id | what | commit |
|---|---|---|
| B8 | `location_scene` relation now written on create and edit. **The recorded symptom was wrong** (the orphan check tests `world`, not scenes); the real cost was an empty location→scenes view in the dashboard. | `c8c31c3` |
| B4 / B5 | `stored_as` was guessed from the field's *name*, so `plot.characters` was called a relation when it is `extra`. Now derived from the declared maps, plus a new `is_reference` flag marking all 21 references. | `780b426` |
| I4 | `chars`/`loc` dropped. They cost 12 tokens (0.7% of the payload) and bought a second vocabulary. The 12.9k in the redesign spec is for the whole redesign, not these two keys. | `ce799d2` |
| D1a | `story_draft` skipped validation for every non-`create` op, so a preview could promise a change that was then dropped. Computed-field writes are now refused at preview. | `8ec315c` |
| B10 | A `number` arriving as a string is coerced on write (`core/writes.py:270-274`) **and** on read (`db._coerce_number`), because existing rows are already wrong and a write-side fix alone would not reach them. **Write side since rewritten** — one `entity.coerce_number` helper on every path; see B13. | — |
| I5 | `character.relationships` `sub_fields` declared — the only undeclared structured read in the payload. | `8ec315c` |
| B11 | A scene's `Content` must open with a scene heading. One rule, because it is the only format failure that is silent. | `0d4a795` |
| B15 | **A lost check-then-insert race leaked a raw database error.** `create_entity` checks for a duplicate with a SELECT and inserts separately, so a concurrent writer wins in between and the primary key's `IntegrityError: UNIQUE constraint failed: entities.id` reached the user verbatim. One `try`/`except` at the INSERT raises the message the check would have. | The user was told a constraint name and nothing about what to do. Measured 40/40 raw errors before, 0/40 after. The behaviour is unchanged — only the message. |
| B6 | `REQUIRED_FIELDS` is now **derived from `ENTITY_SCHEMAS`** instead of hand-maintained. The 12-line dict is deleted. A minimal arc beat went from 3 false findings (`id`, `y`, `order`) to none — and `plot.status` / `project.logline` were wrong too, unreported. One existing test asserted the bug. | A second copy of the schema with nothing keeping it honest. The guard test now fails on any future drift. |
| B13 | `create_project` never coerced a `number` field — B10's fix was on `edit_entity` only. **One helper, `entity.coerce_number`, now reached from every write path**; `create_entity` had neither fix and gained `order` coercion. The read half stays as defence in depth. | The same value was a string, an int and an int in three readers. The dashboard's `max()` on `act_count` was one string away from raising. |
| B12 | **34 placeholder strings are gone from the data layer.** They were field defaults written into the row on create, then rejected by the enum check as values the user had chosen — **10 false findings** on a minimal character/plot/project/arc beat. The 11 *real* defaults stayed (`status`, `type`, and `screenplay_title` → `'Default'`), and a test asserts the split. `UNFILLED = "N.A."` replaces the 34 for a surface that wants to say so. | Same harm as B6, wider blast radius — it fired on the three most-used types. Noise that trains the agent to ignore `validation`, which is the one thing `validation` exists to prevent. |
| **D5 s2** | A beat's id is its own slug, not `{character}-{beat}`. The `id LIKE '%-{slug}'` fallback is gone; the resolver is one exact primary-key match for every type. | **The one reproduced silent wrong-entity write of the round**: two characters each own a beat labelled "The Choice"; `edit(..., 'arc_beat', 'the-choice')` wrote to the first and returned `success: true`. |
| **D5 s3** | One name for the entity id in the op vocabulary. `create` says `id`, not `slug`; both prose bridges deleted. `slug` now means only a project directory. | A tool that has to explain that two names are one value is telling you they should not both exist. `story_admin` had the same defect in another shape — `WHERE id=? OR id=?`, both parameters bound to the same value. |
| **D5 s5** | Filenames are the title; the id lives in the frontmatter for all ten types; the arc folder is the character's title too. | The filename *was* the id, so renaming a note silently renamed the entity and every relation pointing at it. Now a hand-renamed note survives a round trip — and export → delete the database → re-import is **identical**, which it was not before. |
| **D5 s4** | **Cancelled, not built.** Relations are looked up by id, so a generated id costs three round trips per referenced entity, and the only way around that is to match relations by name — the silent wrong-entity write D5 s2 exists to kill. | Recorded because the plan is sound and someone will otherwise build it. The reasoning is kept in a collapsed section of the plan. |

### Resolved by investigation — not bugs

These were investigated and dismissed. Kept because the reasoning is the
valuable part, and because the next keeper will suspect them again.

| id | finding |
|---|---|
| D3 | **Not a defect.** The nine undeclared link fields (`scene.act_id`, `arc_beat.scene`, `plot.characters`, …) are documented as `extra` in `task_20/archived/data_model.md`, and the `act_id`/`sequence_id` redundancy is deliberate — see `verification_findings.md:45`. Columns are the load payload's spine, `extra` holds the rest *including links*, relations are many-to-many. Under that rule all nine are correct. **D3 is closed.** |
| D2 (naming) | **Not a defect.** `story_load` emits `chars`/`loc` for token cost (the redesign spec's first principle) and `story_describe` uses the names `story_draft` takes, where `edit_entity` rejects unknown keys by design. Neither side can be renamed. Resolved as a bridge (I3), then the bridge was deleted when the abbreviations went (I4). |
| B3 | **Not a bug.** `has_database: db.exists()` on a markdown-only project reports `false`, which is accurate — there is genuinely no database. Recorded so it is not re-investigated. |
| `id` vs `slug` | **Superseded — this entry was the wrong conclusion, and it is kept because it is instructive.** It read: *"both correct, in different places — `id` is the column, `slug` is the op argument."* True as a description, wrong as a verdict: the bridge between them had to be *written down twice* in prose, and a tool that must explain that two names are one value is telling you they should not both exist. D5 step 3 made the op argument `id`; `slug` now means only a project directory. |
| B8's original symptom | The orphan-check claim could not be reproduced. The check tests `world`. Correction is in the B8 entry above the original text. |
| D3's `location_scene` symptom | Same shape as B8 — the write was missing, the symptom was not where it was recorded. |

### Still open

| id | what | why it matters |
|---|---|---|
| **D4** | No shape validation at write time for structured values. Verified: no `sub_fields` reference in `core/writes.py` or `core/drafts.py`; both only check that `data`/`frontmatter` *is* a dict, not what is inside it. | D1/B7/B9 fixed the **read** side — the agent can now see the shape. Nothing stops it writing a wrong one, so a bare string can still land where an object belongs. The remaining half of the same class. |
| **B1** | `commit` reports failure for a commit that succeeded. **Re-measured: not this plugin** — one call is truthful, a second correctly says "No open draft", the hook never re-commits, and `registry.dispatch` fires no hooks. The symptom needs a *second* call from outside. **Not disproven either** — the bridge is upstream and still uninstrumented. | Silent — the agent may retry a write that landed. Belongs upstream with B2, which is the same layer. |
| **B2** | Objects nested inside array arguments lose their keys. **Not ours to fix** — the tool-call marshalling drops keys from native arrays; `ops` sent as a JSON string works. Silent data loss on a legitimate op shape. |
| **I2** | Nested object fields render as a raw Python dict repr in the draft preview (`perspectives` as `{'slug': 'prose'}` — single quotes, wraps mid-sentence). | Cosmetic, but the agent reads the wrong thing, and the reformatting hides content in a long line. |
| **D1 (partly)** | The tool cannot show the shape of a structured value. The **read** side is fixed; the **write** side is D4 above. | — |

### Deliberately not done

- **`skills/story-editor` and `skills/story-loader` are obsolete and stay that
  way.** They document `story_create` / `story_edit` (tools that do not exist)
  and the old `slug` argument, across 18 occurrences in six files. They are
  **kept deliberately as reference material** for the proper skill, which is
  still to be written. Fixing the names in a document that is about to be
  replaced would be maintenance of a corpse. The measurement is kept above so
  the new skill does not repeat it.
- **Inline-cue near-miss** (`MIRA: You knew?`) and the other adjacency checks
  B11 originally proposed. Real, but cosmetic: they become `action` and still
  render. Restating the spec in code would mean two things to update when the
  format evolves — the silent failures are the ones worth a check.

### The lesson from this round

**Four** of the diagnoses above were **wrong before measurement corrected them**:
the nine `extra` links, B8's orphan symptom, the "load-bearing" 12.9k figure,
and `id` vs `slug`. Two distinct failure shapes, and the second is the more
dangerous one:

1. **The symptom was in the wrong place** (the nine links, B8). The repo had the
   answer written down in `task_20/`. *Check the design docs before calling
   something a defect.*
2. **The code was described accurately and that was mistaken for a defence**
   (`id` vs `slug`). Every measurement was right — `id` was the column, `slug`
   was the op argument — and the conclusion *"not a bug, a missing bridge"* was
   still wrong. **A bridge that must be written down is not documentation, it is
   the cost of having two names.** The tell is a sentence explaining that two
   things are the same thing.

Failure shape 2 is the one to watch for, because it feels like rigour. Measuring
precisely what the code does does not establish that it *should* do that.

---

## Stale tool names in `skills/` — **NOT A BUG, by decision**

**Raised as B14 and withdrawn the same day. Recorded so it is not re-raised.**

**What was found.** Six files across `story-editor` and `story-loader` document
`story_create` and `story_edit`. Neither tool exists — the real ones are
`story_draft` (stage/commit) and `story_admin`. 18 occurrences. The worst row is
`skills/story-editor/SKILL.md:46`:

```
| `story_create` | Create new entity notes | `entity_type`, `slug`, `frontmatter` |
```

A missing tool, and a `slug` argument that D5 step 3 renamed to `id`.

**Why it is not a bug: `skills/story-editor` and `skills/story-loader` are
obsolete.** They are kept deliberately as **reference material** for the proper
skill, which is still to be written. Fixing the tool names in a document that is
about to be replaced would be maintenance of a corpse.

**The measurement is still worth keeping** — when the proper skill is written,
these are the traps it has to avoid:

- the tool surface is `story_admin, story_backup, story_dashboard,
  story_describe, story_draft, story_export, story_import, story_load,
  story_memory, story_resolve, story_retrieve, story_search`;
- `story_draft` does not create directly — it **stages a batch, then commits**,
  so the prose about *how* to create an entity is stale as well as the name;
- the id argument is `id`, never `slug` (D5 step 3).

**One exception worth noting:** `index-format.md` documents `id: project-slug` /
`id: character-slug` — it was *ahead* of the code, and D5 step 3 caught up to it.
That is what a maintained doc looks like, and it is the standard for the new one.

**This is the fourth time the pattern appeared this round** — a hand-maintained
list or document beside something the code already knows, drifting. B6 was the
schema, I4 the abbreviations, D5 the vocabulary, and this the docs. The fix is
the same in each case: derive it, or delete it.

---

## B15. A lost check-then-insert race leaks a raw database error — **FIXED 2026-09-28**

**Found while investigating B1, not by looking for it.** Two concurrent commits
on the same draft:

```
A: success=True  {'committed': True}
B: success=False {'failed': {'op': 'create character/kael',
                             'error': 'IntegrityError: UNIQUE constraint failed: entities.id'}}
```

**The user is told a database constraint name, and nothing about what to do.**
The message arrives through `drafts._call`'s `f"{type(e).__name__}: {e}"`, so the
raw `sqlite3` text is the whole report.

**Cause: `create_entity` checks for a duplicate with a SELECT, then inserts with
a separate statement.** Between them, a second writer can land the same id. The
primary key is the real guarantee — the SELECT is only there to give a friendlier
message — and when the race is lost the friendly path is bypassed entirely.

**Measured, not assumed — 40 races, before and after:**

| | raw `IntegrityError` escaping | friendly `ValueError` |
|---|---|---|
| before | **40 / 40** | 0 |
| after | **0 / 40** | **40** |

**The fix is one `try`/`except` around the INSERT**, raising the `ValueError` the
check would have raised. `core/writes.py` — so *every* caller benefits, not just
`commit`. Nothing else changed: the row is still refused, the transaction still
rolls back, the batch still stops and keeps its draft.

**The test is two real threads, and it fails without the fix** (verified by
stashing the change: `assert 'Entity already exists' in 'IntegrityError: UNIQUE
constraint failed: entities.id'`).

**One thing worth recording about writing that test.** The first version passed
*with and without* the fix. It passed `vault` where the helper wants
`vault/"projects"/"stc"`, so both threads opened a different database and never
raced — a test that could not fail was worse than no test, because it looked like
coverage. **The check that a test can fail is part of writing it**, and stashing
the fix is the only way to know.

**897 pass.**

**Still open in this area:** the *behaviour* under concurrency is unchanged —
one commit wins, the other is told the entity exists. This fixes the message, not
the race. Serialising commits is a design decision (a claim-the-draft transaction
conflicts with the "keep the draft on failure" resume contract) and is not
justified until something actually needs it.

---

## B1. `commit` sometimes reports failure for a commit that succeeded — **OPEN, not ours**

**Severity: high.** A successful write reported as a failure. **Intermittent.**

### Re-investigated 2026-09-28 — every claim above re-measured, and the plugin is exonerated

**Nothing in this repo produces the reported symptom.** Each claim, checked by
running it rather than by reading it:

| question | answer | how |
|---|---|---|
| can one `commit` call write and then report failure? | **no** | single call → `success: true`, entity on disk |
| does a second call misreport? | **no** — it says `"No open draft"` because the first consumed the row | ran it |
| does our `post_tool_call` hook re-commit? | **no** — it only dispatches `story_dashboard` | read `__init__.py:206-233` |
| does `ctx.dispatch_tool` re-fire hooks or re-invoke a handler? | **no** — `registry.dispatch` calls the handler once and fires no hooks | read `tools/registry.py:893-921` |
| is a commit slow enough to invite a retry? | **no** — commit 100ms, the hook's dashboard rebuild 6ms | timed 5 runs each |

**So the symptom requires a second `commit` call, and this plugin never makes
one.** The remaining candidates are all outside it: the agent calling commit
twice after not seeing a response, or the Hermes bridge dispatching twice.

**Not confirmed, and not assumed either way:** the double-dispatch hypothesis is
still just a hypothesis. It was not proven, and the investigation did not
disprove it — it established only that *this repo* is not the source. **The next
step is still to instrument the bridge, and it is upstream of this repo.**

**A live measurement was set up and did not fire.** The dashboard rebuilds
`<tmpdir>/<slug>.html` on every build, so watching that file counts builds with no
production code. The watcher ran and saw no rebuild, so the "the dashboard runs
twice" report was not reproduced in the window it was live for. **Worth retrying
with the trigger actually performed** — it is the cheapest remaining test, and
the file-watch approach works.

**One real bug *was* found on the way, and it is a different one** — see B15. The
concurrent-commit path leaked `IntegrityError: UNIQUE constraint failed:
entities.id` to the user, now fixed and measured at 40/40 → 0/40.

**Original entry follows, unchanged.**

**Severity: high.** A successful write reported as a failure. **Intermittent.**

**Observed twice, in opposite directions on consecutive commits:**

| draft | reported | actual |
|---|---|---|
| `d-20260928-004343` (2 chars + 1 location) | `{"error": "No open draft: ..."}` | fully written |
| `d-20260928-010136` (3 acts + 3 sequences) | `{"success": true, "committed": true}` | fully written |

**Confirmed:** the write happens; the response misreports it.

**Not the plugin. Reproduced clean.** `core.drafts.commit` called directly
against a fresh project, outside Hermes:

```
staged:               d-20260928-010029
COMMIT                → success, entity written, draft row gone
COMMIT (same id again) → {"error": "No open draft: ..."}   ← correct, it is gone
```

The plugin's commit path behaves exactly as specified: success once, then a
truthful error on a second attempt. The misreport only appears when the call
goes through the Hermes tool-call bridge.

**Leading hypothesis.** Double dispatch — the bridge invoking the handler
twice, the first committing and the second finding the row consumed. This is
the same layer already implicated in B2, which points at the bridge rather
than at the plugin. Not proven: no instrumentation of the bridge yet, and an
alternative not ruled out is that the bridge re-reads state after dispatch.

**Intermittency narrows nothing yet.** One clean commit does not exonerate the
plugin — it is consistent with a race, and with a duplicate dispatch that only
sometimes loses the first response. But it does mean the plugin suite cannot
reproduce this, so a passing test run is not evidence against the hypothesis.
Any test written to catch it must drive the *bridge*, not the handler.

**Why it matters.** The confirmation loop cannot survive this. The agent has a
legitimate reason to tell the user "that did not save" about changes already
in the database, and the user's next move — retry — writes on top of them.

**Next step:** instrument the bridge — count handler invocations per
`tool_call` — to confirm the double dispatch. If it fires there, this belongs
upstream with B2, and the two are likely one defect.

---

## B2. Objects nested inside array arguments lose their keys — **OPEN**

**Severity: high, but not ours to fix.**

**Observed.** Every `story_draft` call with `ops` as a native array of
objects failed:

```
ops[0].op must be one of ['create', 'delete', 'edit', 'reorder']; got None.
```

The handler receives `[{}]`. The same call with `ops` as a JSON **string**
succeeds first time. A list *value* sent natively also came back
double-nested (`[["a","b"]]` rather than `["a","b"]`).

**Confirmed not a plugin bug.** `core/drafts.py` stages correctly when the
handler is called directly with a native list. Both suspects in the Hermes
dispatch path pass the structure through untouched:
`schema_sanitizer.unrename_tool_args` and `arg_coercion.coerce_tool_args` were
each exercised directly and both are no-ops for this shape.

**Not yet established:** which layer does the stripping. The search covered
`tools/arg_coercion.py`, `tools/schema_sanitizer.py`,
`tools/tool_search_validation.py` and the plugin loader without finding it.

**Impact.** The model will hit this on every stage call until it is worked
around. The workaround (serialise `ops` to a string) is recorded as a skill
instruction in `tool_note.md` note 2.

**Next step:** decide between accepting both forms in the handler as a
defensive measure, and reporting the bridge defect upstream. Documenting the
string form in the tool schema is not sufficient on its own — the model emits
whatever the schema implies, and the schema implies a native array.

---

## B3. `list_projects` reports `has_database: false` for a markdown-only project — **NOT A BUG**

**Severity: none — correct behaviour, recorded so it is not re-investigated.**

`save-the-children` has no `.story/story.db` (it is markdown-only, holding
`project.md`, `screenplay.fountain` and entity folders). `list_projects`
reports `has_database: false` for it, which is accurate. Confirmed by listing
the directory.

---

# Improvements

Not defects. Things that work but should work better, found while using the
tools for real.

---

## I1. Scene script content is not presented as a screenplay — **RESOLVED (render side)**

**Superseded in part by B11.** The rendering half stands; the *detection* half
now has a fuller answer, and the two should be read together.

**Resolved on the preview side, 2026-09-28.** The *preview* half of I1 is
fixed: section bodies now render in a fenced block, one per section, always —
so a Fountain script stays intact from the slugline instead of being split at
the first indented cue. The delta goes in a one-line note outside the fence,
the body inside. Chosen as option C over "before + after, two blocks" (two
copies of a screenplay is worse than the delta being stated) and over "new
only" (the delta is the point of an edit preview). Implemented as `_fence` +
`_section_note` in `core/drafts.py`, used by both `_render_edit` and
`_render_create`, so create and edit look the same.

What this does **not** fix: the dashboard, `story_retrieve` and `story_export`
still flatten a scene body to prose. Those are the same defect at other
readouts and want one shared renderer — see the open question above.

**Found:** 2026-09-28, staging three scenes with Fountain `## Content`
prose, then opening the dashboard and seeing the script render as flat prose.

**What happens.** A scene's `Content` section holds real script — sluglines,
character cues, dialogue:

```
The burner is cold. The lamp is not.

ELIAS: You could have telephoned.
MARA: I did. Twice.
```

The draft preview renders it as one undifferentiated markdown block under
`**Content** —`. The line breaks survive, and the `ELIAS:` / `MARA:` cues are
visible, but nothing distinguishes a dialogue exchange from an action line. A
screenwriter reading the preview cannot see the shape of their own scene in it,
which is the main thing they would be checking before approving a commit.

**Why it matters.** The preview is the artefact the user approves. For every
other entity the field table is a fair representation of what is being stored.
For scene script it is not — the storage is structured (it is Fountain, and
`core/screenplay.py` already knows how to parse it) and the preview flattens it
to prose.

**What needs deciding, not doing now.** Whether to render scene `Content` as
fenced `fountain` code, or to actually typeset it (cue names right-aligned,
dialogue indented, parentheticals, transitions). Code-fencing is a few lines
and honest about what it is; typesetting is a renderer worth its own task and
would need a decision on whether it applies to the preview only or to export
as well. `core/screenplay.py` is the existing precedent for parsing — check
whether it can serve the rendering side before writing anything new.

**Open question worth answering while doing it:** does this also affect
`story_retrieve` and `story_export`? Both return scene content, and both would
have the same flattening. If the fix is a shared renderer, all three get it.

**Confirmed on the dashboard, which is the worst case.** The dashboard's
script view is where the failure is most visible: three scenes of genuinely
malformed script rendered as an undifferentiated wall of prose. The preview's
flat rendering and the dashboard's flat rendering are the same defect at two
readouts, which strengthens the case for one shared renderer (B11).

---

## I2. Nested object fields render as a raw Python dict repr — **OPEN**

**Found:** 2026-09-28, staging a `relationship`.

**What happens.** `perspectives` is a `{slug: prose}` object. The preview
renders it as the repr of a dict:

```
| perspectives | {'elias-kade': 'She is the only person who has ever come up
the rock to see it. He wants that to mean she believes him.', 'mara-venn':
'He is a keeper who files nothing, signs nothing...'} |
```

Single quotes, no line breaks, and it runs long enough to wrap mid-sentence.
It is the one field in the whole preview that does not read as prose, and it
is readable only by someone already used to Python.

**Why it matters, narrowly.** This is the field a writer most wants to *see*
when approving a relationship — it is the whole point of the entity, and the
one place two parallel descriptions sit side by side. Rendering it as a dict
repr hides the structure that makes it useful: two characters, two readings,
directly comparable. Rendering it as one labelled block per key makes the
comparison the point again.

**Cheapest honest fix.** A dict field gets one `**key** — value` line per
entry, the same shape sections already use. No new renderer, no typesetting
decision — unlike I1, nothing here is a screenplay.

**Worth checking while doing it:** is `perspectives` the only object-typed
field in any schema? If others exist they all have the same problem, and the
fix belongs in one place in the renderer rather than per-field.

---

## B4 / B5. `stored_as` was a guess from the field's name — **FIXED 2026-09-28**

Both entries had the same root cause and the same fix. `story_describe` built
its relation label from a flattened set of field *names* across all entity
types:

```python
_RELATION_FIELDS_BY_NAME = {field for fields in _RELATION_FIELDS.values() for field in fields}
...
if field in _RELATION_FIELDS_BY_NAME:
    entry["stored_as"] = "relation"
```

So `scene.characters` matched, and so did `plot.characters` and
`relationship.characters` — which are stored in `extra`. Measured before the
fix: **2 fields labelled with storage they do not have**, and nothing
distinguished a reference column from a plain value.

**The fix labels from the declared maps, not from names**, and only for fields
that are actually references:

| truth | how it is decided | count |
|---|---|---|
| `relation` | field is in `_RELATION_FIELDS[entity_type]` | 7 |
| `column` | its column name ends `_id` (a real reference) | 5 |
| unlabelled | everything else — `name`, `order`, `status`, `title` | 25 |

Labelling all 30 columns was the alternative, and it is worse: it buries the 12
that mean something under 18 that do not. A test asserts the 25 stay unlabelled.

**Also added `is_reference`**, which answers a question `stored_as` cannot: a
link in `extra` has no special storage, but its value is still another entity's
slug, and the agent needs to know that before writing one. Nine fields gain
it (`scene.act_id`, `arc_beat.scene`, `plot.characters`,
`relationship.characters`, the `*_scene_id` family, `primary_plot`), so all 21
references are now marked — 12 by declaration, 9 by the description saying
"slug".

**Two limits recorded rather than hidden:**

- `is_reference` is a **heuristic** for the undeclared nine: it reads the word
  "slug" out of the description. It therefore **misses `relationship.scenes`**
  ("Scenes where this relationship is featured"), which stays unlabelled. A real
  `is_reference` flag in `ENTITY_SCHEMAS` would retire the guess; that is a
  schema change, not a tool change, and is not made here.
- The word "slug" also appears in `id`'s own description, so `id` is explicitly
  excluded — it *is* the slug rather than pointing at one. A test guards it,
  because the error in that direction is as bad as the original.

**Why this mattered more than a label.** An agent told `plot.characters` is
relation-backed writes a relation; one told the truth writes frontmatter. Two
tools disagreeing about where a value goes is the same failure as B8, one layer
up — and the label was the only place the disagreement was visible.

---

## B4 / B5 (original entries) — **SUPERSEDED by the entry above**

### B4. `stored_as: relation` is advertised for fields that store in `extra`

**Severity: medium.** Silent. The data is not lost — it is stored somewhere
other than the schema says, so anything reading relations misses it.

**Observed.** Staging a `plot` and a `relationship`, then reading the tables
directly:

| field | `story_describe` says | actually stored as | relations created |
|---|---|---|---|
| `plot.setups` | relation | relation ✅ | `plot_setup` |
| `plot.crisis` | relation | relation ✅ | `plot_crisis` |
| `plot.climax` | relation | relation ✅ | `plot_climax` |
| `plot.payoffs` | relation | relation ✅ | `plot_payoff` |
| **`plot.characters`** | **relation** | **`extra`** ❌ | none |
| **`relationship.characters`** | **relation** | **`extra`** ❌ | none |
| **`relationship.scenes`** | **relation** | **`extra`** ❌ | none |

**Cause.** `core/entity.py:165` `_RELATION_FIELDS` lists relation fields per
entity type. `plot` lists only `setups` / `crisis` / `climax` / `payoffs`, and
`relationship` maps to an **empty dict**. Anything not listed there falls
through `columns_for_insert` into `extra` — the values are all present and
correct in `extra`, verified in SQLite.

So the four plot-scene relations are the only ones that ever get created.
`plot.characters` has been documented as a relation for as long as the schema
has existed, and has never been one.

**Why it matters.** Two readers disagree about where the data is. A
traversal that walks the `relations` table sees a plot with no characters and
a relationship with neither characters nor scenes — an entity that looks
empty. Anything keyed on relations (the dashboard graph, character arc
lookups, `story_load`'s index) is reading a partial picture, and nothing warns
that it is partial.

**Next step, before any fix is designed:** decide what the *correct* storage is
per field, because the two are not the same question.

- `plot.setups` etc. point at **scenes** and become `plot_setup` rows. That
  works and should stay.
- `plot.characters` and `relationship.characters` point at **characters**. A
  `character_plot` / `relationship_character` relation type may not exist in
  the schema at all — worth checking before assuming it should.
- `relationship.scenes` points at **scenes** from a *relationship*, which is a
  third shape again.

Adding rows to `_RELATION_FIELDS` without checking the relation types exist
would produce rows nothing reads. Check what the `save-the-children` fixture
has for these, since it predates all of this and is the reference corpus.

**Not urgent for the live test** — nothing we are doing depends on it, and the
data is intact. But the `stored_as` annotation in the schema is a promise the
code does not keep, and it should either be honoured or removed.

**Not a regression.** The `save-the-children` fixture's 11 relations are
`character_scene` (5), `location_scene` (3), `plot_setup` (2), `plot_payoff`
(1) — no `plot_character` there either. The draft commit path and the
pre-existing write path agree, and both predate task 28.

---

### B5. `arc_beat.scene` creates no relation — confirmed against the fixture

**Severity: medium.** The link exists only in `extra`, so anything walking the
`relations` table sees beats with no scene.

**Confirmed by live test.** Three `arc_beat` ops carrying `scene` each
committed. The composite ids and parentage landed correctly:

| id | parent_id | order |
|---|---|---|
| `elias-kade-first-certainty` | `elias-kade` | 1 |
| `elias-kade-the-offer` | `elias-kade` | 2 |
| `elias-kade-stops-explaining` | `elias-kade` | 3 |

**No relation rows were created.** `relations` stayed at 9 across the whole
commit; nothing referencing a beat id exists in the table. `scene` sits in
`extra` only.

**Not a regression — the reference corpus agrees.** The `save-the-children`
fixture holds 11 relations across exactly four kinds:

```
character_scene 5 · location_scene 3 · plot_setup 2 · plot_payoff 1
```

No beat relation and no `plot_character` there either. So the draft commit
path behaves the same as the pre-existing write path, and both predate task 28.
Whatever is incomplete here was always incomplete.

**Why the empty `_RELATION_FIELDS` entry is still suspicious.**
`core/entity.py:175` has `"arc_beat": {}` next to `"relationship": {}`, but
`columns_for_insert` (`entity.py:281-284`) carries an explicit special case
saying arc_beat keeps `scene` in `extra` *"in addition to* the arc_beat
relation created separately"*. The comment asserts a relation that nothing in
the codebase produces. Either the comment is stale, or the code that made that
relation was lost — and the comment is the only surviving evidence that a
beat→scene relation was ever meant to exist.

**Next step:** check the markdown files in the fixture for how a beat is
supposed to reference its scene, and check the export path — if `story_export`
writes beat→scene links from `extra`, the round trip is intact and only
relation-based readers miss it. If nothing reads `scene` for beats, the link is
decorative and the comment should go.

---

## B12. The enum check rejects the schema's own placeholder defaults — **FIXED 2026-09-28**

**34 placeholder strings are gone from the data layer.** They were field
defaults — `'Goals not set'`, `'Action not described'`, `'Shift not recorded'`,
`'Credit N.A.'` — written into the row on create, and then rejected by the enum
check as values the user had chosen.

**The bug, measured before the fix.** A minimal create, defaults filled in as
the write path does:

| type | false findings |
|---|---|
| `character` | 4 — `Invalid arc_type: Arc type not set`, `character_value_at_open: Not set`, `character_value_at_close: Not set`, and `story_role` |
| `project` | 3 |
| `plot` | 1 |
| `arc_beat` | 2 |

`scene`, `sequence`, `act` reported none — and that is the evidence the fix
works: **every enum-guarded field on those three already defaulted to `""`.**
They are the control group. Same code, same validator, correct behaviour.

**After: 10 → 0**, through the tool the agent calls:

```
before: 10 false findings on a character + plot + arc beat batch
after:  validation: ['ops[2] ... Missing required field: scene']
```

That remaining finding is real — `scene` is required on an arc beat.

**The 11 defaults that stayed, and why the distinction is the whole change.** A
default that is already a *real value* must not become `""`, or the field would
report as unfilled while holding something real:

- `status` → `'active'` / `'planned'` — legal enum members
- `type` → its own type name
- **`project.screenplay_title` → `'Default'`** — not an enum member, not a
  placeholder pattern, but a **real value**: a project with no title set should
  still typeset something, and an empty title page is worse than a generic one.
  **A test asserts the split**, because converting it would silently change the
  rendered title page.

**`UNFILLED = "N.A."`** in `core/constants.py` replaces the 34 strings, for a
surface that wants to say so. It has **no consumer yet** — deliberately, see
below. Four declared `label`s cover the fields whose name is not the human
phrase (`Inciting Incident`, not `Inciting Incident Scene Id`), and the
label-uniqueness check that makes the derived-label shortcut safe: **zero
collisions across all 31 optional fields.**

**Two live references the plan did not list, found by grepping the codebase:**

1. `db.py:396` built a character node with
   `extra.get("arc_type", "Arc type not set")` — for a row missing the key it
   would have **injected** the placeholder this change removes.
2. `writes.py:_default_for` documented *"reset to the placeholder so the UI shows
   the gap"* as the reason for reading the schema default. The function is still
   right — it is what keeps `screenplay_title` resetting to `'Default'` — but
   **a comment saying a placeholder is deliberate becomes a lie the moment the
   placeholder is gone.**

**The plan's measurements, re-checked rather than assumed:**

- **0 placeholders stored** in either real database, and 0 in the fixture
  markdown. They were defaults written on create and never edited, so **there is
  no data to migrate** — the deployment constraint does the rest.
- **The dashboard already handles `""`.** `c.arc_type && c.arc_type !==
  'absent'` and `char.arc_type || 'absent'` — `''` is falsy, so the arc counts
  and the arc-type badge are unchanged, and `'absent'` still reads as a real
  choice. **No JS change needed.** That was the plan's central risk and it held.
- `_omit` drops falsy values on its first branch, so the prose sentinels in
  `db.py` were already dead. They are `""` now for consistency.

**Tests.** 14 `TestUnfilledFields` cases fed the placeholder *string* as input —
the mechanism this change removes — so they now feed `""`. The two that assert
what gets **stored** became the guard instead, and
`test_placeholder_default_is_unfilled` is replaced by
`test_stored_default_is_never_prose`, which fails if a placeholder default is
ever added back. **892 pass, unchanged.**

### B12b — the display side — **BUILT 2026-09-28**

**Decided: one voice, `<label>: N.A.`, on the title page only.** The user chose
the labelled reminder over an empty page. The other 30 fields each decide
separately — *not drawing* a row is the right default for most of them.

| | change | where |
|---|---|---|
| one helper, every slot, no per-field code | `_slot()` | `story_dashboard.py:212` |
| each token keeps its own class instead of being flattened | `tokenHtml` + type lookup | `script-view.js:25-42` |
| a reminder is italic, faint, normal weight | `.tp-unfilled` | `views.css:294` |

**The plan's central assumption was wrong.** It said `type` is "what the
dashboard styles on". **`type` was never read** — `script-view.js:27-30` joined
every token's `.text` into one string and dropped it. So the styling needed real
JS, not just the Python the plan budgeted. Worth recording because the plan was
reasoning about an interface it had not checked.

**A bug I introduced, caught by reading the rendered DOM instead of the tick.**
`_slot()` returned `None` for an empty title, so with `screenplay_title` empty —
which it is in the fixture — `cc[0]` became the credit line, and the JS, which
split the block by position, typeset **`Credit: N.A.` as the title**:

```html
<div class="title-cc">
  <span class="tp-unfilled">Credit: N.A.</span>     <-- the title position
```

The unit tests passed. The assertion could not see it.

**The lesson is the shape of the fix, not the miss: a token that can be absent
invites its consumer to index by position, and position is not an identity.**
`_slot()` now always returns a token, and the dashboard finds the title by
`type` (prefix-matched, since an empty one is `title_unfilled`).

**The Chrome test was proved, not trusted.** It passed in 1.5s — too fast for a
browser. Running the same steps by hand and printing what it got showed 241k of
static HTML becoming a **480k DOM** with both markers present. My first probe
showed neither, because it built a bare project instead of importing the
fixture: the probe's bug, not the test's, and **that difference is the whole
reason the hand-run was worth doing.**

**The rendered result, unfilled project:**

```html
<span class="tp-unfilled">Screenplay Title: N.A.</span>
<span class="tp-credit"><span class="tp-unfilled">Credit: N.A.</span><br>
  <span class="tp-unfilled">Author: N.A.</span></span>
<div class="title-bl"><span class="tp-unfilled">Draft Date: N.A.</span><br>
  <span class="tp-unfilled">Draft: N.A.</span></div>
<div class="title-br"><span class="tp-unfilled">Contact: N.A.</span></div>
```

**896 pass** (was 892; four new tests — two unit, one for the empty-title token,
one end-to-end in headless Chrome).

**B12 is closed: the data is clean and the surface is honest.**

**What changed visibly, and it is not cosmetic.** `_build_title_page` gates on
truthiness, so before this commit an unfilled project rendered:

```
cc: title      'Default'
cc: credit     'Credit N.A.'
cc: author     'Author N.A.'
bl: draft_date 'Draft Date N.A.'
bl: draft      'N.A.'
br: contact    'Contact N.A.'
```

and now renders **only the title**. `tools/story_dashboard.py:210-241` is the
one place in the plugin where removing the placeholders changed output.

**A placeholder printed as if it were content is a real defect** — a typeset
title page is the most deliberately-designed surface in the app, and
`'Credit N.A.'` sitting where the credit line belongs is not typesetting. So the
*removal* is right; the *replacement* is a display decision and was not made
here. Bundled, a title-page change would be invisible in a diff about
placeholder defaults.

**The render, when it happens** — `type` is what the dashboard styles on, so a
reminder is visually distinct from typeset content; otherwise a filled page and
an empty one are structurally identical and the reader cannot tell which slots
are open:

```python
if credit:
    cc.append({"text": credit, "type": "credit"})
else:
    cc.append({"text": f"Credit: {UNFILLED}", "type": "credit_unfilled"})
```

**Only the title page.** The other 30 fields each decide separately, and *not
drawing* a row for an empty field is the right default for most of them.

**Found, not fixed, and out of scope:** `entity.py:79` guards
`act.structure_type`, a field the `act` schema does not have. A dead check,
confirmed present before this change.

---

## B6. `arc_beat` requires an `id` in frontmatter that the write path ignores — **OPEN, PLAN READY**

**Plan: `tasks/task_17*/b6_plan.md`** — one dict becomes a comprehension, the
hand-written `REQUIRED_FIELDS` is deleted, two tests. Scope is B6 only; B12 is
a separate plan. **Not built.** Baseline 889 pass, and the plan must leave that
number at 889 or higher.

**Severity: low, and a false positive** — but it fires on every arc beat, so
every arc draft shows three findings that mean nothing.

**Observed.** Staging three `arc_beat` ops produced, for each one:

```
ops[0] (create arc_beat/first-certainty): Missing required field: id
```

`validation` is otherwise empty — the beats are otherwise valid.

**Cause.** Two different notions of "required" disagree.

- `core/constants.py ENTITY_SCHEMAS['arc_beat']` marks `id` non-optional,
  along with `character`, `scene`, `order`, `label`.
- `core/entity.py REQUIRED_FIELDS['arc_beat']` is
  `['id', 'character', 'scene', 'label', 'action', 'gap', 'choice', 'shift',
  'y', 'order']` — still carrying `id`.
- Every *other* type has already had the structural fields stripped from
  `REQUIRED_FIELDS`, because the write path supplies them:

| type | `REQUIRED_FIELDS` |
|---|---|
| scene | `title`, `sequence_id`, `act_id` — no `id`/`type`/`order`/`status` |
| act | `title` |
| sequence | `title`, `act_id` |
| **arc_beat** | **`id`,** `character`, `scene`, `label`, `action`, `gap`, `choice`, `shift`, `y`, `order` |

`arc_beat` is the last type that was never cleaned up. Dropping `id` from its
list is the fix, matching what every other type already does.

**Re-measured 2026-09-28: it is three findings, not one.** Probing
`validate_shape` with a *minimal valid* beat (`character`, `scene`, `label` —
everything the schema marks `optional: False`) gives:

```
Missing required field: id       ← unsatisfiable; columns_for_insert builds the composite id
Missing required field: y        ← schema says optional, but its default 0.0 is falsy
Missing required field: order    ← same, default 0
```

So the original entry's "three findings that mean nothing" was right in
number and wrong in composition — the other two are not schema drift but the
**falsy-default** half: `if not merged.get(field)` reads a default of `0` or
`0.0` as absent. Blanking a genuinely optional field (`action: ""`) fires a
fourth. A beat where the author filled every field, as the live test did,
showed only the `id` finding — which is why this was recorded as one.

**The rule that reproduces every type.** Required = `optional: False` in the
schema, minus the four fields the write path supplies itself (`id`, `type`,
`order`, `status` — all in `FIELDS_TO_SKIP` or auto-numbered in
`columns_for_insert`). Checked against all ten types: it reproduces seven
exactly, and the three it disagrees with are `arc_beat` (this bug), `plot`
(`status` listed but `optional: True`) and `project` (`logline` likewise).
The latter two have non-empty defaults so they never actually fired — latent,
not reported. **Which is the argument for deriving the list from the schema
instead of hand-maintaining a third copy of it.**

**`id` can never be satisfied anyway.** The op supplies the id as `slug`, and
`columns_for_insert` (`entity.py:293`) builds the composite id itself:

```python
columns["id"] = f"{char_slug}-{slug}" if char_slug else slug
```

So frontmatter `id` is never read on the write path. An author who *did* pass
`id` in frontmatter would have it validated, ignored, and land with a different
id than the one they supplied — which is its own silent surprise. The field
should not be settable here at all.

**Related, worth checking in the same pass:** `arc_beat.REQUIRED_FIELDS` also
lists `action`, `gap`, `choice`, `shift`, `y` — all of which the schema marks
`optional: true` with placeholder defaults. Confirmed: they do not fire on a
defaulted beat (the placeholders are non-empty strings), only when explicitly
blanked. **This is the same class as the inert-merge bug task 28 Phase 6
fixed** — worth checking whether `REQUIRED_FIELDS` is still trustworthy for
any type, not just arc_beat. Done: it is not, for three of ten.

---

## B12. The enum check rejects the schema's own placeholder defaults — **OPEN, PLAN READY**

**Plan: `tasks/task_17*/b12_plan.md`** — the better fix than the one this entry
originally proposed. Measured: **zero** placeholders are stored in either real
database, and **zero** are referenced anywhere in `src/dashboard/`. So the
prose defaults can become type-correct empties, which deletes the cause instead
of teaching `_validate_enum` to tolerate it. Runs after `b6_plan.md`.
**Not built.**

**One trap, and it is the "special case" the plan has to get right:** a default
that is already a *legal enum value* (`project.status` → `'active'`) must not
become `""`, or a filled field would start reporting as unfilled. Only *prose*
placeholders convert. And `arc_type`'s legal `'absent'` value needs no
dashboard change — `statistics.js:225` and `network.js:134` already filter on
it, so `""` renders as `absent` through code that exists today.

**Severity: high, and wider than B6.** Eleven optional fields default to a
prose placeholder (`'Not set'`, `'Arc type not set'`, …) that is not in the
valid set, so every `character`, `plot` and `project` create reports 1–3
findings that mean nothing. Found while measuring B6; **not** part of it.

**Observed.** `validate_shape` on minimal valid ops — nothing but the fields
the schema marks `optional: False`:

```
min character    → Invalid arc_type: Arc type not set
                   Invalid character_value_at_open: Not set
                   Invalid character_value_at_close: Not set
min project      → Invalid story_value_at_open: Opening Value not set
                   Invalid story_value_at_close: Closing Value not set
                   Invalid structure_type: Structure Type not set
min plot         → Invalid value_arc: Value arc not set
min arc_beat     → the same 2 value findings, on top of B6's 3
```

**Every `character`, `plot` and `project` create emits 1–3 findings that mean
nothing.** B6 is 3 false findings on one entity type; this is 1–3 on the three
most-used ones.

**Cause.** `_validate_enum(..., empty_ok=True)` treats "unset" as the empty
string:

```python
if empty_ok and val == "":
    return
```

But the guarded fields do not default to `""`. Eleven optional fields default
to a **prose placeholder** that is not in the valid set, so the schema's own
default is reported as invalid:

| field | schema default | valid set |
|---|---|---|
| `character.arc_type` | `Arc type not set` | `ARC_TYPES` |
| `character.character_value_at_open` / `_close` | `Not set` | `VALUE_CHARGES` |
| `arc_beat.character_value_at_open` / `_close` | `Not set` | `VALUE_CHARGES` |
| `plot.value_arc` | `Value arc not set` | `VALUE_ARCS` |
| `project.story_value_at_open` / `_close` | `Opening/Closing Value not set` | `VALUE_CHARGES` |
| `project.structure_type` | `Structure Type not set` | `STRUCTURE_TYPES` |

The other guarded fields (`time_of_day`, `value_at_open/_close`,
`dramatic_role`, `plot_type`, `plot_scope`) all default to `""` and are
correctly silent — which is why this survived. The `empty_ok` flag was written
against a schema where "unset" meant `""`, and the placeholder strings arrived
later.

**Why nothing caught it.** `validate_shape` merges the op's frontmatter over
schema defaults *before* validating, so the placeholder is always present at
check time. No test creates a minimal `character` or `project` through
`story_draft` and asserts an empty `validation` — the same test gap B7 was
found through, one layer over.

**The fix, and why it is one line.** `empty_ok` should mean *"this value is
not set"*, and the schema already says what not-set looks like for each field:
its own `default`. Comparing against the field's declared default (rather than
`""`) is the tighter form and needs no new list — the placeholder strings are
already in `ENTITY_SCHEMAS`, so nothing new has to be kept in sync.

**Also recorded, because it is the same trap next door:** the *required*-field
check has the mirror-image bug. `if not merged.get(field)` treats a **falsy**
default as missing, so `y` (default `0.0`) and `order` (default `0`) fire even
though the schema marks them optional. That is why B6 produces three findings
rather than one. Same root shape — *the hand-maintained list and the schema
disagree* — different check, and it is fixed under B6.

**What this is not.** Not a schema problem: the placeholders are the intended
way to say "unfilled", and they round-trip through export and the dashboard.
Not a validator-tuning problem either — do **not** widen the valid sets to
include `'Not set'`. That would make the placeholder a legal value of
`character_value_at_open`, and anything reading a charge curve would have to
know that string means "no charge" rather than a charge. The finding is
right; the value is legitimately not-set. Fix the check, not the vocabulary.

---

## B6. `arc_beat` requires an `id` in frontmatter that the write path ignores — **FIXED 2026-09-28**

**The fix, in one line of intent:** `REQUIRED_FIELDS` is no longer maintained
by hand. It is derived from `ENTITY_SCHEMAS` in `core/constants.py`:

```python
WRITE_PATH_SUPPLIED = {"id", "type", "order", "status"}

REQUIRED_FIELDS = {
    entity_type: [field for field, meta in schema.items()
                  if not meta.get("optional", True) and field not in WRITE_PATH_SUPPLIED]
    for entity_type, schema in ENTITY_SCHEMAS.items()
}
```

A 12-line hand-written dict — a second copy of the schema with nothing keeping
it honest — is deleted. Placed after `ENTITY_SCHEMAS` because the derivation
reads it; `WRITE_PATH_SUPPLIED` is a literal rather than an import of
`FIELDS_TO_SKIP` because `core/entity.py` imports from `core/constants.py` and
the reverse would be circular. Verified they agree: `FIELDS_TO_SKIP` is
`{id, type}` and is fully covered, plus `order` (auto-numbered) and `status`
(defaults to a valid value).

**Measured, before and after.** A minimal valid beat — `character`, `scene`,
`label`, the three fields the schema marks non-optional:

| | findings |
|---|---|
| before | `Missing required field: id`, `: y`, `: order` |
| after | **none** |

**Three types were wrong, not one.** Deriving the list fixed `arc_beat` (7
spurious fields) *and* two latent ones nobody had reported: `plot.status` and
`project.logline`, which survived only because their defaults happen to be
truthy. The guard test below fails on all three.

**One existing test asserted the bug.** `test_arcs.py` asserted `order` was
required — actively defending the behaviour this entry removes. Changed to
`label`, which genuinely is required.

**Checks.** Two tests added, both verified to fail against the old list:

- `test_minimal_arc_beat_reports_no_missing_field` — a beat carrying only what
  the schema asks for is silent. (Fails before the fix with `['id','y','order']`.)
- `test_required_fields_is_derived_from_the_schema` — `REQUIRED_FIELDS` equals
  the derivation for every type. (Fails before the fix on `plot`, `project`,
  `arc_beat`.)

The second is the one that matters: it is a guard against the *class*, not the
instance, so a future field cannot reintroduce the drift.

**Deliberately untouched:** `WRITE_PATH_SUPPLIED` is the write path's
knowledge, not the schema's. The schema says which fields exist and which are
optional; only the writer knows what it fills in. Keeping them separate is why
`entity.py` and `writes.py` already declare the same two skip-lists — that
duplication is pre-existing and outside this fix.

**The two remaining findings on a minimal arc beat are B12**, not this entry.
See below.

---

## B13. `create_project` never coerced a `number` field — **FIXED 2026-09-28**

**B10's fix, applied to one write path and not the other.** Found while
deleting the compatibility shims — `_coerce_number`'s read half was on the
deletion list and was nearly removed as "legacy". It is not legacy. It was
the only thing standing between a string `act_count` and the dashboard dying.

**Measured, before.**

```
create_project(act_count='5')  ->  stored '5'  (str)
   get_dashboard_data            ->  act_count=5   <- only because _coerce_number ran
edit_entity(act_count='5')      ->  stored 5     (int)
```

**The fix — one helper, three call sites, no second copy.**
`entity.coerce_number(value)` now holds the four lines, and:

| path | how it reaches the helper |
|---|---|
| `create_project`, `create_entity` | via `columns_for_insert`, which every insert goes through |
| `edit_entity` | calls it directly — this path UPDATEs, so it never reaches `columns_for_insert` |

The original fix was four lines inline in `edit_entity`. Copying them into
`create_project` would have left two copies to drift again, which is how they
drifted the first time; a third path would eventually arrive and copy neither.

**A near-miss worth recording.** `edit_entity`'s copy was first *deleted* on the
assumption that `columns_for_insert` covered it. It does not — that function is
insert-only, and `edit_entity` issues an `UPDATE entities SET extra=?`. The
removal was caught before commit by checking what the function actually did.
Had it shipped, `edit_entity` would have silently stopped coercing and B10
would have reopened with nothing to show for it.

**Measured, after — all three paths, given a string:**

```
create_project   act_count=7      (int)
edit_entity      act_count=8      (int)
create_entity    order_key=2.0    (float, from '2')
'2.5'          -> 2.5            (float, not truncated to int)
'many'         -> 'many'         (left alone; validate_shape reports it)
```

`create_entity` gaining `order` coercion is a **third** write path that had
neither fix — the same value was a string, an int and an int in three readers,
which is the inconsistency B10's entry called "the actual finding".

**A value that is not a number is returned unchanged**, not replaced by the
default. `validate_shape` reports it, and a wrong value the reader can see
beats a plausible one it cannot. Asserted by
`test_a_non_numeric_value_is_left_alone_for_validation`.

**The read half stays.** With every write path coercing, no project can hold a
string — measured across all three real databases, none does. But
`_coerce_number` is what makes that true *for rows already written*, and
deleting it is only safe once that is true of every project, not the ones that
happen to exist. It is now defence in depth rather than the only line of
defence, which is the correct state for it.

**Checks:** two tests in `TestCreateProject`, both verified — the coercion test
fails without the fix (`assert '4' == 4`), the non-numeric one passes either
way by design, since it guards against over-correcting.

---

## B7. `story_describe` hides `sub_fields`, and nothing guards the shape — **FIXED (read side)**

**Severity: high, and the root cause is the tool's, not the author's.** A read
tool dies on data the schema permits the agent to write, because the agent was
never shown the shape.

**This is not a relationships-only defect — it affects every field with
`sub_fields`.** See B9 below for the full survey; `story_describe` drops
`sub_fields` wholesale, so the same silent-truncation class hits `plot`
relation fields as well, with a worse symptom (data written but discarded,
rather than a crash).

**Observed.** `story_load(project="lighthouse-test")` returns:

```
{"error": "'str' object has no attribute 'get'"}
```

Reproduces outside Hermes, straight from the handler — ours, not the bridge
(contrast B1/B2).

**Traceback.**

```
core/db.py:523, in get_project_summary
    "label": p.get("label", ""),
AttributeError: 'str' object has no attribute 'get'
```

**Cause, in two parts.**

`get_project_summary` requires each perspective to be a dict:

```python
p = rel["perspectives"].get(char_id, {})
char_rel_summary.setdefault(char_id, []).append({
    "with": others[0],
    "label": p.get("label", ""),
    "type":  p.get("type", ""),
})
```

That expectation is **correct** and matches `browser-verification-test`, whose
6 relationships all carry the documented `sub_fields` shape. Nothing is wrong
with the data model or the consumer.

The defect is that **`story_describe` never shows `sub_fields`.** Ask it for
`relationship` and `perspectives` comes back as:

```json
"perspectives": {"type": "object", "default": {}, "optional": true,
                 "description": "Per-character relationship view"}
```

— with `sub_fields` (`label`, `feeling`, `type`, `strength`, `secret`) dropped
on the floor, and no hint that the value must be an object per character. The
agent sees "object", writes the natural thing, and the next `story_load`
crashes the entire project — not just that relationship.

**So: no data-structure change is wanted, and none is proposed.** The schema
is right and `core/constants.py` already matches the spec. The fix is to
surface `sub_fields` in `story_describe`'s output, which is where the agent
actually learns the shape.

**Why nothing caught it.** Two independent gaps:

1. `save-the-children` — the fixture most tests use — has **zero**
   relationship entities, so the summary path is never exercised there.
2. `browser-verification-test` has 6 correct ones, but it is not a fixture; it
   is a project nobody runs the test suite against. The gap is that no *test*
   project contains a relationship at all.

**Secondary, worth a defensive pass rather than a schema change.** The
consumer would not crash if it tolerated a string, and there is no validation
anywhere that a perspective *is* an object. That is the same
trust-the-writer gap, one layer down. The builders around it — `_build_act`,
`_build_sequence` — read structural keys off dicts the same way; if one
malformed relationship kills the whole summary, a missing structural field
will too. One pass over `get_project_summary` is cheaper than three more live
crashes.

**Fixture recommendation:** add one relationship to the `save-the-children`
fixture in the documented shape, and a test asserting `story_load` returns a
map rather than an error. That closes the gap that let this ship.

---

## B8. A scene's location is invisible to every relation-based reader — **FIXED 2026-09-28**

**Severity: medium. FIXED 2026-09-28 — but the symptom originally recorded
below was wrong, and the correction comes first.**

### Correction: the orphan check was never the symptom

The entry below claims the orphan check reads relations and so misreports a
referenced location. **It does not.** It tests the **world**:

```python
orphaned_loc_ids = sorted(
    [lid for lid, loc in locations.items()
     if not loc.get("_parent_id") or loc["_parent_id"] not in worlds], ...)
```

`the-lamp-room` was reported orphaned because **it had no `world`**, which has
nothing to do with the missing relation. Confirmed directly: in the
`save-the-children` fixture both locations have `parent_id = None` and both are
reported orphaned — including ones two scenes are set in. Any fix aimed at the
orphan check would have fixed nothing.

### The real gap, measured

Deleting the `location_scene` rows and comparing the dashboard:

```
WITHOUT location_scene   the-central-room -> 0 scenes   the-garden -> 0
WITH    location_scene   the-central-room -> 2 scenes   the-garden -> 1
```

The missing writer leaves **the dashboard's location→scenes view empty** for
any project not built by the importer. A location looks unused, which invites a
cleanup pass — the same *shape* of harm as described below, by a different
route. Only `story_import.py` ever wrote these rows; four readers in
`core/db.py` consume them.

### What was fixed

`entity.location_scene_relations()` builds the rows. `relations_for_insert`
calls it for scenes; `edit_entity` re-derives them whenever the `location_id`
column is touched, **deleting the old row first** — the stale row is what keeps
a location looking used when no scene is there any more. Five tests in
`tests/test_location_scene_relation.py`; two fail without the fix.

### Direction, for whoever touches this next

`location_scene` is stored `from_id=location, to_id=scene`. `character_scene`
is the opposite, `from_id=scene, to_id=character`. Both pre-existing, and every
reader inverts accordingly. Unifying them is a migration with a data fix, not a
cleanup — deliberately left alone.

### Original entry (superseded in its conclusion)

**Severity: medium.** A false positive in the base structural map — the map
tells the author a location is unused when three scenes point at it.

**Observed.** `lighthouse-test` has one location, `the-lamp-room`, and three
scenes all referencing it. `story_load` returns:

```json
"orphaned_locations": [{"id": "the-lamp-room", "name": "The Lamp Room",
                        "one_sentence": "The glass room at the top of the tower..."}]
```

The reference is real and correctly stored — verified directly:

| scene | `location_id` | `parent_id` |
|---|---|---|
| `the-lamp-comes-back-on` | `the-lamp-room` | `seq-the-burning` |
| `mara-offers-to-help` | `the-lamp-room` | `seq-the-burning` |
| `the-last-watch` | `the-lamp-room` | `seq-the-last-watch` |

**Cause.** The orphan check reads the `relations` table, not the `location_id`
column. This project's relation kinds are `character_scene` (5),
`plot_setup`, `plot_crisis`, `plot_climax`, `plot_payoff` — **no
`location_scene` at all**, because `_RELATION_FIELDS` has no `scene` →
location entry (see B4's table; the direction exists in the fixture, not in
this schema).

The `save-the-children` fixture has 3 `location_scene` relations, so a
project built the same way there would *not* be flagged. This is the same
underlying gap as B4/B5 wearing a different hat: **the column and the relation
are two independent ways to express the same link, and readers disagree about
which one is authoritative.**

**Why it matters beyond cosmetics.** `orphaned_locations` is the map telling
the author what is unused — i.e. what is safe to delete, and what the plot is
missing. A location claimed to be orphaned invites a cleanup pass that deletes
a location three scenes depend on.

**Fix direction — one decision, not two.** The codebase has to pick: either
scenes write a `location_scene` relation as well as the column, or the orphan
check reads `location_id`. Writing both is what the fixture implies and keeps
relation-walking code working; reading the column is less code but leaves
every other relation-walker still blind. Do not fix B4 and B8 separately —
they are the same question and will drift apart again.

**Related, same shape:** `world` and `location` `parent_id`. The location row
shows `parent_id = ''` (empty string, not NULL) because I sent `world: ""`.
Probably benign, but a NULL/empty-string split is exactly the kind of thing
that makes an equality check miss. Worth folding into the same pass.

---

## B9. `sub_fields` is dropped by `story_describe` for every field that has it — **FIXED (read side)**

**Severity: high. One root cause, five fields, two failure modes.** This is the
general case of B7; that entry is kept because the crash it causes is the most
visible symptom, but the fix is here and is not relationship-specific.

**The trap is the finding.** The natural response to `story_describe` saying
`"perspectives": {"type": "object"}` is to write prose per character — and
that is precisely the value the reader cannot handle. The same for a plot
field typed `list` with no element shape: the natural value is a list of
slugs, and the natural place for the description is nowhere, so it is
dropped. **In both cases the agent did the reasonable thing and the tool
punished it.** A design that punishes the reasonable thing is the defect,
not the agent that guessed.

**The defect.** `ENTITY_SCHEMAS` uses a `sub_fields` key to document the shape
of a structured value. `story_describe` builds its output from the schema and
**does not copy `sub_fields` through**, so the agent is told a field is an
`object` or a `list` and is never told what goes inside it.

**Every affected field — a full survey, not a sample:**

| field | declared type | `sub_fields` | what happens when the shape is guessed |
|---|---|---|---|
| `relationship.perspectives` | object | `label`, `feeling`, `type`, `strength`, `secret` | **crash** — `story_load` dies (B7) |
| `plot.setups` | list | `scene_id`, `description` | **silent loss** — description dropped |
| `plot.crisis` | list | `scene_id`, `description` | **silent loss** |
| `plot.climax` | list | `scene_id`, `description` | **silent loss** |
| `plot.payoffs` | list | `scene_id`, `description` | **silent loss** |

Five fields, all of them. Two distinct failure modes, and the second is worse
because nothing reports it.

**The plot case, confirmed against the reference project.** The schema says a
plot's `setups` entry is `{scene_id, description}`. `browser-verification-test`
confirms it: its plots carry **no** `setups`/`crisis`/`climax`/`payoffs` in
`extra` at all — the link lives in the `relations` table and the description
lives in that row's **`note`** column:

```
('the-resistance', 'central-room-day',  'plot_setup', "Kael discovers the door isn't locked — it was never locked.", 0)
('the-resistance', 'central-room-night','plot_crisis', 'The Administrator makes its final offer. Kael refuses.', 0)
```

I wrote bare slug strings instead. The relations were created correctly — 4
rows, right scenes, right kinds — but every `note` came out **empty**:

```
('the-light-that-should-be-dead', 'the-lamp-comes-back-on',  'plot_setup', '', 1)
('the-light-that-should-be-dead', 'mara-offers-to-help',      'plot_crisis', '', 1)
('the-light-that-should-be-dead', 'the-last-watch',           'plot_climax', '', 1)
('the-light-that-should-be-dead', 'the-last-watch',           'plot_payoff', '', 1)
```

So the *beat descriptions I wrote were discarded on write*, with no error, no
validation finding, and a commit report saying `✅ create plot/...`. The
relation survived; the reason it exists did not. A `description` is the entire
point of putting a plot beat in a plot — without it the relation says only
"this scene is the setup", which was already obvious from the id.

**Why the crash case was found and the silent case was not.** B7 announces
itself on the next read. The plot case never announces itself: the commit
succeeds, the data is gone, and the only symptom is a missing sentence in a
database column nobody looks at. It was caught here by comparing the
`relations.note` column against the reference project — it would not have been
caught at all otherwise.

**The fix — one place, no per-field work.** `story_describe` should emit
`sub_fields` in its per-field output, exactly as it emits `type`, `default`,
`optional` and `description`. Five fields become correct at once, and any
`sub_fields` added later is covered without touching the tool again. The
alternative — a defensive `isinstance` in each consumer — is five separate
patches for one mistake, and leaves the agent still guessing.

**Should `plot.*` accept a bare string as `{scene_id}`?** Worth a decision
while in there. It is a friendly shorthand and the crash it would otherwise
cause is ugly. But if it is accepted, `description` must default to `""`
rather than being an error, or the silent-loss failure comes back wearing a
different hat. Decide once, apply to all four plot fields together.

**Also worth a look while in there:** `list` fields without `sub_fields` have
the same ambiguity — is `characters: ["a", "b"]` a list of slugs, and is that
documented anywhere the agent can see? `story_describe` says `"type": "list"`
and stops. B4 is a consequence of exactly this gap.

---

# D3 investigation — columns vs relations (2026-09-28)

Investigated without assuming a conclusion. **The premise turned out to be
partly wrong, and the real finding is narrower and more actionable.** Recorded
before any decision, so the reasoning is auditable.

### What I expected to find

Two competing authorities per link type, each with readers that picked one.
Pick the winner per link, derive the other, done.

### What is actually there

**1. Every declared link is unambiguous — the overlap is one field.**
`ENTITY_COLUMN_MAP` and `_RELATION_FIELDS` never both claim the same field.
The declared storage is clean:

| link | storage | why it is there |
|---|---|---|
| `location.world` | column `parent_id` | tree |
| `scene.sequence_id` | column `parent_id` | tree |
| `sequence.act_id` | column `parent_id` | tree |
| `arc_beat.character` | column `parent_id` | tree |
| `scene.location` | column `location_id` | single-valued |
| `scene.characters` | relation `character_scene` | many-to-many |
| `plot.setups/crisis/climax/payoffs` | relations | many-to-many, **with a `note`** |
| `location.variant_of`, `world.variant_of` | relations | graph edge |

The pattern is already consistent and already right: **tree/single links in
columns, multi-links with metadata in relations.** Every column link is a
`parent_id`-style tree or a single-valued reference; every relation is
many-to-many or carries a `note`/`order`. `plot.*` needs relations precisely
because each edge carries a `description` — which is why losing the description
(B9) was possible at all.

**2. The one genuine overlap is `scene.location`, and it is not a conflict —
it is a reverse index, and it is stale.**

`scene.location_id` (scene → location) and the `location_scene` relation
(location → scene) are **the same fact in opposite directions**, and in the
reference project they agree on all six scenes once you invert the relation.
Verified, not assumed:

```
central-room-day   column='the-central-room'  relation_inverted='the-central-room'  AGREE
garden-dream       column='the-garden-dream'  relation_inverted='the-garden-dream'  AGREE
...  6 of 6 agree
```

**But only the importer writes the relation.** Every reference in the codebase:

- `tools/story_import.py:453` — the **only** writer of `location_scene`.
- `core/db.py:380, 693, 986, 1069` — **four readers, zero writers**.

So the decision task 20 already made — "switch to relation-based, the column
has a latent gap" (`task_20/phase_1/task_1_1.md:133`, noting the column "is
always NULL") — was implemented on the **read** side only. The read side
trusts the relation; the write side (story_draft, the normal authoring path)
writes only the column. **Author a scene with a location and every relation-
based reader goes blind to it.** That is B8, and it is a missing write, not an
ambiguous authority.

**3. Nine real links have NO declared storage — and this turns out to be by
design, not an oversight.** See the assessment below; the summary here is the
original (mistaken) reading, kept so the correction is auditable. They land in
`extra` JSON, and the data model documents that as their storage:

| field | kind |
|---|---|
| `scene.act_id` | tree link, in extra — while `scene.sequence_id` (its parent) is a column |
| `arc_beat.scene` | single link, in extra |
| `plot.characters` | many-to-many, in extra — while `plot.setups` (also many-to-many) is a relation |
| `relationship.characters`, `relationship.scenes` | many-to-many, in extra |
| `act.climax_scene_id`, `sequence.climax_scene_id` | single link, in extra |
| `sequence.primary_plot` | single link, in extra |
| `project.inciting_incident_scene_id`, `story_climax_scene_id` | single link, in extra |

**This is the larger half of D3 and the part I had missed.** The declared maps
are clean; the problem is that the maps are *incomplete*, so the rule
"columns for single, relations for multi" is real but only half-implemented.
`scene.act_id` in `extra` while its own parent is a column is the clearest
inconsistency: same field, same entity, two mechanisms.

> **CORRECTION — the paragraph above is wrong.** The maps are not incomplete;
> `extra` is the documented home for these, and the real rule is "columns are
> for the structural spine, `extra` for everything else, relations for
> many-to-many and for edges carrying a `note`". The `act_id`/`sequence_id`
> pairing is a deliberate denormalization, recorded in
> `task_20/archived/verification_findings.md:45`. **Nothing here needs fixing.**
> Full assessment in the section that follows.

### What follows

- **The authority question is already answered by the existing code** — single
  links in columns, multi-links-with-metadata in relations. Nothing needs
  deciding; it needs *applying* to the nine undeclared fields.
- **B8 was a missing write, not a conflict** — but *not* the orphan-check
  false positive originally recorded. The orphan check tests the **world**, so
  the real cost is an empty location→scenes view in the dashboard (measured:
  0 scenes without the rows, correct with them). Fixed; see the B8 entry.
- **The nine undeclared fields are NOT a defect.** Assessed: `extra` is their
  documented storage, and the redundancy is deliberate. Full reasoning in the
  assessment section below.

---

# Design gaps the live test exposed

Not bugs in a single function. These are the *shape* problems the test
surfaced — the ones that make an agent slow, wrong, or uncertain, and that
would do the same to a human writing the same data. They are collected here
because fixing one symptom at a time leaves the cause in place.

### Are the nine undeclared link fields undeclared BY DESIGN? (assessed 2026-09-28)

**Yes — by design, and documented. This is not an oversight, and "fixing" them
would be a regression.** The question was worth asking separately, and the
answer is in the repo rather than in the pattern.

### Evidence 1 — the data model states the storage for each one

`tasks/task_20/archived/data_model.md` has a per-field `Storage` column, and it
says `extra` for every one:

| field | documented storage | required |
|---|---|---|
| `scene.act_id` | **extra** | yes |
| `arc_beat.scene` | **extra** | yes |
| `plot.characters` | **extra** | no |
| `act.climax_scene_id` | **extra** | no |
| `sequence.climax_scene_id` | **extra** | no |
| `sequence.primary_plot` | **extra** | no |

Placed directly beside their declared siblings, the contrast is explicit —
`scene.sequence_id` is `column (parent_id)` on the very next line, and
`scene.act_id` is `extra`. That is a choice made next to its alternative, not
an omission.

### Evidence 2 — the reasoning is recorded

`task_20/archived/verification_findings.md:45`, on the redesign that produced
the current `story_load`:

> The spec drops `act_id` from scenes entirely. Current scenes have both
> `sequence_id` and `act_id` (denormalized). The spec says scenes nest inside
> sequences which nest inside acts, so `act_id` is implicit. **Correct** — but
> note: this means a consumer wanting "what act is this scene in?" walks up
> the tree. The spec considers this fine (and it is for a tree).

And on `plot.characters` (line 27), explicitly checked and confirmed:

> `plot.characters` comes from `extra JSON` (frontmatter `characters:` list),
> NOT from a relation. The spec keeps this as frontmatter-sourced.
> **Consistent.**

### The rule, stated

The codebase's actual rule is **not** "single links in columns, multi in
relations". It is:

- **`parent_id` and the other real DB columns are for the structural spine** —
  the tree the load payload and the dashboard assemble (`sequence_id`,
  `act_id`→parent, `location_id`, `order_key`, `name`, `status`).
- **Everything else that is a link lives in `extra`**, including links. A
  slug string in JSON is a perfectly good way to point at an entity; a column
  is only worth its cost when the value is on the spine.
- **Relations are for many-to-many, and for edges that carry a `note`** —
  `character_scene`, `plot_*`, `location_scene`, `*_variant`.

Under that rule all nine are correct as they stand, and my earlier framing —
"the same field, same entity, two mechanisms", `scene.act_id` in `extra` while
its parent is a column — described a **deliberate denormalization** as though
it were an inconsistency. The `act_id`/`sequence_id` pairing is redundant *on
purpose*: the act is derivable from the tree, and the shortcut is kept because
it saves a walk.

### What this changes

- **D3's scope shrinks to B8 alone**, which is fixed. There is no
  columns-vs-relations decision left to make.
- **B4 and B5 are not "declare these fields" bugs.** B4 (a field advertised as
  `stored_as: relation` that is not one) and B5 still stand on their own — but
  as *documentation* defects, not storage ones. `story_describe` says
  `stored_as: "relation"` for any field whose name appears in
  `_RELATION_FIELDS_BY_NAME`; the fix is to say what is actually true, whatever
  that is.
- **The one genuine question left is consistency of the *label*, not the
  storage**: does `story_describe` tell the truth about where a link lives? It
  must not imply a relation where there is none, and it must not imply a
  column where there is none either. That is the same D1 family — a schema
  annotation the tool does not report faithfully.

### What would actually justify a change

Only evidence that a reader is *wrong*, not that storage is redundant. If some
reader treats `act_id` in `extra` as authoritative where it should walk the
tree — or vice versa — that is a real bug, and the fix is the reader. None has
been found. The redundancy is load-bearing for the export format (a scene's
frontmatter round-trips its own `act_id`), so removing the storage would break
`story_export` for no gain.

---

## D1a. `story_draft` silently swallowed computed-field writes — **FIXED 2026-09-28**

Raised as a question while fixing the `char.relationships` sub_fields: *"if we
declare these as visible, won't the agent try to fill them?"* Yes — and the
answer was worse than a corrupted write.

**Measured, before the fix.** Staging an edit that sets `character.relationships`:

```json
{"success": true, "op_count": 1,
 "preview_md": "... `relationships`: _not set_ → **{'with': 'marcus-chen', ...}**",
 "validation": []}
```

The preview **promises the change** and validation is **empty**. The agent
commits, and only then does `edit_entity` drop the field and report it.

**Root cause: one line.** `core/drafts.py:140` — the validator opened with
`if op["op"] != "create": continue`, so **every edit skipped validation
entirely**. Not just computed fields: an unknown key in an edit reached the
write path unflagged too.

**Why the write path's guard was not enough.** `edit_entity` already collects
`computed_skipped` and returns it (`core/writes.py:409-417`):

```json
{"skipped_read_only": ["relationships"],
 "warning": "Nothing was written: every key was a read-only computed field."}
```

Correct, and it protects the data. But it fires **after** the agent has read a
preview saying the change would happen, and the agent's next decision is
usually to retry or abandon. The preview is the last place it can be told.

**The fix: the guard moved to the draft validator, for every op kind.** One
loop over `frontmatter` (create) or `data` (edit), reported as a `validation`
finding. The write path's guard stays as the backstop.

## I5. `char.relationships` sub_fields declared — **DONE 2026-09-28**

The only undeclared structured read found in a full audit of the load payload
against the schema. `story_describe` now emits the shape, with `with`
documented as **the other character** — the one key that inverts if read as the
holder's own name.

**Two descriptions I wrote were wrong and were corrected against the data
before committing:**

| key | what I first wrote | actual |
|---|---|---|
| `type` | `ally, rival, mentor, family, other` | `ally, rival, enemy, family, romantic` — **no `mentor`, no `other`** |
| `strength` | "Tension 0-5" | **signed**, observed **−0.6 … 0.9** |

The `strength` one matters: an agent told 0-5 clamps every antagonist
relationship to zero, and negative tension is how the data encodes
antagonism. Both descriptions now say what the data shows, and
`type` is explicitly *not* a closed set — a test asserts that, because an enum
list here would break on the next project.

**Audit result for the record:** every other key on every entity node in the
load payload is a real `story_describe` field or a container. **No other
abbreviations exist.** `rel` was the one to worry about and it is already
`relationships` in the code — though `story_load_redesign_spec.md:86,180` still
documents the old `rel: [{id, label, feeling}]`, so the spec needs the same
correction `chars`/`loc` got.

Three audit hits were false positives worth knowing about: `world.locations`,
`act.sequences` and `act.scenes` are **containers, not fields**, so there is
nothing to declare. Only checking against `ENTITY_SCHEMAS` tells them apart.

857 pass; 7 of the new tests fail without the change.

---

## I4. The `chars`/`loc` abbreviations are gone — **DONE 2026-09-28**

I3 bridged the two vocabularies in prose. That was the wrong fix, and the
question "do we need the abbreviations at all?" is what showed it.

**Measured, on the real `browser-verification-test` project:**

| | payload | tokens |
|---|---|---|
| with `chars`/`loc` | 6,830 chars | ~1,707 |
| with `characters`/`location` | 6,880 chars | ~1,720 |
| **cost of abbreviating** | **50 chars** | **~12 tokens, 0.73%** |

**The 12.9k figure was a category error on my part.** `story_load_redesign_spec`
quotes ~12.9k tokens for the *whole* redesign — dropping the flat `relations`
table and expressing structure as nesting. `chars`/`loc` are a rounding error
inside that, and I attributed the redesign's saving to these two keys when I
wrote I3. **They were never load-bearing.** Paying 12 tokens for a second
vocabulary — and for the bridge text, the two tool-description sentences, and
the three tests guarding them — was a bad trade by any measure.

**The change: four lines in one function**, `_build_scene` in `core/db.py`
(`core/db.py:485-500`). Plus the two now-obsolete bridge sentences deleted, and
the tests updated to assert the abbreviations **stay gone** rather than to
document them.

**What it removes, not just renames:** the whole class of agent error where a
read key and a write key don't match. The names are now identical, so an agent
that copies `scene.characters` from a load payload into a `story_draft` op is
correct by construction rather than by having read a bridge note. That is the
same class of defect as B4/B5 and B8 — a tool telling the agent something
subtly untrue — resolved by deletion instead of documentation.

**Tests: 4, one of which is a real guard.** The strongest asserts that every
key `story_load` puts on an *entity* node is a name `story_describe` accepts.
Written from the actual failure mode, not from the two keys I happened to
change: a future invented abbreviation fails there even if nobody remembers the
name. It caught `milestone` (a deliberate load-only climax marker) and had to
be scoped past the `memory` subtree, whose vocabulary is not entity fields.

848 pass; 4 fail without the change.

**Spec updated:** `story_load_redesign_spec.md` still documents `chars, loc` as
the design. The implementation now diverges from its own spec, deliberately and
for a measured reason, and the spec is the thing a future keeper reads first —
so that entry needs updating. Left unedited here to keep this commit to code.

---

## I3. The two vocabularies were never bridged — **SUPERSEDED by I4**

**Kept for the reasoning, not the fix.** The bridge sentences below were the
right answer to the wrong question: I4 removed the need for them by dropping
`chars`/`loc` altogether, so the two vocabularies no longer differ. The
measurement that superseded this is in I4; the table explaining why neither
side could be renamed is still the reason the write vocabulary is exact.

The fix as first written (one sentence per tool description):

- `story_load`: *"Abbreviated keys `chars` and `loc` are the links
  `story_describe` calls `characters` and `location`."*
- `story_describe`: *"These are the field names to pass to `story_draft`: an
  entity's `id` is the `slug` argument of its op, and `story_load` returns some
  links under short names (`chars`=characters, `loc`=location)."*

**Why descriptions and not a rename** — the two tools do different jobs, so
unifying the names would break one of them:

| | `story_load` | `story_describe` / `story_draft` |
|---|---|---|
| job | compressed read summary | the write vocabulary |
| `location` | `loc` | `location` |
| `characters` | `chars` | `characters` |
| drops fields? | yes, by design (`heading`, `time_of_day`, `value*`, `conflict_levels`) | no |
| unknown key on write | n/a | **hard error** — `edit_entity` rejects it |

`chars`/`loc` exist to serve the spec's first principle (remove ~12.9k tokens);
the write names are op keys that must stay exact or a write fails. Both are
load-bearing, so the bridge is prose.

**Tests: 3 added, one of which is a real guard.** The third asserts the
fixture's load payload actually contains `"chars"` and `"loc"` — if the
abbreviation is ever dropped from the read side, the descriptions become wrong
and this fails instead of misleading an agent. That test caught the first draft
of the `story_load` sentence, which named only the targets and not the
abbreviations, so it earned its keep immediately.

847 pass; 2 of the 3 fail without the change.

**Still open from the same investigation:** the `id`-in-output / `slug`-in-op
half is *described* but the op schema still says `slug` while `story_describe`
lists a field called `id`. Both are documented now, so an agent can follow it,
but the naming asymmetry itself is unchanged — settling it means renaming the
column or the op arg, which is a data-model change and not made here.

---

## D2. `story_load` and `story_describe` use different names for the same links — **RESOLVED; see the status index**

**Found 2026-09-28, while fixing B4/B5. Raised as a question: should the
descriptions change so the model's two vocabularies line up? Answer below.**

### The mismatch, measured

`story_load` emits `chars` and `loc`. The write side (`story_describe`,
`story_draft`, the schema) uses `characters` and `location`:

```
story_load actually emits:  acts, characters, chars, id, loc, plots, scenes,
                           sequences, worlds
write-side names absent from story_load:  location, setups, crisis, climax,
                           payoffs, variant_of, sequence_id, act_id, world,
                           act, primary_plot, climax_scene_id, character
load names with NO write equivalent:  chars, loc
```

`chars` and `loc` were **deliberately chosen for token cost**, not by accident.
`story_load_redesign_spec.md:191`:

> `chars, loc` | keep | Structural cross-reference, replaces
> `character_scene`/`location_scene` relations

And line 9, the spec's first principle, is that the payload's whole purpose is
to remove ~12.9k tokens. `chars` and `loc` are the compressed form of exactly
the fields the spec says the relation rows replace.

### So: should the descriptions change, or story_load?

**Neither — and this is the finding.** The two vocabularies are not the same
concept, so renaming either would be wrong:

- **`story_load` is a read summary.** It nests, abbreviates, and drops fields
  the agent can get back with `story_retrieve`. `chars` is a compression of
  `characters`; `loc` of `location`. The spec is explicit that it also drops
  `heading`, `time_of_day`, `value*` and `conflict_levels` **on purpose**, each
  with a "retrieve this instead" note.
- **`story_describe` is the write vocabulary.** Its field names ARE the
  `story_draft` op keys. An agent that renamed `characters` → `chars` in a
  `story_draft` op would get a hard error — `edit_entity` rejects unrecognised
  keys by design, precisely so a wrong name cannot be silently dropped.

Renaming the write side to match the read side would break every op. Renaming
the read side would undo a deliberate token optimisation that saved ~12.9k on a
feature-length project. **Both are load-bearing.**

### What is actually missing

Not a name change — a **bridge**. Nothing currently tells the model that
`loc` in a load payload is the `location` it writes, and nothing in
`story_describe` says its `location` will come back as `loc`. The model has to
infer the correspondence, and the inference is asymmetric: `chars` →
`characters` is guessable, `loc` → `location` is not.

**The fix is documentation, in the two tools' own descriptions** — not a
rename, and not a new field:

- `story_load`'s description states the abbreviations it uses, so the agent
  knows `chars`/`loc` are the same links under shorter names.
- `story_describe`'s description says these are the field names to pass to
  `story_draft`, and that a field named `X` may come back from `story_load`
  under a short form.

Cheap, no data-model risk, and it removes the guess that produced both B7-style
errors and this confusion. **Recorded as an improvement (I3), not a defect** —
nothing is broken, something is undocumented.

### `id` vs `slug` — investigated, and the verdict was WRONG — **reversed 2026-09-28**

> **Read this as the reasoning, not the conclusion.** The measurements below are
> all correct. The verdict they produced — *"not a bug, a missing bridge"* — was
> wrong, and it is the same error the D3 investigation made: **describing what
> the code does and calling that a defence.** The code *worked*. What it needed
> was one fewer name.
>
> Two things this entry got right and then talked itself out of:
>
> 1. It called the problem *"a missing bridge, not a wrong name"* and proposed
>    fixing it **in prose**. That sentence is the mistake. A bridge that has to
>    be written down is the cost of the two names, not a gap in the bridge — and
>    `chars`/`loc` had already been deleted on exactly that reasoning (I4), so
>    the same argument was available here and not applied.
> 2. It noted that `id`'s description says *"Stable slug reflecting dramatic
>    function"* — i.e. the schema was inviting the model to treat the id as a
>    dramaturgical slug. That is a design smell, and it was read as a
>    documentation detail rather than as the naming problem it was.
>
> **What it is now:** D5 step 3. The op argument is `id`, both prose bridges
> are deleted, and `slug` means only a project directory. The measurement
> stands; only the conclusion fell.
>
> Original entry follows, unchanged, as the record of how it was reasoned:

Checked rather than assumed, since it was raised as a possible bug:

- **The DB column is `id`.** `ENTITY_COLUMN_MAP` maps schema fields to it, and
  `FIELDS_TO_SKIP = {'id', 'type'}` deliberately excludes it from writes.
- **The op argument is `slug`.** `story_draft` ops are
  `{op, type, slug, data}` — the slug is a top-level op arg, never a field
  inside `data`.
- **`story_describe` shows `id` as a field** and it is genuinely write-ignored,
  but its description already says *"Stable slug reflecting dramatic function
  (e.g. 'mara-discovers-files')"* — so the value the model sees in `id` is the
  same string it must pass as the op's `slug`.

**Verdict: not a bug, and renaming `id` → `slug` in the schema would be
wrong.** `id` is the field's real name in the data model and in every read path;
`slug` is the op-argument name. The only gap is that the model must notice
`id`'s value becomes the op's `slug` argument. Same class as `chars`/`loc`: a
**missing bridge, not a wrong name.** The bridge note in `story_describe`'s
description covers both at once — worth one line each, no rename.

### What this says about the rest of D2

The original D2 entry claimed `story_describe` shows a section name and a field
name in the same output "with nothing saying they are different namespaces",
and that `id` is offered while ops supply `slug`. Both claims survive this
investigation and are unaffected by the `chars`/`loc` finding — which is
separate, and larger. The `id`/`slug` question raised alongside it is still
open: `columns_for_insert` takes `slug` and the DB column is `id`, so the op
key and the stored column genuinely differ. Worth deciding, but it is a naming
question about the *write* path, not the read path.

---

## D1. The tool cannot show the agent the shape of a structured value — **READ SIDE FIXED; write side is D4**

**`story_describe` now emits every schema key, including `sub_fields`**
(`commit` for that fix is folded into B7/B9 above). What remains is the
write side: nothing validates a structured value at write time. That is D4.

**The pattern.** `ENTITY_SCHEMAS` documents shape with `sub_fields` (B9) and
`stored_as` (B4). `story_describe` copies `type`, `default`, `optional` and
`description` into its output and drops the rest. So the schema knows things
the agent never sees, and the agent fills the gap by guessing.

This is the root of three separate findings — B7 (crash), B9 (silent loss),
B4 (a field advertised as a relation that is not one). **One omission in one
output builder, three unrelated-looking bugs.** Any other schema annotation
added in future will be dropped the same way, silently.

**The fix is one loop, not three patches:** emit every annotation the schema
carries, rather than a hand-picked list of the ones currently understood. A
schema key nobody reads is a schema key that does not exist, and the list of
keys that exists is only discoverable by reading the code that should have
been reading it.

**The design lesson worth keeping:** a schema that only the code reads is
half a schema. Whatever the schema asserts about a field is only true of the
*agent's* behaviour if the agent is shown it.

---

## D2. One concept, two names, and the schema is not the one that wins — **RESOLVED ABOVE**

**Investigated and closed: not a defect.** The corrected analysis is in the
D2 entry above, under the status index. Neither side could be renamed, and
the `chars`/`loc` half was resolved by deleting the abbreviations (I4).

**The pattern.** `perspective` vs `perspectives`. `gap` (the field) vs `The
Gap` (the section). `op` vs `summary` vs `entity_id` across four op kinds.
`arc_complete` on a character against `arc_type`. Each is defensible
individually; together they make every field a small research task, and the
research is invisible — it just looks like slowness.

Two specific costs paid during this test:

- `story_describe` for `arc_beat` shows the **section** name `The Gap` and
  the **field** name `gap` in the same output, with nothing saying they are
  different namespaces. Writing prose to the wrong one is accepted silently
  and lands in a column nobody reads.
- The same output shows `id` as required, while the op supplies it as `slug`
  (B6). Two vocabularies for one identifier, one of them unwritable.

**The fix direction:** the section list and the field list are two different
things and should be *labelled* as such wherever they are shown together.
Whether to also align the names is a smaller question than making the
distinction visible — visibility first, renaming second.

---

## D3. The same link is expressible two ways, and readers disagree — **NOT A DEFECT**

**Investigated and closed.** The nine undeclared link fields are documented as
`extra` and the redundancy is deliberate. The full assessment, with the two
pieces of evidence, is in the D3 assessment above. B8 was the one real defect
in this area and it is fixed.

**The pattern, and it is the widest one here.** A scene's location is a
`location_id` column *and* — in the reference corpus — a `location_scene`
relation. A beat's scene is an `extra` string *and*, per a comment in
`columns_for_insert`, was meant to be a relation. A plot's beats are relations
*and* were also accepted as frontmatter. So for at least three link types there
are two storage paths, no declared authority between them, and readers that
each picked one:

| reader | reads | consequence |
|---|---|---|
| `story_load` orphan check | relations | B8: a referenced location reported orphaned |
| `get_project_summary` | frontmatter/columns | works here, blind to relations |
| relation walkers (dashboard, arc lookups) | relations | blind to the column path |

**Why this is the design finding and not three bugs.** Each symptom has a
local fix — read the column, or write the relation, or add an `isinstance`.
All three leave the underlying ambiguity intact, and the next link type
reintroduces it. B4, B5 and B8 are the same question asked three times.

**The fix direction:** decide, per link type, which storage is authoritative,
and have the other be derived rather than independent. Then every reader is
correct by construction instead of by having chosen the right source.

---

## D5 step 2. The arc_beat composite id enabled a silent wrong-entity write — **FIXED 2026-09-28**

**A beat's id was `{character}-{beat}`, and a bare beat label was resolved
with `id LIKE '%-{slug}'` — which matched every character owning a beat of that
name and took the first.**

**Reproduced, not theorised.** Two characters, each with an arc beat labelled
"The Choice":

```
before:  edit_entity(..., 'arc_beat', 'the-choice', {...})
         -> wrote to kael-the-choice, returned success: true
         -> mira-the-choice untouched, nothing reported

after:   the same call -> ValueError: Entity not found: arc_beat/the-choice
         edit by full id touches exactly one row
```

This was the only reproduced *silent data-corruption* bug in the whole live-test
round. Everything else found was noise in a report or a confusing vocabulary.

**The composite was also wrong on its own terms.** It is ambiguous to parse
back: a character `kael-the` with a beat `choice` yields `kael-the-choice`,
identical to kael/the-choice. That collision *was* caught by the primary key,
so it was loud — but it means the id was incorrect for inputs an author could
plausibly write, which is a defect independent of the lookup.

**Nothing referenced the composite.** The character link is the `parent_id`
column, set from the `character` frontmatter field — it never came from the id.
So the id is now simply the slug, and:

| change | where |
|---|---|
| `columns["id"] = slug`, not `f"{char}-{slug}"` | `core/entity.py:290-294` |
| the whole `arc_beat` branch deleted, `LIKE` fallback included | `core/writes.py:672-694` |
| two `entity_id[len(parent_id)+1:]` slices removed | `tools/story_export.py:164`, `:256` |
| the id is read from the note, not reassembled from the directory | `tools/story_import.py:302` |
| `_diff` matches note stems, not `{char}-{beat}` | `tools/story_import.py:70` |

**Checked across the class, not just the reported case.** Every other type
resolves by exact `(type, id)` and `id` is the PRIMARY KEY, so at most one row
can match. Duplicate *names* on other types are harmless — measured: two
characters named "Kael" and two locations named "The Garden", each edited by
id, **every edit touched exactly one row.** The `LIKE` branch was the only
lookup in the file by anything other than the primary key, and it is gone.

**The fixture needed converting, and not in the database.** The 11 arc-beat
notes were named after the beat number alone (`arcs/kael/1.md`) — fine as a
path, but two characters each have a `1.md`, so the stem is not an id.
Renamed to `arcs/kael/kael-1.md` with `id:` matching, which is **exactly what
the fixture database already held**. No data migration, and the round trip
(export → wipe → re-import) passes.

**Cost, measured before starting:** 892 tests, 57 failed on the first run, and
the failures were not arc-beat-specific — the import's `_diff` stopped matching
the renamed notes and refused to import, which cascaded into the load view and
the orphan check. Bisected per file rather than guessed: `story_import.py`
accounted for 49 of the 57. After the fixture conversion, 9 remained, all of
them tests asserting the old convention.

**Tests.** Two in `TestEditSafety` replaced the two that encoded the composite:
`test_arc_beat_id_is_the_beat_own_slug` asserts the id and that `parent_id`
still carries the character, and `test_arc_beat_edits_the_beat_named_and_no_other`
is the regression — two characters, same label, each full id edits only its
own. Six further tests across `test_arcs`, `test_field_coverage`,
`test_export_sweep` and `test_round_trip` updated off the old convention.

**Suite: 892, unchanged.**

---

## D5 step 3. One name for the entity id — **FIXED 2026-09-28**

**A create op said `slug`; every other op and every other tool said `id`.**
Same value, two names.

**The bridge between them was written down, twice** — and that is what made
this a defect rather than a preference:

- `story_describe.py` — *"an entity's `id` is the `slug` argument of its op"*
- `SKILL.md` — *"Don't use `slug` for retrieve"*

A tool that has to explain that two names are one value is telling you they
shouldn't both exist. Both sentences are now deleted, and a test asserts the
word `slug` cannot return to that description.

**`slug` keeps one meaning, and it is a different one:** a project directory,
`projects/<slug>/`. That is a real concept and it keeps its name — which is why
the word is still in the codebase. The problem was never the word, it was the
second *sense* of it.

**A second instance of the same defect, in `story_admin`.** Its schema
advertised `"slug"` while describing it as *"Entity id, as returned by
story_load"*, and its query was

```sql
WHERE id=? OR id=?     -- both parameters bound to the same value
```

That OR is a leftover from the arc-beat era, where one lookup genuinely tried
two things (the full composite, and the bare beat part). Step 2 removed the
reason for it; this removes the query. It is now `WHERE id=?`.

**Verified as the agent sees it**, served from the tool rather than from
source:

```
create: {op, type, id, frontmatter, sections?, summary}
stage with `id`      -> accepted, preview renders `character/kael`
stage with `slug`    -> "ops[0] (create) is missing: id."
```

**Scope, measured before editing:** 15 files, 51 insertions, 46 deletions. The
bulk of it is mechanical (`op["slug"]` → `op["id"]` in 6 places, 17 op-key
sites in tests). The two judgement calls were the *comments* — two docstrings
in `drafts.py` said "slug" about a field that is now `id`, and an error message
(`"{where}.slug must be alphanumeric…"`). A stale error message names a field
that does not exist, which is worse than a stale comment, so it changed.

**892 pass, unchanged.** Four tests asserted the old vocabulary and were
updated: two error-message strings, one restore target key, and the describe
test — which asserted the bridge sentence *existed* and now asserts its
opposite.

**D5 is now 3 of 5 done.** Steps 4 and 5 remain: generate the id so the agent
stops supplying one, then id-into-frontmatter and title filenames.

---

## D5 step 4. Generate the id — **CANCELLED 2026-09-28, and the reason matters**

**Measured before building, not after. The idea is sound and it does not pay.**

**The blocker:** a relation is a lookup by id, validated at commit. A scene's
`characters: ["kael"]` resolves with `SELECT id FROM entities WHERE id=?`. So
today the agent creates a character *and* a scene that uses it **in one batch** —
verified:

```
2 ops staged -> commit: success
```

That works **only because the agent chose the id.** With a generated id the
agent cannot write `"characters": ["???"]` for a character it is creating in the
same batch. It would have to commit the character, `story_load` to learn the hex
id, then commit the scene — **three round trips per referenced entity**, and for
a 40-entity project that is a hundred-plus places to lose the thread.

**The obvious fix is the bug step 2 just fixed.** Matching relations by *name*
instead of id is exactly the silent wrong-entity write: two characters named
"Kael", the scene goes to the wrong one. Rejected.

**And it does not buy the thing it was for.** The goal was a clean division —
*id for data, title for user-facing* — and **step 5 delivers that**. Generated
ids add nothing to it; they only remove the agent's ability to write its own
references.

| | agent supplies id | agent doesn't |
|---|---|---|
| one batch, entity + its references | yes | **3 round trips each** |
| readable ids in fixtures/tests | yes | yes (fixtures unaffected either way) |
| id/title division (step 5) | yes | yes |

**Kept:** agent-supplied ids. A generated id is a legitimate design — it just
costs more than it returns here, and the cost lands on the agent.

---

## D5 step 5. Filenames by title, id in the frontmatter — **FIXED 2026-09-28**

**The filename *was* the id.** Renaming a note silently renamed the entity and
every relation pointing at it. Now:

```
characters/Kael.md            id: kael
arcs/Kael/The Choice.md       id: kael-3   character: kael
```

This is the division of function the whole D5 investigation was after, and it
was the last step standing between the plan and the goal.

**The premise was stated for the wrong reason, and the right one is stronger.**
The plan said this needs a generated id to put in the frontmatter. It does not —
it needs the id *written down*, because the filename is the only place it used
to live. Only four of the ten types declared `id` in their schema; for the rest
the filename carried it silently. `fm["id"] = entity_id` is now set once after
the per-type branch, rather than in ten of them.

**Collisions are real but harmless, and the reason is worth keeping.** "The
Choice" is one beat per character in `save-the-children` — but they land in
different folders. The counter only fires for two entities in one folder:

```
The Choice.md, then The Choice 2.md
```

It is **cosmetic**: nothing references a filename, whereas an id collision would
be silent. That asymmetry is the entire reason `id` is the primary key, so the
counter is cheap insurance rather than a correctness mechanism.

**One bug, found by a test rather than by reading the code.** The counter is
per *note*; applied to the **arc folder** it gave every beat of one character
their own directory, so Kael's three beats landed in `Kael/`, `Kael 2/` and
`Kael 3/`. Caught by a test asserting on the file list:

```
assert 'characters/kael.md' in ['arcs/Kael/First Doubt.md', ...]
```

The folder is cached per character id now. **A counter's scope is a decision, and
getting it wrong fails loudly in a file listing** — which is the good kind.

**The fixture needed a real conversion, and the failure mode was silent.** Its
31 notes were named for the id with **no `id:` field**, because the filename
carried it. Converting to titles meant adding the field; without it, an export
wrote `Kael.md` beside the old `kael.md` and the re-import died:

```
import: {'error': 'UNIQUE constraint failed: entities.id'}
after re-import: 0 entities        <- everything gone
```

**A real project does not hit this** — the sweep deletes the id-named note,
because the previous export wrote it and the manifest remembers. The fixture
ships without a manifest, so it needed doing by hand. Worth recording: the
manifest is what makes a layout change safe, and a fixture without one is the
only place the hazard is visible.

**The fixture's `story.db` is gitignored** — a build artifact; the markdown is
the source. It also still said `type='arc'` on disk, stale from before that
rename, so no code path read those 11 rows as beats. Corrected, but the
markdown is what makes it stick:

```
rebuild from markdown alone: success
32 entities, type='arc_beat' for all 11 beats, 12 relations
```

**Tests:** 9 assertions that hardcoded a filename now look the note up by its
frontmatter id (`note_for` / `note_rel` in `test_round_trip`). That is the
property this step provides, so the tests use it too.

**The property, measured — and it was not true before.** Export, **delete the
database outright**, re-import from the notes alone:

| | before step 5 | after |
|---|---|---|
| entities | **lost 3, gained 3** | **identical** |
| relations | **lost all** | **identical** |
| sections | **lost prose, incl. whole beats** | **identical** |

And the case that was impossible before — rename a note by hand, re-import:

```
'Kael.md' -> 'Renamed By Hand.md'  ->  ('kael', 'Kael')
```

**892 pass, unchanged.**

**D5 is complete: steps 1, 2, 3 and 5 built; step 4 cancelled with its reason.**

---

## D5. One concept, three names — `slug` / `entity_id` / `id` — **DONE, with one step cancelled**

> **This is the parent entry, and it is now half-superseded by its own steps.**
> The position it records assumed the id would be *generated*. That part was
> cancelled — see the step 4 entry. The other three parts shipped. Read the
> per-step entries above for what is true now; this one is kept because its
> measurements and its two overturned positions are the reasoning the steps rest
> on.

**A position was reached on 2026-09-28.**
`tasks/task_17*/entity_identity.md` holds the full investigation, the
measurements, the two positions that were **wrong and later overturned**, and
`tasks/task_17*/entity_identity_plan.md` holds the build order — five steps,
sequenced so the two that fix reproduced bugs land first and the file-layout
change lands last. **Baseline: 889 tests pass; no step may commit with fewer.
Final: 892, unchanged by every step.**

**The position as agreed, with what actually happened marked:**

> The id is **generated** (`secrets.token_hex(4)`, 8 chars), never supplied by
> the agent, stored in the DB **and** in every note's frontmatter, and never
> derived from anything. The **title** is the only user-facing name — in the
> dashboard, in the payload, and in the exported filename. The op argument is
> `id` everywhere; the word `slug` survives only for a *project directory*.

| clause | outcome |
|---|---|
| id generated, never agent-supplied | **CANCELLED (step 4)** — three round trips per referenced entity |
| id stored in the DB **and** in every note's frontmatter | **done (step 5)** — and it was never about generation |
| title is the user-facing name, including the filename | **done (step 5)** |
| op argument is `id` everywhere; `slug` only for a project directory | **done (step 3)** |

**The third clause is the one that mattered, and it did not depend on the
first.** The filename was the id, so a title-keyed filename needed the id
written down somewhere else — but "somewhere else" is the *frontmatter*, not a
generator. The coupling that made this look impossible was removable on its own,
which is why step 5 was unaffected by cancelling step 4.

**What was established by measurement.** One value had four names depending on
the op: `create` took `slug`, `edit`/`delete` took `entity_id`, `story_retrieve`
took `id`, and the DB column was `id` — with two tools carrying a prose bridge
explaining that `id` and `slug` are the same string, which is the tell. The
filename was the id (`story_export.py:171` writes `{entity_id}.md`,
`story_import.py:279` reads `note.stem`), and that coupling is what made two
earlier proposals wrong.

**Two positions were overturned, and both reversals are recorded:**

- *"Generate opaque uuid ids."* Right in principle, but the first cost figure
  was wrong by ~4× (costed 36 chars against 29 ids, not the 90 appearances in a
  payload). Corrected to +717 tokens per `story_load` for `uuid4()` against
  +87 for an 8-char id.
- *"Name the files after the title"* was **rejected** — correctly, at the time,
  because the filename *is* the id, so a title-keyed filename made the id
  derive from a mutable field and a retitle silently orphaned every reference.
  **That objection was real, and step 5 answered it a different way than this
  entry assumed.** The objection said *"that objection is void once the id is
  generated"* — and step 4 was then cancelled, so that escape route closed. The
  proposal shipped anyway, because the id did not need generating: writing it
  into the frontmatter removes the coupling directly. The filename stopped
  being the id's only home, and a retitle no longer touches it. **The right fix
  for "the filename is a bad place to keep the id" was never "make the id
  independent of everything" — it was "stop keeping it there only".**

**Two fixes fall out of it, and are not chores:** dropping the arc_beat
composite id (a generated id would make it 73 chars, and the character link
already lives in `parent_id`), and deleting `writes.py:689`'s
`LIKE '%-{slug}'` fallback — which is *currently causing* a silent
wrong-entity write, reproduced: two arc beats named "The Choice", an edit on
one hit the other with `success: true`.

**Still open, and not a measurement:** whether the vault is for reading or only
a backup. Title-keyed filenames make it browsable again; the cost is that a
hand-edited filename no longer renames the entity, so the frontmatter `id`
becomes the authority. The safer direction, but a behaviour change.

**The one decision already safe:** `slug` keeps meaning a *project directory
name* (`projects/<slug>/`, `story_resolve`). That is a different concept from
an entity id and should not be renamed as part of this work.

**The deployment constraint, which changes the arithmetic.** The plugin is not
deployed; every project in existence is a test artefact. So any data change is
a one-time script rather than a migration inside the plugin. Two consequences,
both recorded in full in `entity_identity.md`:

- It makes the arc_beat composite fix (making the composite id the value the
  agent supplies) affordable — that option needs a data change, which is now
  just a script.
- It makes three pieces of **compatibility code deletable**, because they exist
  only to serve a database written by an earlier build and no such database
  exists. Measured: all three real databases already have the soft-delete
  columns, none has a `drafts` table, and **zero** number-typed fields are
  stored as a string anywhere. The candidates are
  `ensure_soft_delete_columns` (`core/db.py:125`), `ensure_drafts_table`
  (`core/db.py:149`), and the read half of `_coerce_number` (`core/db.py:302`).
  **Not deleted — filed as Q7 in the analysis, to be sequenced deliberately.**

---

## D4. No shape validation at write time for structured values — **OPEN, the remaining half of D1**

**Verified still open** (no `sub_fields` check in `core/writes.py` or
`core/drafts.py`). D1 fixed the read side; this is the write side. Highest
value of the open items: the agent can now see the shape but is not stopped
from writing a wrong one, so a bare string can still land where an object
belongs — the B7 crash, silent instead of loud.

**The pattern.** A `create` op is validated for required fields and enum
membership (both work — see the verified list). But a value's *shape* is not
checked at all when the schema documents one. So a string where an object
belongs is written, committed, reported as `✅`, and only fails later at read
time — in B7's case taking down `story_load` for the whole project.

**The asymmetry that makes this expensive:** the write path is lenient and the
read path is brittle. Those should not both be true. A cheap
`validate_shape` extension — if a field has `sub_fields`, check the value is
the declared type and the keys are the declared keys — turns B7's crash into a
stage-time finding and B9's silent loss into a reported one, before anything is
written.

**This is the same argument as B9's fix, from the other side.** Showing the
shape prevents the mistake; checking the shape catches it when the display is
not consulted. Both are cheap; neither is a substitute for the other.

---

## B10. A `number` field stores as a string and breaks the dashboard — **FIXED**

**Severity: high.** The dashboard does not open for the project, and the cause
is a type the schema says cannot happen.

**Observed.** `story_dashboard(project="lighthouse-test")`:

```
TypeError: '>' not supported between instances of 'int' and 'str'
  tools/story_dashboard.py:314  data = get_dashboard_data(project_path)
  core/db.py:1294               proj_dict["act_count"] = max(proj_dict.get("act_count", 3), len(acts))
```

**Cause.** `act_count` is declared `"type": "number", "default": 3`. I passed
`3`. It is stored as the **string** `'3'`:

```
act_count value: '3'  type: str
```

`max('3', 3)` raises. The `default: 3` in the `.get()` call does not help —
the key is present, so the default never applies.

**Why the type changed — narrowed by the live test.** `extra` is a JSON blob,
and JSON does preserve int-vs-string, so something in the path coerced it.
That something is the **create** path specifically: an `edit` op writing the
same value through `story_draft` stored a real `int`:

```
before create_project:  act_count = '3'  (str)   → dashboard TypeError
after  an edit op:      act_count = 3    (int)   → correct
```

So `create_project` stringifies and `edit` does not. Worth finding the exact
line in the create path, because the two should agree — and the fact that they
do not is the bug, not either one alone. Note also that the *edit preview*
rendered `act_count: 3 → 3` with an int on the "before" side, so the read
path for previews coerces correctly while `get_dashboard_data` does not. **The
same value is a string, an int, and an int in three different readers.** That
inconsistency is the actual finding.

**The reference project does not set `act_count` at all** — confirmed by
querying it — so `proj_dict.get("act_count", 3)` returns the int default and
the bug never fires there. Which means: **no fixture exercises a numeric
field.** This is the second time in this test that a field's type was only
ever seen in one shape.

**Why this belongs in the same family as B9/D4.** D1 is "the agent cannot see
the shape"; this is "the shape is not preserved". Both are the schema being
advisory rather than authoritative. A `number` field that holds a string is
the same class of problem as an object field that holds prose — the schema
says one thing, the store holds another, and the failure surfaces somewhere
else entirely.

**The fix direction — two halves, and the second matters more.**

1. Coerce on write. `columns_for_insert` already knows `entity_type` and has
   the schema; a field declared `number` should be stored as a number. That
   stops new data breaking.
2. Coerce on read, or at minimum in `get_dashboard_data`. Existing projects
   already hold strings — including `browser-verification-test` for any
   numeric field set as a string by an older write path. **Fixing only the
   write path leaves every existing project broken**, and the fix would look
   complete while the dashboard stayed down.

**Cheapest correct version:** a small `_coerce_number(value, default)` used
wherever a numeric field is consumed. The dashboard is one call site; the
question is how many others exist. Worth grepping for `max(` / `sum(` /
comparisons against schema-typed numbers before assuming this is one line.

**Related, same query.** `structure_type` and `status` on the project are
also strings where the schema may intend an enum. They did not break anything
here, but they are stored in the same blob with the same lack of enforcement,
so they are the same risk waiting for a comparison.

---

## B11. No format check on the authoring path — **RESOLVED, see the entry below**

**Severity: high.** The safeguard for scene formatting does not exist on the
path that writes scene script. **This is not a defect in
`core/fountain_validator.py` — that module works, for what it was built for.**
See "Why the existing validator must not be modified" below; it is a
load-bearing constraint on the fix.

### The gap: nothing checks the authoring path

`core/fountain_validator.py` (235 lines) exposes `validate_screenplay`,
`is_valid_screenplay` and `get_validation_summary`. It is referenced **only**
by the skill reference doc, never by a tool. Task 18 already noticed:

> "**Dead `core/screenplay.py` + `core/fountain_validator.py`** — Retained with
> updated docstrings explaining future use" … "`fountain_validator.py` imported
> nowhere."

It is not in `validate_shape`, so staging a scene performs no format check at
all. **That is the defect: the authoring path is unchecked.**

### Why the existing validator must not be modified

**It was built for a different feature — importing a user's own script — and it
works there.** That feature was never implemented, but the effort is real and
the module is correct for its purpose. Recorded 2026-09-28 as a hard
constraint:

- **Do not modify `fountain_validator.py`.** Its job is to accept a real,
   human-written screenplay and tell you what is in it. Loose, permissive
   parsing is *correct* there: a script with no scene heading is still a valid
   screenplay fragment, and a parser that rejects it would refuse legitimate
   input.
- **Our use case is the opposite.** An agent is *writing* script from a
   documented format, and we need to tell it where it departed. That is a
   linter, not a parser — a different job with different rules.
- **So: a new module**, taking inspiration from the existing one, wired into
  `validate_shape`. The existing file stays intact and available if script
  import is ever built.

Bluntly: **the existing validator is not broken, it is the wrong tool.** Two
modules that both claim to "validate Fountain" but answer different questions
is the same naming trap as D2, so the new one must not reuse the name.

### What the authoring-side check needs

Two additions, and the second is the one that matters:

1. **Presence checks, not just adjacency.** A scene whose `Content` contains
   dialogue-ish text should have at least one classified character cue; a
   scene with a `heading` field should have a matching scene heading. "I found
   zero cues but N lines ending in a colon" is the finding.
2. **Detect the near-miss rather than ignoring it.** A line matching
   `^[A-Z][A-Z0-9 .'-]{1,30}:\s+\S` is almost certainly a character cue
   written inline. Classifying it as `action` is defensible for a *parser*
   (Fountain genuinely has no inline cues); for a *linter* it is the single
   most valuable thing to catch, because it is what the agent naturally
   produces.

**Why the two jobs diverge on this exact line** — the evidence that these are
not one function. `_classify_line` recognises a cue only when:

```python
if stripped.isupper() and any(c.isalpha() for c in stripped):
    return 'character'
```

`ELIAS: You could have telephoned.` is not `isupper()`, so it falls through to
`'action'`. **For an importer that is right**: the line genuinely is action in
Fountain, and reporting "unknown element" would be a false alarm on a valid
file. **For a linter it is a failure**: the author almost certainly meant a
cue. Same input, opposite correct answer — which is the cleanest possible
argument for two modules rather than one configurable one.

**This is the same shape as B10 and B9, one level up.** A validator that
checks local consistency will always pass globally inconsistent content, for
exactly the same reason `max('3', 3)` was never reached: nothing asks the
question that the data actually needs answered.

### Where it should be called, and the skill-path problem

The natural place is `validate_shape` in `core/drafts.py` — the same place
required-fields and enums are checked, so a malformed scene is a **stage-time
finding**, before anything is written, and it lands in the same `validation`
list the agent is already told to relay. That is the whole answer to "some
level of error or advice": the finding says what is wrong with the scene's
format, and does not need to name a skill path at all.

**On naming the skill from the tool:** agreed that is not needed, and should
not be done. A finding that says

> `scene/the-last-watch`: 2 lines look like inline character cues
> ("ELIAS:", "MARA:") — Fountain wants a cue on its own line, ALL CAPS, with
> the dialogue indented beneath it

is actionable on its own. Coupling the tool's message to a skill file path
would break the moment the skill is renamed, moved into the new
`skills/hermes-story-architect/`, or simply not loaded. **The format rules
belong in the skill (prose, for an agent that is learning); the detection
belongs in the tool (a self-contained message).** The skill teaches, the
validator enforces, and neither needs to know the other's filename.

**What is still open:** the new module's name and whether it reuses
`_classify_line` (probably yes — the classification is reusable, the *verdict*
is not) or takes a simpler line of its own. Decide when the fix is scheduled.

---

## B11. Scene Content has no format check — **DONE 2026-09-28**

`core/scene_content_lint.py`, wired into `validate_shape`. **One rule:** the
first non-blank line of a scene's `Content` must be a scene heading.

### Why only that one rule

Everything else the format allows is the agent's business, and restating it in
code means two things to update when the format evolves. This one case is worth
a check because the failure is **silent** — `core/screenplay.py:33` only
accumulates into a scene once a heading has been seen, so:

| Content | result, measured |
|---|---|
| no heading anywhere | **0 scenes** — the scene is absent from the script |
| heading, but not on the first line | scene renders, **everything before the heading is dropped** |

Both look like a working dashboard. Neither is signalled anywhere. The second
is the more dangerous of the two, because the scene *is* there and looks right.

The message names which of the two happened — they look identical from the
dashboard, and "my scene is missing" sends the agent looking in the wrong place.

### Forced headings are headings

`.SNIPER SCOPE POV` and `.OPENING TITLES` are recognised as scene headings and
are **accepted, with no special case**: the linter imports `SCENE_HEADING_RE`
from the renderer rather than re-deriving it, so the two cannot disagree about
what a heading is. (Verified: the existing regex already matches all of
`INT.`/`EXT.`/`EST.`/`INT./EXT.`, forced, lowercase-forced, and `#1A#` numbers,
and correctly rejects action lines, transitions, cues and `#` headings.)

### Three things ruled out by measurement, not assumption

- **Sections (`#`)** — never appear in a scene's Content; structure comes from
  acts. Removed from the reference.
- **Boneyards (`/* */`)** — stripped before rendering, so nothing to check. The
  reference now says so explicitly.
- **Transitions before a heading** — legitimate in Fountain generally, but a
  transition belongs to the scene you cut *from*, so at the top of a scene it is
  the error. That is a **note in the reference**, not a code check.

Once those three are excluded, **nothing** legitimately precedes a heading —
which is what collapses the rule to a single predicate with no exemption list.

### Data

6 of 6 real scenes in `browser-verification-test` open with their heading. The
3 fixture scenes that do not are one-line stubs carrying `heading` in
frontmatter — unfinished, not a pattern, and they render as 0 scenes today.

### The constraint held

`core/fountain_validator.py` is **untouched**. It is a permissive parser for
importing a user's own script, where a fragment with no heading is legitimate
input; this is a linter for an agent writing from a documented format. Same
naming, opposite correct answers — two modules, not one configurable one.

### Not done, on purpose

- **Inline cue near-miss** (`MIRA: You knew?`) — real, but cosmetic: it becomes
  `action` and still renders. Left until it actually bites.
- **The inline-cue/adjacency checks** the original B11 note proposed — same
  reason: they restate the spec, and the silent failures are the ones worth a
  check.

889 pass; 2 integration tests fail without the wiring.

---

## Verified sound

Recorded so the skill does not hedge on what is solid.

- **Destructive actions refuse without a confirmation string.** Both
  `purge` and `delete_project` returned `Purge refused. It is irreversible and
  must be the user's call.` with an `action_required` naming the exact string to
  pass. The refusal message tells the *agent* what to send while making the
  decision the *user's* — the right split, and it means a hallucinated
  confirmation cannot look like a refusal.
- **`purge` honours the age floor and reports the count honestly.**
  With `purge_confirm` supplied and nothing past the floor: `Nothing is old
  enough to purge (0 deleted entities are younger than 30 days). They stay
  restorable.` — a number, not an empty success.
- **`delete_project` backs up outside the project tree.** The folder is
  removed, and `backups/lighthouse-test_20260928_022215.db` is written to the
  *parent* `backups/` directory, so the backup does not go down with the
  project. Verified restorable, not merely present: 18 entities, 120 sections,
  9 relations, `integrity_check: ok`, matching the counts measured before the
  delete. The tool also states the recovery path inline.
- **`story_export` round-trips Fountain and relation-backed objects.**
  Verified on the deleted project: scene `Content` keeps cue indentation,
  parenthetical nesting and transitions verbatim; `relationship.perspectives`
  exports as the correctly nested object with all five sub-keys and `strength`
  still a number; all four plot `description` values are present. This makes
  export a **free regression check for B9** — if those descriptions go empty
  again, export dropped them.
- **Destructive-action ordering is a decision, not a script.** `purge` before
  `delete_project`, because purge's age floor is the one guard standing
  between a soft delete and permanent loss. Testing it on the same project
  that `delete_project` then removes would prove nothing about the ordering.

- `list_projects` — enumerates without opening a database.
- `create_project` — folder + DB created, every non-computed field persisted.
  The empty `sections` rows are `standard_sections()` placeholders, not a fault.
- `stage` — writes nothing. `entities` / `sections` / `relations` counts
  identical before and after; only the `drafts` row appears. Same on restage.
- restage diff — attributed per-op *and* per-field:
  `create character/elias-kade (frontmatter, sections)` vs
  `create character/mara-venn (sections)` when only Elias's frontmatter
  changed. Real granularity, not entity-level hashing.
- `list` and `discard` — both fine.
- `commit` write path — all three ops landed, values correct, draft row
  consumed. Only the *response* is wrong (see B1).
- **Relations from `frontmatter.characters`** — a `create scene` op carrying
  `characters: [...]` inside frontmatter (no separate relations key) produced
  the correct `character_scene` rows, in the order given: 5 rows for 3 scenes
  with cast sizes 1 / 2 / 2. This is the trap task 28's Phase 3 guard test was
  written for, confirmed live.
- **In-batch cross-entity references** — sequences created in the same draft
  as their acts resolved `parent_id` correctly. Commit sorts creates so
  dependents land after their targets.
- **Soft delete is a flag, not a removal, and `restore` is its exact inverse.**
  Deleting `arc_beat/elias-kade-the-offer` left `entities 18` and
  `sections 120` untouched, set `is_deleted=1` with a `deleted_at` stamp, and
  kept the prose, the `extra` fields, `parent_id` and `order_key` intact.
  `story_admin(action="restore")` cleared both flags and reported
  `was_deleted_at` plus an empty `restored_cascade_children`. Counts never
  moved at any point in the round trip.
- **`edit` ops render a real `before → after`.** Confirmed on both a field
  edit (`relationship.perspectives`, `plot.setups`) and the plot description
  fix. One caveat: a relation-backed field's *old* value renders as
  `_not set_` even when a bare string was previously stored, because
  `_preview_edit` cannot read it back. The "after" side is accurate; the
  "before" side is not, and should not be trusted for relation fields.
- **`reorder` renumbers `order_key` and touches nothing else.** Swapping two
  scenes moved them to 1.0/2.0 with the new first, left a third scene in
  another sequence at 1.0, and kept all 9 relations. The commit report names
  it `reorder scene (2 items)` — by item count, since a reorder has no single
  target entity.
- **Shape validation catches a bad enum, a blank required field, and a second
  unplanted enum.** A deliberately broken batch reported all three:
  `Invalid arc_type: sideways`, `Missing required field: title`, and
  `Invalid time_of_day: MIDNIGHT` (unplanted — the enum check firing on a
  second field is not luck, it is the same code path). The blank-`title`
  finding is the case task 28's Phase 6 fixed: present-but-empty on a merged
  frontmatter, invisible to the old `field not in frontmatter` test.
- **Staging an invalid batch is safe.** It reported findings, was discarded,
  and wrote nothing: counts unchanged, neither bad entity present.
