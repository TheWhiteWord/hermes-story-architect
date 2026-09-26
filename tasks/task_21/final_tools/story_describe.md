# story_describe

✅ **Finalized.** Source: `tools/story_describe.py` (75 lines, was 261).
Tests: `tests/test_story_describe.py`. Full suite 323 passed.

The preparation tool. Before the LLM creates an entity or starts asking the user questions about
one, it calls this to learn which fields that entity type expects — so it asks about things that
matter, and doesn't waste the user's time on fields that are optional or already filled.

## Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `entity_type` | enum | no | `character`, `location`, `world`, `plot`, `project`, `scene`, `sequence`, `act`, `arc_beat`, `relationship`. Omit for all 10. |

That is the entire interface. One parameter.

## Example — the actual use case

**Request** `{"entity_type": "character"}` → **2,078 chars, 13 fields**

```json
{"success": true,
 "entity_schemas": {"character": {
   "name": {
     "type": "string", "default": "", "optional": false,
     "description": "Character display name"
   },
   "story_role": {
     "type": "string", "default": "", "optional": false,
     "description": "One of: Protagonist, Antagonist, Supporting, Minor, Cameo"
   },
   ...
 }}}
```

**What the LLM does with it:** `optional: false` marks the two fields it genuinely needs
(`name`, `story_role`) before creating a character. `optional: true` with a real `default`
(`"Summary not set"`) is where worthwhile questions live — worth asking, not worth blocking on.

## Two flags that change how a field is written

- **`stored_as: "relation"`** — not a column on the entity. It lives in the `relations` table as a
  link to another entity, optionally with a note. `plot.setups` / `crisis` / `climax` / `payoffs`,
  scene `characters`, and `variant_of` all behave this way. The most surprising thing about the
  model, and invisible unless reported.
- **`computed: true`** and *"(read-only, computed — do not set)"* — derived at read time, never
  stored. Sending one to `story_create` or `story_edit` is silently ignored.

## Related fix found while checking entity types

Auditing whether every entity type appears everywhere it should turned up a related drift bug:
**`story_edit`'s `entity_type` enum was missing `project`** — 9 of 10 types. The handler fully
supports editing the project entity (it special-cases `entity_type == "project"`), so this was
purely a stale hand-written list hiding a working feature from the model.

Verified before fixing: editing the project's `genre` and `logline` through `story_edit` works
and shows up in `story_load`.

All four entity-type enums now derive from `ENTITY_SCHEMAS` instead of being hand-written, and a
parametrized test fails if any drifts. Same class of bug as the schema-copy problem: a duplicated
list, silently going stale.

## Errors

| Condition | Response |
|---|---|
| Unknown entity type | `{"success": false, "error": "Unknown entity_type: x. Available: ..."}` |

A bad name used to return `success: true` with an empty result — indistinguishable from "this type
has no fields".

## What this tool deliberately does NOT do

**It does not describe the other tools.** Tool schemas are in the model's context at all times —
that is how tool calling works — so repeating them here spends tokens telling the model something
it already knows.

An earlier version hand-copied 7 tool schemas into itself, had already drifted from the real ones,
and omitted `story_import`, `story_export` and `story_backup` entirely. That guidance now lives
where the model actually reads it: in each tool's own `description`.

Tool-selection guidance beyond that belongs in the **skill**, not in a tool — a skill loads when
relevant instead of costing tokens on every session.

## Response sizes

| Request | Original | Now |
|---|---|---|
| `{"entity_type": "character"}` | 15,055 | **2,078** |
| `{}` (all 10 types) | 28,707 | **17,870** |

Both shrank, and neither is a copy of something the model already holds.

## Tool descriptions added along the way

Every tool now carries a `description` saying what it is for *and when not to use it* — 7 of 11
previously had none anywhere, leaving the model to guess. The one that matters most:

> **story_import** — "DESTRUCTIVE. Rebuilds the database from the Markdown vault: deletes every row
> and re-imports, discarding all work done since the last `story_export`. The database is the source
> of truth, not Markdown. Only for an intentional re-sync from Markdown files. Never use this to
> repair a problem — take a `story_backup` first, and prefer `story_edit` or `story_create` to
> change things."

A test asserts no description advertises a parameter its schema doesn't accept, so this text can't
quietly start lying.

Also fixed: `plugin.yaml` omitted `story_memory` from `provides_tools` even though `__init__.py`
registers it.

## Note for future work

`story_create`'s own `SCHEMA` is generated at import time from `ENTITY_SCHEMAS`
(`_build_schema()` in `tools/story_create.py`). It is ~13,000 chars and is sent to the model on
**every session**, whether or not the tool is used. `story_describe` now returns per-entity field
schemas on demand, so the inline list is largely redundant — slimming it is the biggest available
token saving in the toolset. Left alone here because it changes a different tool.
