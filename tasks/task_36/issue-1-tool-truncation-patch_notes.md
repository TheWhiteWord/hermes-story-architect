# RESPONSE-BUDGET PATCH

## STORY RETRIEVE

story_retrieve is now guarded, and I added a character filter and budget to the relationship view. I rebuilt response-budget.patch to cover everything so far, replacing the earlier one. I applied it to a fresh clone of dev and ran the full suite there: 1133 pass and 1 fails. The failure is test_no_hermes_imports, which also fails on untouched dev.

story_retrieve
Entities come back whole or not at all. They arrive in the order you asked for, up to the budget. The rest are listed in deferred_ids, with truncated: true and a hint saying to call again with those ids. This uses the same truncated and hint wording as your unfilled view.
The first entity is always returned, however big. If one entity alone exceeds the budget, the response adds over_budget with section_sizes, so the agent can request that entity one section at a time.
Paging works end to end. On the 100-scene project, with every section and field requested, following deferred_ids returned all 100 scenes exactly once and in order. It took 17 calls at 35k, and no response exceeded the budget.
Asking for specific sections or fields is the way to stay under budget. A scoped request is never truncated.

Reading 100 full scenes takes 17 calls. That is the real cost of reading everything, and the agent now sees it instead of getting a silent cut.

relationship: do you need scoping?

I think yes, but only because of the budget. Each relationship row includes every scene it appears in, so a central pair that spans dozens of scenes gets expensive. And a budget with no way to ask for the rest is a dead end. So the two come together:

view='relationship' with character=<id> returns that character’s relationships in full, always.
Without a filter, a large graph keeps full rows up to the budget. The rest shrink to id, name and characters, which still shows who is tied to whom. detail says how to expand them.

If agents never ask for a whole cast graph, you’ll rarely see this trigger. It exists so the view can’t blow up on a big project.

Notes
Tests: there are now 33 in tests/test_response_budget.py. I broke the code on purpose in several ways and confirmed the tests fail each time. Disabling both retrieve safeguards fails four tests.
The deferral logic has two layers. There is a cheap estimate plus an exact check on the real output. Either alone keeps the response in budget, so don’t be surprised if you ever see one without the other. I kept both, since the exact check is the guarantee.
Ids after the first deferred one aren’t validated. A typo in a deferred id only shows up as not_found on the next call.

## STORY SEARCH

The gap

The schema says maximum: 50, but nothing enforces it. Your MCP server passes arguments straight to the handler, and I found no schema validation in the MCP SDK. I confirmed the handler returns 121 KB for limit=500.

There’s a worse case. SQLite treats LIMIT -1 as “no limit”, so limit=-1 would return every match in the project. Models don’t often ignore a schema bound, but it happens.

Fix: the handler now clamps the limit to 1–50. A bad type, such as a string or null, falls back to the default of 10, and a numeric string like "5" is accepted. When a value is cut down, the response says so in note, so the agent isn’t misled. A limit in range behaves as before and adds nothing.

Tests: I added 11 for this. With the clamp disabled, five of them fail, so they do test it.

Where the patch stands

The patch applies cleanly to a fresh clone of dev. The full suite there gives 1144 passing and 1 failing. The failure is test_no_hermes_imports, which also fails on untouched dev. Files touched:

core/budget.py (new)
core/db.py
tools/story_load.py
tools/story_retrieve.py
tools/story_search.py
tests/test_response_budget.py (new)