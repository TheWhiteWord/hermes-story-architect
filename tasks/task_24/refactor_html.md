# Story Dashboard — Architectural Refactoring

You are refactoring an existing Story Dashboard frontend used as part of a Hermes Harness plugin.

The current dashboard is a single HTML file of approximately 4,300 lines. It contains:

* HTML structure
* a large inline stylesheet
* application state
* story-data loading
* data normalization
* navigation
* multiple views
* detail/expansion panels
* screenplay rendering
* statistics
* D3 charts
* vis-network graph functionality
* character arc visualization
* event handlers
* reusable rendering helpers
* Hermes integration buttons/actions

The goal is to **refactor the application into a maintainable modular frontend without changing its behavior or visual design**.

This is an architectural refactor, not a redesign and not a rewrite.

---

## 1. PRIMARY OBJECTIVE

Transform the current monolithic dashboard into a logically organized set of files/modules with clear responsibilities.

The resulting application should be easier to:

* understand
* navigate
* debug
* modify
* extend with new dashboard views
* modify individual panels independently
* reuse common UI/rendering functionality
* reason about application state
* maintain CSS
* test individual pieces

The most important requirement is:

> **Improve the architecture without changing what the application does.**

The refactored dashboard must preserve existing:

* functionality
* UI behavior
* navigation
* visual appearance
* data interpretation
* data structures
* story-data contracts
* Hermes integration
* graph behavior
* statistics
* screenplay rendering
* panel behavior
* responsive behavior
* loading/error behavior
* sample-data behavior

Do not use the refactor as an opportunity to redesign the UI.

---

# 2. FIRST: ANALYZE BEFORE MODIFYING

Before making substantial changes, inspect the entire existing dashboard and understand it.

Do NOT immediately start moving code into files.

First identify:

### Application responsibilities

Map where the current application handles:

* application boot
* story data loading
* file loading
* injected Hermes data
* story initialization
* data normalization
* global/application state
* navigation
* view activation
* graph construction
* scene rendering
* location rendering
* plot rendering
* sequence rendering
* act rendering
* relationship rendering
* world rendering
* story overview
* detail panels
* panel content generation
* common section rendering
* screenplay rendering
* statistics
* D3 charts
* character arcs
* tooltips
* sorting
* formatting
* HTML escaping
* Hermes actions
* responsive behavior

Also identify:

* shared state
* shared DOM elements
* shared rendering functions
* duplicated logic
* functions that are similar but semantically different
* dependencies between views
* dependencies between panels
* dependencies on global variables
* implicit coupling
* event-handler coupling
* functions that currently depend on declaration order
* code that relies on globals such as `window.__STORY_DATA__`, `window.__SECTIONS__`, `window.__SCREENPLAY_TEXT__`, `window.__SCREENPLAY_STATS__`, or `window.__STRUCTURAL_STATS__`

Create an internal dependency map before performing the refactor.

---

# 3. DO NOT FORCE A FRAMEWORK

Do not introduce React, Vue, Svelte, TypeScript, a bundler, npm dependencies, or another frontend framework unless the existing plugin architecture demonstrably requires it and there is a compelling reason.

This dashboard currently operates as a relatively lightweight browser application.

Prefer:

* standard HTML
* standard CSS
* modern JavaScript modules
* ES module imports/exports
* small focused modules

if the Hermes environment supports them.

However:

> **First verify how Hermes loads this dashboard and what restrictions exist on external/local JavaScript modules.**

Do not assume that `type="module"` or arbitrary relative imports will work inside Hermes.

If the runtime requires a different architecture, adapt to the runtime rather than blindly applying a browser-app template.

---

# 4. PRESERVE THE EXISTING DATA CONTRACT

The dashboard receives story data from the surrounding Hermes/plugin environment.

Do not change the structure or meaning of the data merely to make the refactor easier.

In particular, treat existing injected data and integration contracts as external APIs.

Examples include:

