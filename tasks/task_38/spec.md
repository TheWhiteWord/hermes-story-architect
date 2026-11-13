# Structured scene headings — spec

## Problem

A scene's heading exists as **two independent representations**:

| | A — the field | B — the Content first line |
|---|---|---|
| Stored | `entities.extra.heading` (free text) | first non-blank line of `## Content` |
| Declared | `core/constants.py:184` — optional string | nothing |
| Written by | agent (`story_draft`/`story_edit`), importer | agent (Content), human (script editor) |
| Read by | dashboard list/panels, structure tree, content hash | script view, all screenplay stats, the lint |

They are kept equal by exactly one writer: `manual_edits.save_scene_script`
(`core/manual_edits.py:350-356`). Every other path can move one without the
other.

**The bug this spec fixes.** `get_screenplay_text` (`core/db.py:1567-1579`)
and `get_dashboard_data` (`core/db.py:1434-1444`) concatenate `sections.body`
and nothing else — the field is never composed into the script. Verified by
building the fixture DB and running the pipeline:

```
assembled screenplay_text:
'KAEL stands before the door…\n\nThe ADMINISTRATOR speaks…\n\nThe children step through…'
stats scene count: 0
```

The fixture stores `heading: INT. THE CENTRAL ROOM - DAY` in frontmatter and
body-only `## Content`. So an imported project has an **empty script view and
zero scenes in stats**, while the dashboard scene list shows the heading text.
That is the "cannot read the statistics of the script" problem.

Secondary defects:

- The agent path writes `Content` and `heading` independently; nothing requires
  a heading, and nothing composes one.
- The heading line is parsed in **four** places: `scene_script.parse_heading`,
  `fountain_lexer.parse_location`, `stats._parse_scene_location`,
  `screenplay.LOCATION_RE`. The place segment (below) touches all four.
- `screenplay_scene_ids` (`core/db.py:1444`) lists every scene with Content,
  but stats count only headed scenes; `script-view.js:89-93` maps ids to
  rendered headings positionally, so once any scene lacks a heading every click
  below it opens the wrong scene.

## Target model

### Schema (scene)

| Field | Type | Status | Notes |
|---|---|---|---|
| `int_ext` | string enum `INT.`, `EXT.`, `INT./EXT.`, `EST.` | new | default `INT.` |
| `place` | string | new | optional; the specific place within the location. Suggested from the parent location's `places` |
| `location` | string ref | keep | flat — a column + relation + delete cascade |
| `time_of_day` | string enum | keep | flat |
| `forced_heading` | string | new | the `.SNIPER SCOPE POV` escape; replaces the old "custom" mode |
| `heading` | — | **retire** | replaced by the fields above |

`int_ext`, `place`, `location`, `time_of_day`, `forced_heading` carry
`group: "Scene heading"` in the schema. `manual_entities.GROUPS`
(`core/manual_entities.py:200-202`) reads that key instead of its own dict, so
the form groups them and `story_describe` shows the group to the agent. The
form already renders groups (`manual_entities.py:316-317,387`).

The working name was `child`; it collides with the existing parent/child
hierarchy (`parent_id` on locations and scenes), so the field is `place` and the
location's list is `places`.

### Schema (location)

