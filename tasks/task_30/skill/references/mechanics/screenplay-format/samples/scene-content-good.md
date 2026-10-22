# Scene content — a good example

*Sample. Read when the shape is wanted rather than the rule.*

A scene `Content` that renders. Verified against the lexer: one scene heading,
and the exchange produces a cue and a dialogue token rather than a paragraph.

The rule this illustrates is in `../screenplay-format.md`.

---

## The example

INT. WATER ARCHIVE - BASEMENT - DAY

Fluorescent tubes. Ranks of grey shelving disappear into the dark. Water finds
its way down one wall in a thin steady thread.

KAEL
(without looking up)
You're late.

MIRA
The filing's wrong. Not late — wrong.

Kael closes the drawer. The thread of water has reached the floor.

KAEL
Then fix it.

MIRA
(she's said this before, and it has never worked)
I did. That's why I'm telling you.

Kael looks at her for the first time. She has a folder under her arm and she is
holding it like it has weight.

KAEL
Put it down.

---

## What each part is doing

- **The heading** opens the scene: `INT.` inside, the location, the time. It is
  the first non-blank line, which is the one thing the lint checks.
- **Action** is flush left and says what the camera sees. The water is doing
  work here — it is the image the scene will be remembered by.
- **Cues** are the name alone, capitals, on their own line. Every one of them
  in this example is on its own line, which is the rule nothing checks.
- **Dialogue** sits beneath its cue, indented.
- **Parentheticals** are bracketed, under the cue, and short. They carry delivery
  — `(without looking up)`, `(she's said this before...)` — rather than
  information the audience cannot hear.
- **No transition** here, because the scene does not end on a cut. One would be
  flush right and end in a colon if it did.

## The result

Verified by running the example through the lexer: **one scene heading, five
character cues, five dialogue blocks, two parentheticals, and no lint
finding.** Every name is on its own line in capitals, which is the part nothing
checks and the part that decides whether this reads as a scene.

Whether a cue then *links* to a character entity is the script view's matching
rather than the lexer's, and it depends on the name matching a character that
exists — which is a reason to spell a character's name the same way in every
scene.
