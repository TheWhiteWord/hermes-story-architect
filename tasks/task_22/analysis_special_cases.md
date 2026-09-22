# Phase D — Special Cases Brainstorm (time/space variants)

## Cases
1. World versions — same world, different time ("Earth today" / "Earth +400y")
2. Location versions — same place, different reality layer (real / dream / memory /
   simulation / mirror)
3. Adjacent: alternate timelines, pre/post-event, nested story worlds, virtual layers

## Theory anchors
- Consistent vs inconsistent realities = Archplot/Antiplot **design axis** — a
  variant is a design decision, not metadata noise.
- Flashback/variant rule: dramatize it, only when audience needs it — variants
  are stages, not labels.
- Creative limitation: every variant must stay a knowable unit — no namespace
  explosion.
- Image system: the audience recognizes "same place" through the **repeated
  common core**; the variant's charge comes from **what shifts**. This is the
  craft basis for the base/variant convention below.

## Decision: S1 + one link field
Variants are separate entities (convention-governed), connected by a single
`variant_of` link.

### The link
```yaml
# location FM                          # world FM
name: Kitchen (Dream)                  name: Earth (400 Years Later)
one_sentence: ...                      one_sentence: ...
mood: ...                              period: +400y after the collapse
world: dream-world                     variant_of: earth
variant_of: kitchen                    # → relations row, kind=world_variant
# → relations row, kind=location_variant
```

- **Single pointer to a base** (star topology, not chains/lists). The base is
   the "reality"/original; every variant points at it. Reverse lookup
   (`SELECT from_id FROM relations WHERE to_id=? AND kind='location_variant'`)
   gathers the family — same pattern as character_scene reverse lookups.
- Stored in the existing `relations` table via the existing `_RELATION_FIELDS`
  machinery (character_relationship is the template). No DB migration.
- Two orthogonal links, no conflict: `world` = **containment** (where it lives),
  `variant_of` = **identity** (what it's the same place as). Dream-kitchen sits
  in dream-world AND points at real-kitchen.
- note column stays empty — one_sentence already says what the variant is. YAGNI.

### The convention (zero machinery)
- **Base holds the common core; variant holds only the deltas.**
- Base location = enduring physical facts (layout, the oak table, north window).
- Variant = what shifts (light wrong, table missing) + its own mood/atmosphere
  charge (imagery specifics live in each entity's Image System section).
- Retrieve base + variants together (story_retrieve already batches refs) →
  agent sees common core once, deltas per variant. No duplication.

### Naming convention (from Phase C constraint)
Variant display names MUST be distinct: "Kitchen (Dream)". Keeps name-based
fuzzy matching unambiguous. variant_of additionally gives the future matcher a
disambiguation hook (match base name, then pick variant by context) — noted,
not designed now (matcher is dormant).

## Rejected
- Symmetric `variants` lists on both sides — sync burden, redundant with reverse lookup.
- Chains (memory-of-the-dream) — writer points at whichever base defines the
  common core. Star is enough.
- Shared-aspect machinery (fields marking "this detail is common") — the
  base-holds-core convention covers it; add only if a real story breaks it.
- `reality_mode` enum — the variant pattern makes it redundant: the existence of
  linked variants IS the statement "this world has layers."

## Phase A/B/C reframe check
- A: world gains `variant_of` + keeps `period` (period states WHEN, variant_of
  states SAME-AS-WHAT). Compatible, no changes.
- B: location unchanged beyond `variant_of`.
- C: untouched — world/parent_id containment stands; variant_of is orthogonal.
- Fuzzy matcher: unaffected (distinct names enforced by convention).
