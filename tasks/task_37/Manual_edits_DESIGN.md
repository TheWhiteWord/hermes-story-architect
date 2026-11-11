# MANUAL EDITS DESIGN

## What already works in our favor

- **Backend:** `core/writes.py` already does create, edit and soft-delete with full validation. `manual_edits.py` says it's where manual authoring should land, and the script editor is the pattern to copy: a thin route calls `manual_edits`, which calls `writes`, with a content hash and a 409 on conflict.
- **Schema:** `ENTITY_SCHEMAS` describes itself, with `optional`, `computed`, `ref`, `sub_fields` and `enum`. That is enough to generate forms instead of hand-building one per entity.
- **Delete:** it already has a consent preview, soft-delete and `restore`.

## Core idea: one schema-driven form

The server turns the schema into a form spec, and one JS renderer draws it. Adding a field to the schema later makes it appear in the form with no extra work.

| Schema shape | Widget |
|---|---|
| string, number, boolean | input, number input, toggle |
| string with a closed vocabulary (`story_role`, `status`, `time_of_day`…) | select |
| list of strings (`knowledge`, `rules`, `values`) | add/remove rows |
| `ref` (single or list) | searchable picker over existing entities, so a link can't point at nothing |
| `sub_fields` list (`plot_roles`, `value_turns`) | "Add entry" cards; sub-fields only exist once an entry is added |
| `computed` | read-only line with a short hint, e.g. "Set on the scene's plot roles" |
| body sections (`Personality`, `Arc`…) | text areas on their own tab |

**Overlay:** same shell and look as the Memory dialog, but wider. It has a header (type and name), two tabs (**Fields** | **Sections**), and a footer with Cancel, Save and a quiet Delete. A scene gets a third **Script** tab that hands off to the existing editor.

**Save flow:**
- *Create* saves directly, with no draft step.
- *Edit* shows a "review changes" step (field: before → after) before writing, with a hash check so an agent commit in between gives a clear "this changed since you opened it".
- *Delete* shows an impact list first (see below).

**Errors:** most problems are prevented by the controls themselves (selects, pickers, an auto-generated id with a live "already used" check). The rest come from a no-write `/check` endpoint, like the script editor's. Messages show next to the field, with a red dot on the tab that holds them, instead of the agent-style error text.

## Things I noticed that matter (I'll verify each in Phase 1)

1. **Deleting entities that scenes' `value_turns` name** (plots, values) isn't scrubbed, so those scenes can end up with dangling references. I plan a dependency scan: show where it's used, and block the delete when it can't be cleaned safely.
2. **Deleting a character** looks like it leaves their relationship as a one-sided entity.
3. **The "Project updated / Refresh" banner** would fire on our own saves. I'll suppress it and refresh in place.
4. **`DASH.normalise` is lossy**, so the form loads raw stored values from a new endpoint instead of reading from `DASH.story`.
5. **A value's id must equal the slug of its name**, so a value's name gets locked after creation.

## Proposed phases

1. **Foundation plus vertical slice:** the form spec, the API (load, check, create, edit, delete preview and delete), the overlay and the tests. Character, location, world and value come first, since they're mostly flat fields, lists and pickers.
2. **Plot, relationship and project settings:** ref lists and keyed perspectives, plus "+ New…" inside pickers so you can create a missing location or character mid-form.
3. **Structure:** act, sequence and scene metadata with the script hand-off, then the nested editors (`value_turns`, `scene_beats`).
4. **Polish:** an undo toast via `restore`, plus a hidden note in chat so the agent knows you edited something by hand.

## Questions

**1. Scene cast, location, time of day and heading.** The script editor writes these together with the script text, so the heading line and the fields can never disagree. I recommend showing them read-only in the form with "Edit in script editor", and editing everything else on the scene (title, status, objective, plot roles) in the form. The alternative is to make them editable in both places, which risks drift. Which do you prefer? (APPROVED)

**2. Deleting a character:** should their relationship entities be removed too (my recommendation, since a relationship with one person is meaningless), or kept as a half-relationship? (APPROVED)

**3. Phase 1 scope:** are you happy to start with character, location, world and value, or is there a type you'd rather see first? (APPROVED)
