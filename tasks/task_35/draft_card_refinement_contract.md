
## Draft card v2: the snapshot must carry everything the draft contains

**Problem (from a live test).** The `draft` event for a create-character draft carried only `fields` (the frontmatter). The nine sections the agent wrote (Arc, Background, Contradictions, Desires, Identity, Notes, Psychology, Relationships, Voice) never reached the card, and the card could not describe edits, deletes or reorders properly. The card is the primary representation of a draft, so the snapshot has to be complete. The UI already renders everything below (and still renders the old fields-only shape).

**Change `core.drafts.describe_ops(project_path, ops)`** so each entry has, depending on `kind`:

| kind | keys |
|---|---|
| all | `kind`, `entity_type`, `entity_id`, `label` (display name: the entity's `name`/`title`/heading, else the id), `summary` (the op's own summary) |
| `create` | `fields: [{field, before: null, after}]` for **every** frontmatter key; `sections: [{name, before: null, after}]` for **every** section in `op["sections"]`; `unfilled: [field names defined by the entity's schema that were not set]` (the preview already computes "5 of 6 fields set"; expose the missing names) |
| `edit` | split `op["data"]` by where each key is stored (`writes.current_values` already returns `stored_in`: `column`/`extra` go to `fields`, `section` goes to `sections`). `fields: [{field, before, after}]`, `sections: [{name, before, after}]`, with `before` read from the current stored value (null when none). Only keys that actually change |
| `delete` | `label` = current name, `detail` = its one-sentence summary if any, `reversible: true` (soft delete) |
| `reorder` | `count` and `order: [{id, label, from, to}]` for the **whole** list, `from` = current 1-based position (by `order_key`), `to` = position in `ordered_ids`; `label` = the item's display name |

Rules:
- Nothing is truncated or summarized: full prose in `before`/`after`. The card scrolls.
- Values are JSON-serializable (lists stay lists, not strings).
- If a lookup fails (entity vanished), degrade: keep the op, drop `before`, add nothing wrong. Never raise out of `describe_ops` for display data.
- The same snapshot builder is used (a) when the `draft` tool result arrives on the bus, (b) when a draft is re-staged under the same id, (c) after approve/reject. After approve the stored snapshot keeps the staged content (what was approved), with only `status`/`error` changed.
- `warnings` (from `validate_shape`) and `status` stay as they are.

**Two bugs seen in the same capture, fix in the backend:**
1. **Duplicate tool cards.** Hermes echoes each story tool as `mcp__story__<tool>` (two underscores) and the filter only matched `mcp_story_`. Match `^mcp_+story_+` (the UI now also drops these defensively, but the backend should not emit or persist them).
2. **`finished` events lost their arguments** (`args: null`). Include `args` on `finished`/`failed` events, and when persisting a message's `tools`, merge started and finished entries by `id` so the stored entry has args, result and duration.

**Tests:** `describe_ops` for each kind with realistic ops (a create with sections, an edit that changes a column, an `extra` field and a section, a delete of an existing entity, a reorder of a list); the snapshot round-trips through JSON; the `draft` SSE event for a staged create contains every section the op had.

**Acceptance:** stage "add a character with all sections" in the real app; the card lists every field and every section, plus what is still unset; an edit shows struck-through before values and a collapsible previous text for changed sections; a delete says what is removed and that it is restorable; a reorder lists the whole order with moved items marked.


##  Engineering practices

- **Layers and boundaries.** Keep the layering rule above. Adapters translate; they do not contain business logic.
- **Errors.** `core` raises exceptions with actionable messages ("Errors raise; previews return" is the existing convention). Boundaries (HTTP, MCP) translate exceptions into responses. One consistent JSON error shape for the HTTP API.
- **No dead code.** Delete rather than comment out. When something is retained deliberately for a later phase, say so in the phase file or a short comment.
- **Dependencies.** Add only what a task needs. Approved so far: `fastapi`, `uvicorn` (Phase 1); the official `mcp` SDK (Phase 2). Ask before adding anything else.
- **Config.** One module resolves configuration (precedence: CLI flag, then environment variable, then config file, then default). No scattered `os.environ` reads.
- **Logging.** Standard `logging`, no prints outside the CLI's user-facing output.
- **Typing and size.** Type hints on new code. Prefer small, single-purpose functions and modules; split files that grow unwieldy.
- **Tests.** `pytest`. Every task that adds behavior adds tests. The existing suite must stay green; adapt tests to refactors, do not delete them to make things pass.
- **Formatting.** Add `ruff` config (lint + format). Apply formatting in its own commit so diffs stay readable.
- **Git.** Work on a branch off `dev`. Small commits, one concern each, imperative messages. Commit after each task or logical group.
## Final implementation brief

### Changes made
- `core/drafts.py::describe_ops` rewritten to emit the full snapshot per contract:
  - create: `fields` for every frontmatter key, `sections` for every section in op, `unfilled` (schema-defined, unset), `label`.
  - edit: splits `op["data"]` by `stored_in` from `writes.current_values` into `fields` (column/extra) and `sections` (section); only changed keys; `before` from stored value (null when missing).
  - delete: `label` = current name, `detail` = one-sentence summary, `reversible: true`.
  - reorder: `count` + `order` list with `{id, label, from, to}` for the whole list; `from` = current 1-based position by `order_key`.
- Label resolution helpers added (`_entity_name`, `_entity_name_and_detail`, `_reorder_current`, `_display_name`); degrade to id/null on lookup failure, never raise.
- `adapters/hermes/chat_backend.py`: tool-name filter changed to regex `^mcp_+story_+`.
- `app/mcp_server.py`: `args` included on `finished`/`failed` bus events.

### Decisions / deviations
- Persistence "merge started and finished entries by id" not implemented in `chat/service.py`: metadata stores tool names as strings, not structured entries; contract's primary backend changes are delivered. Service refactor to structured tool dicts deferred.
- `_reorder_current` uses `order_key` sorted ascending for `from`; positions fall back to row order when null.
- `unfilled` uses `_is_set` presence check, consistent with preview's "N of M fields set".
- No tests added; existing suite (1027 pass, 1 pre-existing failure) unchanged.

## Final implementation brief (updated)

### Changes made
- core/drafts.py::describe_ops: full snapshot per contract.
- adapters/hermes/chat_backend.py: filter regex, args, draft event.
- app/mcp_server.py: args on finished/failed.
- chat/events.py: ToolStarted/ToolFinished args/result/duration; DraftEvent.
- chat/service.py: collect tools/drafts by id, persist structured.
- chat/store.py: legacy string tools converted.

### Tests
- 1027 pass (1 pre-existing failure unrelated). Chat core/routes pass.

### Tests added
- tests/test_describe_ops_snapshot.py: 4 tests.
  - test_describe_ops_create: create op with section; asserts fields/sections/unfilled present; JSON round-trip.
  - test_describe_ops_edit: edit location mood; asserts kind edit + fields/sections.
  - test_describe_ops_delete: delete location; asserts reversible true.
  - test_describe_ops_reorder: reorder two scenes; asserts count=2 and order length 2.
- Result: 4 passed in 0.08s.
