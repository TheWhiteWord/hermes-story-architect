# Arc beats

*Schematic draft — headings and notes only.*

The chain that makes up one character's arc. A beat is a moment where the
character acts, something disconfirms what they expected, they choose, and their
value moves.

The field names are in `story_describe`. What a beat is in general is not here.

---

## What a beat is anchored to

*Three things are required, and two of them are checked.*

- **A character** and **a scene** are required, and **both must exist** — the
  write path refuses a beat pointing at a character or a scene that is not
  there, naming the missing one. **[checked]**
- **So a beat cannot be written before the scene it happens in.** That is a real
  ordering constraint, not a formality: the beat lives in the scene, so the
  scene comes first. A character with an arc designed in the abstract has
  nowhere to put the beats yet.
- **A label is required** — the human-readable name of the beat, which is what
  appears on the arc graph. "First Doubt", not "beat 1".
- **`order` auto-numbers.** It does not have to be supplied, and the next
  position is worked out. It is still the field that makes an arc a chain
  rather than an unordered set, because it is what the curve is drawn against.
- The id is whatever slug the caller passes. Nothing constrains its shape, but
  reading a beat back by its bare name works — retrieval falls back to a suffix
  match — so a hyphenated id like `mara-first-doubt` is the least surprising
  choice.

## The four parts

*The beat's own content, in the order they happen.*

- **Action** — what the character does. Their move.
- **The Gap** — what happens that disconfirms it. The expectation and the
  reality, and the distance between them. This is the part that makes a beat
  more than an event: an action that goes as planned is not a beat.
- **Choice** — what they do about it. The part that reveals them, because it is
  chosen rather than reflex.
- **Value Shift** — how their value moves as a result, in their own language.
- **Each of the four exists twice** — as a field and as a section of the same
  name. That is not a duplication to resolve: the field is the fact every other
  reader uses, and the section is the thinking behind it. A beat can be written
  either way round, and often only one of them is worth writing yet. →
  `entity-sections.md`
- **A beat with an action but no gap is an event.** That is the practical test,
  and it is the one worth applying before staging.

## The charge, and where the arc lands

*How a beat connects to the character's value track.*

- Each beat carries **its own** charge entering and leaving, plus a `shift` and
  a `y`. None of it is inherited from the character — the character states the
  promise, the beats are the path, and every beat charges its own movement.
- → `value-system.md` for the charge words, how to read a shift, and where `y`
  should land.
- **The character and the story are read on separate tracks.** A beat is always
  on the *character's* value, whatever the story's is. That is the second track,
  and it is not a mismatch. → `value-system.md`
- **Nothing checks that the beats deliver the character's promise.** A character
  whose arc is stated as going one way and whose beats go another is not an
  error anywhere — it is information, and it means the design needs adjusting.
  That is a judgement made by reading the beats in order, not a check a tool
  performs.

## Crisis and climax

*Two flags, and they are about the beat rather than the arc.*

- **`is_crisis`** marks the beat where the character's position is most
  seriously tested. **`is_climax`** marks the one that resolves it.
- **A character can have neither.** A supporting character with a small change
  is not missing a climax; the flags mark the beats that carry one, and a beat
  without them is an ordinary step.
- **The flags are read** — by the arc view and by the arc graph, where a crisis
  beat is drawn differently. So an unmarked crisis is a beat the graph will not
  show as one.
- *Not the same as the scene's own flags:* a scene can be a story climax while
  no beat in it is a character climax. They are different claims at different
  levels. → `scene-design.md`

## Writing a chain

*The practical order, which is not the order of the fields.*

- [ ] The character exists. → `character-and-arc.md`
- [ ] The scenes the beats happen in exist. **This is the constraint** — a beat
  cannot be staged before its scene.
- [ ] The first beat: an action, and the gap that disconfirms it.
- [ ] Each subsequent beat follows from the last. The chain is the point; a set
      of unrelated moments is a list with numbers.
- [ ] The charge moves on each one that turns. A beat that changes nothing is a
      rest, and that is allowed — it should be a choice, not an oversight.
- [ ] The crisis and climax beats flagged, if the arc has them.
- [ ] Read the beats in order against the character's stated start and end. If
      they do not arrive, the design is wrong — not the data.

---

## Open questions

- [ ] Four of five sections shadow a field of the same meaning. The file says
      that is the arrangement working rather than a duplication to resolve. Is
      that the right call, or should one of them be retired?
- [ ] The order constraint — a beat cannot exist before its scene — is enforced
      but unstated anywhere in the plugin's own documentation. Worth flagging as
      a code issue alongside the deferred work?
