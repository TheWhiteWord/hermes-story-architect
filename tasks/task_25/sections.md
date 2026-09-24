# Task 25 — Standard Sections Design

## Project

### Theory Foundation
- **Premise**: "What would happen if...?" — the inspiring idea
- **Controlling Idea**: the story's ultimate meaning — how and why life changes from beginning to end
- **Spine**: protagonist's desire forms the energy of the story — every scene relates to it
- **Value Arc**: the sweep from opening to closing value charge — must be absolute and irreversible
- **Story Triangle**: Classical/Miniplot/Antiplot — the fundamental design choice
- **Inciting Incident**: unbalances the protagonist's life, launches the quest
- **Structure as cosmology**: the writer's understanding of life's hidden order

### FM Fields
`name`, `logline`, `genre`, `setting`, `status`, `spine`, `controlling_idea`, `value`, `value_at_open`, `value_at_close`, `inciting_incident_scene_id`, `story_climax_scene_id`, `structure_type`, `act_count`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Premise** | The "what if" idea that inspired the story | — (inspires controlling_idea) |
| 2 | **Spine** | Protagonist's desire — the story-long drive | spine |
| 3 | **Controlling Idea** | How and why life changes — the story's argument | controlling_idea |
| 4 | **Value Arc** | Value at stake, opening/closing charge, the sweep | value, value_at_open, value_at_close |
| 5 | **Structure** | Design type (Classical/Miniplot/Antiplot), acts, key turning points | structure_type, act_count, inciting_incident_scene_id, story_climax_scene_id |
| 6 | **Genre** | Genre conventions, world contract with audience | genre, setting |
| 7 | **Notes** | Catch-all | — |

### Section List
```python
["Premise", "Spine", "Controlling Idea", "Value Arc", "Structure", "Genre", "Notes"]
```

**Removed:** Synopsis, Themes  
**Added:** Premise, Spine, Controlling Idea, Value Arc, Genre, Notes  
**Preserved:** Structure

---

## Character

### Theory Foundation
- **True character** revealed only through choice under pressure — dilemma, not good-vs-evil
- **Character depth**: internal contradiction + surface-vs-core contradiction ("principals must be written in depth")
- **Three conflict levels**: inner, personal, extra-personal
- **Character ↔ Structure interlocked**: structure creates escalating pressure, character embodies qualities to enact choices
- **Desires**: conscious + unconscious, drives the spine
- **Arc**: change in inner nature, for better or worse
- **Metaphor**: "a character is a work of Art, a metaphor for human nature"

### FM Fields
`name`, `story_role`, `one_sentence`, `goals_short`, `goals_long`, `knowledge`, `arc_type`, `arc_value`, `arc_value_at_open/close`, `arc_complete`, `relationships` (computed), `arc_beats_list` (computed)

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Identity** | Core traits, essence, surface vs. deep self | name, one_sentence, story_role |
| 2 | **Desires** | Conscious & unconscious wants, motivations | goals_short, goals_long |
| 3 | **Background** | Formative experiences, history | knowledge |
| 4 | **Contradictions** | Internal conflicts, what lies beneath | — (depth) |
| 5 | **Psychology** | Inner life, fears, secrets, mental landscape | — (depth) |
| 6 | **Arc** | How they change, growth/degradation | arc_type, arc_value_* |
| 7 | **Relationships** | Dynamics with others | — (complements computed) |
| 8 | **Voice** | Expression, speech, mannerisms | — (not in FM) |
| 9 | **Notes** | Catch-all | — |

### Section List
```python
["Identity", "Desires", "Background", "Contradictions", "Psychology", "Arc", "Relationships", "Voice", "Notes"]
```

**Removed:** Personality, Greatest Fear, Secrets, Goals  
**Added:** Identity, Desires, Contradictions, Psychology, Notes  
**Preserved:** Background, Voice, Arc, Relationships

---

## Plot

