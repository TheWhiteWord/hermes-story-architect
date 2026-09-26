# story_dashboard

**Role:** open the visual dashboard in the preview pane. Not a data tool —
it renders HTML for the *user*; the agent reads data via `story_load` /
`story_retrieve`.

---

## How it works

1. `get_dashboard_data(project_path)` — one DB read for everything
2. `assemble_dashboard()` — inlines `index.html` + 5 CSS files + 18 JS modules
   into a single self-contained HTML file (no external requests)
3. Injects `__STORY_DATA__`, `__SECTIONS__`, `__SCREENPLAY_STATS__`,
   `__STRUCTURAL_STATS__` above a marker comment in `core.js`
4. Writes to a temp file and returns a `file://` URL with a `?t=` cache-buster

The agent then passes that URL to `desktop_preview(action=open, url=...)`.

## Two silent-failure defects fixed

### 1. Output file named after the *title* — projects collided

The temp file was named from the project's display name. Two projects with the
same title wrote **the same file**, so the second dashboard rendered the first
project's data under the second's name — with `success: true`.

```python
# before: both projects -> /tmp/The_Film.html
project_name = sd.get("project", {}).get("name", "")
# after: the folder slug, which is unique per project
project_name = project_path.name or project
```

The per-call `?t=` cache-buster masked this in normal single-project use, which
is why it survived.

### 2. Injection anchor had no guard

The injections are spliced in with `html.replace(<comment in core.js>, ...)`.
If that comment is ever reworded, the replace silently no-ops, `__STORY_DATA__`
is never defined, and the dashboard renders **empty** while still reporting
success. Now asserted:

```python
if boot_marker not in html:
    return json.dumps({"error": "Dashboard boot marker not found …"})
```

The tool now fails loudly at the only place that knows the anchor is wrong.

## Verified

- All 3 placeholders replaced; all 4 injections present and **valid JSON**
- `__STORY_DATA__` carries characters, scenes, plots, worlds, arcs, relationships
- Cache-buster changes on reopen (1.1s apart → different URL)
- Missing project / missing DB / no schema → error, not a crash
- Screenplay stats: empty text → zeroed stats; garbage → parses without crashing;
  duration buckets always 20 long (the chart needs a fixed count)
- Punctuation in a title can't break the output filename

**Headless Chrome check** (`TestActuallyRenders`): the page is executed and its
built DOM inspected. Static file 234,969 chars → rendered DOM 472,611 chars with
`Kael`, `Elena`, `Central Room` present, and no uncaught JS errors. Everything
else in this suite inspects strings; only this proves the bundle *consumes* the
injected data.

## Tests

`tests/test_dashboard.py` — 20 tests.
