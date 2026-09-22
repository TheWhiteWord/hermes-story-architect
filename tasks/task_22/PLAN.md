# Task 22 — Refine Location & World Entities

Goal: richer schemas for `location` and `world`, plus a world↔location connection
that handles time/space variants (world versions, location versions) at STORY
DESIGN level only.

## Grounding sources
- Theory: `docs/research/McKee_Story/Good_Writing.md`
- Existing schemas: `core/constants.py` (ENTITY_SCHEMAS), `core/entity.py` (standard_sections, ENTITY_COLUMN_MAP, _RELATION_FIELDS)
- Code patterns: relations table with `kind`, `extra` JSON column, scene.location_id

## Protocol (agreed with user)
One aspect at a time, in order:
- **A) BRAINSTORM WORLD** — fields/sections for the world entity
- **B) BRAINSTORM LOCATION** — fields/sections for the location entity
- **C) BRAINSTORM CONNECTION** — how locations belong to worlds
- **D) BRAINSTORM SPECIAL CASES** — time/space variants (world versions, location versions: dream, past, future...)
- **E) BRAINSTORM SOLUTIONS** — converge into a concrete schema + conventions proposal

Rules:
- After each phase, re-check earlier phases for simplifications/reframings
  triggered by new findings.
- OUT OF SCOPE: in-story continuity (events/changes within the story). Design-level
  structure only.
- Avoid overly verbose solutions. Prefer targeted refinement / reframing of
  entity definitions over new machinery.

## Status
- [x] A) World brainstorm — LOCKED, EXTENDED (period+values+power FM; sections: Description, History, Livelihood, Power, Rituals, Values, Conflict)
- [x] B) Location brainstorm — LOCKED, REVISED (mood+dramatic_function FM + Image System section; motif rejected for FM — LLM constraint risk)
- [x] C) Connection brainstorm — LOCKED (world FM field → parent_id; fuzzy matcher audited, unaffected; variant-name constraint recorded for D)
- [x] D) Special cases brainstorm — LOCKED (S1 + variant_of link; base-holds-core convention)
- [x] E) Solutions / final proposal — LOCKED → `FINAL_PLAN.md` (design only, no code)

## Design rules (accumulated)
- FM lean; sections verbose. FM = decision (queryable), section = reasoning.
- FM fields may have a paired section expanding the decision when it matters
  for development discussion (e.g. `mood` FM + Atmosphere section).
- **FM = constraints + permeating context** (needed in EVERY scene; absent it,
  the LLM defaults wrongly and doesn't know to ask). **Sections = expansions +
  situational material** (needed when the moment calls — the moment itself
  prompts retrieval). Specific imagery/sound in FM = LLM would impose it on
  every scene; generalized mood in FM, specifics in Image System section.
- **FM-summary test:** a section earns an FM counterpart only if (1) needed at
  FM-only access time (index/pick/scene-writing context) AND (2)
  constraint-treatment is harmless or correct. Passed: world values/power,
  location dramatic_function. Failed: rituals (insertable material),
  livelihood (folds into power), history summaries (period covers "when").
