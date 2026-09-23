# Task 23: Character Relationship System — Investigation & Brainstorm

## Current State

### Storage
- Generic `relations` table: `(from_id, to_id, kind, note, order)` PK
- Character relationships: `kind='character_relationship'`, `note` = JSON `{"label", "feeling"}`
- **Only ONE relationship per (from, to) pair** (PK enforces)

### Data Model
- `constants.py:52`: `relationships` field on character only, sub_fields: `id`, `label`, "feeling"
- Described as "Unidirectional" — no auto-mirror

### Data Flow (7 touchpoints)
1. **Create** (`story_create.py` → `entity.py:relations_for_insert`) — list → rows
2. **Import** (`story_import.py:_insert_relations`) — frontmatter → rows
3. **Edit** (`story_edit.py:_edit_note_db`) — DELETE + INSERT rows
4. **Load** (`db.py:get_project_summary`) — rows → `char.rel`
5. **Dashboard** (`db.py:get_dashboard_data`) — rows → `character.relationships`
6. **Export** (`story_export.py`) — rows → frontmatter list
7. **Round-trip** tested in `test_round_trip.py`

### UI
- Network graph: directional edges from `c.related`, **deduped via `[from,to].sort()`**
- Character panel: relationship-rows with clickable name + label + feeling

---

## The General Problem

The current model treats a relationship between two characters as **a single value per pair**. But a relationship is a **directed multigraph edge**:

1. **Multiplicity** — one character can have multiple simultaneous roles toward another
2. **Direction-dependence** — the relationship quality depends on which direction you read
3. **Asymmetry** — the two directions can have contradictory qualities

### Manifestations (examples, not the problem itself)

| Case | Multiplicity | Direction-dependence |
|------|--------------|----------------------|
| A loves B / B sees A as a friend | no | yes |
| A is ally / B is enemy | no | yes |
| A is coworker / B is coworker + investigator | yes | yes |
| A was enemy in Act I, now ally | no | yes (temporal) |
| A is friendly in public / secretly hostile | yes (public+secret) | yes |

All of these are the **same underlying issue**: the current schema permits at most one fact per directed pair, and the UI collapses both directions into one edge.

---

## Root Causes

### Storage Constraint
PK `(from_id, to_id, kind)` with `kind='character_relationship'` → exactly ONE row per pair. Cannot store "coworker" AND "investigator" for B→A.

### UI Constraint
`[from,to].sort()` dedup → both directions collapsed into one edge. Cannot show asymmetric labels.

---

## General Solution: Directed Multigraph

### Part 1: Multiple entries per directed pair
Encode role into the `kind` column. Each label gets its own row:

```sql
-- B→A coworker
INSERT INTO relations VALUES ('bob', 'alice', 'character_relationship:coworker', '{"label":"Coworker"}', 1);

-- B→A investigator  
INSERT INTO relations VALUES ('bob', 'alice', 'character_relationship:investigator', '{"label":"Secret investigator","secret":true}', 2);
```

All 7 touchpoints use prefix matching: `kind LIKE 'character_relationship:%'`. Old rows (`kind='character_relationship'`) still match — zero migration.

**Cost**: 🟢 ~40 lines across import/create/edit/export/load

### Part 2: Directed graph edges (no dedup)
Render each relationship as its own directed edge. Remove the `[from,to].sort()` collapse.

```js
edges.push({
  from: c.id,
  to: rel.id,
  label: rel.label,
  dashes: !!rel.secret,
  width: 1 + (rel.strength || 0) * 2,
});
```

Multiple edges between same pair: vis-network renders parallel curves. Asymmetry is visually explicit.

**Cost**: 🟢 ~30 lines in dashboard + CSS

---

## Metadata Extensions (General-Purpose)

Each relationship entry can carry optional fields. All are additive — old entries without them still work.

| Field | Type | Purpose |
|-------|------|---------|
| `type` | enum | Categorical: ally/enemy/family/romantic/professional/mentor/rival/custom |
| `strength` | float (-1..1) | Intensity → edge thickness |
| `secret` | boolean | Hidden from other character(s) → dashed edge |
| `mutual` | boolean | Whether both characters acknowledge it |

These are **orthogonal** — any combination works. No new schema.

**Cost**: 🟢 ~40 lines (schema + graph rendering + panel)

---

## Summary

| Tier | Feature | Solves | Cost |
|------|---------|--------|------|
| 🟢 | Multi-entry storage (kind prefix) | Multiplicity | ~40 lines |
| 🟢 | Directed graph edges (no dedup) | Direction-dependence | ~30 lines |
| 🟢 | Metadata fields (type, strength, secret, mutual) | All (visual encoding) | ~40 lines |
| 🟡 | Reverse lookup (`related_by`) | See who views me | ~15 lines |
| 🟡 | Controlled vocabulary | Filter/validate | ~50 lines |
| 🔴 | Relationship as first-class entity | Advanced CRUD | ~500 lines |
| 🔴 | Temporal arcs | Evolution across scenes | ~400 lines |

**Recommended first pass**: All 3 🟢 items (~110 lines) — covers multiplicity AND direction-dependence for all cases.

