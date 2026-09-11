# Frontmatter Audit — Field Drift Analysis

> Source of truth: `index-format.md` (design) vs actual note frontmatter vs code (`entity.py`, `index.py`, `constants.py`) vs dashboard (`story-dashboard.html`).
> Stripped of "Save the Children" specifics — fields described generically.

---

## Character

### Current frontmatter (from notes)
```yaml
name: <Character Name>
one_sentence: <Single sentence description>
story_role: <Protagonist|Antagonist|Supporting|Minor|Cameo>
```

### Design expectation vs actual

| Field | Design name | Note has | Code uses | Dashboard uses | Verdict |
|-------|-------------|----------|-----------|----------------|---------|
| Display name | `name` | ✅ `name` | ✅ required | ✅ | OK |
| Role | `role` | ❌ uses `story_role` | ❌ validates `story_role` | ✅ normalizes `story_role`→`role` | **MISMATCH**: design says `role`, code/notes say `story_role` |
| Index label | `one_sentence` | ✅ | ✅ required | ✅ | OK |
| Short-term goal | `goals_short` | ❌ | ❌ | ✅ reads `goals.short` | **MISSING from notes** |
| Long-term goal | `goals_long` | ❌ | ❌ | ✅ reads `goals.long` | **MISSING from notes** |
| Relationships | `related` | ❌ | ❌ | ✅ reads `relationships` | **MISSING from notes**; dashboard expects legacy `relationships`, design says `related` |
| Known facts | `knowledge` | ❌ | ❌ | ✅ | **MISSING from notes** |
| Age | — | ❌ | ❌ | Demo data has it | **UNDOCUMENTED** — remove from demo, add to design if needed |

### Critical fields (consumed by other processes)
- `story_role` — validated in `entity.py`, displayed in dashboard
- `one_sentence` — required, used as index label everywhere
- `name` — required, primary display key

### Naming issues
1. **`story_role` vs `role`**: Design doc says `role`. Code validates `story_role`. Dashboard normalizes one to the other. Pick one. Since `role` collides with YAML reserved-ish naming and `story_role` is already wired in validation, **rename design field to `story_role`** (code is the consumer, design should match).
2. **`related` vs `relationships`**: Dashboard code at line 1634 expects `relationships` (legacy). Design says `related`. **Rename dashboard expectation to `related`** (design is canonical).
3. **`goals_short`/`goals_long` vs `goals.short`/`goals.long`**: Dashboard flat-normalizes from nested `goals` object. But notes don't have either. **Decide**: flat fields in frontmatter (simpler) or nested object (matches dashboard). Recommend flat — matches design, easier to author.

---

## Location

### Current frontmatter
```yaml
name: <Location Name>
one_sentence: <Single sentence description>
```

### Design expectation vs actual
| Field | Design | Notes | Verdict |
|-------|--------|-------|---------|
| `name` | ✅ | ✅ | OK |
| `one_sentence` | ✅ | ✅ | OK |

No drift. Clean.

### Critical fields
- `name`, `one_sentence` — required, displayed in dashboard

---

## World

### Current frontmatter
```yaml
name: <World Name>
one_sentence: <Single sentence description>
```

### Design expectation vs actual
| Field | Design | Notes | Verdict |
|-------|--------|-------|---------|
| `name` | ✅ | ✅ | OK |
| `one_sentence` | ✅ | ✅ | OK |
| `rules` | ✅ | ❌ | **MISSING from notes** |

### Critical fields
- `name`, `one_sentence` — required
- `rules` — design expects `string[]` of world rules; dashboard renders them; notes lack the field

---

## Plot

### Current frontmatter (updated)
```yaml
name: <Plot Name>
one_sentence: <Single sentence description>
status: <active|resolved|abandoned>
characters: [<char-slug>, ...]    # who drives the plot (frontmatter-only)
setups:
  - number: <scene number>
    heading: <scene heading>
    description: <what happens>
payoffs:
  - number: <scene number>
    heading: <scene heading>
    description: <what happens>
```

