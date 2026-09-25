# Deferred: audit pre-DB file reads and writes

**Status:** Deferred architectural cleanup. Do not mix this refactor into the story-memory implementation.

**Recorded:** 2026-09-25, during task_25 memory design.

## Problem

Some Story Architect logic predates the project DB and still treats Markdown files as operational sources of truth. The DB was introduced to make the database authoritative, but some tools and dashboard paths still read Markdown directly.

The desired architecture is:

```text
DB = operational source of truth
Markdown files = user-facing export/projection, visibility, and interoperability
```

Memory follows this rule from the start:

```text
project.extra.memory (DB)
        ↓
story_load / story_dashboard / story_memory
        ↓
.story/memory.md via story_export
```

## Confirmed existing issue

`tools/story_dashboard.py:338-343` reads `project.md` directly to obtain project frontmatter for title-page fields:

```python
# Read project.md directly for title page fields (output-only, not in DB title_page)
try:
    project_fm = fm.load(project_path / "project.md")
    project_frontmatter = dict(project_fm.metadata)
except Exception:
    project_frontmatter = {}
```

This is explicitly labelled as output-only in the current code, but it still means the dashboard has a Markdown dependency for project data. `get_dashboard_data(project_path)` is already the DB-based dashboard data source and is the correct place to resolve this later.

## Related pre-DB paths to audit

Do not assume this is the only occurrence. Search before changing anything.

- `tools/story_create.py` — memory/other file creation may happen even where the DB should be populated first;
- `tools/story_edit.py` — older file-oriented edit paths may bypass DB writes;
- `tools/story_dashboard.py` — direct `project.md`/Markdown reads;
- `core/db.py` — `get_memory_outline()` currently reads `.story/memory.md` directly and must be replaced by the DB-first memory design;
- `tools/story_export.py` — should be the deliberate Markdown projection boundary;
- dashboard/data loading — should consume DB-generated injected data, not fetch Markdown files;
- any remaining `frontmatter.load()` / `frontmatter.dump()` calls whose data is authoritative project state.

## Cleanup rules for the later task

1. Identify the DB field or relation that owns each value.
2. Make the DB the single operational read/write path.
3. Keep Markdown export only where external visibility is required.
4. Do not add compatibility fallback reads from Markdown to the new memory path.
5. Do not mix this audit with the v1 memory implementation; keep the memory change small and DB-first.
6. Add tests that prove the operational path works when the Markdown projection is absent or stale.

## Relationship to task_25

The memory implementation must not introduce a new file-first dependency. `.story/memory.md` is generated/exported from `project.extra.memory`; the dashboard popup also reads DB-derived injected data.

This note is a reminder to audit the older architecture later, not a request to start that refactor now.
