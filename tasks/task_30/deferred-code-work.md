# Deferred code work — found while drafting the skill

Not for this session. The skill is being designed now; these are plugin changes
found while designing it, written down so they are not lost and not half-fixed.

Each entry says what was found, what the change would be, and **which skill
file has to be revisited afterwards** — because a skill drafted around a missing
capability will be wrong once the capability exists.

---

## 1. Blank sections are never reported

**Found while drafting** `skill/references/model/entity-sections.md`.

Every entity is created with all of its standard sections present and empty — a
new character returns nine empty strings. Nothing reports a section as unfilled:
`unfilled_fields` counts **fields** only, comparing against schema defaults in
`core/entity.py::unfilled_fields`, and section bodies are not in that dict at
all. So a blank section is indistinguishable from a section holding a space, and
nothing in the dashboard or the tools flags it.

This is not the same as an absent section, and the difference is already
visible: requesting a name that is not in the standard set returns `null` plus
`sections_not_found` from `story_retrieve`. Blank and absent are distinguishable
today. Blank and *meaningfully empty* are not.

**The change, roughly.** Extend the unfilled reporting to sections — the same
shape as the field version, so a caller can tell "this entity has three blank
sections" without diffing bodies itself. The pieces already exist:
`standard_sections()` for the expected set, and `story_retrieve::_sections` for
the actual bodies. What is missing is the comparison and the reporting.

Not designed. It may turn out to belong on `story_load(view="unfilled")` rather
than on `story_retrieve`, and that is a design question for when it is picked
up, not now.

**Skill file to revisit:** `skill/references/model/entity-sections.md`. Its
second section, "The empty-section problem", is written around the absence. Once
blank sections are reported, that content either moves down a level — the
problem becomes "here is what is blank, decide what matters" — or disappears
into a tool call. The per-type blocks should not change.

---

## 2. `goals: {short, long}` is accepted, then silently discarded

**Found while drafting** `skill/references/craft/character-and-arc.md`.

Two character field descriptions promise a second shape:

    "goals_short": "... (flat form; nested goals.short also accepted)"
    "goals_long":  "... (flat form; nested goals.long also accepted)"

It is not accepted. Verified by creating a character with the nested form:

    create_entity(..., {"name": "Nested", "goals": {"short": "Stay.",
                                                    "long": "Survive."}})
    -> success, no error, no warning
    -> stored extra: {"goals_short": "", "goals_long": "", ...}

The nested key is gone entirely — not stored verbatim, not split into the two
fields, just dropped. The mechanism is `core/writes.py:123`, which builds the
row from the schema's own keys and therefore discards anything not declared
before the insert. `goals` appears nowhere in the codebase except inside those
two description strings.

This is the worst shape of defect: the call **succeeds**, so the agent and the
user both see a character created, and the goal is simply not there. Nothing
downstream reports it, and the character reads as someone without a want.

**Two ways to close it, and they are not equivalent.**

- *Correct the description.* The flat form is what works; there is no nested
  form. This is a two-word change and it removes a lie. It is also the whole
  fix if the nested form was never intended.
- *Implement the mapping.* Accept the nested shape and split it into the two
  fields on the way in. More work, and it adds a second accepted shape to every
  future reader of the schema — which is the thing that made this confusing in
  the first place.

The first is the smaller change and removes the hazard. Not started, and not
started here: the session is on the skill.

**Skill file to revisit:** none, strictly — the flat form is already what
`craft/character-and-arc.md` tells the agent to write. But the file should carry
the trap until the description is fixed, because an agent that reads the schema
will try the nested form it is told is accepted.

---

## 3. Structural references are never checked, so renaming breaks the story silently

**Found while drafting** `skill/references/craft/plot-and-structure.md`.

Containment is enforced: a scene's sequence must exist, a scene's act must match
its sequence's act, a sequence's act must exist. All three refuse the write.

Nothing else is. Verified — each of these stages, produces **no warning at
all**, and commits:

    act.climax_scene_id      -> a scene that does not exist
    sequence.climax_scene_id -> a scene that does not exist
    sequence.primary_plot    -> a plot that does not exist
    act.climax_scene_id      -> one scene, while a different scene
                                 carries is_act_climax

The last one is the pattern rather than the bug: a climax is stored twice — the
container points at the scene, and the scene carries the flag — and the two are
never reconciled. `project.inciting_incident_scene_id` against
`scene.is_inciting_incident` is the same shape, and the same for the story
climax at both levels.

**Why this is worth a fix rather than a note.** A user who renames or deletes a
scene leaves every container that pointed at it pointing at nothing, and nothing
anywhere reports it. The story's structure silently loses a link. The value
fields on the same entities *are* validated, so a clean validation report reads
as "the structure is sound" when it is not — the shape is enforced and the
wiring is not.

**The change, roughly.** A dangling-reference check on the write path, the same
shape as the existing `validate_scene_act_id`: resolve each `*_scene_id` and
`primary_plot` against committed state and report the ones that miss. The
references are declared in the schema already, and `story_describe` marks them
`is_reference`, so the set of fields to check is derivable rather than
hand-listed.

The harder half, and the one that decides whether it is worth doing, is the
**reconciliation**: whether a container pointing at scene A while scene B
carries the flag is a finding, a warning, or nothing. That is a design question
about which of the two is authoritative, and it is the user's to answer — not
something to pick in passing.

**Skill file to revisit:** `skill/references/craft/plot-and-structure.md`, whose
first section is written around the absence, and `craft/project-design.md` and
`craft/scene-design.md`, which state the same climax-pair problem at their own
levels.



---

## Status

None of these is started. Listed here so the skill design can proceed without them
and so nobody later assumes the skill is the only place this was noticed.
