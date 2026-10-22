# Deferred code work — found while drafting the skill

Not for this session. The skill is being designed now; these are plugin changes
found while designing it, written down so they are not lost and not half-fixed.

Each entry says what was found, what the change would be, and **which skill
file has to be revisited afterwards** — because a skill drafted around a missing
capability will be wrong once the capability exists.

---

## 1. Structural references are never checked, so renaming breaks the story silently

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
