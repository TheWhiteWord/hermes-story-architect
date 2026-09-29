# Dashboard

*Schematic draft — headings and notes only.*

The user has a dashboard, and the plugin drives it. Three things about it are
not derivable from the data, and this file is those three things.

Everything else on that surface is computed from the entities — the character
web from relationships, the arc graph from beats, the statistics from value
charges, the view list from what exists. The agent already knows all of it from
what it has staged, so describing the views would be a second source of truth
for something derived.

---

## It opens by itself, and only sometimes

*The first thing to know, because it decides whether to call the tool at all.*

- **The plugin opens the dashboard after a write.** A `post_tool_call` hook
  dispatches it, so the user sees the change without asking. **Calling
  `story_dashboard` unprompted is therefore noise** — it re-opens a pane the
  plugin has already opened.
- **But only on a committed draft, and only on a memory write.** Verified
  against the hook: of the three tools it watches, a `story_draft` triggers it
  **only when the commit actually landed** — a staged draft does not, by design,
  because staging writes nothing and there is nothing to redraw. Reads
  (`load`, `retrieve`, `search`, `describe`) never trigger it.
- So: **after a commit the user already sees it; before a commit they cannot.**
  A staged change is not on the dashboard and will not appear until it is
  committed. Do not tell the user to look at the dashboard to check a proposal.
- The hook is wrapped in a bare `except` — a dashboard that fails to build does
  not fail the write that triggered it. **A write can succeed with no dashboard
  and no error anywhere**, so the absence of a refreshed pane is not evidence
  that nothing changed.

## Scene order is the screenplay

*The second thing, and the reason sequencing is a dramatic decision.*

- The script view is assembled from the scenes **in order**. The dashboard does
  not render each scene separately and place them — it concatenates them into
  one screenplay, and that concatenation *is* the film's reading order.
- **So moving a scene changes the film, not a list.** A user reordering scenes is
  making a decision about the story, and it is worth treating as one: ask what
  the new order does rather than performing the move mechanically.
- It is also why `reorder` exists as an operation at all — it renumbers a whole
  list, because the list is the thing being changed. → `staging-changes.md`
- *Not the same as a scene's own position within its sequence.* Order is per
  parent, and the screenplay concatenates across all of them. → `scene-design.md`

## It is generated from committed data, into a temporary file

*Why the dashboard never shows a staged change.*

- The dashboard is **built from the database** and written to a temporary HTML
  file, which the preview pane is pointed at. It is not a live view of a draft;
  it is a snapshot of what has been committed.
- The URL carries a timestamp so re-opening refetches — which is why the same
  URL behaves correctly after an edit.
- Two consequences worth holding: **the dashboard cannot be used to review a
  proposal** (that is what the draft's `preview_md` is for), and **it costs
  nothing to leave alone**, because it is not maintained by hand.
- *Not in this file:* how to read the preview pane, which is a desktop
  capability rather than this plugin's.

---

## Open questions

- [ ] The hook swallows every exception, so a failed dashboard refresh is
      invisible. Deliberate — a dashboard must not be able to fail a write — but
      it means a stale pane is ambiguous. Worth a line, or is the preview's
      freshness the user's to judge?
