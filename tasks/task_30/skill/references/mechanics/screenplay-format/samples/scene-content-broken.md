# Scene content — the ways it fails

*Sample. Read when the shape is wanted rather than the rule.*

The same material written three ways that do not render, and what each one
becomes. Every case here was run through the write path and the lexer; the
outcomes are observed, not predicted.

The rule this illustrates is in `../screenplay-format.md`.

---

## 1. The inline cue — the silent one

ELIAS: You could have telephoned.

**What happens.** One block of action. No dialogue token, no character token —
the line was never a cue, it was a sentence with a colon in it.

**Nothing says anything.** The heading is present and present is all the
boundary checks. This is the failure that looks like a working dashboard: a
paragraph where a conversation should be, and no finding anywhere.

---

## 2. No heading fields — refused, or merged

Mira does not answer.

MIRA
I said no.

**What happens.** A write with Content and no heading fields is refused before
anything is stored. An imported note is not refused, and it does not vanish
either: the dashboard concatenates every scene and lexes the result as one
document, so this text flows into the *previous* scene as action and dialogue.
The visible effect is a scene that has merged into its neighbour, not one that
is missing — which is why it is worth reading the script rather than trusting
the entity list.

---

## 3. A heading line in `Content` — stripped

INT. WATER ARCHIVE - BASEMENT - DAY

Kael waits. He is not alone.

**What happens.** The boundary requires the heading fields when Content is
non-empty, then strips a leading heading line from the body. The typed line is
gone — not an error, but a silent substitution. If the fields say something
else, the script shows the fields' line.

---

## The three, side by side

| Written | Caught | In the script |
|---|---|---|
| inline cue | **silent** | a paragraph where a conversation should be |
| no heading fields | refused at write | merged into the previous scene (imported) |
| heading line in `Content` | stripped | the fields' heading, not the typed one |

Only the first is invisible. The other two are caught, and neither costs the
scene — but the third means the heading the author typed is not the heading the
script shows.
