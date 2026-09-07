# UI Design Evaluation — Claude vs DeepSeek

> Both designs reviewed against requirements. Neither is perfect — pick-and-mix recommended.

---

## Side-by-Side Preview

Open `research/dashboard_preview.html` in a browser to see both designs rendered with the same sample data (The Water Audit project).

---

## Evaluation Matrix

| Criterion | Claude | DeepSeek | Winner |
|-----------|--------|----------|--------|
| **Information density** | ★★★★★ Compact, fits more in less space | ★★★☆☆ Spacious but wastes vertical space | Claude |
| **Navigation clarity** | ★★★★☆ Sidebar icons + labels | ★★★★★ Tab-based, always visible | DeepSeek |
| **Character graph** | ★★★★★ vis-network, role colors, legend | ★★★★☆ vis-network, simpler legend | Claude |
| **Scene browsing** | ★★★★☆ List with tags, inline filter | ★★★★☆ List with tags, search filter | Tie |
| **Story overview** | ★★★★☆ Stats + logline + plots + risks | ★★★☆☆ Not built (missing from output) | Claude |
| **Continuity report** | ★★★★☆ Risks listed in Story view | ★★★☆☆ Not built (missing from output) | Claude |
| **Multi-entity support** | ★★★☆☆ Characters, Scenes, Story only | ★★★★★ Characters, Scenes, Locations, Plots, Worlds | DeepSeek |
| **Detail panel** | ★★★★★ Slides in, doesn't disrupt layout | ★★★☆☆ Replaces main content area | Claude |
| **"Ask Hermes" buttons** | ★★★★☆ In panel footer | ★★★★☆ In detail header | Tie |
| **Responsive/narrow** | ★★★★☆ Collapsible sidebar, narrow media query | ★★★☆☆ Stacks vertically but sidebar stays wide | Claude |
| **Loading states** | ★★★★☆ Spinner + error + sample data fallback | ★★★☆☆ Spinner + error text | Claude |
| **Sample data for preview** | ★★★★★ Built-in "Preview with sample data" button | ☆☆☆☆☆ None | Claude |
| **Code quality** | ★★★★☆ Clean JS, some inline styles | ★★★★☆ Clean JS, some inline styles | Tie |
| **Hermes conventions** | ★★★★☆ CSS vars, data-hermes-send | ★★★★☆ CSS vars, data-hermes-send | Tie |

**Total**: Claude 52, DeepSeek 43

---

## What Claude Does Better

1. **Information density** — Compact layout fits more data without scrolling. Writers need to see many entities at once.
2. **Character graph** — Role-based colors, legend, curved edges with labels. More useful for understanding relationships.
3. **Story overview + continuity** — Has a dedicated Story view with stats, logline, plots, and continuity risks. DeepSeek is missing this entirely.
4. **Detail panel** — Slides in from right without disrupting the main view. DeepSeek's detail panel replaces the list, losing context.
5. **Sample data fallback** — Can preview with built-in data even without an index.yaml. Great for testing.
6. **Collapsible sidebar** — Icon-only mode saves horizontal space in narrow preview panes.

## What DeepSeek Does Better

1. **Tab navigation** — Always-visible tabs for all 5 entity types. Claude only has 3 views (Characters, Scenes, Story) — Locations, Plots, Worlds are buried.
2. **Multi-entity support** — All 5 entity types are first-class citizens. Claude treats Locations/Plots/Worlds as secondary.
3. **Search** — Search bar is always visible in sidebar. Claude hides it in the header.
4. **Cleaner typography** — More whitespace, easier to read at a glance.

---

## Critical Gaps

### Claude Missing:
- **Locations, Plots, Worlds as top-level views** — Only accessible via tags in Story view. Writers need direct access.
- **Scene content loading** — Scenes list shows metadata but no way to load screenplay content for a specific scene.

### DeepSeek Missing:
- **Story overview** — No project stats, logline, or continuity report.
- **Continuity risks** — Not displayed anywhere.
- **Sample data** — Can't preview without a real index.yaml.
- **Scene content** — Has a "Load scene content" button but implementation is fragile (regex-based).

---

## Recommended Approach: Pick-and-Mix

### From Claude (take these):
1. **Layout shell** — Sidebar + main content + slide-in detail panel
2. **Character graph** — vis-network with role colors and legend
3. **Story overview view** — Stats cards + logline + plots + continuity risks
4. **Collapsible sidebar** — Icon-only default, expands on toggle
5. **Sample data fallback** — "Preview with sample data" button
6. **Loading/error states** — Spinner + error screen + manual file load

### From DeepSeek (take these):
1. **Tab navigation** — 5 tabs: Characters, Scenes, Locations, Plots, Worlds
2. **Search bar** — Always visible in sidebar, below tabs
3. **Entity list items** — Name + subtitle (role/status/one_sentence)
4. **Detail sections** — Card-based layout with section titles

### New (build these, neither has them well):
1. **Scene content viewer** — Load screenplay.md, extract scene by heading, display in detail panel
2. **Cross-entity navigation** — Click a character in scene detail → load character detail
3. **Continuity risk badges** — Visual indicators in scene/character lists

---

## Proposed Hybrid Structure

```
┌─────────────────────────────────────────────────────────┐
│ [≡] Characters    Scenes    Locations    Plots    Worlds │ ← Tabs (DeepSeek)
├──────────┬──────────────────────────────────────────────┤
│ Search   │  Entity list or Graph                        │
│ [______] │  - Item 1 (subtitle)                         │
│          │  - Item 2 (subtitle)                         │
│          │  - Item 3 (subtitle)                         │
├──────────┴──────────────────────────────────────────────┤
│ Stats: 8 chars │ 24 scenes │ 3 locs │ 3 plots │ 2 risks │ ← Stats bar (DeepSeek)
└─────────────────────────────────────────────────────────┘
                    ↓ Click entity ↓
┌─────────────────────────────────────────────────────────┐
│ Detail Panel (slides in from right)                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [Role] Character Name                          [✕]  │ │
│ │ One sentence...                                     │ │
│ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ Scenes          │ [tag] [tag] [tag]             │ │ │
│ │ │ Goals           │ short/long                    │ │ │
│ │ │ Knowledge       │ [tag] [tag]                   │ │ │
│ │ │ Relationships   │ → Detective Oak (Wary respect)│ │ │
│ │ └─────────────────────────────────────────────────┘ │ │
│ │ [💬 Ask Hermes about this character]                │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Recommendation

**Start with Claude's structure, add DeepSeek's tab navigation.**

Claude's layout is fundamentally better for our use case (information density, slide-in panel, story overview). DeepSeek's tab navigation is the single best feature — all 5 entity types accessible in one click.

The hybrid gives us:
- Claude's dense, professional layout
- DeepSeek's complete entity coverage
- Neither's missing features (scene content, cross-navigation) built fresh

---

## Next Step

1. User reviews `research/dashboard_preview.html` (both designs with sample data)
2. User confirms hybrid approach (or suggests changes)
3. Build `src/dashboard/story-dashboard.html` implementing the hybrid
