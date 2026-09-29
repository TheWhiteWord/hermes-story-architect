# Screenplay format

*Schematic draft — headings and notes only.*

A scene's `Content` is **Fountain** — a screenplay, not prose about one. This
file is what the format requires, and what happens when it is not followed.

The worked examples are in `samples/`, read when the shape is wanted rather
than the rule. → `scene-design.md` for what the section is *for*.

---

## The one rule

**A character's name is on its own line, in capitals. Their dialogue is on the
lines beneath it.**

    ELIAS: You could have telephoned.

is not a stylistic choice and is not a near miss. It is **a wall of prose to the
renderer**, and nothing reports it. That is the whole reason this file exists:
every other format error is caught, and this one is not.

## What is checked, and what is not

*One rule is enforced. Know which, because the rest is on the author.*

- **Checked: the first non-blank line of `Content` is a scene heading.** The
  draft's validation reports it as a finding, naming the line it found instead.
- **Not checked: anything else.** Not the cues, not the dialogue, not the
  parentheticals, not the transitions. The lint exists to catch one
  disappearance, not to police the format.
- So a well-formed opening is necessary and not sufficient. **Everything past
  the first line is the author's responsibility**, and the only way to know it is
  right is to know the format.

## The shape

*The elements a scene uses, and what each looks like.*

- **Scene heading** — opens the scene. `INT. ARCHIVE - DAY`, or `EXT.` for
  outside. A forced heading, `.SNIPER SCOPE POV`, is a legitimate heading and is
  accepted for a location that has no inside or outside.
- **Action** — anything that is not a cue or dialogue. Set flush left.
- **Character cue** — the name alone on a line, capitals. The name must match a
  character for the script to link them; an unknown name still renders.
- **Dialogue** — beneath the cue, indented.
- **Parenthetical** — a line in brackets under the cue, for delivery.
- **Transition** — flush right, ending in a colon: `CUT TO:`. Used to close a
  scene and open the next.
- *Not in this file:* the full grammar, including centred text, emphasis, lyrics
  and notes. A scene does not usually need them, and the examples show the shape
  that matters.

## What actually goes wrong, and what it looks like

*Three failure modes, verified. Only one is caught.*

**1. An inline cue — silent, and the expensive one.**
`ELIAS: You could have telephoned.` on one line lexes as a single block of
action. There is no dialogue token at all. The dashboard renders a paragraph
where a conversation should be, and **the lint says nothing**, because the
heading was there. This is the one that looks like a working dashboard while
being wrong.

**2. No heading at all — caught, and worse than it looks.**
The lint names it. But the consequence differs by where the text goes: the
dashboard **concatenates every scene and lexes the result as one document**, so a
scene without a heading does not vanish — its text flows into the *previous*
scene as action and dialogue. Verified: three scenes, one of them correct,
produce **one** scene heading in the script. So the visible effect is a scene
that has merged into its neighbour rather than one that is missing.

**3. Text before the heading — caught, and the message overstates it.**
The lint says everything before the heading is "dropped from the script". It is
not: the text is rendered, above the heading it should have come after. The
error is real and visible; the consequence described is not the one that happens.
Worth knowing so the finding is not dismissed as cosmetic — the prose is in the
wrong place, which is a layout error the user will see.

## Which heading is read

*Two headings exist on a scene, and only one of them is the script.*

- **The first line of the `Content` section** is what the script renders. The
  script view is built from the lexed text of the concatenated scenes, and the
  scene heading it draws comes from the token, not from a field.
- **The `heading` field** is metadata for the user's own organisation — it shows
  in the scene list and is searchable. It is not the screenplay.
- They can disagree and nothing checks it. → `scene-design.md`

## Before staging a scene

- [ ] The first non-blank line is a scene heading.
- [ ] **Every cue is on its own line**, with dialogue beneath it. This is the
      one nothing checks.
- [ ] Character names match characters that exist, so the script links them.
- [ ] A scene that is not a new heading does not need one — the flow is the
      user's call, but a scene entity whose text merges into its neighbour is
      almost never what was meant.
- → `samples/scene-content-good.md` and `samples/scene-content-broken.md`

---

## Open questions

- [ ] The lint's message for "text before the heading" describes text being
      dropped when it is rendered. Small, but it is a message the agent will
      relay to the user, so it is worth correcting — deferred work, or a fix
      here?
- [ ] Should the lint check cues? It is one rule today and the inline cue is the
      expensive failure. Extending it is a code change, and a false positive on a
      legitimate ALL CAPS action line would make it worse rather than better.
