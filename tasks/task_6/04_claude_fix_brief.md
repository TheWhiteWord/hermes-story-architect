# Dashboard Fix Brief — Claude

> Your dashboard has data structure mismatches with our backend output. Fix them. Add missing functionality. You have full design freedom for all design decisions.

---

## Data Structure

Our `.story/index.yaml` uses a different structure than your sample data. Full example:

```yaml
project:
  name: The Water Audit
  logline: A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.
  genre: Sci-fi thriller
  setting: Near-future city-state
  scene_count: 3
  character_count: 2
  location_count: 1
  world_count: 1
  plot_count: 1

characters:
  - id: detective-oak
    name: Detective Oak
    story_role: Supporting
    one_sentence: Homicide detective investigating the same cartel.
    sections: [Personality, Background, Voice, Arc, Relationships]
    relationships:
      - id: mara
        feeling: Wary respect — she's useful but unpredictable
        label: Partner
    scenes:
      - number: 2
        heading: INT. POLICE STATION - DAY
      - number: 3
        heading: INT. KITCHEN - NIGHT
    goals:
      short: Bring down the cartel's leadership.
      long: Redeem his failure to protect his last partner.
  - id: mara
    name: Mara Chen
    story_role: Protagonist
    one_sentence: Forensic accountant who finds her firm laundering cartel money.
    age: 34
    sections: [Personality, Background, Voice, Greatest Fear, Secrets, Arc, Relationships, Goals]
    relationships:
      - id: detective-oak
        feeling: Wary respect
        label: Partner
      - id: victor-hale
        feeling: Fear — he knows what she's found
        label: Boss
    scenes:
      - number: 1
        heading: INT. MARA'S APARTMENT - NIGHT
      - number: 3
        heading: INT. KITCHEN - NIGHT
    goals:
      short: Find the account number her brother left behind.
      long: Burn the cartel's financial network to the ground.
    knowledge:
      - Her brother Daniel was murdered
      - Victor Hale is the cartel's CFO

locations:
  - id: kitchen
    name: The Kitchen
    one_sentence: Commercial kitchen in a closed restaurant.
    sections: [Description, History, Scenes]
    scenes:
      - INT. KITCHEN - NIGHT

worlds:
  - id: gilead
    name: Gilead
    one_sentence: Near-future city-state where water is privatized.
    sections: [Description, History, Conflict]
    rules:
      - Water rationing is enforced by biometric scanners.
      - Off-grid water extraction is a capital offense.
      - The police are funded by AquaCorp.

plots:
  - id: brother-investigation
    name: Brother Investigation
    status: active
    setups:
      - scene: INT. MARA'S APARTMENT - NIGHT
        description: ""
      - scene: INT. POLICE STATION - DAY
        description: ""
    payoffs:
      - scene: INT. KITCHEN - NIGHT
        description: ""
    characters:
      - mara
      - detective-oak
    sections: [Summary, Obstacles, Stakes]
    one_sentence: Mara follows her brother's account number into the cartel's network.

scenes:
  - heading: INT. MARA'S APARTMENT - NIGHT
    scene_number: null
    characters:
      - mara
    id: 1
    locations: []
  - heading: INT. POLICE STATION - DAY
    scene_number: null
    characters:
      - detective-oak
    id: 2
    locations: []
  - heading: INT. KITCHEN - NIGHT
    scene_number: null
    characters:
      - detective-oak
      - mara
    id: 3
    locations:
      - kitchen

story_memory:
  last_updated: 2026-09-06T14:30:00
  continuity_risks:
    - Mara's skimming hasn't been discovered (ticking clock)
    - Oak's investigation is off-books (if his captain finds out, he's burned)
  summary: Mara and Oak are allied but don't fully trust each other. Victor Hale is the cartel's CFO — Mara doesn't know yet.
```

**Field explanations**:
- `feeling` = emotional tone (how the character feels about the other)
- `label` = relationship type/role (e.g. Partner, Boss, Mentor, Rival, Ally, Enemy)
- `description` = user-provided context for setups/payoffs (initially empty)

---

## Functionality to Add

Your dashboard has 3 views: Characters (graph), Scenes, Story.

Add:
1. **Locations** — view showing all locations from `index.yaml`
2. **Plots** — view showing all plots from `index.yaml`
3. **Worlds** — view showing all worlds from `index.yaml`
4. **Scene content** — when clicking a scene, load the actual Fountain content from `screenplay.md`
5. **Cross-entity navigation** — clicking a character/location/plot name in one entity's detail should open that entity's detail

---

## Output Format

Provide **only code snippets** (CSS + JS) that need to be added or modified. Do NOT rewrite the entire HTML file. For each snippet, indicate:
- Where to add it (e.g., "add this CSS after line 487", "replace the `buildGraphView` function")
- What it does

Keep snippets minimal and focused on the specific fix or feature.

## Known Issue

The current detail panel opens with `position: absolute` and a **transparent background**. In the Hermes preview pane (narrow side panel), this causes the panel to overlap with the existing content underneath — both the panel text and the content behind it become unreadable. Fix this so extended views (character detail, plot detail, scene detail, etc.) are clearly readable when opened in a narrow viewport.

## Graph Observation

The character graph currently only shows characters as nodes. Consider whether other entity types (locations, plots) should also appear as nodes, or if the graph should remain character-only.
