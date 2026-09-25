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

## Explicit memory import boundary

`story_import` is the one intentional Markdown import exception to the DB-only runtime rule:

- `.story/memory.md` may be read as an explicit import/rebuild source.
- A valid memory file is validated and written to `project.extra.memory`.
- If the file is absent, existing DB memory is preserved.
- If the file is invalid, import fails before the DB is changed.
- Runtime tools (`story_load`, `story_memory`, `story_dashboard`) read DB memory only.

This is an import boundary, not a compatibility fallback. Memory is already DB-first for runtime reads and mutations; the Markdown file remains the human-facing projection/import surface.

## Future target: `structure.md`

`structure.md` is the future realignment target for project structure, not a current runtime file path in this repository. The later DB-first audit should use it as the canonical Markdown/import target once the broader structure architecture is defined.

The intended separation is:

```text
structure.md  → explicit import source for project structure
project.md    → project metadata
memory.md     → explicit import source for project memory
DB            → operational source for load, edit, memory, and dashboard
```

Do not conflate the memory exception with the broader structure migration. The memory path is settled; the later audit must determine how `structure.md` maps to the existing project, act, sequence, scene, and arc data without creating a second operational authority.


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
- `core/db.py` — the legacy `get_memory_outline()` reader was removed during task_25; future audit should verify no runtime path reintroduces it;
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

The memory implementation must not introduce a new runtime file-first dependency. `.story/memory.md` is generated from `project.extra.memory`; `story_import` may read it only as the explicit import/rebuild boundary described above. The dashboard popup reads DB-derived injected data.

This note is a reminder to audit the older architecture later, not a request to start that refactor now.
