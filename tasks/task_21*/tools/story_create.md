# story_create — VERIFY (P2)

`tools/story_create.py` (283 lines) · `core/entity.py:225 columns_for_insert`

## What it does
Creates a project (special path, initialises structure) or any other entity. Merges input over schema defaults, maps to columns/extra/relations, validates parents, auto-orders children, inserts sections + relations.

Substantially more validation than any other write tool — this is good work. Verification needed, not redesign.

## Findings

1. **Duplicated field map.** `_ENTITY_COLUMN_MAP` is defined in *both* `story_create.py:... ` (via `columns_for_insert`) and `story_edit.py:45`. Two maps, independently maintained. `story_edit`'s version is hand-written; `core/entity.py`'s is the one `story_create` uses. They already differ (`story_edit` maps `location.world → parent_id`, `scene.location → location_id`; verify the core map agrees).
2. **`except Exception: conn.execute("ROLLBACK")`** (line 194–196). `get_db` sets `isolation_level=None` (autocommit), so there is no transaction to roll back — the rollback itself can raise and mask the original error. The comment on line 168 knows autocommit is in use; the handler forgot.
3. **No dry-run and no existence-based update path.** Creating an entity that already exists is a hard error. Combined with `story_edit`, the agent must know which to call. A `story_create` that upserts would collapse that decision — but that's a design change, see below.
4. **Project path is built directly**: `vault_path / "projects" / slug` (line 227), bypassing `resolve_project`. So a project can only be created at the canonical path, never elsewhere. Probably intended; it's undocumented.
5. **Slug validation is alphanumeric + `-_`** (line 96) — but arc_beat entity ids are composite `{char}-{beat}`, and `project` creation skips the check entirely.
6. **The generated `SCHEMA` is enormous.** `_build_schema()` flattens every field of every entity type into one `frontmatter` property bag, each description carrying `(used by: ...)`. This is most of the tool's token cost in every conversation, and it's largely redundant with `story_describe` — which already returns per-entity field schemas. **Candidate for the biggest single token saving in the toolset**: slim `story_create`'s schema to `{entity_type, slug, project, frontmatter: {}}` and point the agent at `story_describe`.
7. **`_create_project` doesn't create a default act/sequence structure**, despite the schema having `structure_type` and `act_count`. New projects start empty. Verify that's intended.

## Work
1. Verify against a real project: create each entity type, confirm the row lands in the right column/extra/relation. (Read-only review can't do this.)
2. Fix the useless `ROLLBACK` in the error path.
3. Delete `_ENTITY_COLUMN_MAP` from `story_edit.py` and use `core.entity`'s.
4. **Decide the schema question (#6).** Slim `story_create` + rely on `story_describe`, or keep the inline field list. This is the one change here that could visibly reduce prompt bloat.

## Open questions for you
- **Should `story_create` upsert?** One write tool (`story_create` = "make sure this exists with these fields") would remove a whole class of agent error. Cost: loses the "creation failed, it already exists" signal, which is sometimes useful. I lean toward keeping them separate — the error is informative and the human can see it.
- **Trim `story_create`'s schema?** See #6. This is a real token cost on every session, not a one-off.
