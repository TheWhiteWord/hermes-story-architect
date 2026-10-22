# Story Value Tracking System: Design Document

Design document, Draft 1, October 9, 2026. Based on Robert McKee's *Story* (condensed version) and the design discussion that followed.

## 1. Purpose

A system for tracking how values change across a story, scene by scene, so that dramatic structure (setup, inciting incident, complications, crisis, climax, resolution) can be identified, verified, and revised at every level: scene, sequence, act, and story.

It must work for two kinds of writers:

- **Planners**, who define the climax and story value before writing.
- **Discovery writers**, who write first and find the climax afterwards.

## 2. Theoretical foundation (McKee)

| Unit | Definition | Impact |
| --- | --- | --- |
| Scene | Action driven by conflict, in continuous time and space, that turns the value-charged condition of a character's life on at least one value. Ideally a story event. | Minor but significant change |
| Sequence | Series of scenes culminating in a scene with greater impact than any preceding scene. | Moderate reversal |
| Act | Series of sequences peaking in a climactic scene, more powerful than any previous sequence or scene. | Major reversal |
| Story | Series of acts culminating in a story climax that brings absolute and irreversible change. | Absolute, irreversible change |

Key rules carried into the design:

- **"No scene that doesn't turn."** A scene with no value change is a non-event.
- **Every level has its own crisis, climax, and resolution.** The five-part pattern repeats at each level.
- **The story climax is the final act climax.** It is a value swing at maximum charge that is absolute and irreversible, with or without irony.

### 2.1 Schema of antagonism

Each value has four states, ordered by depth of negation:

| Code | Name | Meaning | Example (justice) |
| --- | --- | --- | --- |
| P | Positive | The ideal state | Justice |
| C | Contrary | Opposite, but not absolute negation | Unfairness |
| CD | Contradictory | Direct negation of the positive | Injustice |
| NN | Negation of negation | Perversion or false version of the positive | Tyranny
### 2.2 Concentric circles of conflict (conflict_levels)

1. **Inner:** mind, body, emotions (self as antagonist).
2. **Personal:** intimate relationships (family, lovers, friends).
3. **Extra-personal:** institutions, social roles, environment.

**Conflict_levels** are **not** a category of value. The same value can be contested on several conflict_levels at once.

## 3. Core design principles

1. **Plan and observation are stored separately.** The writer's intent is one layer, what the scenes actually contain is another, and analysis is derived by comparing them.
2. **Derive, don't hand-enter.** Climaxes, rankings, and the story value are computed from scene data wherever possible.
3. **Every plan field is optional.** Partial plans are valid.
4. **Provenance on every tag.** Each role tag records whether it was declared, detected, or confirmed.
5. **Equal weight per unit.** Each sequence counts once toward its act, and each act once toward the story, regardless of how many scenes or sequences it contains. Roll-ups use full profiles, never truncated lists.
6. **Same value can have several lines.** A value can be tracked on several conflict_levels as independent lines.

## 4. Value model

### 4.1 Numeric scale

To compute shifts, each schema state maps to a number. The default scale (configurable per project):

| State | Score |
| --- | --- |
| P | +2 |
| Mixed | 0 |
| C | -1 |
| CD | -2 |
| NN | -3 |

A scene's **turn** on a value line is `Δ = close - open`. Magnitude is `|Δ|`. A sign change (positive to negative, or the reverse) is flagged as a **crossing**.

### 4.2 Value lines

A value line is one value tracked on one arena within one plot. Example for a detective story:

| Line | Value | Arena | What it measures |
| --- | --- | --- | --- |
| A | Justice (inner) | Inner | His faith and integrity |
| B | Justice (outer) | Extra-personal | Whether the system or criminal is actually held to account |
| C | Love / trust | Personal | A relationship that may pay the cost |

Lines A and B are the same value on different conflict_levels, because they can move independently. A story can end with A positive (he believes again) while B stays negative (the system still fails).

### 4.3 Positive-to-positive arcs

A story may start and end on the positive and still contain a full arc (a redemptive or "tested faith" shape). The system therefore:

- stores the **full trajectory** of each line, not just the first and last state;
- measures the story climax from the **pre-climax state to the post-climax state**;
- records **how the end differs from the start**: naive versus earned, different object of the value (line A versus line B), or an ironic cost on another line.

### 4.4 Ironic climaxes

A climax is **ironic** when two or more lines in the same scene move in opposite directions (for example A: negative to positive, C: positive to negative). Such a scene carries more than one tagged charge. The meaning of the story (the Controlling Idea) often lives in that tension.

## 5. Notes on Data model

A scene can belong to several plots, and one scene can have several SceneTurn rows. This is a many-to-many structure by design.

## 6. Derivation rules

### 6.1 Scene