* `window.__STORY_DATA__`
* `window.__SECTIONS__`
* `window.__SCREENPLAY_TEXT__`
* `window.__SCREENPLAY_STATS__`
* `window.__STRUCTURAL_STATS__`

and any other values supplied by the surrounding application.

If an abstraction around these values is useful, create one deliberately, for example:

```text
data/
    story-data.js
```

or another appropriate name.

But the external contract must remain unchanged unless there is an explicit requirement to change it.

---

# 5. TARGET ARCHITECTURE

Do not blindly copy this exact structure.

Use it as a conceptual starting point and adjust it based on the actual dependencies discovered during analysis.

A reasonable target may resemble:

```text
story-dashboard/
│
├── index.html
│
├── css/
│   ├── base.css
│   ├── layout.css
│   ├── components.css
│   ├── views.css
│   ├── panels.css
│   ├── screenplay.css
│   ├── statistics.css
│   ├── graph.css
│   └── arc-graph.css
│
└── js/
    ├── app.js
    │
    ├── state/
    │   └── app-state.js
    │
    ├── data/
    │   ├── story-data.js
    │   └── normalize.js
    │
    ├── navigation/
    │   └── navigation.js
    │
    ├── views/
    │   ├── story-view.js
    │   ├── graph-view.js
    │   ├── scenes-view.js
    │   ├── locations-view.js
    │   ├── plots-view.js
    │   ├── sequences-view.js
    │   ├── acts-view.js
    │   ├── relationships-view.js
    │   ├── worlds-view.js
    │   └── script-view.js
    │
    ├── panels/
    │   ├── panel-manager.js
    │   ├── character-panel.js
    │   ├── scene-panel.js
    │   ├── location-panel.js
    │   ├── plot-panel.js
    │   ├── relationship-panel.js
    │   ├── sequence-panel.js
    │   ├── act-panel.js
    │   └── world-panel.js
    │
    ├── statistics/
    │   ├── statistics-panel.js
    │   ├── statistics-renderer.js
    │   └── charts/
    │       ├── duration-chart.js
    │       ├── character-chart.js
    │       └── barcode-chart.js
    │
    ├── graph/
    │   ├── network-graph.js
    │   ├── graph-tabs.js
    │   └── arc-graph.js
    │
    ├── components/
    │   ├── tags.js
    │   ├── badges.js
    │   ├── empty-state.js
    │   └── ...
    │
    └── utils/
        ├── dom.js
        ├── html.js
        ├── formatting.js
        └── ...
```

This is NOT a requirement to create all these files.

Use fewer files where that produces a cleaner architecture.

Use more files where a genuinely independent responsibility warrants it.

The architecture should follow **responsibility and dependency boundaries**, not arbitrary line counts.

---

# 6. AVOID BOTH EXTREMES

Do NOT produce either of these:

### Bad approach A — cosmetic splitting

For example:

```text
dashboard.js
dashboard-part1.js
dashboard-part2.js
dashboard-part3.js
dashboard-part4.js
```

where the files remain tightly coupled and effectively behave like one giant script.

This does not constitute meaningful modularization.

### Bad approach B — excessive fragmentation

Do not create dozens of tiny modules such as:

```text
render-name.js
render-title.js
render-tag.js
create-div.js
create-button.js
get-color.js
get-label.js
...
```

just because individual functions exist.

A module should represent a meaningful responsibility.

---

# 7. MODULE DESIGN PRINCIPLE

Use this rule:

> A module should have a coherent reason to change.

For example:

* graph behavior changes → graph module
* statistics behavior changes → statistics module
* character detail panel changes → character panel module
* story data normalization changes → normalization module
* navigation changes → navigation module
* common HTML escaping changes → HTML utility

Do not extract code solely because it is long.

---

# 8. SHARED CODE

Carefully identify code that is genuinely shared.

Examples worth considering for shared modules:

* HTML escaping
* DOM lookup/manipulation helpers
* duration formatting
* common tag rendering
* role/color lookup
* common badges
* common empty states
* common panel lifecycle
* common section rendering
* shared data lookup
* common formatting

