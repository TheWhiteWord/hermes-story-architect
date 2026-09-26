# story_edit

✅ **Finalized.** Source: `tools/story_edit.py`.
Tests: `test_edit_safety.py`, `test_edit_silent_success.py`, `test_delete_cascade.py`,
`test_soft_delete.py`, `test_purge.py`. Full suite **595 passed**.

The tool that changes and deletes. `story_create` writes, this one changes.

**Deleting is reversible.** `delete_entity` flags the entity rather than erasing
it, and `action="restore"` brings it back exactly. `action="purge"` is the only
irreversible operation, and it is guarded so that only the user can trigger it.

## The delete lifecycle

```
delete_entity  →  is_deleted=1, deleted_at=now      (soft; restore is exact)
                   ↓ next story_export
                 .md note swept from disk
                   ↓ purge, age floor passed, DELETE <slug> supplied
                 row removed for good
```

## Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `action` | `edit_note` \| `delete_entity` \| `restore` \| `purge` \| `reorder` | yes | |
| `target` | `{entity_type, slug, project}` | yes | `slug` ignored for `project` |
| `data` | object | for `edit_note` | **Flat**: field names and section names directly |
| `order_context` | `{ordered_ids}` | for `reorder` | Complete new ordering |
| `summary` | string | yes | |
| `dry_run` | boolean | no | Report and change nothing |
| `confirm` | boolean | for delete | Required to delete |
| `purge_confirm` | string | for `purge` | Must contain `DELETE <project slug>` — the user's call |
| `older_than_days` | integer | for `purge` | Default 30. Newer deletes stay restorable |

## What was fixed

### 1. A silently lost edit — the worst bug in the plugin

The file kept **its own copy** of the field→column map. The copy was missing `project`, so:

```
edit logline → {"success": true}
one_sentence column → unchanged
extra → {"logline": "A NEW logline."}   ← landed here instead
```

Reported success, wrote nothing the rest of the system reads. Now uses `ENTITY_COLUMN_MAP` from
`core.entity` — the one map. `project` and `relationship.type` came along with it.

The map was missing exactly the fields nobody exercised in tests, which is why a behaviour test
alone wouldn't have caught the reintroduction:
`test_no_local_map_remains` asserts the local copy does not come back.

### 2. Delete was unguarded

The delete ran on a single call with no chance to see what would go. Now refused
without `confirm`, and the refusal tells you exactly what would go:

```json
{"error": "Delete refused: pass confirm=true to proceed.",
  "would_delete": ["kael", "kael-1", "kael-2", "kael-3"],
  "cascade_children": [{"id": "kael-1", "type": "arc_beat"}, ...],
  "sections_deleted": 13,
  "reversible": true,
  "action_required": "Run with dry_run=true ... then re-run with confirm=true ...
                      This is reversible: action=\"restore\" undoes it."}
```

See **Delete is a SOFT delete** below for why the operation is no longer
irreversible at all.

### 3. `dry_run` for the actions that can change something

| Action | Preview reports |
|---|---|
| `edit_note` | Per field: `from` → `to`, and **where it is stored** (`column`/`section`/`extra`) |
| `delete_entity` | `would_delete`, `cascade_children`, section and relation counts |
| `restore` | `restored_cascade_children`, `was_deleted_at` |
| `purge` | `purged` (empty if the age floor holds everything back) |
| `reorder` | Which items move, and from which order to which |

Only actual differences are listed — setting a field to the value it already holds reports nothing.

### 4. The structural guard is not a speed bump

**A bug I introduced and then caught.** My first consent gate wrapped the structural-children check
inside it, so `confirm: true` *skipped* it and deleted a sequence with three scenes in it. The
check now sits outside the consent gate: a structural child means refusal, confirm or not.

```
delete seq-discovery, confirm=true
→ "Cannot delete: 3 structural child(ren) reference this: central-room-day, ..."
   blocking_children: [{id, type}, ...]
```

Worth stating plainly: this is why the three pre-existing "blocked delete" tests were the ones that
failed when I patched them. They encoded the correct behaviour and caught my regression.

### Delete is a SOFT delete, and `restore` undoes it exactly

