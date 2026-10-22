# Phase 0: probe results

Plan: `../story_draft flat-call redesign design and test plan.md` §5. Model in session:
stepfun/step-5-preview:free. Date: 2026-10-13.

Each probe P1–P9, 5 runs, through the `tool_call` bridge. Status column: `pass` = the
call reached the handler (a handler-level error like "No open draft" counts as a pass
per the plan); `fail` = it died in the bridge (`normalize_tool_call_entries` or
argument validation).

<!-- Results appended below as probes are run. -->

Run harness: one-shot `hermes chat -q` sessions (44 logged runs, one session lost to a
rate-limit retry — P2_r2). Probes cannot be emitted from inside an interactive desktop
session: the tool-call surface wraps `tool_call` arguments one extra level, which makes
every probe structurally identical to the model's failing double-wrap. Session ids per run
are in `../results/probe_run.log`.

## Probe table

| Probe | Description | Runs | Pass | Fail | Error text |
| --- | --- | --- | --- | --- | --- |
| P1 | baseline `action=list project=X` | 5 | 5 | 0 | — (all reached handler; drafts: []) |
| P2 | `action=list project=X summary="x"` | 4 | 4 | 0 | — |
| P3 | `action=list project=X note="x"` | 5 | 5 | 0 | — |
| P4 | `action=list project=X foo="x"` | 5 | 5 | 0 | — |
| P5 | `story_memory` add + `summary="x"` | 5 | 5 | 0 | handler error when `category` missing (expected: schema validation, not bridge) |
| P6 | `story_load project=X view=values value=trust` | 5 | 5 | 0 | — |
| P7 | `story_load project=X view=values val=trust` | 5 | 5 | 0 | — |
| P8 | 6 scalar args, nonexistent draft | 5 | 5 | 0 | `No open draft: zzz` (handler error = pass per plan) |
| P9 | 6 args, 500-char value with quotes+newline | 5 | 5 | 0 | `No open draft: zzz` (pass) |

**Every probe passed — 44/44 list-form calls reached the handler. Zero bridge failures.**

## Run log

<!-- One line per run: probe, run #, exact arguments sent, pass/fail, exact error, stored function.arguments for failures. -->

## Findings (after all probes)

### Probe results vs. the plan's read-guide

The plan said: *"Everything passes: nesting alone is the trigger, and the flat design is
sound."* The probes contradict that. **All 9 probes passed with flat, scalar arguments —
including 6-argument calls, the `summary` name, and a 500-char value with quotes and a
newline.** Flatness is not what saves a call.

What actually fails, per the 35 real failures in `state.db` (session
`20261013_042357_0c170a`, same model): the model sometimes emits `calls` as a
**JSON-encoded string** instead of a native array, and when it does, the string is
**always exactly one `}` short** (the entry object's closing brace, right before the
final `]`) and **35/37 omit the `name` key entirely**. Repair = insert `}` before `]`
→ all 35 parse; but they still fail at `calls[N] requires a 'name'`.

So the flat-call redesign would not fix the reported bug. The corruption pattern
(string-form, missing brace, missing name) is a property of how this model emits the
envelope, not of argument nesting.

### Ground-truth stats (all sessions, `state.db`)

- 523 bridge calls total: **488 list-form (all fine), 35 string-form (all corrupt)**.
- All 35 string-form payloads: exactly one `}` missing; 35/37 entries missing `name`.
- String-form occurs in exactly one session (20261013_042357_0c170a); every other
  session is 100% list-form.

### (a) Direct-load vs bridge

`tools/tool_search.py:149` `is_deferrable_tool_name()` — plugin tools are deferrable by
default, so `story_draft` is routed behind the `tool_call` bridge. Config:
`tool_search.defer_tools` (`tool_search.py:56`, `effective_defer_tools`); an empty list
(`defer_tools: []`) loads every tool eagerly and removes `story_draft` from the bridge
entirely. This is a one-line config change, not a plugin change.

### (b) Rewrite points between provider response and `normalize_tool_call_entries`

- `agent/conversation_loop.py:997` `_canonicalize_tool_call_arguments` —
  `json.dumps(json.loads(arg_str), sort_keys=True)` on the send path; explains the
  alphabetically sorted keys stored in `state.db` (re-serialization, not truncation).
  Runs only on already-parseable JSON — it raises on malformed input and falls back to
  `_repair_tool_call_arguments`.
- `agent/agent_runtime_helpers.py:233` `sanitize_tool_call_arguments` — rewrites
  unparseable args to `"{}"` + corruption marker; a repair path, not a corruption source.
- No truncation logic exists between the provider stream and
  `normalize_tool_call_entries` — the truncated JSON is what the provider delivered.

### Conclusion for the redesign decision

The flat-call redesign targets a cause the probes do not support. Two paths actually
address the observed failure:

1. **Eager-load the plugin tools** (`tool_search.defer_tools: []`) — removes the bridge
   from the path entirely; `story_draft` is called directly like `story_admin` was in
   probe 139032 (which worked with the identical envelope).
2. **Harden the bridge for string-form calls** in `normalize_tool_call_entries` — when
   `calls` is a string that fails `json.loads`, attempt the one-brace repair and, if the
   entry lacks `name`, look for it in the outer envelope; only then reject. This is a
   Hermes-side change, outside the plugin.

Option 1 is the smaller, plugin-local change and is what the probes support trying first.