Avoid duplication.

However:

> Do not combine two pieces of code merely because they currently look similar.

If two functions have different semantics or are likely to evolve independently, keep them separate.

Prefer:

```text
shared abstraction when semantics are shared
```

rather than:

```text
shared abstraction whenever code happens to look similar
```

Avoid "god utilities" such as:

```text
utils.js
helpers.js
common.js
misc.js
```

containing unrelated functionality.

If a utility module grows into unrelated responsibilities, split it by concept.

---

# 9. STATE MANAGEMENT

The current application has shared application state.

Do not leave a large collection of mutable globals scattered throughout modules.

Identify the actual application state and centralize it where appropriate.

For example:

```js
const state = {
    story,
    currentView,
    selectedEntity,
    sidebarExpanded,
    ...
};
```

But do not create an elaborate state-management framework.

The goal is simply to make:

* ownership
* mutation
* reading
* dependencies

clear.

Prefer explicit dependencies over hidden global dependencies.

If a module needs access to story data, make that relationship clear.

Do not pass enormous objects through every function merely to avoid a global.

Use good judgment.

---

# 10. RENDERING VS APPLICATION LOGIC

Where appropriate, separate:

```text
data transformation
```

from:

```text
DOM rendering
```

and from:

```text
event handling
```

For example, avoid a single function becoming:

```text
retrieve data
→ transform data
→ mutate global state
→ construct HTML
→ attach events
→ perform navigation
```

if those responsibilities can reasonably be separated.

However, do not abstract every function into separate layers.

The goal is **clear boundaries**, not architectural ceremony.

---

# 11. VIEWS

Each major dashboard view should have a clear owner.

The current application has views such as:

* Story
* Characters / graph
* Relationships
* Scenes
* Locations
* Plots
* Sequences
* Acts
* Worlds
* Script

Give each view a module when appropriate.

A view module should ideally own:

* its rendering
* its view-specific event handling
* its view-specific state
* its view-specific helpers

It should not secretly modify unrelated views.

Shared functionality should go through shared modules.

---

# 12. DETAIL / EXPANSION PANELS

The detail panel is an important architectural boundary.

There is a shared panel mechanism and multiple entity-specific panel renderers.

Keep those concepts separate.

For example:

```text
panel-manager
    owns opening / closing / lifecycle

character-panel
    owns character-specific content

scene-panel
    owns scene-specific content

relationship-panel
    owns relationship-specific content
```

Do not duplicate the open/close/DOM lifecycle code in every panel.

Likewise, do not make the panel manager understand every field of every entity.

The panel manager should manage the panel.

The entity panel should render the entity.

---

# 13. STATISTICS

Statistics should be treated as its own subsystem.

The current dashboard includes:

* statistics panel
* statistics groups
* overview statistics
* character statistics
* scene statistics
* structural statistics
* duration information
* D3 visualizations
* tables
* sorting
* charts

Keep those responsibilities together conceptually, while separating genuinely independent chart implementations where useful.

For example:

```text
statistics/
    statistics-panel.js
    statistics-data.js
    charts/
        duration-chart.js
        character-chart.js
        barcode-chart.js
```

Do not make every individual statistic its own module.

---

# 14. GRAPH / ARC GRAPH

The graph system should be isolated from unrelated dashboard views.

The current graph functionality includes:

* vis-network
* character nodes
* relationship edges
* relationship strength/proximity behavior
* graph tabs
* character arc visualization
* arc controls
* arc legends
* arc tooltips
* spline/label controls

Keep these concerns together but distinguish:

```text
network graph
```

from:

```text
character arc graph
```

where that improves clarity.

Third-party library integration should not leak unnecessarily into unrelated application modules.

For example, normal application code should not need to know how vis-network is configured internally.

---

# 15. CSS REFACTOR

The CSS should also be modularized.

Do not simply move the entire `<style>` block into one `dashboard.css`.

