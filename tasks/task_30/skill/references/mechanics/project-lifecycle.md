# Project lifecycle

*Schematic draft — headings and notes only.*

The operations that sit outside the draft path: creating, listing, backing up,
restoring, purging, exporting, importing, and deleting a project. These are the
calls that can lose work, so what matters here is **ordering and confirmation**,
not parameters — those are in the tool schema.

---

## The two destructive operations, and how they are gated

*Both require the same literal string, and neither should be supplied by the
agent.*

- **`delete_project`** and **`purge`** each need a confirmation containing the
  literal text `DELETE <project slug>`. Without it both refuse, and both say why:
  *"It removes every entity in the project and no flag in the database can undo
  it"* and *"It is irreversible and must be the user's call."*
- **The string is the user's to give.** It exists so that a human types the word
  DELETE for an operation that cannot be undone. Supplying it on the user's
  behalf removes the only thing it does. **Ask, and wait.**
- `purge`'s refusal also points at the exact alternative: *"To undo a delete
  instead, use action='restore' — that is exact."* So the choice between
  restore and purge is the choice between reversible and not.

## `create_project` is the one write with no review loop

*The asymmetry at the centre of this file.*

- **A project cannot be drafted**, so this does not go through the preview. The
  response is a path and a message — there is no `preview_md` to relay and
  nothing to confirm against. Verified.
- **Every other creative write in the system has a preview.** This one does not,
  and it happens at the very start, when the user knows least about how the tool
  represents a story.
- So this is the moment to be most careful and least automatic: **ask what the
  project is before creating it, and do not invent a logline or a genre to fill
  a field.** An empty field is recoverable through the ordinary draft loop; a
  wrong one is a decision the user did not make.
- It is forgiving in the other direction: only `name` is required, and the rest
  fall back to defaults, so a project can be created nearly empty and filled in
  later. → `project-design.md`

## Back up before anything irreversible

*The ordering, since that is what this file is for.*

- **`story_backup` before a delete, before an import, and before the end of a
  working session.** The database holds every write — commits and memory alike —
  and the Markdown files are only an export of it.
- **A backup cannot be restored by any tool.** It is a file copy, and recovering
  from it is a manual copy back into place. That is stated in the tool's own
  description, and it is the reason a backup is worth taking anyway: it is the
  only copy that will exist.
- **`delete_project` takes its own backup** before removing anything, and says
  where it put it and how to put it back. So that one is recoverable by
  following the message — **but the user has to be told the path**, because
  nothing surfaces it again.
- **`export` is not a backup.** It writes Markdown, and the tool says so
  directly. Use it to publish or to snapshot before an import; use `backup` to
  keep the database.

## `export` also deletes

*Not a side effect to discover — a deliberate one, and worth knowing anyway.*

- `export` writes every entity out as a note **and sweeps away the notes a
  previous export wrote for entities the database no longer has.** Its own
  comment says why: without the sweep a deleted entity would leave its note
  behind and the next import would resurrect it.
- So a round trip is honest — a delete survives it. The response reports both
  counts: files written and files removed.
- **That is also what makes `import` survivable**, which is the next section.
- On a first export of a project with one character, the output is three files:
  the project note, that character's note, and the memory export.

## `import` is the one that throws work away

*The most dangerous call in the system, and the most gated.*

- **`import` rebuilds the database from the Markdown files**, discarding
  everything committed since the last export. The database is the source of
  truth, so anything not exported is simply gone.
- **The sequence is: export, then dry-run, then import.** The dry run reports
  what would be deleted and re-imported without changing anything, and it is
  the step that tells you whether there is work to lose.
- **`confirm` is required** to actually import when the database holds work that
  exists only there — which is exactly the case the dry run is for.
- **Never use it to repair something.** A backup and `story_draft` are the tools
  for changing things; import is for an intentional re-sync from Markdown, and
  using it as a repair would destroy the thing being repaired.
- *In practice, the correct answer is almost always that import is not the tool
  being wanted.* If the problem is a missing field, that is a draft; if it is a
  broken link, that is `ids-and-links.md`; if it is a lost entity, that is
  `restore`.

## Restore is exact

*And it is the answer far more often than purge.*

- A soft delete keeps the row. **`restore` brings an entity back with its prose
  and its relations as they were**, and reports what it did — including any
  children restored with it.
- So delete is genuinely reversible, and the exposure is only at `purge`.
- **`purge` is the only irreversible operation on an entity, and it is gated
  three times over:**
  1. it needs the confirm string, exactly as `delete_project` does;
  2. **it only touches entities deleted more than thirty days ago** — verified by
     backdating one deletion: given the confirm string, it purged the 45-day-old
     character and left the recent one untouched and still restorable;
  3. **it takes its own backup** first, and says where.
- So even the irreversible operation is recoverable by hand, and a fresh delete
  has a thirty-day window in which it is not even eligible. **The practical
  consequence: there is almost never a reason to purge.** Restore covers the case
  people reach for purge to solve.

## Listing

- `list_projects` enumerates every project under the root **without opening a
  database**, so it is safe to call when the name is uncertain — and worth
  calling before guessing, since every other call needs a project that resolves.
- Note the resolution: a project name is matched **fuzzily**, silently above a
  high threshold. A near-miss writes to the wrong project. → `story-memory.md`,
  which covers the same mechanism where it bites hardest.

---

## Open questions

- [ ] `create_project` has no preview, and it is the only creative write without
      one. Worth stating in SKILL.md as a hard rule, or is this file enough?
- [ ] The confirm string is the user's to type, and the schema says so — but a
      model under instruction to be helpful can supply it. Is there a phrasing
      here that survives that, or is it a matter of the instruction's authority?
