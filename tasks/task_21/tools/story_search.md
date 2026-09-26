# story_search — FIXED ✅ (was P1, cheap)

**Status: implemented and verified.** 311 tests pass (3 new). Every finding below was confirmed against real DBs first.

`tools/story_search.py` (62 lines) · `core/db.py:697 search_sections`

## What it does
`(project, query)` → FTS5 `MATCH` over the `sections_fts` index → `[{entity_id, heading, snippet}]`.

Small, does one thing, DB-only. The right shape. The implementation has three defects.

## Findings

1. **Exceptions are masked as a missing database** (lines 47–55). Any FTS5 error — malformed MATCH syntax (very easy: `query="the garden (part 2)"` is a syntax error in FTS5), missing `sections_fts` table, corrupt index — falls through to `"Database not found. Run story_import first."` The agent is told to re-import a project that is fine. **This is the worst bug in the toolset** because it sends the agent down a destructive path (re-import wipes the DB — see `story_import.md`).
2. **Three connections for one query.** Own `sqlite3.connect`, then `has_schema(conn)`, then `search_sections` → `get_db` (another). One `get_db` call covers it.
3. **`snippet` is the entire section body** (`core/db.py:711` selects `s.body` and calls it `snippet`). A 3000-word `Arc` section comes back whole, for every hit. Unbounded token cost on the one tool whose whole purpose is being called in a loop.
4. **No result limit.** 200 hits × 3000 words is a context kill with no way for the agent to ask for less.
5. **Searches section prose only.** Structured fields (`goals_short`, `knowledge`, `one_sentence`, plot beat `note`) are not indexed. For "find every place Kael wants to leave" the agent needs field search too — but see the complexity note below.
6. **Bare `query`.** FTS5 operators (`AND`, `NEAR`, `*`) pass through unvalidated, which is the source of defect 1.

## RESULT — all four fixed

| Fix | Where |
|---|---|
| Real errors, no swallow; one `get_db`; distinct "schema incomplete" error | `tools/story_search.py` — rewritten |
| `fts5_query()`: quote each term + AND, so punctuation can never be a syntax error | `core/db.py:697` |
| `limit` (default 10, max 50) + `total_matches` + honest truncation `note` | `core/db.py:search_sections` |
| `_snippet()`: ~200 chars centred on the match | `core/db.py` |
| Regression test | `tests/test_search_query_safety.py` |

Measured on `save-the-children`: `q="the"` 112 matches — payload **31,310 → 2,481 chars**, with
`"Showing 10 of 112 matches. Narrow the query, or raise limit (max 50). Use story_retrieve to read a section in full."`

`"garden (part 2)"`, `'the "garden'`, `"Kael & Mira"`, `"garden ^ 2"` — all previously
`"Database not found"`; all now return results or a clean empty result. The destructive
search → import chain is closed.

Nothing was deleted: `total` still reports what was shown, `total_matches` reports the truth,
and full section text remains one `story_retrieve` call away.

### Original work list (for the record)
1. Report the real exception. Delete the `except Exception: pass`. A missing FTS table should say so; a bad MATCH should say so.
2. Add `limit` (default ~10, max ~50) and truncate `snippet` to ~200 chars around the match.
3. One `get_db`.
4. Quote the query as an FTS5 string literal unless the caller opts into raw syntax (`raw_query: true`), or strip unbalanced parens/quotes.

## Complexity note (search, per your instruction)
Field search is the tempting over-engineering here. A `fields:` filter, per-type field search, ranking, fuzzy matching — each is a small feature that compounds. **Recommendation: do steps 1–4 only.** FTS5 already covers prose, which is where a writer's search intuition points. If field search is genuinely needed later, `story_retrieve` with `fields=[...]` plus `view="unfilled"` already covers the "what's set" case without new machinery.

## Open question
Should a bare-word query be AND-ed across terms (FTS default) or treated as a phrase? Default AND is fine; just be aware `"kael mira"` returns only adjacent matches.