Identify meaningful CSS layers.

At minimum consider separating:

```text
base / tokens
layout
shared components
views
panels
screenplay
statistics
graph
arc graph
responsive rules
```

The exact structure should follow the actual dashboard.

Preserve the existing visual appearance.

Do not perform a visual redesign while reorganizing CSS.

---

# 16. CSS NAMING

Preserve existing class names where possible.

Do not rename hundreds of classes just to impose a naming methodology.

If introducing a convention, use it consistently for new or substantially reorganized code.

Prefer semantic naming.

Avoid names based purely on appearance such as:

```text
.blue-box
.left-thing
.big-panel
```

Prefer:

```text
.panel-header
.character-card
.stats-group
.arc-legend
```

The existing dashboard already uses many semantic names, so preserve that strength.

---

# 17. HTML STRUCTURE

Move the static HTML into a clean `index.html` or equivalent entry document.

Keep the document responsible primarily for:

* application shell
* stable containers
* navigation
* view mounting points
* panel mounting points
* loading/error states

Dynamic content should remain generated by JavaScript where it currently is.

Do not convert the entire application to static HTML simply because the HTML is being separated from the JavaScript.

Likewise, do not dynamically generate the entire application shell if there is no architectural reason to do so.

---

# 18. EVENT HANDLING

The existing application contains inline handlers such as:

```html
onclick="switchView(...)"
```

Evaluate whether these should be replaced with module-owned event listeners.

Prefer modern event handling where it genuinely improves architecture.

For example:

```js
button.addEventListener('click', ...)
```

or event delegation where appropriate.

However, do not mechanically replace every inline handler without understanding the existing lifecycle and Hermes environment.

The important thing is that event ownership becomes clear.

---

# 19. HERMES INTEGRATION

Preserve all existing Hermes integration.

In particular, do not break:

```html
data-hermes-send="..."
```

or whatever mechanism the surrounding Hermes environment uses.

Treat Hermes-provided attributes, globals, and integration hooks as external contracts.

Do not replace them with a hypothetical API.

If integration behavior is unclear, inspect the surrounding plugin code before modifying it.

---

# 20. EXTERNAL LIBRARIES

Preserve existing dependencies unless there is a concrete reason to change them.

The dashboard currently uses external libraries including:

* vis-network
* js-yaml
* D3

Do not replace these simply for architectural cleanliness.

If modules need access to these libraries, choose the loading strategy that is compatible with the Hermes runtime.

---

# 21. ERROR HANDLING

Do not remove existing error handling.

Preserve:

* loading state
* missing story-index behavior
* manual file loading
* sample-data preview
* graceful empty states
* missing optional data handling

If the refactor reveals opportunities to make error handling clearer, improve it without changing externally visible behavior.

---

# 22. NAMING CONVENTIONS

Use consistent naming.

### JavaScript

Use:

```text
camelCase
```

for variables and functions.

Use:

```text
PascalCase
```

only for classes/constructors if classes are actually appropriate.

Use descriptive names.

Prefer:

```js
renderCharacterPanel()
```

over:

```js
doChar()
```

Prefer:

```js
characterPanel.js
```

over:

```js
char.js
```

unless the existing domain vocabulary strongly favors the shorter form.

### Files

Use consistent kebab-case or another single convention.

For example:

```text
character-panel.js
relationship-panel.js
arc-graph.js
story-view.js
```

Do not mix:

```text
characterPanel.js
relationship-panel.js
ArcGraph.js
story_view.js
```

### CSS

Use the existing semantic vocabulary where possible.

Do not rename everything merely for stylistic consistency.

---

# 23. DEPENDENCY DIRECTION

Avoid circular dependencies.

Prefer a dependency direction similar to:

```text
entry point
    ↓
application/state
    ↓
views / panels / subsystems
    ↓
shared utilities
```

Data/model utilities should not depend on UI modules.

Low-level utilities should not import application-specific panels.

