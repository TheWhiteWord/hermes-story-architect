# Task 7: Integration & Real-Project Testing

> End-to-end testing with "Save the Children" — a complex multi-timeline, multi-character, multi-location story.

---

## Test Project: "Save the Children"

**Source**: `/media/theww/AI/TWW/DESK/reference/Save_the_children.md`

**Why this story**: Complex structure with two parallel timelines, multiple locations across different eras, large cast of characters, and layered plot threads — exercises every tool in the plugin.

---

## Subtasks

### Subtask 7.1: Test Project Setup
Create the full story project in vault with:
- 8 characters (protagonist + supporting children + scientists + outsiders)
- 5 locations (Institute rooms across two timelines + outside)
- 2 worlds (The I simulation, Real world 400 years later)
- 4 plots (parallel storylines across timelines)
- 12+ scenes (distributed across both timelines)
- 1 project.md with logline
- 1 screenplay.md with Fountain-formatted scenes
- 1 story memory

**Output**: `~/story-vault/projects/save-the-children/` (or configured vault path)

---

### Subtask 7.2: story_load Test
- Load the project
- Verify index reads correctly
- Verify memory loads
- Confirm scene/character/location counts

---

### Subtask 7.3: story_retrieve Test
- Retrieve specific sections from each entity type
- Test fuzzy project resolution
- Test "all" sections retrieval
- Test missing section handling

---

### Subtask 7.4: story_index Test
- Regenerate index from vault
- Verify cross-references resolve
- Verify scene matching works
- Verify relationship labels appear

---

### Subtask 7.5: story_search Test
- Search for character names
- Search for location references
- Search for plot-specific terms

---

### Subtask 7.6: story_create Test
- Create a new character (e.g., a child inside The I)
- Create a new location (e.g., the Garden)
- Create a new plot (e.g., a discovery thread)
- Verify all validate against REQUIRED_FIELDS

---

### Subtask 7.7: story_edit Test
- Edit a character's frontmatter (change role)
- Edit a character's body section (update Personality)
- Edit screenplay (add a scene)
- Delete an entity (verify recycle bin)
- Verify index updates after each edit

---

### Subtask 7.8: Dashboard Test
- Open dashboard in preview pane
- Verify character graph renders
- Verify scene list populates
- Test navigation between views
- Test detail panel on click
- Verify "Ask Hermes" buttons work

---

### Subtask 7.9: End-to-End Flow
Full workflow:
1. Load project
2. Retrieve protagonist's background
3. Query a character relationship
4. Propose an edit
5. Apply the edit
6. Verify index reflects change
7. Search for the changed content
8. Dashboard shows updated data

---

## Execution Order

```
7.1 (Setup) → 7.2 (load) → 7.3 (retrieve) → 7.4 (index) → 7.5 (search)
    ↓
7.6 (create) → 7.7 (edit) → 7.8 (dashboard) → 7.9 (e2e)
```

Each subtask depends on 7.1 (project setup). Subtasks 7.2-7.5 can run in parallel (read-only). 7.6-7.7 are write operations. 7.8-7.9 require all prior subtasks complete.
