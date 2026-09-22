# Phase B — Location Entity Brainstorm

## What exists
```
location FM:  name, one_sentence
sections:     Description, History, Scenes
```
Scene links to location via `location_id` (free text or slug, loose).

## What theory/craft says a location must do
McKee (Good_Writing.md):
- Setting dim 3 = LOCATION: "story's place in space."
- **Scene = action in continuous time and space** — location is the *stage* where
  value turns happen. It exists to be dramatized, not described for its own sake.
- **Image system / motif**: "a strategy of motifs... repeats in sight and sound...
  subliminal communication." Locations are prime carriers of image systems
  (the rain-slick alley, the sterile lab).
- **Principle of transition**: "the third element... held in common by two scenes"
  — locations can be that hinge.
- **Creative limitation**: knowable world → locations should be knowable units.

Screenwriting common sense:
- A location earns its place by **dramatic function**: where conflict happens,
  what pressure it exerts (extra-personal antagonism includes *environment*:
  "time, space, objects in the environment").
- **Atmosphere/mood ≠ story**, but mood amplifies emotion.
- Physical detail that can be *shown* (props, sensory anchors) beats abstract
  description.

## Candidate FM fields
| Field | Type | Why | Verdict |
|---|---|---|---|
| `name` | string | existing | keep (required) |
| `one_sentence` | string | existing | keep (required) |
| `mood` | string | emotional register of the place | candidate |
| `sensory_anchor` / `image` | string | McKee image system — the ONE recurring visual/sound motif | candidate |
| `dramatic_function` | string | why this place exists in the story | candidate — or section? |
| `world_id` | string | belongs-to (Phase C) | defer to C |
| `kind`/`type` | enum (interior/exterior, urban/wild...) | Fountain INT/EXT is scene-level | **skip** — heading lives on scene |
| `era`/`period` | string | location versions (Phase D) | defer to D |

## Candidate sections
Current: Description, History, Scenes

Candidates:
- Description (keep — sensory surface, what the camera sees)
- History (keep — backstory of the place)
- Atmosphere (mood, sensory palette — what it feels like beyond the visual)
- Dramatic Function (why this location exists; what pressure it exerts)
- Inhabitants (who's here — but again, relation vs prose?)
- Scenes (existing — but scenes already carry location_id; this section is
  redundant *data*; could stay as free prose notes about how scenes use it)

## LOCKED (user decisions)
1. `image` as FM — approved, with a clear name (see below).
2. Drop `Scenes` section — approved (redundant with scene→location relation).
3. No filmmaking-specific conventions for now.
4. NOTE (design rule, applies everywhere): **FM fields may have a paired section
   that expands on the decision** when it matters in development discussion.
   FM = the decision (queryable); section = the reasoning (verbose).

## Phase B result (locked, revised after LLM-constraint + FM-summary reviews)
```yaml
# location FM (lean)
name:
one_sentence:
mood:               # generalized emotional register ("oppressive domesticity") — NOT specific imagery
dramatic_function:  # why this place exists in the story, short ("where the past catches up")
world:              # (Phase C) world slug
variant_of:         # (Phase D) slug of base location, empty on bases
```

**Revision 1 (motif → mood):** `motif` (specific image/sound) was rejected
for FM — an LLM treats FM as absolute constraint and would force the imagery
into every scene. Swap: generalized `mood` in FM; specific imagery/sound lives
in the **Image System** section as material to draw from.

**Revision 2 (dramatic_function added):** passes the FM-summary test — absent
at FM-time, the LLM treats the place as generic backdrop; permeation is the
job. Pairs with the Dramatic Function section (field = gist, section =
reasoning). Supersedes the earlier one_sentence-convention idea (that
overloads one_sentence, whose job is index identification).

Design rule: FM = constraints + permeating context; sections = expansions +
situational material.

Sections: Description, Atmosphere, Image System, History, Dramatic Function
- Description — what the camera sees (sensory surface)
- Atmosphere — expands `mood`: sensory palette, how the register is felt
- Image System — recurring images/sounds; palette, not mandate
- History — backstory of the place
- Dramatic Function — expands `dramatic_function`: reasoning, pressure, usage

Dropped: Scenes (derived from scene.location_id).
