# Relationships

*Schematic draft — headings and notes only.*

The entity that lives **between** two characters. It is not a field on a
character and it is not edited through one: it is its own record, with two
people on it, and it is the only place a bond can be written down.

The field names are in `story_describe`.

---

## It belongs to two, and that is checked only softly

*Read this before staging: the rule that looks enforced is not.*

- `characters` should hold **exactly two slugs**, and a warning is raised if it
  does not. But it is a **warning, not a refusal** — verified: a relationship
  with three characters **stages, warns, and commits.** The write lands.
- **A character slug that does not exist is not checked at all.** Verified: a
  relationship naming a character who was never created stages, warns only
  about the missing *perspectives*, commits, and appears in the relationship
  view carrying a slug that resolves to nothing.
- **On edit it is completely silent.** Verified: changing the characters of an
  existing relationship to a non-existent slug produces **no warning at all**,
  commits, and leaves a bond pointing at nobody. So a bond cannot be quietly
  broken by editing it, and the character view is the place a broken link shows
  up.
- The same two characters may have **more than one relationship** between them,
  with nothing objecting. A professional history and a personal one are two
  records, and only the user can say whether that is what they meant.

### What the warnings are

- Raised on stage, in the draft's own validation output, and they do not stop
  the commit:
  - a character count that is not two;
  - a character on the relationship with no perspective.
- **So the discipline is the agent's: read the validation before asking the
  user to confirm, and fix a finding rather than reporting past it.** Nothing
  downstream will raise it again.

## The two sides are written separately

*The centre of the file. This is not one description of a bond.*

- **`perspectives` is a dict keyed by character slug** — one entry per person,
  each holding that person's own view: a label for the bond, how they feel about
  it, a type, a strength, and whether they are hiding it.
- **The two entries are meant to disagree.** A relationship where both sides
  read the same is usually a relationship that has not been thought about from
  both ends. The interesting content is the gap: what Kael believes the bond is,
  and what Mira knows it to be.
- **Verified asymmetry, and it is the shape to aim for:** one side
  `professional / +0.6 / not secret`, the other `rival / -0.5 / secret`. Same
  two people, opposite readings, and one of them concealing it. That is a
  relationship with something in it.
- **`strength` runs −1.0 to +1.0** and is the signed tension between them —
  negative is antagonism. It is range-checked, and it is optional: a side
  without one comes back empty rather than wrong.
- **A missing side is visible, not fatal.** A one-sided relationship commits,
  warns about the absent character, and shows up in the relationship view as a
  shorter list. The view does not distinguish "not written yet" from "not
  applicable" — so a half-written perspective reads as half-written, which is
  accurate.

## `secret` is the field that carries the subtext

*Why the flag exists at all.*

- `secret` marks that **one of them knows something the other does not.** It is
  the only field on this entity that records an asymmetry of *knowledge* rather
  than of feeling.
- So a relationship with a secret and a relationship with conflicting
  perspectives are different things, and the secret is the one that generates
  scenes: someone has to find out.
- This is the field that makes the entity worth having rather than a note about
  who knows whom. Everything else describes the bond; this describes the
  pressure in it.

## Not on the character

*Stated once, because it is the most common wrong turn.*

- **`character.relationships` is computed and read-only.** It is a summary built
  from these entities, and writing to it is refused.
- So a bond is never added, edited or removed through a character. It is created
  and edited as its own record, and the character picks it up.
- → `character-and-arc.md`

## Reading a relationship back

- `story_load(view="relationship")` returns every relationship with its
  characters, its scenes and its perspectives as a list keyed by character.
- That view is where a one-sided relationship shows as a short list, and where
  two records between the same pair are visible side by side — both worth
  looking at before writing a new one.

---

## Open questions

- [ ] The two-character rule warns but does not refuse, and neither does the
      existence of the characters. Should the file argue for a hard check, or
      record it as a deliberate looseness? A loose rule with a clear warning may
      be the right design for a triangle.
- [ ] The same pair may have several relationships. Worth saying when to make a
      second one rather than extending the first, or is that the user's call
      every time?
