# Current State Summary
## Value system (3 independent levels):

### Project level: story_value, story_value_at_open, story_value_at_close
Scene level: value_at_open, value_at_close, shift, y
Character level: character_value, character_value_at_open, character_value_at_close
Plot level: value_arc (Maturation, Redemption, Education, Punitive, Disillusionment, Testing)
Arc beat level: character_value_at_open, character_value_at_close, shift, y
### Plot level:

Plot has plot_scope (main/sub), plot_type (Contradictory, Resonant, Complicating, Setup), value_arc
Plot has 5 computed fields: setups, complications, crisis, climax, resolutions (read from scenes' plot_roles relations)
Scene has a plot_roles field that writes the plot relations
Scene has dramatic_role (plot_role, transition, non-event)
Scene has milestone flags: is_inciting_incident, is_sequence_climax, is_act_climax, is_story_climax
### Structural levels:

Project → Act → Sequence → Scene
Plots are separate entities, linked through scenes' plot_roles
Arc beats are separate entities, linking character and scene
## Issue A: Disconnect between story-level and plot-level
Current design: Plots are separate entities with their own value_arc and plot_type. The structural elements (setup, complication, crisis, climax, resolution) are computed fields on the plot, read from scenes' plot_roles relations. At the same time, scenes carry independent milestone flags (is_inciting_incident, is_story_climax, etc.) that are completely separate from the plot level.

The problem: This creates two parallel structural systems:

Plot level: setups → complications → crisis → climax → resolutions (derived from scenes' plot_roles)
Milestone level: is_inciting_incident, is_sequence_climax, is_act_climax, is_story_climax (stored directly on the scene)
Proposal: The plot (especially the main plot) should define the story-level structural elements. Milestone flags should be derived from the plot level, not stored independently. Specifically:

The main plot's climax scene is the story's climax
The main plot's crisis scene is the story's crisis point
The main plot's setup scene is the story's inciting incident
This way the plot level becomes the single source of structural elements, and milestone flags become derived results rather than independently stored facts.

## Issue B1: Value system belongs at the plot level, not 3 independent levels
Current design: The value system is set independently at 3 levels:

Project level: story_value + story_value_at_open/close
Scene level: value_at_open/close + shift + y
Character level: character_value + character_value_at_open/close
The problem: This causes values to be "preset" rather than "derived". The user sets story_value at project level, then each scene independently sets value_at_open/close, with no propagation mechanism.

Proposal: Values should propagate upward from scenes:

Scene level: each scene evaluates the main values at play in that scene (possibly several)
Sequence level: take the main values from all scenes in that sequence, rank by frequency, take the top 3
Act level: take the main values from all sequences in that act, rank by frequency, take the main one
Story level: take the main values from all acts, rank by frequency, take the main one
The project level can set an "expectation" value as a soft verification — not defining the story's values, but helping to understand whether the expectation was met.

## Issue B2: Value shift schema (P/C/CD/NN)
Current design: A simple positive/negative/mixed/ironic charge, ranging from -1.0 to +1.0.

The problem: This is too simplified and cannot capture McKee's progressive antagonism pattern.

Proposal: Use McKee's P/C/CD/NN schema:

[P] Positive: ideal state
[C] Contrary: direct negation of the positive
[CD] Contradictory: opposite but not absolute negation
[NN] Negation of Negation: negation of the contradictory, often a perverted/false version of the positive
Each value shift should track movement within this schema, not just a positive/negative flip.

## Issue B3: Character arc should not be an independent value system
Current design: arc_beat has its own independent character_value_at_open/close, shift, y, completely separate from the scene's value system.

The problem: This makes the character arc an independent value system, rather than the effect of value changes on the character.

Proposal: The character arc should track how value changes affect the character, not act as an independent value system. Specifically:

Character arc beats should reference the scene's value shift
Character state should be derived from the scene's value shift + the character's historical context + new reflections
The character arc is not a value shift, but the effect of a value shift on the character
Suggested order of work
Issue A: unify the plot level and the milestone system
Issue B1: implement the value propagation mechanism
Issue B2: implement the P/C/CD/NN schema
Issue B3: redesign the character arc system
Each issue should be designed, verified, then implemented. We work through them one at a time, making sure each design is solid before implementation.

Does this summary accurately reflect your thinking? Which issue should we start with in depth?