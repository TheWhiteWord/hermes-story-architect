# Descibe and search patch notes

I've changed `story_describe` so it never returns a half-cut schema, and packaged it in `describe-and-search.patch`. It applies cleanly to your current `dev`. The full suite is 1187 passed, with only the unrelated `test_no_hermes_imports` failing as before.

**What the tool returns.** It returns entity schemas, not tool definitions. The tools' own schemas are already in the model's context. The section names it lists are a closed set, and `story_draft` rejects any name not on the list. A half-read schema can therefore lose a whole write, not just one field.

**How it gets cut.**
- Asking for all types is ~30 KB. A 65k-token model or larger copes, but a 32k-token model's Hermes limit is 19,200 chars, so it spills.
- Hermes also spills the largest result first when several tool calls land in one step. A 30 KB describe next to a `story_load` call is the first thing to go.
- A single type is only 1.3–5.7 KB, so asking for the types you need avoids both problems.

**What the patch changes.**
- **Whole types only.** Each type comes back complete, with every field and its sections, or not at all. Whatever doesn't fit is named in `deferred_types`, with `truncated: true` and a hint to ask again. This reuses the pattern from the other tools, so there's no compact form and nothing is shortened.
- **New `entity_types` list.** You can ask for `["scene", "scene_beats"]` in one call. `entity_type` still works, and a bare string is accepted.
- **The first type is never cut,** even if it alone exceeds the budget. Bad type names return an error that lists the valid ones.
- **Paging works at every budget I tried.** At 17,000 chars (the helper's number for a 32k-token model) the full set takes 2 calls. At 8,000 it takes 6, and every type arrives once, complete.
- **Tests:** 18 new ones check that a returned type equals the full schema field for field, and that the section list survives every budget. I broke the code on purpose twice and the tests failed each time.

**Why a second patch contents changed.** `dev` has moved since my earlier clones. Your `db.py` has an `is_deleted=0` fix mine doesn't, so I left `db.py` alone and built this patch against the current `dev`. It touches four files:
- `story_describe.py`
- `story_search.py`
- `tests/conftest.py`
- `tests/test_response_budget.py`

**Also in the patch.**
- **`story_search` limit clamp.** It never reached `dev`, because it came after the version you applied. I checked that the patch only overwrites old code and nothing of yours.
- **Test isolation.** Your `config.toml` budget could otherwise make the describe completeness tests fail on your own machine. The tests now ignore user config, and the duplicate fixture in `test_response_budget.py` (the earlier patches stacked) is gone.
