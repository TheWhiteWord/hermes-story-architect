# Character relationship

*The bond between two characters, and each of their separate views of it.*

A relationship is one record seen from two sides. It is not a property of
either character alone, and the two views are allowed to disagree — that
disagreement is usually the interesting part. → `theory/character-and-arc.md`

## Requisites

**Two existing characters**, and exactly two — `characters` is required and
anything other than a pair is a validation warning. Both must exist, and
confirm they do: a slug that names nobody is not refused, it is committed, and
the bond points at a character that is not there.

## Deciding it

**`name`** — the label for the bond, the two of them together. How the user
finds it in a list.

**`characters`** — the pair. Order carries no meaning here; which of the two
is first is not a claim about anything.

**`perspectives` — the substance, and the only part that must be decided
field by field.** It is a view per character, and **both are required**: a
missing one is a validation warning, so a relationship with one side written
and the other empty is not a finished record. Each holds:

- **`label`** — what *this* character calls the other. Not the shared truth;
  their word for it.
- **`feeling`** — their emotional stance toward the bond.
- **`type`** — how this character reads it: ally, enemy, family, romantic,
  professional, mentor, rival, custom, neutral. Free text, not a closed set —
  it is their description, so "the only one who tells me the truth" is a
  legitimate value and no enum survives the next project.
- **`strength`** — signed, `-1.0` to `1.0`, and out of range is a warning.
  Negative is antagonism. It is a position on a signed scale, not an
  intensity from zero: read it as opposition or as bond, and an antagonistic
  pair must be allowed to go negative.
- **`secret`** — whether this character is hiding the bond from the other. It
  is the only field here that records an asymmetry of *knowledge* rather than
  of feeling, which is what makes it the one that generates scenes: someone
  has to find out. A bond with two perspectives that disagree is a bond they
  read differently; a bond with a secret is a bond where one of them is
  wrong about what the other knows.

**The two views are decided against each other.** Write one, then the other,
with the question being where they part: the mentor who reads the bond as
trust and the apprentice who reads it as surveillance are one record, not two
inconsistent ones. A perspective identical to the other is a sign the second
one was filled rather than considered.

**`scenes`** — where this bond is on stage. The scenes it is featured in, not
every scene both characters are in.

**`status`** — active, resolved, or complex. `complex` is the one that says
the bond is unresolved in a way the story is using.

**`history`** — how it got here. What made it this.

**The sections** — `Nature`, `Perspectives`, `Tension`, `History`, `Scenes
to Write`, `Notes`. The same bond in prose. The reasoning belongs here, not in
the fields restated.

## The couplings

- **`perspectives` is keyed by character slug, and both keys are required.**
  A perspective under a slug that is not one of the two characters is not
  checked against `characters` and is not what anyone reads — the reads go
  through the two characters. → `character.md`

- **`strength` exists on both sides and is a signed scale, so the two are
  read as one bond's tension from two ends.** Two characters at `+0.9` are
  not necessarily close; a `+0.9` and a `-0.4` can be the same bond described
  by a character who is being flattered and one who is not.

- **The bond is read on the characters, and it is written here.** Each
  character's `relationships` is computed from these records, with `with`
  naming *the other* character. A character on one side only is a bond the
  other has not been told about yet, in the store and in the story alike. →
  `character.md`

- **The same pair may hold more than one bond, and nothing objects.** A
  professional history and a personal one are two records, and both appear on
  both characters, stacked. Only the user can say whether that is what they
  meant — so before writing a bond, check whether one already exists for the
  pair, and put the question to them rather than choosing.
