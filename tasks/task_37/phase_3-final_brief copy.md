# PHASE 3b scene's value turns and beat sheet

Phase 3b is done: you can now edit a scene's value turns and its beat sheet in the scene overlay. The patch is attached (`phase3b-value-turns-and-beats.patch`), built against your current `dev`. Apply it with `git apply phase3b-value-turns-and-beats.patch`.

On a pristine clone of `dev` it applies cleanly and the 217 related tests pass. A browser run of the Phase 1–3 flows showed no regressions. I haven't re-run the full suite for this patch.

## What's in it

The scene overlay now has five tabs: **Fields · Sections · Value turns · Beats · Script**. A small badge on each tab shows how many turns or beats you have, and updates as you type.

**Value turns.** This is the part I designed around what a value turn actually is:
- **Pick, don't type.** Choosing a value shows its four words as a ladder (P, C, CD, NN). You click one word for "When the scene opens" and one for "When it closes", so a typo can't happen.
- **Protagonists come from the plot.** Choose the plot and its protagonists appear. You tick which levels the shift reaches (Inner, Personal, Extra-personal), and each ticked level opens a one-sentence input.
- **Sensible defaults.** A new turn starts on the scene's own plot if it has one. Changing the value clears words that no longer belong to it.
- **Nothing is silently dropped.** If you change the plot under effects you've already written, those effects stay visible, flagged "not a protagonist of this plot", with a remove button.

**Beats.** Driver, turning point, true-character moments, what changed by the end, and the ordered beats. Each beat has Action and Reaction columns (by, surface, subtext) plus a gap, and ↑ ↓ to reorder. The "by" and "what changed" pickers are grouped by type (characters, locations, worlds, relationships).

**One Save does it all.** The beats are a separate record behind the scenes (`<scene>-beats`), created on first use, but you never need to know that. Review changes lists only what changed, so a one-word fix to a long beat sheet shows as one line before and one line after, with "5 unchanged".

## Things I found and decided

1. **A stale value turn blocks every edit of its scene.** The write path re-checks a scene's stored turns on any edit. So a turn whose value was later deleted would block even an unrelated change, with an agent-style error. The form now checks turns on every save and says it plainly on the right card, e.g. "'x' isn't a defined value". Removing the turn unblocks the scene. This extends Phase 3's delete guard, which already refuses to delete a value or plot that turns still name.
2. **One Objective, not two.** The scene and its beats record both store an objective, and the dashboard shows the scene's if set, otherwise the record's. The form shows that same merged value once, on the Fields tab. The Beats tab leaves it out, so you never see two competing inputs.
3. **Partial-failure message.** The scene and the beats are two writes. If the second fails after the first succeeded, you get "The scene was saved, but the beats were not: …". I validate both first, so this should be rare.
4. **Conflict detection covers the beats.** If the agent edits the beats while your form is open, you get the same "changed since you opened it" flow with "Apply my edits on top of the latest".

## Not tested

- **Your real data:** I used a small seeded project, not `save-the-children`.
- **Long, messy scenes:** the form behaved well with a few turns and beats, but I haven't tried a scene with a dozen of each.

## Optional check for your assistant

- ☐ On `save-the-children`, open a scene that already has value turns and beats. Do they load and display correctly? Without editing, "Review changes" should be disabled.
- ☐ Change one word in one beat, then press **Review changes**. It should show one line before and one after.
- ☐ Send a screenshot of the Value turns tab for the scene with the most turns.

## What's next

The remaining list is the polish pass across all four phases: the searchable picker with "+ New…" inside pickers (useful now for plots, characters and values in these tabs), the Undo toast after deletes, and a general tidy. If you notice anything in your own testing, send it over and I'll fold it into that pass.