`places` — `{"type": "list", "default": [], "optional": True, "computed": True}`
— the distinct `place` values of this location's scenes, derived at read time.
Computed fields are skipped by every write path (`core/entity.py:442`), so it
needs no maintenance and cannot go stale: a scene written with a new place
appears here on the next read. Derived in `story_retrieve._entity_fields` (the
agent's view, `tools/story_retrieve.py:128-167`) and in the dashboard's location
payload. The editor's place picker suggests from it; free text is still allowed,
so a new place is never blocked.

A nested `heading:` object was considered and rejected — see *Rejected
alternatives*.

### Content is body-only

`## Content` holds the script body. The heading line is **composed at
assembly** from the fields, never stored. One source of truth; no derived line
to keep in sync.

### The line format

```
INT. LOCATION - TIME              (no place)
INT. LOCATION - PLACE - TIME      (with place)
```

- **Time is always emitted.** When `time_of_day` is unset the composer writes
  `UNSPECIFIED`, so the last segment is always the time and the parser can
  split on ` - ` unambiguously: last = time, first = location, middle = place.
  Cost: the assembled/exported script shows `INT. MANOR - UNSPECIFIED`.
- **No ` - ` in location names or place values.** The location's `name` is the
  heading segment (`compose_heading` takes the name, not the slug), so the rule
  is enforced on the **location entity** (`validate_entity`, `location` type,
  `name`) and on the scene's `place`. This is the cost of using ` - ` for both
  place and time; the alternative is a distinct place separator (` / `), which
  would lift the restriction.
- `forced_heading` is emitted verbatim and validated against
  `SCENE_HEADING_RE` (`core/fountain_lexer.py:14,40`). It is **exclusive** with
  the composed heading: when it is set, `int_ext`, `place` and `time_of_day`
  must be empty. `location` is not part of the exclusivity — it is an entity
  link (location panel, delete cascade, cast), not just heading text, so a
  forced heading can still be linked to a location. A composed heading requires
  it.

### Write boundary

`writes.create_entity` (`core/writes.py:186-199`) and `writes.edit_entity`
(`core/writes.py:442-468`), before `BEGIN`, on the merged state:

```
scene + merged Content non-empty:
    heading = structured(int_ext, location, place, time_of_day)
           or forced_heading text
    if none: raise ValueError("a scene with a script needs a heading — "
                              "set int_ext + location, or a forced heading")
scene:
    if forced_heading and (int_ext or place or time_of_day):
        raise ValueError("forced_heading is exclusive with the composed heading")
```

Every authored path funnels through these two functions: the agent's draft
commit, the script editor save (`core/manual_edits.py:352`), the entity form.
One guard covers all. Empty Content needs no heading (planned scenes). A forced
heading may still carry a `location` link.

### Assembly

`get_screenplay_text` and `get_dashboard_data` compose each scene's line from
its fields, then concatenate in order. The location segment is the location
entity's `name` (`compose_heading` takes the name, not the slug), so the
assembly resolves `scene.location` → `location.name` — one join, or a name map
built alongside the scene rows. This is the fix for the 0-scene bug.

### Stats

Unchanged pipeline: `services.py:59-64` → `_compute_screenplay_stats`
(`app/stats.py:49`) parses the assembled text. The parser
(`stats._parse_scene_location`, `app/stats.py:269-282`) gains one rule: split
the location segment on ` - `, last = time, middle = place. Because the line is
composed, never free text, the parse is unambiguous. The same parser is what the
future "import a script" feature will use to turn a full screenplay into scenes.

### Import / export

- **Import** reads the fields from frontmatter. If a note's `## Content` opens
  with a heading line (hand-written note), parse it into the fields and strip
  it — the import canonicalising its input, not a migration.
- **Export** writes the fields to frontmatter; `## Content` stays body-only.

### Editor

`manual_edits` loads the fields + blocks; `save_scene_script` writes the fields
+ Content in one `edit_entity` call. `scene_script.parse_heading` and
`compose_content` shrink to the composer; `split_heading` remains for the paste
path and imported notes. The editor UI (`web/js/script-editor/editor.js`,
`model.js`) reads `int_ext`/`place`/`forced_heading` instead of the parsed
`mode` object.

## Affected surfaces

| File | Change |
|---|---|
| `core/constants.py:184` | schema: add `int_ext`, `place`, `forced_heading`; retire `heading`; add `group` keys; `places` on location |
| `core/entity.py` | enum/ref validation; no-dash rule on the scene's `place`; no-dash rule on the location's `name` |
| `core/writes.py:186-199,442-468` | the write-boundary guard (create + edit), incl. exclusivity |
| `core/db.py:1434-1444,1567-1579` | compose the line at assembly (both paths); resolve the location name |
| `core/db.py` location payload | computed `places` for the dashboard |
| `tools/story_retrieve.py:128-167` | computed `places` for the agent's location read |
| `app/stats.py:269-282` | place split in `_parse_scene_location` |
| `web/js/script-view.js:89-93` | derive `sceneIds` from the parse, not the scene list |
| `core/scene_script.py` | `compose_heading` gains `place`; `parse_heading` shrinks |
| `core/manual_edits.py` | load/check/save carry the fields |
| `core/scene_content_lint.py` | import-only; authored writes are guaranteed by the boundary |
| `core/manual_entities.py:156,200-202` | `SCRIPT_FIELDS`; `GROUPS` reads the schema |
| `core/manual_structure.py:62` | `node.heading` derived from the fields |
| `core/drafts.py:178-184,599` | preview finding + display name |
| `tools/story_import.py`, `tools/story_export.py` | FM fields |
| `web/js/script-editor/editor.js`, `model.js` | heading state; place picker suggests from the parent's `places` |
| `web/js/views/scenes.js:16,62` | heading display + search |
| `web/js/panels/entity-panels.js:169-186,509-511` | scene refs + heading display |
| `web/js/core.js:111-120,143-146` | character/location scene matching |
| `web/js/views/locations.js:12`, `web/js/utils.js:12` | location scene refs |
| `web/js/views/reorder.js:79` | reorder list subtitle |
| `web/js/forms/entity-form.js:346,353` | script-tab note text |
| `web/js/data-load.js:34,46,74-76` | sample payload carries the heading |
| tests | `test_scene_script`, `test_manual_edits`, `test_scene_heading_lint_integration`, `test_core`, round-trip, dashboard harness |
| skill docs | `tasks/task_30/skill/references/mechanics/screenplay-format.md:81-90`, `craft/scene-design.md:199-205` |

Verified NOT heading-dependent (no change): `core/db.py` `_build_scene` (the
base `story_load` view omits heading), `core/manual_entities.py:1325` (delete
preview reads Content length only), `tools/story_retrieve.py` (returns extra
fields dynamically).

## Migration

No migration in the app. The fixture and the live project are adapted once:

- **Fixture markdown** (`tests/fixtures/save-the-children/scenes/*.md`, three
  files): replace `heading: INT. …` with `int_ext: INT.` and add `place: ""`.
  `location`/`time_of_day` already exist. The DB is rebuilt from markdown by
  `tests/conftest.py:32-52`, so no DB edit.
- **Live project** (`browser-verification-test`): a standalone one-off script
  parses each scene's FM `heading` (or Content line) into `int_ext`/`place`.
  Run once, not part of the app.

## Rejected alternatives

- **Nested `heading:` object / `Script: {heading, content}`.** The codebase
  already has a presentation grouping mechanism (`GROUPS`), and nesting would
  move `location`/`time_of_day` and touch the column/relation/delete-cascade
  machinery for a presentation gain. Flat fields + `group` is the same grouping
  at a fraction of the cost.
- **Storing the composed line in Content.** Derived data; composing at assembly
  keeps one source. (Accepted tradeoff: the vault note's `## Content` is
  body-only, so the note is not a complete screenplay. The fixture already works
  that way.)
- **Keeping `heading` as free text.** The ambiguity and drift source.
- **Dropping forced headings.** Fountain's escape for a scene with no INT/EXT;
  the skill teaches it (`screenplay-format.md:42-43`).
- **Distinct place separator (` / `).** Would lift the no-dash restriction; not
  chosen, but the cheap alternative if location names with dashes matter.

## Open questions

1. ~~Does the no-dash restriction on location names break any existing
   location?~~ Resolved: no — the fixture and the live project have no ` - ` in
   any location name. Enforce it.
2. ~~Should `UNSPECIFIED` be the emitted default time, or should the parser
   treat a non-enum last segment as a place and allow a missing time?~~
   Resolved: emit `UNSPECIFIED`. The last segment is always the time, so the
   split is unambiguous.
3. ~~Does `story_describe` need the group key surfaced explicitly, or is the
   field order enough?~~ Resolved: surface it. `_entity_schemas`
   (`tools/story_describe.py:129-139`) copies every schema key verbatim, so a
   `group` key reaches the agent with no extra code; field order alone is an
   implementation detail the agent cannot rely on. The grouped fields also get
   descriptions that name the heading, since the schema description is the
   channel the model learns from.
