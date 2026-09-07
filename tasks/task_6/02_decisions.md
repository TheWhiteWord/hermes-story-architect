# Task 6: Preview Pane Dashboard — FINAL DECISIONS

> All subtasks resolved. Ready to hand requirements to UI model.

---

## Status: RESOLVED

| Subtask | Status |
|---------|--------|
| 01_dashboard_requirements.md | RESOLVED (revised — views not imposed) |

---

## Key Decision

**Views are NOT imposed.** The UI model decides what views and layouts best serve user needs based on the data, relationships, and constraints provided.

---

## What We Gave the UI Model

1. **Plugin context** — story-writing environment
2. **Data model** — full index.yaml structure
3. **Data relationships** — characters↔scenes, plots↔scenes, etc.
4. **User needs** — what writers need to see (not how to show it)
5. **Interaction model** — clicks, "Ask Hermes" buttons
6. **Hermes desktop conventions** — CSS variables, data-hermes-send, no margins
7. **Technical constraints** — single HTML file, vis-network CDN, fetch()
8. **Visual style** — dark/light via CSS variables, compact, app font

---

## What the UI Model Produces

- `src/dashboard/story-dashboard.html` (single file, embedded CSS/JS)
- Views that answer core user questions
- vis-network for character graph
- "Ask Hermes" buttons with `data-hermes-send`

---

## What happens next

1. Hand `tasks/task_6/01_dashboard_requirements.md` to UI model
2. Review output, iterate
3. Test in Hermes preview pane
4. Proceed to **Task 7 (Integration)**
