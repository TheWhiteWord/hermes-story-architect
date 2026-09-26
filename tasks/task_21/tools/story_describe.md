# story_describe — REDESIGN (P0)

`tools/story_describe.py` (261 lines) · registered in `__init__.py:35`

## What it does
Returns JSON Schemas for 7 tools and/or field metadata for all entity types from `ENTITY_SCHEMAS`.

## Findings

1. **It hand-copies 7 tool schemas** (`_build_tool_schema`, lines 26–185). The real schemas live in each tool module as `SCHEMA`. Every tool change must be made twice.
2. **Already drifted, three ways:**
   - `story_import`, `story_export`, `story_backup` are **absent** from both the enum (line 197) and the schema map.
   - `story_load` is described as "Load a story project's index and memory into context" with only `project` — no `view`, so the spec's 5 views are undiscoverable.
   - `story_retrieve` is described with `slug` + required `sections` — no `fields`, no `id` list. Matches today's code, contradicts `spec.md` §4.
3. **Tool schemas are lossy vs the real ones.** `story_edit`'s `target`/`data`/`order_context` are bare `{"type": "object"}` — no properties, no required. The real schema documents them.
4. **Duplicated logic with `story_create`.** `_all_fields()` here and `_build_schema()` in `story_create.py:7` are near-identical field-flattening passes over `ENTITY_SCHEMAS`.
5. **No `view` list, no relation-field documentation.** The agent cannot learn that `plot.setups` is stored as `relations` rows, not `extra` — the single most surprising thing about the data model.

## Options

**A. Make it a mirror (recommended, lazy).** Delete `_build_tool_schema`; import each tool module and return its `SCHEMA`, plus an added `description` field. Drift becomes structurally impossible. ~40 lines deleted, ~15 added.

**B. Merge into the tool registration.** The plugin already knows every schema at `register_tool` time — `ctx.register_tool(schema=...)`. Expose them through one `story_describe` that reads a registry built in `__init__.py`. Slightly more plumbing, same payoff.

**C. Keep as-is.** Not viable: it is already wrong.

**Do not** build a code generator for the schema. The mirror is the whole fix.

## Open questions for you
- Should `story_describe` cover the 3 file-boundary tools (import/export/backup)? They're rarely what an agent needs, but hiding them makes them undiscoverable.
- Do you want relation-backed fields (`setups`, `crisis`, `climax`, `payoffs`, `variant_of`, scene `characters`) called out explicitly per entity type? Costs ~15 lines, removes the biggest source of agent confusion.