- A scene is a **non-event** if every SceneTurn on it has Δ = 0.
- The scene's impact is the largest |Δ| among its lines, weighted by the story value if one is set.

### 6.2 Sequence climax

The last scene of a sequence whose |Δ| is greater than every earlier scene in that sequence. If the strongest scene is not the last, flag the sequence as having a misplaced climax.

### 6.3 Act climax

The last scene of an act that satisfies all of:

1. Its |Δ| exceeds every previous scene and sequence climax in the story so far.
2. It turns the **story value** (the central value of the plot).
3. It redirects the progression into the next act.

Every act climax is also a sequence climax and a scene turn, but not the reverse.

### 6.4 Story climax

The final act climax of the plot, where:

1. It is the global maximum |Δ| of the plot.
2. It turns the story value, and reaches the furthest point on the schema (strongest positive, or the deepest negation).
3. It is **absolute and irreversible**: no later scene turns that line back, except for resolution consequences.

The **story value** is therefore defined top-down by the story climax.

### 6.5 Other dramatic roles

The opening state, crisis, and resolution cannot be derived from value shifts alone:

| Role | Detectable from values? | How it is identified |
| --- | --- | --- |
| Setup/s (Opening state) | Partly | The balance of values before the inciting incident; these scenes may have no turn, and they establish the baseline against which the first turn is measured |
| Inciting incident | Yes | First major turn that upsets the balance and arouses a desire; the protagonist must react to it. Each plot, act, and sequence has its own |
| Complication/s | Mostly | Run of turns with rising magnitude and risk |
| Crisis | No | A dilemma and decision, tagged by the writer or confirmed from a proposal |
| Climax | Yes | Peak |
| Resolution | No | Post-climax aftermath with little or no new turn |

The value data validates the tags (for example, a "climax" with a small Δ is flagged), but crisis and resolution are tagged by role, not computed.

### 6.6 Normalized value profile

Every unit counts once at the next level up, however many scenes or sequences it contains. Value weights are therefore computed as normalized profiles that roll up level by level:

1. **Scene profile.** Each value line's share is its |Δ| divided by the total |Δ| of the scene, so a scene's shares sum to 1. A non-event scene has no profile and is left out of the averages (it is flagged by the checks in section 8).
2. **Sequence profile.** The average of its scenes' profiles.
3. **Act profile.** The average of its sequences' profiles.
4. **Plot profile.** The average of its acts' profiles.

Every profile sums to 1, so units of different lengths and pacing compare directly. Lines of the same value are summed when reporting by value.

- The full profile is stored at every level, and a ranking is just that profile sorted. No cutoff (such as a top 3) is applied, so a value that stays minor but runs through the whole story keeps its share.
- The **dominant values** (bottom-up profile) are shown beside the **story value** (top-down, from the story climax). When they differ, that is reported as a finding.

### 6.7 Subplots

Each plot has its own roles, climaxes, and rankings. The story-level value is taken from the main plot, but subplot values are always retained, because subplots often counterpoint the main plot, and the comparison between them is where the thematic argument appears.

## 7. Workflows

### 7.1 Planner (top-down)

1. Fill in the Plan: story value, intended arc, planned climaxes (partial is fine).
2. Write and log scenes.
3. The system compares planned versus detected climaxes and reports mismatches.
4. Revise scenes that fail to deliver.

### 7.2 Discovery writer (bottom-up)

1. Skip the Plan.
2. Write and log scenes.
3. The system **proposes** climaxes and a story value from the data.
4. The writer accepts, rejects, or reassigns each proposal (for example, "that is a sequence climax, the act climax is the later scene").
5. Confirmed proposals become the Plan for the next draft.

### 7.3 Provenance and drafts

- Every role tag has a source: **declared**, **detected**, or **confirmed**.
- Data is stored per draft, so the history of how a climax moved is visible.
- Detection is **provisional** on incomplete units. Climaxes are proposed only for units the writer marks complete.

## 8. Automatic checks

These run with or without a plan:

1. Non-event scenes (Δ = 0).
2. Planned climax whose |Δ| is not the largest in its unit.
3. Sequence whose strongest scene is not its last.
4. Act climaxes that do not escalate.
5. story value differs between the plan and the detected story climax.
6. Dominant value differs from the story value.
7. Subplot lines that never resolve.
8. Positive-to-positive arcs where the end state is identical to the start (no earned difference recorded).
9. Ironic climaxes: opposite-signed Δ on two or more lines (informational, not an error).

## 9. Open questions and caveats
- Beats (action and reaction exchanges) are not tracked in this version. They could be added as a level below the scene. **RESOLVED**: Maybe later, not now.
- The positive side of the schema has a single level here. If a story needs gradations of positive (for example, hope versus fulfilment), the scale needs extending. **RESOLVED**: Not necessary.
