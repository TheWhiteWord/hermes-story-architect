# story_search

✅ **Finalized.** Verified by running against a real database; defects fixed; regression-tested.
Source: `tools/story_search.py` (68 lines) + `core/db.py:search_sections`.

Search the prose of every scene, character, plot and note in a project.

## What it is for

Find *where* something is mentioned. The LLM calls this to locate material, then calls
`story_retrieve` on the entity it found to read it properly. It is a pointer, not a content tool.

## Example

**Request** — a name and a subject, the way a writer would ask
```json
{"project": "save-the-children", "query": "Kael garden", "limit": 5}
```

**Response** — real output
```json
{"query": "Kael garden",
 "results": [
   {"entity_id": "kael", "heading": "Secrets",
    "snippet": "Kael has been dreaming of a garden they've never visited. In the simulation, no garden exists yet. They haven't told anyone."}
 ],
 "total": 1, "total_matches": 2}
```

**What the LLM does with this:** `kael` / `Secrets` is the pointer. It now calls
`story_retrieve(entity_type="character", slug="kael", sections=["Secrets"])` to read it in full.

Note `total: 1` but `total_matches: 2` — the second match was cut by `limit`, and the response
says so rather than hiding it.

## Parameters (live schema)

| Param | Type | Required | Notes |
|---|---|---|---|
| `project` | string | yes | Slug, project name (fuzzy), or absolute path |
| `query` | string | yes | **All words must be present (AND).** Punctuation is safe. |
| `limit` | integer | no | 1–50, default **10** |

## Returns

```json
{"query": "...", "results": [{"entity_id": "...", "heading": "...", "snippet": "..."}],
 "total": 10, "total_matches": 112, "note": "Showing 10 of 112 matches. ..."}
```

- `total` — how many are in `results`
- `total_matches` — the true count. **Always present.**
- `note` — only when truncated, and it says so in plain words
- `snippet` — ~200 chars centred on the match. Full text is one `story_retrieve` call away.

## Behaviour notes for skill authors

- Multi-word queries are ANDed. `garden dream` = both words, not either.
- No phrase / `NEAR` / prefix operators. Deliberate: they were the cause of the crash below.
- Searching a **character name** returns scenes and sections that mention them, not the character entity
  itself. Use `story_retrieve` for a specific entity.
- Searches **section prose only**. Structured fields (`goals_short`, `knowledge`) are not indexed.

## Errors

| Condition | Response |
|---|---|
| No such project | `"No project matching 'x'. Available projects: ..."` |
| Project has no DB | `"Database not found. Run story_import first."` |
| Schema incomplete | `"Database schema incomplete. Run story_import first."` |

## Regression fixed this session

`garden (part 2)`, `the "garden`, `Kael & Mira` used to return
`"Database not found. Run story_import first."` — a false alarm that sent the agent to a tool which
**wipes the database**. Cause: FTS5 syntax errors were caught and relabelled as a missing DB.
Fixed by `fts5_query()` in `core/db.py` (quote each term + AND) and by deleting the blanket `except`.

Measured on the fixture: `q="the"` went from **31,310 chars → 2,481 chars**.

Tests: `tests/test_search_query_safety.py`. Full suite 311 passed.
