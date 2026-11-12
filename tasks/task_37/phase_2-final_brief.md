# PHASE 2 plots, relationships, project

Phase 2 is done: plots, relationships and the project settings can now be created, edited and (except the project) deleted by hand. The patch applies on top of Phase 1 on a fresh clone of `dev`, and the new and neighbouring tests (149) pass there. I also re-ran your Phase 1 flows in the browser and found no regressions.

Apply it after Phase 1 with `git apply phase2-plot-relationship-project.patch`.

## What you get

- **Plots:**
  - "+ New" in the Plots header and an Edit button in the plot panel.
  - The protagonists come from a character picker.
  - "Kind of subplot" appears only when the scope is *sub*. It is reset when you save a main plot, so a stale value can't linger.
  - The scene roles (Setups, Inciting incident, Crisis and so on) show read-only under "derived", with a note that they're set on a scene's plot roles. Empty ones collapse into one "Not used yet" line.
- **Relationships:**
  - You pick two different characters, and the name fills in as "Kael & Mira" until you type your own.
  - Once a character is picked, a card appears: "How Kael sees Mira" with label, feeling, kind, strength and a hidden toggle.
  - Swapping a character re-keys the cards and keeps the one that stayed.
  - A strength of 5 gives "Strength is a number from −1 (hostile) to 1 (devoted)."
- **Project:** an "Edit project" button in the Story header, with the title-page fields grouped. The project can't be created or deleted here. Lowering the act count below your existing acts warns that the count will stay at your existing acts. Renaming shows up in the header immediately.
- **Delete:**
  - A plot's delete preview lists the scenes that lose their role.
  - It is refused while a scene's value turns still name that plot, with the scene named, matching the Phase 1 rule.
  - Deleting a character now also shows "No longer a protagonist of 1 plot".

## Two bugs the browser run caught

- The form focuses the Name field on open, so tabbing away counted as "typed a name" and switched off the auto-name. It now tracks actual typing.
- After a step change focus fell onto the page behind, and Esc stopped working. Esc now works from anywhere, and focus returns into the dialog.

## Decisions to know about

1. A relationship between the same two characters that already has one is a **warning**, not an error. You can have a second one, and the form says so.
2. Warnings now always show. Errors still wait until you've touched a field or pressed save.
3. A value already stored that isn't in a dropdown's list no longer blocks an unrelated edit. The form only holds you to what you changed.
4. The perspective "Kind" options (ally, enemy, family and so on) come from the schema's description text, since nothing enforces them. A stored kind outside the list is kept.
