"""Work out story_architect's response budget for a Hermes model.

Hermes spills an MCP result to disk (leaving the agent a ~1.5k-char preview and
a path it cannot read) when the result is longer than

    min( tool_budget.mcp_result_size_chars,           # config.yaml, default 50000
         clamp(15% of the context window in chars,    # window_tokens * 4 * 0.15
               8000, 100000) )

The second term is the one that bites: it shrinks with the model. A 32k-token
model spills at 19,200 chars, a 65k one at 39,000, a 128k one at the full 50,000.
The plugin cannot see the model, so this derives the number once, with a margin,
for you to put in ~/.config/story-architect/config.toml.

This mirrors Hermes's tools/budget_config.py. If a Hermes upgrade changes those
constants, update them here (tests pin the current values).

    python -m story_architect.adapters.hermes.budget 65000
    python -m story_architect.adapters.hermes.budget 32000 --mcp-cap 40000
"""

from __future__ import annotations

import argparse

CHARS_PER_TOKEN = 4              # Hermes's own estimate (agent/model_metadata.py)
PER_RESULT_WINDOW_FRACTION = 0.15
MIN_RESULT_CHARS = 8_000
MAX_RESULT_CHARS = 100_000
DEFAULT_MCP_CAP = 50_000         # tool_budget.mcp_result_size_chars default
SAFETY = 0.90                    # stay under the cap: the host counts its own way
ROUND_TO = 500


def hermes_spill_threshold(context_tokens: int, mcp_cap: int | None = None) -> int:
    """The result length above which Hermes spills an MCP result to disk."""
    window_chars = context_tokens * CHARS_PER_TOKEN
    scaled = max(MIN_RESULT_CHARS,
                 min(int(window_chars * PER_RESULT_WINDOW_FRACTION), MAX_RESULT_CHARS))
    return min(mcp_cap or DEFAULT_MCP_CAP, scaled)


def suggest_budget(context_tokens: int, mcp_cap: int | None = None) -> int:
    """A response budget safely under Hermes's threshold for this model."""
    threshold = hermes_spill_threshold(context_tokens, mcp_cap)
    return int(threshold * SAFETY) // ROUND_TO * ROUND_TO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m story_architect.adapters.hermes.budget",
        description="Suggest max_response_chars for a Hermes model.")
    ap.add_argument("context_tokens", type=int,
                    help="the model's context window in tokens (e.g. 65000)")
    ap.add_argument("--mcp-cap", type=int, default=None,
                    help="tool_budget.mcp_result_size_chars from the profile's "
                         "config.yaml, if you set one (default 50000)")
    args = ap.parse_args(argv)
    if args.context_tokens <= 0:
        ap.error("context_tokens must be positive")
    threshold = hermes_spill_threshold(args.context_tokens, args.mcp_cap)
    budget = suggest_budget(args.context_tokens, args.mcp_cap)
    print(f"Hermes spills MCP results longer than {threshold:,} chars "
          f"on a {args.context_tokens:,}-token model.")
    print(f"Suggested budget: {budget:,} chars. In "
          f"~/.config/story-architect/config.toml:\n")
    print(f"[story_architect]\nmax_response_chars = {budget}")
    if budget < 15_000:
        print("\nNote: below ~15,000 the base map's fixed part (characters, plots, "
              "worlds, one compact row per scene) can exceed the budget on a large "
              "project; use act=/sequence= scoping to stay under it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
