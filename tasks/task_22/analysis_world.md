# Phase A — World Entity Brainstorm

## What exists
```
world FM:  name, one_sentence, rules (list of strings)
sections:  Description, History, Conflict
```

## What McKee says a "world" must answer (Good_Writing.md)
Before the Inciting Incident, define the story world:
- **Livelihood** — how characters earn a living
- **Politics (power)** — power dynamics: society, relationships, households
- **Rituals** — customs and practices
- **Values** — good/evil, right/wrong, laws (moral/ethical/legal distinction)
- **Genre** — genre or combination
- **Biographies / Backstory** — characters' pasts, significant past events
- **Cast design** — roles, polarization

Plus:
- **Setting = Period, Duration, Location, Level of conflict** (4 dimensions)
- **Principle of creative limitation** — "small, knowable world"; knowledge of everything *germane* to the story
- **Audience contract** — once rules are known, breaking them = unconvincing
- **Consistent vs. inconsistent realities** — Archplot/Miniplot = consistent; Antiplot = inconsistent (this is a *design decision*, not an error)
- **Cliché comes from not knowing your world** — the world doc is literally the anti-cliché device

## Candidate FM fields
| Field | Type | Why (McKee) | Verdict |
|---|---|---|---|
| `name` | string | existing | keep (required) |
| `one_sentence` | string | existing | keep (required) |
| `rules` | list | existing — audience contract | keep |
| `period` | string | Setting dim 1 | candidate |
| `duration` | string | Setting dim 2 | candidate |
| `genre` | string | world question; project already has genre | **skip** — duplicate of project.genre |
| `level_of_conflict` | string | Setting dim 4 | candidate (but scene already has conflict_levels...) |
| `reality_mode` | enum: consistent/inconsistent | Archplot/Miniplot vs Antiplot — a *design* choice about world versions | **strong** for Phase D |
| `power_structure` | string | Politics | candidate |
| `values` | string | world values | candidate |
| `livelihood` | string | McKee question | candidate |
| `rituals` | list | McKee question | candidate |

## Candidate sections (prose)
Current: Description, History, Conflict

McKee-informed candidates:
- Description (keep — sensory surface)
- History (keep — backstory)
- Conflict (keep — antagonism levels in this world)
- Society (livelihood, politics, rituals, values — could be one section)
- Cast / Inhabitants (who lives here — but is that a *relation*, not prose?)

## LOCKED (user decisions)
1. `period` on world FM — **approved**.
2. Sections can be verbose; FM must stay lean. McKee world questions become
   **separate sections**, not one "Society" blob, not FM fields.
3. `reality_mode` — out of scope for Phase A; resurfaces in Phase D.

## Phase A result (locked, extended after FM-summary check)
```yaml
# world FM (lean)
name:
one_sentence:
rules:        # list — audience contract (how it works)
period:       # when this world exists (e.g. "2040s", "post-collapse +400y")
values:       # list — short entries: what this world holds sacred (permeates every scene)
power:        # list — short entries: who holds power and how (antagonism source)
variant_of:   # (Phase D) slug of base world, empty on bases
```
Triad: `rules` = how it works, `values` = what it holds sacred, `power` =
who's on top. `values`/`power` pass the FM-summary test (permeating context,
constraint-treatment correct); the sections expand them with reasoning.

Sections (writer prompts, verbose OK):
- Description
- History
- Livelihood
- Power (expands `power` FM)
- Rituals
- Values (expands `values` FM)
- Conflict

Rejected: genre (project-level), level_of_conflict (scene-level),
rituals/livelihood as FM (situational material — motif lesson), history
summaries as FM (`period` covers the "when").