`delete_entity` no longer erases. It flags the row
(`is_deleted=1, deleted_at=?`) and leaves sections and owned relations intact —
the design `tasks/task_18/spec.md` chose, with columns that had been sitting in
the schema unused. So:

```json
"reversible": true,
"how_to_undo": "story_edit action=\"restore\" with the same target. Deleted at …"
```

`action="restore"` clears the flag and brings cascade children (a character's
arc beats) back with it. Nothing is reconstructed, so the round trip is
**byte-identical** — verified on fields, prose and `deleted_at`.

A soft delete is only safe if nothing can see through it, which is why the
filter is applied in three places, not one:

| surface | filter |
|---|---|
| entity reads (`core/db`, `story_load`, `story_retrieve`) | `AND is_deleted=0` |
| relation reads | both endpoints must be live |
| FTS search | join filtered, **including the count** — a total that counted invisible prose would mislead |

Relations *owned by* a deleted entity survive (restore needs them); relations
*pointing at* one are removed (a live character must not point at a dead scene).

`ensure_soft_delete_columns()` migrates older databases — `CREATE TABLE IF NOT
EXISTS` leaves an existing table alone, so without it every reader filtering on
`is_deleted` would fail with "no such column" on a project created earlier.


## Delete semantics

| Situation | Result |
|---|---|
| `act`/`sequence` with scenes | **Blocked**, even with `confirm` |
| `character` with arc beats | Arc beats cascade-flagged alongside it |
| Any entity | Its relations are detached; the entity and its children are **flagged** |

Nothing is erased. A delete sets `is_deleted=1, deleted_at=?` on the entity, its
cascade children (arc beats, scenes), and drops relations that *point at* it.
Relations *owned by* a deleted entity are kept, so `restore` can bring them back.

Response: `entity_id`, `reversible: true`, `how_to_undo`, `cascade_deleted`
(the children flagged alongside it), `references_purged`, `detached`.

`fields_emptied` is **not** currently emitted — required fields the cascade
clears keep their column and become empty, so `story_load`'s `unfilled` view
still reports them. Worth adding to the response, but not built.

`edit_note` additionally returns **`applied`**, naming every field, section and
relation that actually landed:

```json
"applied": {"fields": ["goals_short"], "sections": ["Background"], "relations": []}
```

plus `skipped_read_only` when a computed field was passed, and a `warning` when
nothing at all was written. `success: true` can no longer mean "silently did
nothing".

### `data` is flat — and an unrecognised key is now a hard error

`data` takes field names and section names **directly**:

```json
{"goals_short": "ESCAPE OR DIE", "Background": "She was born in the I."}
```

It does **not** nest under `frontmatter` / `sections`. That mistake used to be
dumped verbatim into `entities.extra`: the write reported `success: true`,
nothing changed, and the edit was lost with no signal. Now:

```json
{"error": "Unrecognised character edit key(s): frontmatter. `data` must be flat …",
 "unrecognised_keys": ["frontmatter"],
 "valid_field_examples": [...], "hint": "Use story_describe(...) for the full list."}
```

**Validated before the transaction opens**, so one bad key rejects the whole
call — a partial write would leave the agent believing the valid half landed.
`tests/test_edit_silent_success.py` also sweeps every valid key of all 10 entity
types, so a future schema addition cannot be locked out by the guard.

## The cascade was incomplete — references lived outside the relations table

The cascade handled relation *rows* and `parent_id`. But **a relationship is a
first-class entity, not a relation row**, and several reference sites live in the
`extra` JSON blob. Deleting Kael left two zombie relationships naming them,
perspectives intact:

```
kael-mira  {"characters": ["kael", "mira"], "perspectives": {"kael": {…}, "mira": {…}}}
```

`_purge_references` now walks every survivor once and clears each known site:

| Site | Kind | Action |
|---|---|---|
| `extra.characters` | list of ids | dead ids removed |
| `extra.scenes` | list of ids | key kept, dead ids removed |
| `extra.scene` | single id | key kept, value `""` |
| `extra.perspectives` | dict keyed by character | dead keys removed |
| `location_id` | column | set to `""` |
| `parent_id` | column | set to `""` |

