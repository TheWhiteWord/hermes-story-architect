# Tool Review — index

**Status:** read-only review, no code changed. Source of truth: `tools/*.py` + `__init__.py` + `core/db.py`.
**Judged against:** the app intent — *an LLM assisting a human writer*, not an autonomous generator. Runtime is DB-authoritative (`.story/story.db`); Markdown only at the import/export boundary.

## The 11 registered tools

`story_describe`, `story_load`, `story_retrieve`, `story_search`, `story_edit`, `story_memory`, `story_create`, `story_import`, `story_export`, `story_backup`, `story_dashboard`

`tools/story_resolve.py` is **not a tool** — it's an internal helper (`resolve_project`). It is a major part of why the toolset feels bigger than it is.

## Verdict table

| Tool | Verdict | Priority | One-line issue |
|---|---|---|---|
| `story_describe` | **REDESIGN** | P0 | Hand-copies every tool's schema; already drifted (omits 3 tools, missing `view`/`fields`) |
| `story_retrieve` | **REWRITE to spec** | P0 | `fields`, `id`-list, relation-backed fields all unimplemented; sections-only |
| `story_load` | **EXTEND** | P0 | Base view works; all 5 spec views (`arc`, `story_value`, `dramatic_elements`, `relationship`, `unfilled`) missing |
| `story_import` | **HARDEN** | P1 | `_clear_all` wipes the DB before import — destroys DB-only work, no dry-run, no confirm |
| `story_edit` | **FIX + RENAME** | P1 | `edit_note` is a lie (edits DB); no dry-run; delete is irreversible with no guard |
| `story_search` | **FIX (cheap)** | P1 | Exception masked as "Database not found"; 3 connections for 1 query; unbounded body in `snippet` |
| `story_create` | **VERIFY** | P2 | Duplicates `ENTITY_COLUMN_MAP` from `core/entity.py` — drift waiting to happen |
| `story_export` | **VERIFY** | P2 | Never deletes stale `.md`; relation/extra asymmetry makes round-trip fragile |
| `story_dashboard` | **KEEP** | P2 | Works, heaviest tool, shares `get_dashboard_data` with nothing else |
| `story_memory` | **KEEP AS IS** | — | The only tool with real error recovery. Use it as the pattern |
| `story_backup` | **KEEP** | — | 45 lines, correct, trivially verifiable |

## Cross-cutting problems (fix once, not per tool)

1. **Schema duplication.** `story_describe` re-declares the schemas of 7 tools by hand. Every tool change must be made twice; three have already drifted. `story_describe` should read `SCHEMA` from the modules.
2. **Vault-path resolution copy-pasted** in 6 handlers (3 slightly different variants: `kwargs["vault_path"]` vs `_vault`, `.expanduser()` in some paths only). One `get_vault_path(**kwargs)` helper.
3. **Error-message convention by copy-paste.** `"Database not found. Run story_import first."` appears verbatim in 4 tools — including in `story_search`, where it masks unrelated FTS errors.
4. **DB-authority drift.** `story_import`/`story_export` are the only Markdown boundary (correct), but `story_search`/`story_retrieve` still carry vestigial "Phase 2" comments and dead fall-through paths from the file-based era.
5. **Relation-vs-extra asymmetry.** Scene `characters` live in `relations`; relationship `characters`/`perspectives` live in `extra` (`constants.py:187`, marked "frontmatter-only"). Both import and edit have to special-case this. Worth deciding, not patching twice.

## Suggested order of work

1. `story_describe` → make it read real schemas (kills the drift class, cheap).
2. `story_retrieve` + `story_load` views → finish `spec.md` (the work already started).
3. `story_import` guard → dry-run/confirm, because it's the one tool that can lose data.
4. Cheap fixes: `story_search` exception, vault-path helper.
5. Verify-only: `story_create`, `story_export`, `story_dashboard`.

## Deliberately not doing

No tool merge. The 11 split cleanly into: *read* (load/retrieve/search), *write* (create/edit/memory), *file boundary* (import/export/backup), *presentation* (dashboard), *discovery* (describe). Merging would couple unrelated lifecycles. `story_backup` is 45 correct lines — merging it into `story_export` would save nothing and lose the ability to back up without exporting.
