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
| detecting the error | `validate_shape` in `core/drafts.py` | it must run whether or not a skill is loaded |
| reporting the error | `story_draft`'s `validation` list | the agent is already told to relay this list |

**The dashboard gets the second half.** Rendering malformed script as prose is
I1, and it is a separate fix: the dashboard should not assume its input is
well-formed. A renderer that falls back to `<pre>` when it cannot parse a scene
is more robust than one that assumes success — same lesson as B1 at a
different layer: do not trust that data arriving in a view was already checked.

**What this does not settle:** whether the presence checks extend the existing
`fountain_validator.py` or are written fresh. See the caveat at the end of B11
— `fountain_lexer.py` is an unfinished port, and reviving half-finished code
may cost more than the checks are worth. Decide when the fix is scheduled.

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

## B4. `stored_as: relation` is advertised for fields that store in `extra`

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

## B5. `arc_beat.scene` creates no relation — confirmed against the fixture

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

## B8. `story_load` reports a referenced location as `orphaned`

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

# Design gaps the live test exposed

Not bugs in a single function. These are the *shape* problems the test
surfaced — the ones that make an agent slow, wrong, or uncertain, and that
would do the same to a human writing the same data. They are collected here
because fixing one symptom at a time leaves the cause in place.

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

## B11. The Fountain validator passes malformed script, and nothing calls it

**Severity: high.** The safeguard for scene formatting does not exist in
practice, despite existing in the codebase. This is the answer to "should
there be a safeguard if scene content is not written properly" — the answer
is that one was written, it works, and it is not wired up and does not detect
the failure it was meant to catch.

### The unused half

`core/fountain_validator.py` (235 lines) exposes `validate_screenplay`,
`is_valid_screenplay` and `get_validation_summary`. It is referenced **only**
by the skill reference doc, never by a tool. Task 18 already noticed:

> "**Dead `core/screenplay.py` + `core/fountain_validator.py`** — Retained with
> updated docstrings explaining future use" … "`fountain_validator.py` imported
> nowhere."

So the module is dead code, retained on the expectation of a future
Fountain→entity import feature. It is not in `validate_shape`, so staging a
scene performs no format check at all.

### The broken half — it does not detect the actual failure

Wired in or not, it would not have caught this. Run against the three scenes
staged in `lighthouse-test`:

```
mara-offers-to-help     valid: True   0 issues
the-lamp-comes-back-on  valid: True   0 issues
the-last-watch          valid: True   0 issues
```

All three are malformed — no scene heading in the body, inline `ELIAS:` cues
instead of Fountain cues — and the dashboard renders them as prose, which is
what prompted this. The validator is silent on all of it.

**Two independent reasons:**

**1. Every rule is local.** The checks are all "does this line agree with its
neighbour" — a cue needs a blank line before it, a transition needs `TO:` at
the end. There is no rule of the form "a scene must contain a scene heading",
because nothing tracks what the scene *contains*, only how each line relates to
the one above. A scene with no heading and no dialogue has no misbehaving
line, so there is nothing to flag. Tested and confirmed: a pure-action scene
scores 0 issues.

**2. Inline cues are misclassified, so the most common error is invisible.**
`_classify_line` recognises a character cue only when:

```python
if stripped.isupper() and any(c.isalpha() for c in stripped):
    return 'character'
```

`ELIAS: You could have telephoned.` is not `isupper()` — the dialogue after
the colon is lowercase — so it falls through to `'action'`. **A scene written
entirely in inline-cue style classifies as 100% action**, and a validator that
only reasons locally sees a perfectly well-formed action sequence. Tested:
inline-cue text and mixed-style text both score 0 issues.

**This is the same shape as B10 and B9, one level up.** A validator that
checks local consistency will always pass globally inconsistent content, for
exactly the same reason `max('3', 3)` was never reached: nothing asks the
question that the data actually needs answered.

### What a working safeguard needs

Two additions, and the second is the one that matters:

1. **Presence checks, not just adjacency.** A scene whose `Content` contains
   dialogue-ish text should have at least one classified character cue; a
   scene with a `heading` field should have a matching scene heading. "I found
   zero cues but N lines ending in a colon" is the finding.
2. **Detect the near-miss rather than ignoring it.** A line matching
   `^[A-Z][A-Z0-9 .'-]{1,30}:\s+\S` is almost certainly a character cue
   written inline. Classifying it as `action` is defensible for a Fountain
   parser; for a *linter* it is the single most valuable thing to catch,
   because it is what the agent naturally produces.

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

**One caveat to check before building it:** `fountain_validator.py` is dead
code of unknown quality — `_classify_line` is a hand-rolled classifier, and
`fountain_lexer.py` is an unfinished port (per the task notes). Extending a
half-finished module is a bigger job than writing the presence checks fresh.
Worth a look at `fountain_lexer.py`'s state before deciding whether to revive
or replace.

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
