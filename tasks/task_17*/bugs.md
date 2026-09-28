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

## B1. `commit` sometimes reports failure for a commit that succeeded

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

## B2. Objects nested inside array arguments lose their keys

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

## B3. `list_projects` reports `has_database: false` for a markdown-only project

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

## I1. Scene script content is not presented as a screenplay

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

## I2. Nested object fields render as a raw Python dict repr

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

## B4 / B5 (original entries)

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

## B6. `arc_beat` requires an `id` in frontmatter that the write path ignores

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

**Why `id` can never be satisfied anyway.** The op supplies the id as `slug`,
and `columns_for_insert` (`entity.py:293`) builds the composite id itself:

```python
columns["id"] = f"{char_slug}-{slug}" if char_slug else slug
```

So frontmatter `id` is never read on the write path. An author who *did* pass
`id` in frontmatter would have it validated, ignored, and land with a different
id than the one they supplied — which is its own silent surprise. The field
should not be settable here at all.

**Related, worth checking in the same pass:** `arc_beat.REQUIRED_FIELDS` also
lists `action`, `gap`, `choice`, `shift`, `y` — all of which the schema marks
`optional: true` with placeholder defaults. So the same list disagrees with the
schema about those five as well. They did not fire here only because I filled
every field. An author leaving `action` at its `"Action not described"`
placeholder would get a "Missing required field" finding on a field documented
as optional. **This is the same class as the inert-merge bug task 28 Phase 6
fixed** — worth checking whether `REQUIRED_FIELDS` is still trustworthy for
any type, not just arc_beat.

---

## B7. `story_describe` hides `sub_fields`, and nothing guards the shape

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

## B8. A scene's location is invisible to every relation-based reader

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

## B9. `sub_fields` is dropped by `story_describe` for every field that has it

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

## What I expected to find

Two competing authorities per link type, each with readers that picked one.
Pick the winner per link, derive the other, done.

## What is actually there

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

## What follows

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

## Are the nine undeclared link fields undeclared BY DESIGN? (assessed 2026-09-28)

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

## I3. The two vocabularies were never bridged

One sentence per tool description, which is the whole fix:

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

## D2. `story_load` and `story_describe` use different names for the same links

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

### `id` vs `slug` — settled: both are correct, in different places

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

## D1. The tool cannot show the agent the shape of a structured value

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

## D2. One concept, two names, and the schema is not the one that wins

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

## D3. The same link is expressible two ways, and readers disagree

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

## D4. No shape validation at write time for structured values

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

## B10. A `number` field stores as a string and breaks the dashboard

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

## B11. No format check on the authoring path (the existing validator is not the tool for it)

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
