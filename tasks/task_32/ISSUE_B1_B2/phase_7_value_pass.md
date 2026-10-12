# Phase 7: Value Pass Over Fixture and Test Project

**Goal:** Run the value pass over the fixture and the test project. Note anything the model cannot express.

**Plan reference:** §6 Step 7

## Tasks

### 7.1 — Run the value pass over the fixture
- [ ] Open the fixture project
- [ ] For each scene, identify the values at play
- [ ] Record value turns using the new system
- [ ] Define value schemas on plots where needed
- [ ] Verify the turns read back correctly through `story_retrieve` with `fields=['value_lines']`

### 7.2 — Run the value pass over the test project (if one exists)
- [ ] Same as 7.1 but for the live test project
- [ ] If no test project exists, skip this task

### 7.3 — Note anything the model cannot express
- [ ] Are there value shifts that don't fit the four-rung ladder?
- [ ] Are there effects that don't fit the three conflict levels?
- [ ] Are there values that need more than four words?
- [ ] Is the `from`/`to` vocabulary too coarse or too fine?
- [ ] Note any friction in the recording process

### 7.4 — Final verification
- [ ] Full test suite passes
- [ ] Fixture data is consistent (no orphaned value_turns, all schemas registered)
- [ ] `story_retrieve` with `fields=['value_lines']` returns sensible data for the fixture
- [ ] The dashboard still loads with the updated fixture
- [ ] Export/import round-trip works with value data

## Checklist

- [ ] Value pass run over fixture
- [ ] Value pass run over test project (if applicable)
- [ ] Model limitations noted
- [ ] Full test suite passes
- [ ] Fixture data consistent
- [ ] Dashboard loads with fixture
- [ ] Round-trip works
