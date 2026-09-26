# story_retrieve — REWRITE to spec (P0)

`tools/story_retrieve.py` (156 lines) · `spec.md` §4–§6

## What it does today
`(project, entity_type, slug, sections)` → resolves entity id → returns section prose from the `sections` table, plus `unfilled_fields`.

## Spec vs implementation

| Spec §4 | Status |
|---|---|
| `id` (list of slugs) | **Missing** — `slug` is a single string |
| `fields` (incl. `["all"]`) | **Missing entirely** |
| `entities[]` array return shape | **Missing** — returns a single flat object |
| Relation-backed fields (plot beats, relationship perspectives) | **Missing** |
| `sections=["all"]` | Present |
| `unfilled_fields` | Present, but only on the success path |
| DB-only, no Markdown | **Holds** |

So roughly half the spec is unimplemented. The parts that exist are correct and DB-only — the invariant is intact.

## Other findings

1. **Exceptions swallowed** (lines 65–72): `except Exception: pass`, then falls through to `"Database not found. Run story_import first."` A malformed `extra` JSON reports as a missing database.
2. **Three connections to read one entity.** Own `sqlite3.connect` (56) + `has_schema` + `get_entity_sections`'s own `get_db`. `core.db.get_db` already exists and handles this.
3. **Inconsistent with the spec's own return key.** Spec says `entities[].id`; code returns `slug` at top level. Anything already written against the current shape will break — decide now, not during the rewrite.
4. **Dead import** at line 124: `from core.section_parser import list_sections` is unused.
5. **Missing-entity is silent.** If `_entity_id_for` returns `None`, the code falls through the `if` and eventually reports "Database not found" — a wrong error for a typo'd slug. This is the most likely real-world failure.
6. **`_unfilled_for_entity` duplicates `get_unfilled_map`'s plot-merge logic** (`core/db.py:566`). Two places to keep in sync.

## Work
1. Add `id` (list) + `fields` (incl. `["all"]`); switch return to `entities[]`. Keep `slug` accepted as a deprecated alias only if something already depends on it — otherwise drop it cleanly.
2. Resolve relation-backed fields from `relations` (plot beats with `note` as description; relationship perspectives from `extra`).
3. Replace the try/except-swallow with: distinct errors for *no DB*, *no such entity*, *malformed row*. Let real errors surface.
4. Use `core.db.get_db`; delete the unused import.

## Open question
`unfilled_fields` on every retrieve call is free-ish and genuinely useful for "what should we work on" — but it costs tokens on every call. Keep always, or only with `fields=["all"]`? Spec says "included when `fields` is requested" — I'd follow the spec.