**A reference that lost its target keeps its key.** `unfilled_fields` treats a
missing key and an empty value identically, so either would register — but the
difference is visible to a *reader*: `scene: ""` in the Markdown says "this beat
has no scene", whereas a vanished key just looks like a field that was never part
of the schema. Verified through the whole stack:

```
story_retrieve fields → {"scene": "", "action": "Elena makes the call…"}
exported Markdown     → scene:
unfilled_fields       → []   (see note)
```

Note that `arc_beat.scene` is `optional: False` in the schema, and `unfilled_fields`
deliberately skips required fields — an empty required field is a schema violation, not
a "needs filling" hint. So the blank is a *visible* gap, not an `unfilled_fields` entry.
Optional reference fields (`scene.location`, `relationship.perspectives`, `plot.characters`)
do show up there.

`extra.perspectives` is the one genuine removal: a dead viewpoint has no blank form,
and the surviving half is what the relationship entity is for.

### `action="purge"` — permanent removal, two guards

Soft delete means nothing is lost, which quietly removes the need for a safety
net — and quietly makes permanent deletion *necessary*, or the database grows
without bound. `purge` closes that loop, and is deliberately the hardest action
to trigger:

1. **`purge_confirm` must contain the literal `DELETE <project slug>`.** The
   agent cannot guess that string, so it can only purge if a human handed it
   over — a UI button or a typed instruction. `confirm: true` is *not* a
   substitute.
2. **An age floor**, `older_than_days` (default 30). Only rows deleted longer
   ago than that are eligible, so **anything deleted in this session stays
   restorable** and tidying up can never destroy a fresh mistake.

A `story_backup` is taken before the wipe, and the response lists every
destroyed id. To undo a recent delete, use `restore` — that is exact.

### Deleted notes are swept on the next export

A soft-deleted entity is not exported, so its `.md` goes stale — and
`story_import` reads Markdown, which would **resurrect the entity**. The export
sweep removes it:

```
second export: written=29
files_removed: ['arcs/kael/1.md', 'arcs/kael/2.md', 'arcs/kael/3.md',
                'characters/kael.md']
after re-import, kael present?: False
```

The sweep only touches files a *previous export wrote* (tracked in
`.story/exported.json`), so a hand-authored note is never removed.

### `detached` — reporting the gaps the schema would hide

A reset field takes its **schema default**, so a field with a visible placeholder
keeps it. In practice only one cascade site has such a default, and it is
column-backed, so this currently buys little — the mechanism is right, not yet
load-bearing.

`detached` is the part that matters. `unfilled_fields` skips **required** fields by
design, so an emptied `arc_beat.scene` (which is `optional: False`) would otherwise
be invisible:

```json
"detached": [
  {"entity_id": "dr-elena-voss-1", "entity_type": "arc_beat",
   "field": "scene", "was_pointing_at": "central-room-day"},
  {"entity_id": "kael-1", ...}, ...
]
```

The agent can turn that into something a user can act on: *"I deleted that scene;
4 of Elena's beats no longer point at one."* Naming `was_pointing_at` is what makes
the report useful rather than a count.
| `relations` rows | both directions | deleted |

A relationship **entity survives** when one of its two characters goes — the
remaining half is still true, so only the dead side is stripped. The test
`test_the_relationship_entity_itself_survives` pins that judgement call.

Verified clean across nine delete targets (character, scene, world, location,
plot, relationship) with a helper that looks for *any* surviving reference of
*any* kind: `tests/test_delete_cascade.py`.

`location_id` was the one the first pass still missed — it is a column, not
`extra` — found by running the check across all target types rather than only
the one that prompted the question.

## Arc beats resolve from the beat part

`slug: "1"` finds `kael-1`, matching `story_retrieve` and `story_create`.

## Note for the skills

`data` keys are routed by the same rules the preview reports, so the preview doubles as
documentation: a key matching a standard section goes to the section, a mapped field to its column,
everything else to `extra`. The fixture's `kael.md` uses `Personality`, which is **not** a standard
character section — it lives in `extra`. The preview makes that visible instead of surprising.
