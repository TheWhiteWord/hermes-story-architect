# Scene content — the ways it fails

*Sample. Read when the shape is wanted rather than the rule.*

The same material written three ways that do not render, and what each one
becomes. Every case here was run through the lexer and the lint; the outcomes
are observed, not predicted.

The rule this illustrates is in `../screenplay-format.md`.

---

## 1. The inline cue — the silent one

ELIAS: You could have telephoned.

**What happens.** One block of action. No dialogue token, no character token —
the line was never a cue, it was a sentence with a colon in it.

**The lint says nothing.** The heading is present and present is all it checks.
This is the failure that looks like a working dashboard: a paragraph where a
conversation should be, and no finding anywhere.

---

## 2. No heading

Mira does not answer.

MIRA
I said no.

**What happens.** The lint catches it and names the first line.

**But it does not vanish from the script.** The dashboard concatenates every
scene and lexes the result as one document, so this text flows into the
*previous* scene as action and dialogue. The visible effect is a scene that has
merged into its neighbour, not a scene that is missing — which is why it is
worth reading the script rather than trusting the entity list.

---

## 3. Text before the heading

Kael waits. He is not alone.

INT. WATER ARCHIVE - BASEMENT - DAY

KAEL
You're late.

**What happens.** The lint catches it. Its message says the text before the
heading is "dropped from the script" — **it is not.** The text is rendered,
above the heading it should have followed.

**So the finding is real and the reason is wrong.** The prose is in the wrong
place, which the user will see on the page. Do not dismiss it as cosmetic
because of how the message describes it, and do not repeat the "dropped" part
back to the user.

---

## The three, side by side

| Written | Lint | In the script |
|---|---|---|
| inline cue | **silent** | a paragraph where a conversation should be |
| no heading | warns | merged into the previous scene |
| text first | warns | rendered above the heading |

Only the first is invisible. The other two are caught, and the real consequence
of each is different from what the message says.
