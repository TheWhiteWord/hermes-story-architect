# story_memory

**Role:** durable project facts that outlive the conversation.
**Status:** verified. No defects in this tool.

---

## What it does

Three exact-entry mutations on `project.extra.memory`, across four categories:
`decisions`, `directions`, `open_questions`, `continuity_warnings`.

`add` / `remove` / `replace` — one entry at a time, matched by **complete exact
text**. That strictness is deliberate: a fuzzy memory match could silently
rewrite the wrong decision, and these are the facts a future session trusts.

## Verified behaviour

Probed and confirmed working:

| Case | Result |
|---|---|
| bad category / bad action | error + the four valid names, memory untouched |
| entry > 300 chars | rejected (`MEMORY_ENTRY_LIMIT`) |
| whitespace-only entry | rejected |
| remove/replace a missing entry | error + `current_entries` so the agent can see the real text |
| duplicate add | no-op, `success: true` (idempotent) |
| nonexistent project | error, no write |
| 3000-char project limit | fires at entry 76, keeps prior 75, `action_required` given |
| persistence | survives a fresh connection and shows in `story_load` |

The 3000-char limit is enforced in `core/db.validate_memory`, and the failure
returns `current_entries` so the agent can tell the user what to prune.

## The one change: `project` may now be a guess

Project resolution is shared by all 11 tools and used a threshold of 40 (shared
with screenplay title matching). At 40, **an unrelated name matched a real
project**: `project="ghost"` scored 72 against the slug `stc` and wrote to the
wrong story, reporting `success: true`.

Fixed in `tools/story_resolve.py` with a local `PROJECT_THRESHOLD = 75`:

| Input | Score | At 40 | At 75 |
|---|---|---|---|
| `the children` → `save-the-children` | 76 | match | **match** (kept) |
| `ghost` | 72 | match | **rejected** |
| `a totally unrelated phrase` | 45 | match | **rejected** |
| `stc` | 100 | match | **match** |

75 rather than 80 because 80 rejects the legitimate `the children` →
`save-the-children` (76). `FUZZY_THRESHOLD` is untouched — screenplay title
matching behaves exactly as before.

`story_memory` additionally reports a **weak** match (score < 90) on success, so
the agent can see it guessed rather than was told:

```json
"warning": "Project 'the children' was matched to 'save-the-children'
            (similarity 76). Memory was written to 'save-the-children'."
```

Scoped to this tool only, per decision. A failed call does not also carry a
warning — it already lists the available projects.

## Tests

`tests/test_project_resolution.py` — 13 tests. Plus the pre-existing
`test_memory.py`, `test_memory_e2e.py`, `test_memory_export.py`,
`test_story_memory.py`.
