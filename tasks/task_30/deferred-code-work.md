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

## Status

Neither is started. Listed here so the skill design can proceed without them and
so nobody later assumes the skill is the only place this was noticed.