A character panel should not import the graph merely to obtain a color if that color can be supplied by a shared domain utility.

If circular dependencies appear, stop and reconsider the boundaries rather than patching around them.

---

# 24. AVOID PREMATURE ABSTRACTION

Do not create abstractions merely because they are theoretically reusable.

For example, do not create:

```js
createGenericEntityPanel()
```

unless the existing entity panels genuinely share a stable semantic structure.

Likewise, do not build a generic rendering framework.

Prefer simple, explicit code over a sophisticated abstraction that makes the dashboard harder to understand.

---

# 25. PRESERVE COMPLEX LOGIC

Some parts of this application are inherently complex.

Do not simplify complex algorithms merely because they make the refactor harder.

In particular, do not rewrite or "simplify":

* graph layout logic
* relationship calculations
* arc graph calculations
* D3 chart logic
* screenplay rendering
* story-data normalization
* structural-statistics calculations

unless required to establish module boundaries.

If existing code is complex but correct, move it with minimal semantic changes first.

Improving its internal algorithm is a separate task.

---

# 26. REFACTOR IN STAGES

Do not attempt a blind all-at-once rewrite.

Use a staged process.

### Stage 1 — Analyze

Document:

* current architecture
* major responsibilities
* dependencies
* global state
* shared utilities
* view boundaries
* panel boundaries
* third-party integrations

### Stage 2 — Establish the shell

Separate:

* HTML
* CSS
* JavaScript

without changing behavior.

### Stage 3 — Establish shared foundations

Extract:

* state
* data access
* normalization
* DOM utilities
* HTML escaping
* formatting
* shared rendering helpers

only where justified.

### Stage 4 — Extract views

Move major views one at a time.

After each extraction verify that the application still behaves correctly.

### Stage 5 — Extract panels

Move the shared panel lifecycle and entity-specific panels.

### Stage 6 — Extract specialized systems

Move:

* statistics
* charts
* network graph
* arc graph
* screenplay rendering

### Stage 7 — Cleanup

Only after behavior is preserved:

* remove obsolete code
* remove duplicate code
* resolve naming inconsistencies
* simplify imports
* document non-obvious dependencies

---

# 27. VALIDATION IS PART OF THE REFACTOR

Do not consider the task complete merely because the files are smaller.

After refactoring, verify:

### Application startup

* dashboard loads
* story data loads
* injected story data works
* fallback file loading works
* sample data works
* loading state works
* error state works

### Navigation

Test every navigation item.

### Views

Verify every view renders correctly.

### Panels

Open every type of detail panel.

Verify:

* opening
* closing
* content
* entity links
* nested navigation
* Hermes actions

### Graph

Verify:

* nodes
* edges
* relationship strength
* layout
* graph tabs
* arc graph
* arc controls
* tooltips
* character selection

### Statistics

Verify:

* all groups
* charts
* tables
* sorting
* structural statistics
* duration statistics

### Script

Verify:

* screenplay content
* title page
* scene headings
* scene navigation
* formatting
* page breaks
* dual dialogue
* empty state

### Responsive behavior

Verify narrow and wide layouts.

---

# 28. REGRESSION SAFETY

Before declaring the refactor complete:

1. Compare the old and new application behavior.
2. Search for functions from the original implementation and verify that every responsibility has a deliberate destination.
3. Search for DOM IDs/classes used by JavaScript and verify they still exist.
4. Search for event handlers and verify they remain connected.
5. Search for global variables and verify external contracts remain intact.
6. Check for browser console errors.
7. Check for failed module imports/resources.
8. Check for duplicate implementations accidentally left behind.
9. Check for circular dependencies.
10. Check that no functionality was silently dropped.

Do not delete old code simply because it looks redundant until you have established that its responsibility is covered elsewhere.

---

# 29. KEEP A REFACTORING MAP

Before and during the refactor, maintain a concise mapping such as:

```text
OLD FUNCTION / RESPONSIBILITY
        ↓
NEW MODULE / FUNCTION
```

