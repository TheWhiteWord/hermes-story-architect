# story_retrieve

✅ **Finalized.** Source: `tools/story_retrieve.py`. Tests: `tests/test_retrieve_reading.py` (18).
Full suite 379 passed. 18 existing tests updated for the new response shape.

The counterpart to `story_load`: load says *what exists and where*, retrieve says *what does this
say*. It is **the** content-reading tool.

## Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `project` | string | yes | Slug or name |
| `entity_type` | enum(10) | yes | Derives from `ENTITY_SCHEMAS` |
| `id` | **array** of string | yes | Ids exactly as `story_load` returned them. A bare string is tolerated. |
| `sections` | array | no | `["all"]` or names. Omit for none. |
| `fields` | array | no | `["all"]` or names. Omit for none. |

At least one of `sections` / `fields` is required — otherwise the call returns an empty entity and
the agent concludes the entity is empty.

## Response shape

```json
{"entity_type": "character", "entities": [{"id": "kael", "fields": {...},
  "unfilled_fields": [...], "sections": {"Personality": "..."}}]}
```

Plus, when relevant: `not_found` (with per-id errors), `sections_not_found` + `available_sections`,
and a `hint` pointing at `story_load`.

## What was fixed

### 1. A typo no longer points the agent at the destructive tool

Both a misspelled id and a **valid id with the wrong entity_type** returned:

> `Database not found. Run story_import first.`

That sent the agent to the one tool that can destroy the project — to fix a typo. Now:

```json
{"entities": [], "not_found": [{"id": "kael-vale",
   "error": "No character with id 'kael-vale'. Ids are exactly as returned by story_load."}],
 "hint": "Call story_load to list valid ids for this project."}
```

Good ids in the same batch still come back normally. A genuinely missing database still says so.

### 2. Relation-backed fields are now readable — the big one

`setups`, `crisis`, `climax`, `payoffs` and scene `characters` are **rows in `relations`**, not
columns. They were unreachable through any tool. An agent could not discover that a plot had no
crisis scene. Now:

```json
{"fields": {"setups": [{"scene_id": "central-room-day",
                        "description": "Kael discovers the door isn't locked — it was never locked."}],
            "crisis": [], "climax": [],
            "payoffs": [{"scene_id": "the-core-day", "description": "..."}]}}
```

An unset beat reads as `[]` and appears in `unfilled_fields` — which is the whole point.

`character_scene` is the one relation stored from the **character** side, so a scene's characters
are the rows pointing *at* it. Handled via `REVERSED_KINDS` rather than by special-casing the query
at each call site.

### 3. Several ids per call

`id` is an array. One call reads five characters instead of five.

### Also

- **`unfilled_fields` only when fields were requested** — no point reporting it for a prose read.
- **A missing section is reported** (`sections_not_found` + `available_sections`) rather than
  silently absent, so a wrong heading name is visible instead of reading as empty prose.
- **Computed fields are excluded from `fields: ["all"]`.**
- **Arc beats resolve from the beat part alone.** Beats are keyed `{character}-{beat}`; asking for
  `"1"` finds `dr-elena-voss-1`, and the response reports the *resolved* id.
- `entity_type: "project"` takes the project name from `story_load`; the slug is ignored.

## A note on the module-level cache I removed

My first version cached `PRAGMA table_info` in a module global. It passed alone and failed only
when the whole suite ran in one process — the dashboard and the tests use different databases, and a
cached column list silently misaligns row values into the wrong fields. Removed. Worth remembering:
**no cross-request state in a tool module.**

## Errors

| Condition | Response |
|---|---|
| Unknown id or wrong type | `not_found` per id, others still returned |
| No database | `Database not found. Run story_import first.` |
| Neither `sections` nor `fields` | `"Nothing requested. Pass sections and/or fields."` |
