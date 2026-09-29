# Character and arc

*Schematic draft — headings and notes only.*

Building a character: who they are, what they want, what does not add up, and
where they end up different. Enough to know when an arc or a relationship needs
writing, and no more — **both are separate entities with their own files beside
this one.**

The field names are in `story_describe`. The theory of character is not here.

---

## The minimum a character needs

*Three fields are required; everything else can wait.*

- `name`, `story_role` and `one_sentence`. That is the whole requirement, and
  it is deliberately small: **a character the user has a feeling about should be
  creatable before there is a character.**
- `one_sentence` is not decoration — it is the label the character appears under
  everywhere, in the load, in the dashboard, in a list. It is the difference
  between "Mara" and "the archivist who stopped reading".
- `story_role` is a role in the story's shape — Protagonist, Antagonist,
  Supporting, Minor, Cameo. **Nothing enforces how many of each**: two
  protagonists is accepted without complaint. So the role is the user's
  bookkeeping, and a story with two protagonists has a decision to make that no
  tool will raise.
- **A character with a role and a sentence but nothing else is a legitimate
  state.** It is someone the user knows they want and has not worked out yet.

## What a character is for

*The working parts, in the order they usually become answerable.*

- **Desire** — what they want, and what they want underneath that. Two fields:
  the immediate one and the story-long one. A character with only the long-term
  goal is someone who knows where they are going; only the short one is someone
  who knows what they want tonight.
- **Contradiction** — what does not add up in them. This is the depth, and it is
  the thing that makes a character more than a want with a name.
- **Knowledge** — the facts they know. This is the character's own half of
  continuity: a fact here is a fact *they* hold, and someone else acting on it
  is a scene. A fact nobody knows belongs on a world or a plot instead.
- **Voice** — how they speak. There is no field for it at all, so the section is
  the only place it can live, and nothing reads it but the person writing.

### A trap in the goals fields

- The two goal fields describe themselves as accepting a nested form as well as
  a flat one. **It does not.** Verified: a character created with
  `goals: {short, ..., long: ...}` succeeds, raises nothing, and stores neither
  — the values are dropped before the write, and the character reads as someone
  with no want at all.
- **Write the two fields flat.** The trap is recorded in
  `deferred-code-work.md`; until it is fixed, the schema description is the thing
  that is wrong, not the call.

## The arc: a promise, not a path

*What the character record holds about where they are going.*

- **The character states the value their arc explores, and the charge at each
  end.** That is the promise: where the arc begins and where it must arrive.
- **The path is not here.** The beats are separate entities, and this record
  deliberately holds no `shift` and no `y` — it is the destination, and the beats
  are the journey. → `arc-beats.md`
- **A character's value may differ from the story's, and that is not a
  mismatch.** It is the second track, and it is often the point: a protagonist
  whose arc runs on something other than the theme is doing something the theme
  alone cannot. → `value-system.md`
- `arc_type` records the *shape* of the change — positive, negative, flat,
  ironic, or **absent**. And `arc_complete` records whether the arc is finished.
  These are different claims and nothing reconciles them: **`absent` says there
  is no arc; `arc_complete: false` says there is one that has not landed.** A
  character meant to have no arc wants `absent`; one whose arc is unfinished
  wants a type and `false`.
- Nothing checks that the beats, if any, deliver the promise. That is a
  judgement made by reading them.

## Relationships are not a character field

*Named here only so it is not looked for here.*

- **`relationships` on a character is computed and read-only.** It is a summary
  built from the relationship entities, and writing to it is refused.
- So a bond is never edited through a character. It is its own entity, with two
  characters on it, and it is edited as one. → `relationships.md`
- This is also why the character record cannot be the home for a relationship:
  it does not have a field to hold it, and the one that looks like it does is
  derived.

## What to ask, and when

*The practical shape of the work.*

- A character with a name and a role is enough to create. Everything past that
  is a conversation, and the sections are where that conversation is written
  down. → `entity-sections.md`
- **Ask about desire before contradiction.** Contradiction is only visible once
  there is something to be in conflict *with*, and a contradiction stated before
  a desire is a contradiction about nothing in particular.
- **Ask about the arc's value late, if at all.** It is a reading of who they
  are, and it often only becomes answerable once the user has seen the character
  in a few scenes. An empty arc is a fine state.
- *Knowledge is the exception: it accumulates.* A fact learned in one scene is
  worth recording in the next, because it constrains what they can do. This is
  the one place where recording early beats recording late.

---

## Open questions

- [ ] The goals fields advertise a shape that silently loses data. The file
      carries the trap until the description is fixed — is that the right
      amount of prominence for a known bug?
- [ ] `arc_type: absent` and `arc_complete: false` are two ways to say an arc is
      unfinished, and nothing reconciles them. Worth a line here, or is that
      `arc-beats.md`'s business?
