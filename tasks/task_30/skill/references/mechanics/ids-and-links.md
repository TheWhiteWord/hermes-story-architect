# Ids and links

*Schematic draft — headings and notes only.*

What an id is, what it may contain, and what happens to the things that point at
it. The last of those is the reason this file exists.

The field-by-field list is in `story_describe`.

---

## What an id may be

*Checked at stage, and refused rather than warned.*

- **Alphanumerics, hyphens and underscores.** Nothing else. A dot, a slash or a
  space is refused outright with `id must be alphanumeric with
  hyphens/underscores only` — a hard refusal, not a finding.
- **Case is allowed and preserved.** `Mara-Venn` and `mara-venn` are two
  different entities, which is a trap rather than a convenience.
- **Length is not limited.** An eighty-character id is accepted.
- **Ids are global across every type.** A scene cannot reuse a character's id,
  and the refusal says so: *"Entity ids are unique across all types — choose a
  different one."* That is a good error message, and it is worth knowing before
  inventing a slug that collides.
- So the id is the entity's name in the system, and **it is chosen once, at
  creation, and never changed.** Everything that refers to it uses this string.

## Naming them

*No convention is enforced, so pick one and hold it.*

- Lowercase, hyphenated, descriptive of the thing rather than of its role:
  `kael-mira` for a bond, `water-archive` for a place, `first-doubt` for a beat.
- **Match the display name where it is short enough to read.** A character named
  "Dr Elena Voss" and an id of `dr-elena-voss` line up on every screen, and
  nothing enforces it — so it is a decision, not a default.
- **The id is not editable.** `id` and `type` are the two fields the write path
  discards: they are not in the schema as settable, and passing one changes
  nothing. There is no rename operation either — the op kinds are create, edit,
  delete and reorder, and nothing else.
- **So renaming is delete plus create**, which is a destructive way to change a
  label, and it is the subject of the next section.

## The rename problem

*The most important thing in this file.*

- **A rename silently breaks every link to the entity.** Deleting the old id and
  creating a new one leaves every `climax_scene_id`, `primary_plot`,
  `location.world` and `variant_of` pointing at nothing — and, as established in
  `plot-and-structure.md`, those references are **not checked on write**. Nothing
  warns. Nothing reports it later.
- **The same applies to a delete.** Removing a scene does not clear the acts and
  sequences that pointed at it; it leaves them dangling.
- So: **before renaming or deleting anything that other entities point at, find
  what points at it.** A project-wide `story_load` gives the structure, and
  `view="relationship"` or the unfilled views will not show it — this is a case
  where reading the structure is the only way to know.
- **Creating with a new id and deleting the old is a two-op batch**, so it goes
  through the same preview as any other change, and the user sees both halves.
  That is the safe way to do it: one draft, create and delete together, so the
  links are visibly part of the same decision.
- *This is the gap recorded in `deferred-code-work.md`. A dangling-reference
  check would make the rename safe; until then the ordering is the mitigation.*

## Fields you must never write

- **`character.relationships` and `character.arc_beats_list` are computed** and
  read-only — the only two in the system. Writing either is refused, because
  they are derived from the relationship and arc-beat entities rather than
  stored. → `relationships.md`, `arc-beats.md`
- **`id` and `type` are discarded** rather than rejected — passing them is
  accepted and ignored, which is quieter than a refusal and worth knowing.
- So there are three different answers to "can I write this field": refused
  (computed), ignored (id, type), and accepted (everything else, valid or not).
  Only the computed ones tell you anything.

## Telling a reference from a value

*How to know what a field wants without guessing.*

- `story_describe` marks reference fields with **`is_reference`** — the ones that
  take another entity's id rather than a value. That is the tie-breaker: a
  string field that is a reference wants a slug, and the same string in a
  non-reference field wants text.
- **The flag is a best-effort inference, not a guarantee.** It is derived by
  reading the field's description for the word "slug" and cross-checking the
  declared relation and column maps, so it is known to miss a reference whose
  description does not say slug.
- So when a reference field is not marked, that is weak evidence rather than
  proof — and the reliable test is behavioural: **a value that names an existing
  entity works, and one that does not is silently stored.**
- *The field list itself is in `story_describe`. This file is only about the
  judgement the flag cannot make for you.*

---

## Open questions

- [ ] Rename is delete-plus-create and breaks links silently. The mitigation in
      this file is procedural — find the referrers, batch both ops — and it
      depends on the agent remembering to. Worth saying louder, or is it better
      raised as a tool gap than as a skill rule?
- [ ] `is_reference` is a heuristic with a known miss. Should the skill tell the
      agent to trust it, or to treat it as a hint and confirm behaviourally?
