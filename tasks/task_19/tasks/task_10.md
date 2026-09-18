# Task 10: Fix `project.act_count` (max of declared vs actual)

## Goal
Implement the special `act_count` logic: `max(declared, actual)` where declared is the user's `act_count` field in project frontmatter.

## The Problem
The old system read `act_count` from project.md frontmatter (user can declare 3 acts even if only 2 act files exist yet) and took the max with the actual act count. The new system doesn't do this.

## Spec (from `dev` branch `_parse_project`)
```python
declared = project.get("act_count", 3)
project["act_count"] = max(declared, acts_count)
```

## Implementation

### 1. Verify act_count is imported into project extra
Check `tools/story_import.py:_import_project` — it imports all project.md fields except `name`/`logline` into `extra`. So `act_count` should already be in extra. **Verify this against the code before editing.**

### 2. In `get_dashboard_data()` (Task 8 code), fix act_count:
```python
declared = proj_dict.get("act_count", 3)
proj_dict["act_count"] = max(declared, len(acts))
```

Note: `proj_dict` already merges `extra` at top level, so `proj_dict.get("act_count", 3)` reads the declared value from extra.

### 3. Import fix if needed
If `act_count` is not in extra after import, check `_import_project` skip set — `act_count` should not be in skip.

## Files
- `core/db.py` — `get_dashboard_data()` project counts
- `tools/story_import.py` — `_import_project()` (only if act_count not imported)

## Verification (against old dashboard)
- [ ] Project.md with `act_count: 3` and only 2 act files → dashboard shows 3 acts
- [ ] Project.md with `act_count: 3` and 4 act files → dashboard shows 4 acts
- [ ] Project.md without `act_count` field → dashboard shows max(3, actual)
- [ ] Stats row (line ~2443): `p.act_count` must show correct count

## Deferred Issues
None.