### Theory Foundation
- PLOT = the writer's carefully chosen sequence of events and their design in time — an internally consistent, interrelated pattern
- **Subplot taxonomy**: Contradictory (ironic enrichment), Resonant (thematic variation), Setup (delayed opening), Complicating (adds complexity)
- Plot exists in dialectical tension with the Central Plot — it can contradict, echo, or complicate
- Each plot has its own **value arc** — how a value shifts across its span

### FM Fields
`name`, `one_sentence`, `plot_type`, `plot_scope`, `value_arc`, `status`, `characters`, `setups`, `crisis`, `climax`, `payoffs`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Summary** | One-sentence, overall through-line | name, one_sentence |
| 2 | **Role** | Plot type, scope, narrative function in the story | plot_type, plot_scope |
| 3 | **Threads** | How this plot weaves through scenes — setups, complications, turning points, payoffs | setups, crisis, climax, payoffs |
| 4 | **Value** | What value is at stake and its journey across the plot | value_arc |
| 5 | **Characters** | Who's involved, their stakes and arcs within this plot | characters |
| 6 | **Notes** | Catch-all | — |

### Section List
```python
["Summary", "Role", "Threads", "Value", "Characters", "Notes"]
```

**Removed:** Obstacles, Stakes  
**Added:** Role, Threads, Value, Characters, Notes  
**Preserved:** Summary

---

## Scene

### Theory Foundation
- **Scene = story in miniature**: action through conflict in continuous time/space that *turns* a value-charged condition
- Every scene should turn — no scene without value change
- **Scene-Objective** (immediate desire in time/place) vs **Super-Objective** (story-long spine)
- **Beat**: exchange of behavior in action/reaction — beats shape the turning
- **Scene Analysis**: conflict → opening value → beats → closing value → turning point
- **Dilemma**: true choice requires pressure — irreconcilable goods or lesser evils
- Scene has **dramatic role**: setup, complication, crisis, climax, resolution, transition, non-event

