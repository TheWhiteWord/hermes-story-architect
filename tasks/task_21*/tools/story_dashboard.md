# story_dashboard — KEEP (P2)

`tools/story_dashboard.py` (389 lines) + `src/dashboard/` + `core/db.py:718 get_dashboard_data`

## What it does
Builds a self-contained HTML dashboard (CSS + JS + JSON injections) and returns a URL for `desktop_preview` to open. Injects 6 shapes of data, screenplay text, and computed statistics.

## Findings

1. **Not a normal tool.** It doesn't return story data to the agent — it returns a URL for the *human* to look at. It should be judged as presentation, and it is the only tool where that's true. That distinction matters for your "assist a human" framing: this is the human's window, everything else is the agent's.
2. **Duplicated CSS/JS manifest.** `CSS_ORDER` and `JS_ORDER` (lines 5–17) enumerate `src/dashboard/` contents by hand. Adding a JS file means editing Python. A `sorted(glob(...))` would drift less — but explicit order is sometimes needed for load sequence, so this may be deliberate. Verify before changing.
3. **Duplicated `try/except ImportError` with identical branches** (lines 36–38) — both branches are the same import. Dead defensive code.
4. **`_compute_screenplay_stats` swallows all errors and returns None** — deliberate ("dashboard still works without stats"), and correct for a presentation tool. Contrast with `story_search`, where the same pattern causes data loss. Same idiom, right call in one place, wrong call in the other.
5. **Shares `get_dashboard_data` with nothing.** The load views in `spec.md` §3.2/§3.3 explicitly must *not* reuse the dashboard payload ("focused DB projections, not the dashboard payload"). So this stays isolated — but it means the dashboard payload shape is not reusable for the agent-facing views, by design.
6. **`get_screenplay_text` is in the same path** — the screenplay/Fountain work is coupled to the dashboard. Given `core/fountain_lexer.py` is a known incomplete port (per your notes), a screenplay regression surfaces as a *dashboard* regression, which is a confusing place to notice it.

## Work
1. Nothing required. Verify it renders (that's a runtime check, not read-only).
2. Small: delete the duplicated `except ImportError` branch; collapse the identical branches.
3. Consider whether the CSS/JS manifest should be generated.

## Note
`src/dashboard/js/` is large and hand-built. Reviewing *it* is a separate piece of work from the tool layer — out of scope here, but worth a task when the toolset settles.
