# Issue 1 — Tool output truncation vs. MCP tool design

## State of things
- Story Architect exposes MCP tools (story load/search/get, describe, draft, etc.) returning JSON.
- Hermes truncates tool output (terminal, execute_code, MCP) via `tools/tool_output_truncate.py` `truncate_head_tail`, default cap ~50k bytes (configurable globally via `tool_output.max_bytes` in config.yaml). Marker: `... [OUTPUT TRUNCATED - N chars omitted out of T total] ...`. Full text spilled to disk.
- Native tools (read_file, search_files) use their own pagination, not this helper.
- No per-tool opt-out; limits are global per profile.

## Why it's an issue
- The app domain is story data where context is the product. Tools were split granularly (targeted args) so the agent fetches only what it needs — but what it fetches must arrive complete.
- `story_describe` returns entity schemas; truncation there defeats the purpose (agent can't see full schema).
- Truncation is silent-ish (marker present but model may proceed on partial data).

## Findings (verified)
- No per-tool opt-out or max-size declaration exists in Hermes. Limits are global per profile (`tool_output.max_bytes/max_lines/max_line_length`).
- MCP results: 2M-char hard cap (`_MCP_HARD_RESULT_CAP_CHARS`, anti-flood) + 50k budget/spillover layer truncates the LLM-facing view while spilling full text to disk.
- Native tools (read_file, search_files) use their own pagination, not this helper.
- So the lever is entirely at our tool-design level.

## Proposed direction (for specialist)
- Keep truncation as safety net; don't disable globally.
- Make tools enforce targeting: small default limits, required filters for large entity sets, pagination with `next_cursor`, summary-first when no filter.
- Split "get by id" (full payload, small) vs "list/search" (ids + counts) so truncation rarely triggers.

## Specialist correction (verified)
- `tool_output.max_bytes` does NOT touch MCP results. It only caps terminal output.
- MCP results use `tool_budget.mcp_result_size_chars` (default 50k chars), a separate knob, also per-profile in config.yaml.
- Mitigation: in the profile's config.yaml set:
  ```yaml
  tool_budget:
    mcp_result_size_chars: 100000
  ```
  Capped at 100k and scaled down by small context windows. Set the app's budget slightly below the effective threshold so Hermes never spills.
- This is a config-level change in the Hermes profile, not code in this repo. No setup.py exists here to write it; managed via Hermes profile setup / config editing.

## Open questions
- Should truncation threshold be raised for MCP specifically, or should tools self-limit?
- How to make "fetch all" impossible/impractical so the model stays selective?
