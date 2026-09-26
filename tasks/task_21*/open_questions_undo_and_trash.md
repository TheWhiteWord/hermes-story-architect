# Open questions — the trash, and undo

Raised 2026-09-26, right after the delete/soft-delete/purge work landed.

The delete side is done and tested. Two things about *seeing and reversing* it
are still unresolved, and they are worth deciding together rather than alone —
they change what the UI should offer.

---

## 1. There is no way to see what is in the trash

`purge` can delete soft-deleted rows, and the DB carries `is_deleted` /
`deleted_at` for every one of them. But **nothing exposes that list**. There is
no tool, no view, no dashboard panel that shows:

- which entities are currently deleted
- when each was deleted
- how many are old enough for the age floor to purge
- what size they are (prose in `sections`, relations)

So today the user cannot answer "what would purge remove?" or "can I get X
back?" without going to SQLite by hand.

**The blocker is `older_than_days`.** Purge defaults to 30 days, which means
nothing deleted recently is eligible — by design, so a fresh mistake stays
restorable. But that also means **the trash is invisible in practice for the
first month**, which is exactly when a user is most likely to want to look at
it.

**To decide together:** is a "deleted items" view a `story_load` view (alongside
`unfilled`), a separate read-only tool, or purely a dashboard panel? The
dashboard is a static HTML file with no backend today, so it cannot call Python
at all — a panel there needs a bridge that does not exist yet. That constraint
should shape the answer, not the other way round.

## 2. Undo is still an open design question

Soft delete solved *"I deleted the wrong thing"* — `restore` is exact, because
nothing is reconstructed; the row was only flagged. That case is closed.

What is **not** solved is undo of *edits*. `story_edit(action="edit_note")`
overwrites a field in place. If an agent sets `goals_short` to the wrong value,
there is no way back — `dry_run` prevents a bad edit, but it cannot undo a good
faith edit that turned out to be wrong.

**Possibilities, none chosen:**

- **A change journal** — every write records before/after, and an undo replays
  backwards. The full version is a lot of machinery for a tool suite this size.
- **Field-level history** — keep prior values per field. Cheaper, and closer to
  what a person actually wants ("what was this field before?").
- **Snapshot-based undo** — reuse `story_backup`, restore a copy. Simple, but
  coarse: it rolls back *everything*, not one edit.
- **Nothing.** `dry_run` plus the fact that most edits are agent-visible may be
  sufficient in practice.

**Also unresolved:** a journal or history changes the cost of *every* write, and
`story_edit` is on the hot path. That cost is the main argument for doing
nothing, and it should be weighed before choosing.

**The link between the two:** if we build a change journal for undo, it also
solves the "what is in the trash" view — the same rows record who changed what
and when. If we do not, the two are separate features and should be costed
separately.

---

## Where things stand

- Delete, soft delete, `restore`, `purge`: **built and tested** (597 passing).
  See `final_tools/story_edit.md` for the delete lifecycle.
- `purge` guards: requires `purge_confirm` containing `DELETE <project slug>`
  (the agent cannot guess it — this is the human-in-the-loop mechanism), plus a
  30-day age floor by default. A backup is taken before the wipe.
- Deleted notes are swept from disk on the next `story_export` — otherwise
  `story_import` would read the stale `.md` and resurrect the entity. That was a
  real bug; it is fixed and pinned by a test.
- UI buttons for import / export / purge: **user's stated plan**, not started.
  Blocked on the dashboard having a backend.
