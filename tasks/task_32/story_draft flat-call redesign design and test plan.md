# story\_draft flat-call redesign: design and test plan

Plugin: hermes-story-architect, branch `feature/issue-redesign`. Prepared 2026-10-13. Working assumption: the model is not the cause.

## 1. Goal

Make every `story_draft` call survive the Hermes `tool_call` bridge by using only flat, scalar arguments. The core (`core/drafts.py`, `core/writes`) stays untouched. Only the tool's front door changes. Before building it, run probes that tell us whether flat calls actually work and what exactly breaks.

## 2. What we know and what we only suspect

**Established by the logs**

- The error comes from `normalize_tool_call_entries()` in `tools/tool_search_validation.py`, so the call dies in the `tool_call` bridge, before `story_draft`'s schema or handler runs.
- Failing payloads have `calls` as a JSON string with the `"name"` key missing and the final `}` missing. Working payloads have `calls` as a native list with `name` present.
- The stored payloads have alphabetically sorted keys, so what `state.db` holds was re-serialized by Hermes. It is not raw model output.
- Flat calls with 3 or 4 scalar arguments work (`story_memory`, `story_retrieve`, `list`). Calls that include `ops` fail every time. `list` plus `summary` failed once with no nesting at all. `story_load` plus `value` failed once, intermittently.
- Direct Python calls to the handler work, and the plugin suite passes (1157 tests).

**Still unproven**

- Where the corruption happens (provider adapter, stream assembly, a sanitizer or coercion step, or storage).
- Whether the trigger is nesting, the argument count, the total length, or specific argument names (`summary`, `ops`, `value`).
- Whether the lines 589-643 note in the repo skill (keys stripped, pass arrays as strings) describes the same bug.

## 3. Design principles

1. Every argument is a string, number, or boolean. No arrays, no objects, no JSON in a string.
2. Lists are comma-separated strings (`ordered_ids="a,b,c"`).
3. One call changes one thing. A failed call costs one field, not a whole batch.
4. Every write action is an upsert, so retrying is always safe.
5. Argument names avoid anything the probes flag as suspect.
6. The old `stage` path with `ops` stays available for runtimes where it works.

## 4. Proposed actions

All actions take `project`. Draft state lives in the existing `drafts` row, and each call appends or updates one op in its op list.

| Action | Extra arguments | Effect |
| --- | --- | --- |
| `begin` | `note` | Creates an empty draft and returns `draft_id`. |
| `add_create` | `draft_id`, `type`, `id`, `note` | Adds one create op with empty frontmatter. |
| `set_field` | `draft_id`, `entity_id`, `field`, `value` | Sets one frontmatter field on a staged create. |
| `set_section` | `draft_id`, `entity_id`, `section`, `text`, `mode` (`replace` or `append`) | Sets or appends one section body. |
| `add_edit` | `draft_id`, `entity_type`, `entity_id`, `field`, `value`, `note` | Stages one edit to an existing entity. |
| `add_delete` | `draft_id`, `entity_type`, `entity_id`, `note` | Stages one delete. |
| `add_reorder` | `draft_id`, `entity_type`, `ordered_ids`, `note` | Stages a reorder. |
| `preview` | `draft_id` | Returns `preview_md` and validation findings. |
| `commit`, `discard`, `list` | as today | Unchanged. |

The parameter `note` replaces `summary` until the probes show whether `summary` is safe.

Open design questions to settle after the probes:

- How `set_field` handles non-string values (numbers, lists in frontmatter). Options: infer from the entity type's schema, or accept a `value_type` hint.
- A cap on `value` and `text` length, and whether `append` mode is enough for long prose.
- Whether `stage` (old path) and the new incremental path may mix in one draft.

## 5. Phase 0: probes (no code changes)

Run each probe 5 times and record pass or fail plus the exact error. Use a throwaway project. Run all of them in the same session and on the same model, so only one thing varies.

| # | Call | Question it answers |
| --- | --- | --- |
| P1 | `story_draft action=list project=X` | Baseline. |
| P2 | `story_draft action=list project=X summary="x"` | Does the name `summary` break a flat call? |
| P3 | `story_draft action=list project=X note="x"` | Is `note` safe where `summary` isn't? |
| P4 | `story_draft action=list project=X foo="x"` | Control: any extra key at all. |
| P5 | `story_memory` add with its 4 args plus `summary="x"` | Does `summary` break a tool that otherwise works? |
| P6 | `story_load project=X view=values value=trust` | Reproduce the `value` failure. |
| P7 | `story_load project=X view=values val=trust` | Same call with a different argument name. |
| P8 | A hand-made call with 6 scalar arguments (shape of `set_field`) on a nonexistent draft | Does argument count alone break flat calls? The handler error `No open draft` counts as a pass. |
| P9 | The same 6-argument call, with `value` holding a 500-character string containing quotes and a newline | Does string content or length break a flat call? |

**How to read the results**

- P2 fails, P3 and P4 pass: a name-based rule on `summary`. Avoid it, and look for the rule in the bridge or sanitizer.
- P2 and P4 both fail: any extra key breaks it, so the argument count or the schema match matters. Investigate before building anything.
- P6 fails, P7 passes: same finding for `value`.
- P8 passes, P9 fails: escaping or length is the trigger, so long text needs chunking.
- P8 fails: even flat calls are unsafe, so the premise of this redesign is wrong and we go back to root-cause work.
- Everything passes: nesting alone is the trigger, and the flat design is sound.

## 6. Phase 1: prototype and test

Only if Phase 0 supports it.

1. Implement `begin`, `add_create`, `set_field`, `preview`, `commit` first, in `tools/story_draft.py` and `core/drafts.py`, with tests.
2. Live test, 5 runs each, on a throwaway project: create one `value` entity (`duty`) with 4 frontmatter fields and 2 section bodies, preview it, commit it, and verify the DB row and note file.
3. Failure test: stage an invalid op and confirm `preview` reports it and `commit` refuses.
4. Retry test: send the same `set_field` twice and confirm no duplicate op.
5. Then add `add_edit`, `add_delete`, `add_reorder`, and `set_section` with `append`.

**Success criteria:** at least 95% of live calls succeed over 50 or more calls, with no change to `core/writes` behavior and the full existing suite still green.

## 7. Instructions to hand the Hermes assistant

> Treat the model as a correct emitter. Do not edit `tools/story_draft.py` yet. Create a throwaway project, then run probes P1-P9 from the plan, 5 runs each, in one session. For each run record the exact arguments sent, pass or fail, and the exact error text. If a call fails, also record the stored `function.arguments` from `state.db` for that message. Report a table of results. Do not interpret beyond the table. Then, separately, answer: (a) which Hermes code decides whether `story_draft` is loaded directly or hidden behind the `tool_call` bridge, and can `story_architect` be made eager-load; (b) does any code between the API response and `normalize_tool_call_entries` rewrite tool-call arguments (grep for `sort_keys`, `json_repair`, `sanitize`, `redact`, `unrename`, `coerce`).

## 8. Report-back template

- Probe table (P1-P9): runs, passes, error text.
- Answer to (a) and (b) above, with file and function names.
- Anything unexpected.

Paste this back and we either iterate on the design or move to implementation.
