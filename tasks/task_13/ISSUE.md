Issue: Premature Split of Project Index into Two Files
What was done
The project index was split into two files:

index.yaml — navigation data (entities, cross-references, counts)
structure-index.yaml — dramatic metadata (value arcs, spine, controlling idea, dramatic roles, plot tracking)
Why the original motivation was wrong
The split was motivated by the assumption that loading the project would always load the entire index, and that splitting would reduce context passed to the LLM. This was incorrect because:

Context savings are identical either way. Whether you split files or filter a single file, the LLM receives the same filtered subset of data for any given task. The two-file approach doesn't save tokens — it just moves the filter boundary from the tool layer (projection/filtering) to the filesystem (physical separation).

The real cost: maintenance burden
Every new field requires a classification decision: "Does this go in index.yaml or structure-index.yaml?" This is a permanent tax. The split introduced:

Sync complexity — two files must be regenerated in lockstep, kept in sync, and read by different consumers
Dual generation logic — generate_index() and generate_structure_index() with duplicated iteration and classification scattered across both
Split load paths — story_load needs a structure_only param to work around the split; dashboard injects two separate globals; stats panels pull from both
Classification ambiguity — plot tracking, value arcs, and dramatic roles have no clear "home" — they're structural metadata that serves both navigation and analysis, so the split forces arbitrary placement
What should be done instead
One index, filtered views.

Single index.yaml holds all project data — navigation, dramatic metadata, plot tracking, value arcs, everything
Tool layer (e.g., story_load) applies field filters based on the task context, returning only the relevant projection
No classification decisions when adding fields — everything lives in one place
Dashboard reads one global, stats panels pull from one source
Key principle
Filter at the consumer, not at the source. The index is the source of truth — complete and unified. Each consumer (LLM tool, dashboard, stats panel) takes what it needs via projection. The boundary between "navigation" and "structural" data is a consumer concern, not a storage concern.