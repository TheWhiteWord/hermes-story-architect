# Subtask: Dashboard Requirements & Context Gathering — REVISED

> Gather all information needed for the UI model to design the dashboard. References: `task_1/04_decisions.md`, `task_2/04_decisions.md`, `plan/plan.md`.

---

## What we know

From the plan (v6):
- Single HTML file with embedded CSS/JS
- vis-network (MIT/Apache 2.0) loaded from CDN
- Reads from `.story/index.yaml` for structure, vault for content
- Updates when project changes (manual refresh or file watcher)

From Task 1:
- Vault: `~/story-vault/projects/<slug>/`
- Index: `.story/index.yaml` (always-loaded graph)

From Task 2:
- Index schema: project, characters, locations, worlds, scenes, plots, story_memory

---

## Plugin Context (for UI Model)

**Purpose**: Story-writing environment for Hermes Desktop. Story projects live as Markdown + YAML frontmatter in a vault. The dashboard provides interactive navigation of a story's entities (characters, locations, worlds, scenes, plots).

**Data source**: `.story/index.yaml` — a graph with entities as nodes, relationships as edges.

**Index structure** (what the dashboard reads):
```yaml
project: {name, logline, genre, setting, scene_count, character_count, ...}
characters: [{id, name, role, one_sentence, sections, scenes, related, goals_short, goals_long, knowledge}]
locations: [{id, name, one_sentence, sections, scenes}]
worlds: [{id, name, one_sentence, sections, rules}]
scenes: [{id, heading, characters, locations, plots}]
plots: [{id, name, status, setups, payoffs, characters, sections, one_sentence}]
story_memory: {last_updated, continuity_risks, headings, summary}
```

---

## User Needs (What Writers Need to See)

### Core questions the dashboard should answer:
- Who are the characters and how are they connected?
- What happens in which scene?
- Where does each scene take place?
- What's the chronological flow?
- What are the active plot threads?
- What continuity risks exist?

### User interactions to support:
- Click entity → see full details
- Click scene → see scene content (loaded from `screenplay.md`)
- "Ask Hermes about this" → sends pre-formulated prompt
- Filter/sort entities
- Navigate between related entities

---

## Data Relationships (for visualization)

- **Characters ↔ Scenes**: Many-to-many (characters appear in scenes)
- **Locations ↔ Scenes**: One-to-many (location hosts scenes)
- **Plots ↔ Scenes**: Many-to-many (plots span scenes)
- **Characters ↔ Plots**: Many-to-many (characters involved in plots)
- **Characters ↔ Characters**: Many-to-many (relationships, unidirectional)
- **Worlds ↔ Plots**: One-to-many (world contains plots)

---

## Interaction Model

### Clicks
- Character → show profile (name, role, one_sentence, scenes, goals, knowledge)
- Scene → show scene content (loaded from `screenplay.md`)
- Location → show where it appears
- Plot → show setups/payoffs, involved characters

### "Ask Hermes about this" buttons
```html
<button data-hermes-send="Tell me more about Mara Chen's character development.">
  Ask Hermes
</button>
```

Pre-formulated prompts:
- Character: `"Tell me more about [name]'s character development."`
- Scene: `"What happens in [heading]?"`
- Location: `"Describe [name] and its role in the story."`
- Project: `"Give me an overview of [name]."`

### Hermes Desktop Conventions
- CSS variables: `var(--foreground)`, `var(--muted-foreground)`, `var(--accent)`, `var(--border)`, `var(--card)`
- No margins, no background (transparent)
- Content frames to height, width from first measured span
- Font: app font (don't set own)
- `::preview{file="path.html"}` to open in preview pane
- `data-hermes-send="prompt"` on clickable elements

---

## Technical Constraints

- **Single HTML file** with embedded CSS/JS (no build step)
- **vis-network** loaded from CDN (MIT/Apache 2.0) — for character graph
- **Reads `.story/index.yaml`** via `fetch()` (file:// or local server)
- **Reads `screenplay.md`** for scene content (on demand)
- **Updates on**: manual refresh button, file watcher (optional)

---

## Visual Style Guidance

- **Dark/light theme**: Use Hermes CSS variables (automatic)
- **Responsive**: Works in preview pane (narrow width ~400-600px)
- **Typography**: App font, inherit from Hermes
- **Colors**: Use `var(--accent)` for highlights, `var(--border)` for dividers
- **Spacing**: Compact (writers need information density)
- **Icons**: Minimal, text-based where possible

---

## What to Hand the UI Model

This document provides everything needed to design the dashboard:
1. Plugin context (what it does)
2. Data model (index.yaml structure)
3. Data relationships (for visualization)
4. User needs (what writers need to see)
5. Interaction model (clicks, "Ask Hermes" buttons)
6. Hermes desktop conventions
7. Technical constraints
8. Visual style guidance

The UI model should produce:
- Single HTML file (`src/dashboard/story-dashboard.html`)
- Embedded CSS (using Hermes variables)
- Embedded JS (vis-network for character map, navigation, data loading)
- Views that answer the core user questions
- "Ask Hermes" buttons with `data-hermes-send`

---

## Status: RESOLVED (revised — views not imposed)