For example:

```text
boot()
    → app/bootstrap.js

normalise()
    → data/normalize.js

switchView()
    → navigation/navigation.js

buildScenesView()
    → views/scenes-view.js

showCharacterPanel()
    → panels/character-panel.js

openPanel()
    → panels/panel-manager.js

renderDurationChart()
    → statistics/charts/duration-chart.js

buildArcGraph()
    → graph/arc-graph.js
```

The exact mapping should be based on the actual implementation.

This is important because the original file contains many responsibilities intertwined in one script.

---

# 30. DO NOT CHANGE FUNCTIONALITY TO MAKE THE REFACTOR EASIER

This is a hard requirement.

Do not:

* remove features
* remove edge cases
* change data structures
* change calculations
* change graph behavior
* change visual styling
* change labels
* remove empty states
* remove error handling
* replace complex code with a less capable implementation
* remove functionality that appears unused without proving it is unused
* change Hermes integration
* change the story-data schema

If something appears unnecessarily complicated, preserve it unless there is strong evidence that it is dead code.

A later cleanup can be a separate task.

---

# 31. IMPORTANT: DO NOT OPTIMIZE FOR LINE COUNT

The objective is not:

> "Make the code shorter."

The objective is:

> "Make responsibilities explicit and the codebase easier to maintain."

A good refactor may produce more total lines because:

* imports/exports become explicit
* modules have clearer boundaries
* CSS becomes organized
* functions become more focused
* repeated logic is centralized
* responsibilities become easier to locate

That is acceptable.

A 20-line abstraction that makes a simple 5-line operation difficult is not an improvement.

---

# 32. FINAL ARCHITECTURAL REVIEW

After implementation, review the resulting architecture as if another developer had to maintain it for several years.

Ask:

* Can I find the implementation of each dashboard view quickly?
* Can I find each detail panel quickly?
* Is application state obvious?
* Is data normalization separate from presentation?
* Is shared code genuinely shared?
* Is duplicated code minimized?
* Are modules cohesive?
* Are dependencies understandable?
* Are there circular dependencies?
* Are utilities appropriately scoped?
* Is there any "god module" that became the new monolith?
* Is there any abstraction that exists only to make the architecture look sophisticated?
* Can a developer add a new view without understanding the entire application?
* Can a developer modify the character panel without touching unrelated systems?
* Can the graph implementation evolve independently?
* Can the statistics subsystem evolve independently?
* Is the HTML entry point easy to understand?
* Is the CSS easy to locate by feature?
* Does the application still behave exactly as before?

If any answer is poor, improve the architecture before considering the refactor complete.

---

# 33. DELIVERABLES

At the end provide:

### A. Final file tree

Show the complete resulting structure.

### B. Architecture summary

Briefly explain the responsibility of each major directory/module.

### C. Refactoring map

Show the important old responsibilities/functions and where they moved.

### D. Shared-code decisions

Explain:

* what was extracted as shared
* why it is genuinely shared
* what similar-looking code was intentionally kept separate
* why

### E. State/dependency decisions

Explain:

* where application state lives
* how modules access story data
* how dependencies flow
* how circular dependencies were avoided

### F. Runtime compatibility

Explain how the modular files are loaded by the Hermes environment and why the chosen loading mechanism is compatible.

### G. Validation

List the functionality that was checked and any remaining limitations.

---

# FINAL PRINCIPLE

The standard for success is NOT:

> "The 4,300-line HTML became many smaller files."

The standard is:

> "The application now has clear architectural boundaries, shared functionality is actually shared, independent functionality remains independent, dependencies are explicit, the code is easier to locate and modify, and the dashboard behaves exactly as it did before."

When in doubt, choose the solution that makes the **domain structure of the Story Dashboard more obvious**, not the solution that produces the largest number of files.

Before making destructive changes, understand the existing implementation completely.

Preserve behavior first. Improve architecture second. Optimize or redesign only in a separate task.
