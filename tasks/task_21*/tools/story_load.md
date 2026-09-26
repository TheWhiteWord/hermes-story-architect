# story_load — EXTEND (P0)

`tools/story_load.py` (62 lines) + `core/db.py:207 get_project_summary` · `spec.md` §2–§3

## What it does today
`(project)` → DB check → `get_project_summary()` → nested project/acts/characters/plots/worlds + `memory`.

The **base view is implemented and good**. It matches spec §2 closely, including the confirmation string and the DB-only rule.

## Findings

1. **All 5 extended views are missing** (spec §3.1–§3.5): `arc`, `story_value`, `dramatic_elements`, `relationship`, `unfilled`. The `view` parameter does not exist in the schema. This is the bulk of the remaining spec work.
2. **Two of the five backends already exist** — `get_character_arcs` (`core/db.py:646`) and `get_unfilled_map` (`core/db.py:566`). §3.1 and §3.5 are wiring, not new code. §3.2 and §3.3 need new focused DB projections.
3. **Return key drift from spec:** code returns `memory`; spec §2 says `memory_outline`. The spec's own `{"status": "placeholder — design deferred"}` shape suggests `memory_outline` is the intended name and memory shape is still open. **Decide this before implementing views** — it is in the base payload.
4. **No `characters[].rel`** — spec §2 shows per-character relationship summaries in the base view; `get_project_summary` does not emit `rel` (confirmed: no `rel` key is built).
5. **Locations are nested under worlds, plus `orphaned_locations`** as a top-level array. Sensible; spec doesn't mention the orphan case. Keep, document.
6. **Vestigial connection handling** (lines 42–59): opens a connection only to call `has_schema`, then `get_project_summary` opens its own. Same triple-open pattern as retrieve/search.
7. **Payload size unbounded.** Spec budgets ~8K. `get_project_summary` returns every character `one_sentence` and every location nested — a 40-character project will blow it. No truncation, no count in `confirmation` to warn the agent.

## Work
1. Resolve the `memory` vs `memory_outline` question (open question below) — blocks views.
2. Add `view` to the schema; dispatch to focused readers.
3. `arc` + `unfilled`: wire existing backends. `story_value` + `dramatic_elements`: new projections off `entities`/`relations`.
4. Single connection via `core.db.get_db`.
5. Decide on a size guard: return a count and instruct the agent to narrow, or add a `view="outline"` that emits ids+titles only.

## Open questions for you
- **`memory` or `memory_outline`?** Spec says `memory_outline`; code says `memory`. Spec §7 defers the *shape* but not the name, and defers memory retrieval entirely.
- **Is a size guard in scope?** A 40-character project may genuinely not fit in 8K. Options: truncate + say so, or refuse and tell the agent to filter by act. I'd do: emit the tree with `one_sentence` dropped past a threshold, and always include the counts.
