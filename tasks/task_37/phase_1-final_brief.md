# PHASE 1 charcters, locations, worlds, values

Phase 1 is done: you can create, edit and delete characters, locations, worlds and values by hand from the UI. I ran it in a real browser against a throwaway project and checked each flow below. The patch applies cleanly to a fresh clone of `dev`, and the 115 tests I ran from the new and neighbouring test files pass there. Apply it with `git apply phase1-entity-form.patch`. The three preview images are screenshots from that run.

## What you get

- **Entry points:** a "+ New" button in the Character web, Locations and Worlds headers. An "Edit" button appears in the detail panel for characters, locations and worlds, wherever they were opened from.
- **Values** have no list or panel in the app today, so I added an "Edit values ▾" menu to the Values view header.
- **Overlay:** it uses the Memory dialog's look, with a **Fields** tab and a **Sections** tab for the prose.
- **Relational fields:** pickers list only entities that exist, so a link can't point at nothing.
- **Derived fields:** a character's relationships appear read-only, with a note saying where to edit them.
- **Confirmation:**
  - Create saves directly, and the overlay previews the id (`id: zion`) as you type.
  - Edit goes through a before/after review step first.
  - Delete lists everything it will affect.
- **Errors:** messages appear beside the field, and only for fields you've touched or after you press save. For example, "Each rung needs its own word."
- **Edits during an agent commit:** if the agent changes the entity while the form is open, you get "Apply my edits on top of the latest". It keeps your changes and the agent's untouched fields. I tested this with the agent editing mid-form, and the agent's edit survived.
- **After saving:** the app refreshes in place and the "Project updated" banner stays quiet, using the mechanism the script editor already had.

## Architecture

- The server turns `ENTITY_SCHEMAS` into a form description, and one JS file draws every type.
- A field added to the schema later shows up in the form without touching the JS.
- All writes go through `core/writes.py`, the same path the agent uses.
- The new backend code is in `core/manual_entities.py` and `app/routes/entities.py`.

## Decisions to know about

1. **Deleting a character** also removes their relationship entities, as you asked. I did this in the form only, because `test_delete_cascade.py` pins the agent path to keep the surviving half. Say so if you want the agent to behave the same way.
2. **Some deletes are blocked.** If a character or value is still named in a scene's beats or value turns, the delete is refused and the dialog says which scenes to fix first. The agent's delete leaves those references dangling, which breaks the next edit of that scene. So with your demo data, deleting Kael will be blocked until his beats are cleaned up.
3. **A world's delete takes its locations with it.** That's existing behaviour, but the dialog now says so before you confirm.
4. **Only the name is required.** The schema marks more fields as required, but the write path doesn't enforce them, so a quick character with just a name is allowed.
5. **A value's name is locked after creation.** Scenes refer to values by name, so it can't be renamed.
6. **A deleted value's id stays reserved.** Recreating it gives a clear message rather than a cryptic error.