### Design expectation vs actual
| Field | Design | Notes | Code | Dashboard | Verdict |
|-------|--------|-------|------|-----------|---------|
| `name` | ✅ | ✅ | — | ✅ | OK |
| `one_sentence` | ✅ | ✅ | — | ✅ | OK |
| `status` | ✅ | ✅ | ✅ validated | — | OK |
| `setups` | object[] | ✅ | ✅ `_normalize_beat` → `{scene, description}` | ✅ | **FIXED**: backend maps `heading`→`scene` so dashboard gets plain strings |
| `payoffs` | object[] | ✅ | ✅ same as setups | ✅ | **FIXED** |
| `characters` | `string[]` | ✅ | ✅ preserved from frontmatter | ✅ renders as tags | **FIXED**: frontmatter-only, not derived from scenes |

### Naming issues (resolved)
1. ~~**`heading` vs `scene`**~~ — **FIXED**. Backend `_normalize_beat` maps note `heading` to dashboard's `scene` key. Dashboard no longer aliases `_setup_objs`/`_payoff_objs`. One consistent shape: `{scene: <heading>, description: <text>}`.
2. **`number` type** — Notes store `number: '2'` (string). Design implies numeric. *Cosmetic — left as-is, not causing complexity.*
3. ~~**`characters` missing**~~ — **FIXED**. `characters` added to plot frontmatter. `_enrich_plots` no longer derives characters from screenplay scenes (scenes may have passersby not involved in the plot). Frontmatter is the single source of truth.

### Critical fields
- `status` — validated, used by dashboard filter
- `setups`/`payoffs` — core plot structure, dashboard renders as beat board
- `characters` — who drives the plot, rendered as tags on plot cards
- `one_sentence` — required, displayed in dashboard

---

## Project

### Current frontmatter
```yaml
name: <Project Name>
genre: <Genre>
setting: <Primary setting>
logline: <One-sentence summary>
status: <active|abandoned|archived>  # not in design
```

### Design expectation vs actual
| Field | Design | Notes | Verdict |
|-------|--------|-------|---------|
| `name` | ✅ | ✅ | OK |
| `logline` | ✅ | ✅ | OK |
| `genre` | ✅ | ✅ | OK |
| `setting` | ✅ | ✅ | OK |
| `slug` | ✅ | ❌ (derived from folder) | OK — derived, not in frontmatter |
| `scene_count` | ✅ | ❌ (derived) | OK |
| `character_count` | ✅ | ❌ (derived) | OK |
| `world_count` | ✅ | ❌ (derived) | OK |
| `plot_count` | ✅ | ❌ (derived) | OK |
| `status` | ❌ | ✅ | **EXTRA** — not in design, keep if useful |
| `location_count` | ❌ | ❌ (derived) | **EXTRA in code** — `index.py` emits it, design doesn't list it |

### Naming issues
- `location_count` emitted by `index.py` but not in design schema. **Remove from code** or add to design.

### Critical fields
- `name`, `logline` — required, displayed everywhere

---

## Summary of Required Fixes

| # | Issue | Where | Action | Status |
|---|-------|-------|--------|--------|
| 1 | `story_role` vs `role` | Design doc | Design: rename `role` → `story_role` (match code) | ⏳ pending |
| 2 | `related` vs `relationships` | Dashboard JS | Dashboard: rename `relationships` → `related` (match design) | ⏳ pending |
| 3 | `goals` missing from notes | Notes | Add `goals_short`, `goals_long` to character frontmatter | ⏳ pending |
| 4 | `knowledge` missing from notes | Notes | Add `knowledge: string[]` to character frontmatter | ⏳ pending |
| 5 | `related` missing from notes | Notes | Add `related: [{id, label, feeling}]` to character frontmatter | ⏳ pending |
| 6 | `setups`/`payoffs` key `scene` vs `heading` | Dashboard JS | Backend `_normalize_beat` maps `heading`→`scene`; dashboard reads plain strings | ✅ **FIXED** |
| 7 | `number` type in setups/payoffs | Notes + dashboard | Enforce numeric type (or string-escape, but be consistent) | ⏳ cosmetic, left as-is |
| 8 | `characters` missing from plots | Notes + index.py | `characters` added to frontmatter; preserved as-is from frontmatter | ✅ **FIXED** |
| 9 | `rules` missing from worlds | Notes | Add `rules: string[]` to world frontmatter | ⏳ pending |
| 10 | `location_count` extra in index | index.py | Remove or document in design | ⏳ pending |
| 11 | `age` in dashboard demo | Dashboard HTML | Remove (undocumented) | ⏳ pending |
