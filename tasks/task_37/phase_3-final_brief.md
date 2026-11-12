# PHASE 3 scenes, sequences, acts

The attached `phase3-structure-and-reorder.patch` is built against your current `dev`, including your PWA and idle-exit commits. Apply it with `git apply phase3-structure-and-reorder.patch`.

I checked it on a pristine clone of `dev`: it applies cleanly, 188 tests pass, and a browser run of Reorder and the new-scene form showed no console errors. Earlier in this phase I also ran the Phase 1 and 2 flows again and found no regressions. The full suite has 1,306 passing plus the same existing failure as before (`test_no_hermes_imports`).

## What's in it

**Forms for acts, sequences and scenes.** There's a "+ New ▾" menu in the Scenes header (scene, sequence, act), and an Edit button in each panel.
- **Position:** you choose it once, when you create the item, with the picker labelled "Act One › Wakes". After that it's locked, and the form points you to Reorder. A new scene also takes its act from its sequence automatically.
- **Scene fields:** title, status, one-sentence summary, objective, dramatic role and plot roles. Plot roles are a stack of cards (plot, role, what happens) that you add and remove.
- **Sections tab:** all sections except the script itself.
- **Script tab:** shows the heading, location, time of day and cast read-only, with "Edit in script editor →". If you have unsaved edits it asks before leaving. The form never writes any of these four fields or the script text, and a test checks that.
- **Derived fields:** turning point, beats record and value turns appear read-only.

**Reorder**, a button next to "+ New".
- **Moving:** you can drag, use ↑ ↓, or use "Move to…". Scenes move within or across sequences, sequences move within or across acts and carry their scenes along, and acts reorder.
- **Review before saving:** nothing is written until you read a list in plain words, such as "Move scene 'The Door Opens' from Act One › The Door · 1 to Act Two › Aftermath · 2". It lists only what you moved, not the items that shifted around it.
- **Consistency:** a scene's act is updated whenever its sequence moves, which the agent's edit doesn't do on its own. A test checks that all three (parent, order, act) agree afterwards.
- **If the story changes meanwhile:** if the agent changes the structure while Reorder is open, you get "The story changed" with a Reload button instead of a silent clobber.

**Delete is safer.** A sequence with scenes, or an act with sequences, can't be deleted and the dialog says why and how to fix it. Deleting a scene tells you "Its script (N characters) is deleted with it."

## Changes to existing behaviour

1. **The Scenes tab now shows empty sequences and acts** ("No scenes yet"), unless you're filtering. Without this, a sequence you just created would look as if it had vanished.
2. **A Phase 2 bug is fixed.** The "Review changes" step didn't use the same leniency for stored legacy values that saving does. So it could have refused an edit that saving would accept. My earlier tests called save directly and missed it. There's a test now.

## Not in this patch

`value_turns` and `scene_beats` stay read-only here ("Edited with the agent for now"). They need their own design, with pickers that know the value ladders and protagonists, and squeezing them in would have made this patch hard to review. I'd call that Phase 3b.

## Things to check on your real data

- ☐ On `save-the-children`, enter Reorder, move a scene to another act, and open "Review changes". Does the list read correctly?
- ☐ Apply it, then open that scene in the script editor. The script text and heading should be unchanged.
- ☐ Create a scene with a plot role, then open its Script tab and check the heading, location and cast show correctly.

## What's next

Phase 3b would be `value_turns` and `scene_beats`. After that is the polish list: the searchable picker with "+ New…" inside pickers, and an Undo toast. Do you want 3b next, or the polish list first?