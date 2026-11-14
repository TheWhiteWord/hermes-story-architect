# Screenplay format

*Schematic draft — headings and notes only.*

A scene's `Content` is **Fountain** — a screenplay, not prose about one. This
file is what the format requires, and what happens when it is not followed.

The worked examples are in `samples/`, read when the shape is wanted rather
than the rule. → `references/craft/scene-design.md` for what the section is *for*.

---

## The one rule

**A character's name is on its own line, in capitals. Their dialogue is on the
lines beneath it.**

    ELIAS: You could have telephoned.

is not a stylistic choice and is not a near miss. It is **a wall of prose to the
renderer**, and nothing reports it. That is the whole reason this file exists:
the heading is enforced, and this one is not.

## What is enforced, and what is not

*One rule is enforced. Know which, because the rest is on the author.*

- **Enforced: a scene with a script has a heading.** The heading is not written
  into `Content` — it is composed from the scene's fields (`int_ext`,
  `location`, `place`, `time_of_day`, or `forced_heading`). A write carrying
  Content with no heading is refused before anything is stored.
- **Not enforced: anything else.** Not the cues, not the dialogue, not the
  parentheticals, not the transitions. The boundary exists to catch one
  disappearance, not to police the format.
- So a heading is necessary and not sufficient. **Everything past the heading
  fields is the author's responsibility**, and the only way to know it is right
  is to know the format.

## The shape

*The elements a scene uses, and what each looks like.*

- **Scene heading** — composed, never written. `INT. ARCHIVE - DAY`, or `EXT.`
  for outside. The location segment is the linked location's name; a `place`
  sits between it and the time. A scene with no inside or outside sets
  `forced_heading` instead — `.SNIPER SCOPE POV` — and leaves the composed
  fields empty.
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

*Three failure modes, verified. Only one is silent.*

**1. An inline cue — silent, and the expensive one.**
`ELIAS: You could have telephoned.` on one line lexes as a single block of
action. There is no dialogue token at all. The dashboard renders a paragraph
where a conversation should be, and **nothing reports it**, because the
heading was there. This is the one that looks like a working dashboard while
being wrong.

**2. No heading — refused at write, and worse when it is not.**
A scene with Content and no heading fields is refused before it is stored. An
imported note is not refused, and its consequence is the one to know: the
dashboard **concatenates every scene and lexes the result as one document**, so
a scene without a heading does not vanish — its text flows into the *previous*
scene as action and dialogue. Verified: three scenes, one of them headed,
produce **one** scene heading in the script. So the visible effect is a scene
that has merged into its neighbour rather than one that is missing.

**3. A heading line in `Content` — stripped, not duplicated.**
The boundary requires the heading fields when Content is non-empty, then strips
a leading heading line from the body. So a heading typed into `Content` is
discarded, and the script shows the composed line — which may not be the one
that was typed. Not an error, but a silent substitution.

## Which heading is read

*One heading exists, and it is composed.*

- **The heading line is composed from the scene's fields** — `int_ext`,
  `location`, `place`, `time_of_day` — at assembly, above the body. The
  location segment is the linked location's `name`, not its slug.
- **`Content` is body-only.** It never holds a heading line, and a leading one
  is stripped on write.
- **`forced_heading` replaces the composed heading outright**, verbatim, and is
  exclusive with `int_ext`, `place` and `time_of_day`. `location` may still be
  set — it is an entity link, not heading text.
- A scene with Content but no heading fields contributes its body alone, so an
  imported note whose heading could not be parsed still renders — merged into
  the previous scene rather than missing.

## Before staging a scene

- [ ] The scene has a heading: `int_ext` + `location`, or `forced_heading`. A
      write with Content and neither is refused.
- [ ] **Every cue is on its own line**, with dialogue beneath it. This is the
      one nothing checks.
- [ ] Character names match characters that exist, so the script links them.
- [ ] A planned scene needs no heading — the boundary asks for one only when
      Content is written.
- → `references/mechanics/screenplay-format/samples/scene-content-good.md` and `references/mechanics/screenplay-format/samples/scene-content-broken.md`

---

## Open questions

- [ ] Should anything check cues? The heading is enforced and the inline cue is
      the expensive failure. Extending the check is a code change, and a false
      positive on a legitimate ALL CAPS action line would make it worse rather
      than better.
