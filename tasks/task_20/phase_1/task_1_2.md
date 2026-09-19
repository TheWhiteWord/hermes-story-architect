# Task 1.2: Memory Outline Extraction — `memory_outline`

## Goal
Add `memory_outline` computation to `get_project_summary()` — parse `## ` headings from `.story/memory.md` and emit `{heading, preview}` per section.

**Scope:** `core/db.py` — new helper function + integration into `get_project_summary()`. Independent of Task 1.1 (can be developed in parallel).

---

## Current State

`get_project_summary()` currently has no memory handling. `tools/story_load.py:90-94` reads the full memory file text and emits it as `memory` key.

The `.story/memory.md` file exists in the fixture at `tests/fixtures/save-the-children/.story/memory.md`. It contains `## ` headings with prose bodies.

---

## Target State (spec §5)

```json
"memory_outline": {
  "status": "placeholder — design deferred, see §5",
  "sections": [
    {"heading": "<heading>", "preview": "<preview-line>"},
    ...
  ]
}
```

- Heading: the text after `## ` (trimmed)
- Preview: first non-empty line after the heading, truncated to ~120 chars
- `status` key is a literal string placeholder per spec §5

---

## Implementation Plan

### Step 1: Helper function
```python
def get_memory_outline(project_path: Path) -> dict:
    """Parse .story/memory.md, return {status, sections} with heading + preview per section."""
    memory_path = project_path / ".story" / "memory.md"
    if not memory_path.exists():
        return {"status": "placeholder — design deferred, see §5", "sections": []}
    
    text = memory_path.read_text()
    sections = []
    current_heading = None
    current_preview = None
    
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_heading is not None:
                sections.append({"heading": current_heading, "preview": current_preview or ""})
            current_heading = stripped[3:].strip()
            current_preview = None
        elif current_preview is None and stripped and current_heading is not None:
            current_preview = stripped[:120]
    
    if current_heading is not None:
        sections.append({"heading": current_heading, "preview": current_preview or ""})
    
    return {"status": "placeholder — design deferred, see §5", "sections": sections}
```

### Step 2: Integrate into `get_project_summary()`
- Call `get_memory_outline(project_path)` 
- Add result to returned dict as `memory_outline` key

---

## Code anchors

| What | Where |
|---|---|
| Current memory read (to be removed in Phase 2) | `tools/story_load.py:90-94` |
| Fixture memory file | `tests/fixtures/save-the-children/.story/memory.md` |

---

## Test impact

No tests in this task (Phase 3). The fixture has a real `memory.md` to verify against.

---

## Checklist

- [x] `get_memory_outline()` parses `## ` headings from `.story/memory.md`
- [x] Preview = first non-empty line after heading, truncated to 120 chars
- [x] Returns `{status, sections}` dict
- [x] Graceful when file missing (empty sections list)
- [x] Integrated into `get_project_summary()` return value as `memory_outline`
- [x] Verify against `tests/fixtures/save-the-children/.story/memory.md`

---

## Final Brief

**Changes made:**
- Renamed `_build_memory_outline()` → `get_memory_outline()` (public, matching task spec)
- Fixed `status` value: was runtime strings (`"no_memory_file"`, `"ok"`, `"empty"`), now always returns spec literal `"placeholder — design deferred, see §5"`
- Updated call site in `get_project_summary()` (line 510)

**Verification:** All 3 test cases pass — fixture (no H2 headings → empty sections), synthetic H2 headings (correct parsing + preview truncation), missing file (graceful empty sections).

**Deferred:** None.