### FM Fields
`title`, `one_sentence`, `order`, `status`, `heading`, `location`, `time_of_day`, `sequence_id`, `act_id`, `characters`, `value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role`, `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Content** | The actual scene content / prose draft (first — special UI section) | — |
| 2 | **Objective** | What the character wants in this scene, scene-objective vs super-objective | — |
| 3 | **Conflict** | The force(s) of antagonism at play — inner, personal, extra-personal | conflict_levels |
| 4 | **Beats** | Action/reaction exchanges, the gap between expectation and result | — |
| 5 | **Value Turn** | Value at stake, opening charge, closing charge, the reversal | value, value_open, value_close |
| 6 | **Dramatic Function** | Scene's role in larger structure (setup, complication, climax, etc.), flags | dramatic_role, is_inciting/is_climax_* |
| 7 | **Production** | Location, time, heading — screenplay-facing details | location, time_of_day, heading |
| 8 | **Notes** | Catch-all | — |

### Section List
```python
["Content", "Objective", "Conflict", "Beats", "Value Turn", "Dramatic Function", "Production", "Notes"]
```

**Removed:** Description  
**Added:** Objective, Conflict, Beats, Value Turn, Production, Notes  
**Preserved:** Content (moved to first position), Dramatic Function

---

## Sequence

### Theory Foundation
- **Sequence** = a series of scenes that culminates in a scene with greater impact than any preceding scene
- Progression of change: scenes → minor, sequences → moderate, acts → major
- Sequence builds to a **climactic scene** — a reversal more powerful than any scene within the sequence
- Sequences are the **hinge points** of act structure — each sequence raises the stakes
- The **sequence climax** is a turning point that recontextualizes everything before it

### FM Fields
`title`, `order`, `status`, `act_id`, `value`, `value_open`, `value_close`, `climax_scene_id`, `primary_plot`, `purpose`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Summary** | What this sequence accomplishes in the story | title |
| 2 | **Purpose** | Dramatic function — why this sequence exists, what it builds toward | purpose |
| 3 | **Value Arc** | Value at stake, how it shifts from open to close across the sequence | value, value_open, value_close |
| 4 | **Progression** | How scenes build — escalation, the path to the climax | — (informs scene order) |
| 5 | **Sequence Climax** | The climactic scene, the reversal, why it lands with maximum impact (distinguishes from act/story climax) | climax_scene_id |
| 6 | **Plots** | Which plot(s) this sequence serves (one or many) | primary_plot |
| 7 | **Notes** | Catch-all | — |

### Section List
```python
["Summary", "Purpose", "Value Arc", "Progression", "Sequence Climax", "Plots", "Notes"]
```

**Removed:** Scene Order  
**Added:** Purpose, Value Arc, Progression, Sequence Climax, Plots, Notes  
**Preserved:** Summary

---

## Act

### Theory Foundation
- **Act** = a series of sequences that peaks in a climactic scene, causing a **major reversal** of values, more powerful than any previous sequence or scene
- Act climax delivers a **revolution in values** — a value swing at maximum charge that is **absolute and irreversible**
- Acts are the **largest structural units** below the story itself
- Act structure is **beaten into sequences**, sequences into scenes
- The **act climax** is the biggest reversal in the story — the point beyond which the protagonist cannot return to their old life

### FM Fields
`title`, `order`, `status`, `value`, `value_open`, `value_close`, `climax_scene_id`, `act_objective`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Summary** | What this act accomplishes in the story | title |
| 2 | **Objective** | Protagonist's immediate goal for this act — what they're trying to achieve | act_objective |
| 3 | **Value Arc** | Value at stake, how it shifts across the act | value, value_open, value_close |
| 4 | **Reversal** | The climactic scene, the major reversal, why it's absolute and irreversible | climax_scene_id |
| 5 | **Notes** | Catch-all | — |

### Section List
```python
["Summary", "Objective", "Value Arc", "Reversal", "Notes"]
```

**Removed:** Thematic Function  
**Added:** Objective, Value Arc, Reversal, Notes  
**Preserved:** Summary

---

## Arc Beat

### Theory Foundation
- **Beat** = exchange of behavior in action/reaction — smallest building blocks of scene turning
- Each beat has: **Action** (what character does), **Gap** (expectation vs reality), **Choice** (decision in response), **Shift** (resulting value change)
- **Arc beat**: a beat contributing to character arc — a moment of growth or degradation
- The **gap** is the soul of story — rift between probability and necessity
- Beats build scenes → sequences → acts

### FM Fields
`id`, `character`, `scene`, `order`, `label`, `action`, `gap`, `choice`, `shift`, `y`, `is_crisis`, `is_climax`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Action** | What the character does | action |
| 2 | **The Gap** | Expectation vs reality, the collision point (McKee's loaded term) | gap |
| 3 | **Choice** | The decision made under pressure | choice |
| 4 | **Value Shift** | How values change as a result | shift, y |
| 5 | **Notes** | Catch-all (flags: crisis/climax) | is_crisis, is_climax |

### Section List
```python
["Action", "The Gap", "Choice", "Value Shift", "Notes"]
```

**Removed:** Development Log  
**Added:** The Gap (proper noun), Value Shift, Notes  
**Preserved:** Action, Choice

---

## Relationship

### Theory Foundation
- **Relationships** are the crucible of character revelation — we discover who someone is through their choices in relationship to others
- **True character** expressed through choice in dilemma — relationships create the pressure that forces those choices
- **Polarization**: cast design principle — contrasting attitudes between characters create conflict
- **Subtext**: relationships operate on two levels — the surface (what's said) and the hidden (what's felt but not expressed)
- **Dramatic irony**: one character knows something the other doesn't — creates tension and audience engagement

### FM Fields
`name`, `characters`, `perspectives` (object with label, feeling, type, strength, secret per character), `scenes`, `status`, `history`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Nature** | The fundamental dynamic — what defines this bond at its core | — |
| 2 | **Perspectives** | Each character's view — label, feeling, type, what's hidden | perspectives |
| 3 | **Tension** | Friction, what creates dramatic potential between them | — |
| 4 | **History** | How the relationship evolved over time | history |
| 5 | **Scenes to Write** | What scenes this relationship needs — not where it happens, but what kind of scenes are necessary (e.g., "we need a confrontation scene") | — |
| 6 | **Notes** | Catch-all | — |

### Section List
```python
["Nature", "Perspectives", "Tension", "History", "Scenes to Write", "Notes"]
```

**Removed:** Description, Dynamics, Scenes  
**Added:** Nature, Perspectives, Tension, Scenes to Write, Notes  
**Preserved:** History

---

## Location

### Theory Foundation
- **Setting as dramatic function** — places exist in story not as backdrop but as active forces that shape character choices and create/attenuate conflict
- **Four dimensions of setting**: Period (time), Duration (length), Location (space), Level of Conflict (inner/personal/extra-personal)
- **Cliché vs originality**: cliché arises from ignorance of the story world. Complete knowledge of a knowable world = creative choices = originality
- **Principle of creative limitation**: fine stories take place within limited, knowable worlds — small = knowable, not trivial
- **Image system**: subliminal communication through repeated visual/auditory motifs — locations carry symbolic weight
- **Mood as emotional register**: atmosphere shapes audience feeling, not just scenery

### FM Fields
`name`, `one_sentence`, `mood`, `dramatic_function`, `world`, `variant_of`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Description** | Sensory surface — what we see, hear, smell | one_sentence |
| 2 | **Atmosphere** | Emotional register, mood, how the place feels | mood |
| 3 | **Image System** | Recurring visual/auditory motifs, symbolic charge | — (not in FM) |
| 4 | **History** | The place's past — what happened here before | — (depth) |
| 5 | **Dramatic Function** | Why this place exists in the story, what choices it shapes | dramatic_function |
| 6 | **Notes** | Catch-all | — |

### Section List
```python
["Description", "Atmosphere", "Image System", "History", "Dramatic Function", "Notes"]
```

**Removed:** —  
**Added:** Notes  
**Preserved:** Description, Atmosphere, Image System, History, Dramatic Function

---

## World

### Theory Foundation
- **Setting as cosmology**: a writer's personal understanding of the world's order, motivations, patterns — "map of life's hidden order"
- **Internal laws**: story must adhere to its own logic and probability — once rules are set, breaking them feels illogical
- **The world as antagonist**: environment (man-made and natural) is a source of extra-personal conflict
- **Values and power**: what a world holds sacred, who holds authority — these create the friction points for character arcs
- **Rituals and customs**: the texture of daily life in this world — what makes it distinct from others
- **Research as originality**: memory + imagination + fact — fuel for invention against cliché

### FM Fields
`name`, `one_sentence`, `rules`, `period`, `values`, `power`, `variant_of`

### Section Map

| # | Section | Thinking Space | Informs FM |
|---|---------|---------------|------------|
| 1 | **Description** | The world as experienced — its surface, its peoples | one_sentence |
| 2 | **History** | How this world came to be, what shaped it | — (depth) |
| 3 | **Livelihood** | How characters earn a living, daily survival | — (texture) |
| 4 | **Power** | Who holds authority and how — the hierarchy of control | power |
| 5 | **Rituals** | Customs, practices, what makes daily life distinct | — (texture) |
| 6 | **Values** | What this world holds sacred, its moral code | values |
| 7 | **Conflict** | The friction points this world creates for characters | — (informs rules) |
| 8 | **Notes** | Catch-all | — |

### Section List
```python
["Description", "History", "Livelihood", "Power", "Rituals", "Values", "Conflict", "Notes"]
```

**Removed:** —  
**Added:** Notes  
**Preserved:** Description, History, Livelihood, Power, Rituals, Values, Conflict

---

## Design Principles Applied

1. **Sections are thinking spaces, not FM field labels** — they invite exploration that may or may not end up in frontmatter
2. **Granularity is lazy** — fewer sections with clear purpose beats many narrow ones (e.g., `Threads` covers four FM fields under one arc)
3. **Order implies a workflow** — Identity → Drives → History → Conflicts → Psychology → Change → Connections → Expression
4. **Notes always last** — catch-all for anything that doesn't fit cleanly elsewhere
