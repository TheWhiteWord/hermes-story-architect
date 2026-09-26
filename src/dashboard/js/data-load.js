window.DASH = window.DASH || {};

DASH.loadFromFile = function() {
  document.getElementById('file-input').click();
}

DASH.handleFileLoad = function(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = jsyaml.load(e.target.result);
      document.getElementById('error-screen').style.display = 'none';
      document.getElementById('loading-screen').style.display = 'flex';
      DASH.initStory(data);
    } catch(err) {
      alert('Could not parse YAML: ' + err.message);
    }
  };
  reader.readAsText(file);
}

DASH.loadSampleData = function() {
  // Sample data in the REAL backend schema (as per brief) — exercises the normaliser
  const sample = {
    project: { name: "The Water Audit", logline: "A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.", genre: "Sci-fi thriller", setting: "Near-future city-state", spine: "", controlling_idea: "", story_value: "", story_value_at_open: "", story_value_at_close: "", inciting_incident_scene_id: "", story_climax_scene_id: "", structure_type: "", scene_count: 3, character_count: 2, location_count: 1, world_count: 1, plot_count: 1 },
    characters: [
      {
        id: "detective-oak", name: "Detective Oak", story_role: "Supporting",
        one_sentence: "Homicide detective investigating the same cartel.",
        sections: ["Personality","Background","Voice","Arc","Relationships"],
        relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }],
        scenes: [{ number: 2, heading: "INT. POLICE STATION - DAY" }, { number: 3, heading: "INT. KITCHEN - NIGHT" }],
        goals: { short: "Bring down the cartel's leadership.", long: "Redeem his failure to protect his last partner." }
      },
      {
        id: "mara", name: "Mara Chen", story_role: "Protagonist", age: 34,
        one_sentence: "Forensic accountant who finds her firm laundering cartel money.",
        sections: ["Personality","Background","Voice","Greatest Fear","Secrets","Arc","Relationships","Goals"],
        relationships: [
          { with: "detective-oak", label: "Partner", type: "ally", strength: 0.4 },
          { with: "victor-hale", label: "Boss", type: "enemy", strength: -0.6 }
        ],
        scenes: [{ number: 1, heading: "INT. MARA'S APARTMENT - NIGHT" }, { number: 3, heading: "INT. KITCHEN - NIGHT" }],
        goals: { short: "Find the account number her brother left behind.", long: "Burn the cartel's financial DASH.network to the ground." },
        knowledge: ["Her brother Daniel was murdered", "Victor Hale is the cartel's CFO"]
      }
    ],
    locations: [
      { id: "kitchen", name: "The Kitchen", one_sentence: "Commercial kitchen in a closed restaurant.", sections: ["Description","History","Scenes"], scenes: ["INT. KITCHEN - NIGHT"] }
    ],
    worlds: [
      { id: "gilead", name: "Gilead", one_sentence: "Near-future city-state where water is privatized.", sections: ["Description","History","Conflict"], rules: ["Water rationing is enforced by biometric scanners.", "Off-grid water extraction is a capital offense.", "The police are funded by AquaCorp."] }
    ],
    plots: [
      {
        id: "brother-investigation", name: "Brother Investigation", status: "active",
        one_sentence: "Mara follows her brother's account number into the cartel's DASH.network.",
        setups: [{ heading: "INT. MARA'S APARTMENT - NIGHT", description: "" }, { heading: "INT. POLICE STATION - DAY", description: "" }],
        payoffs: [{ heading: "INT. KITCHEN - NIGHT", description: "" }],
        characters: ["mara", "detective-oak"],
        sections: ["Summary","Obstacles","Stakes"]
      }
    ],
    scenes: [
      { heading: "INT. MARA'S APARTMENT - NIGHT", scene_number: null, characters: ["mara"], id: 1, locations: [] },
      { heading: "INT. POLICE STATION - DAY", scene_number: null, characters: ["detective-oak"], id: 2, locations: [] },
      { heading: "INT. KITCHEN - NIGHT", scene_number: null, characters: ["detective-oak","mara"], id: 3, locations: ["kitchen"] }
    ],
    story_memory: {
      last_updated: "2026-09-06T14:30:00",
      continuity_risks: ["Mara's skimming hasn't been discovered (ticking clock)", "Oak's investigation is off-books (if his captain finds out, he's burned)"],
      summary: "Mara and Oak are allied but don't fully trust each other. Victor Hale is the cartel's CFO — Mara doesn't know yet."
    },
    relationships: [
      {
        id: "mara-oak",
        name: "Mara & Oak",
        characters: ["mara", "detective-oak"],
        perspectives: {
          mara: { label: "Partner", feeling: "Wary respect — he's useful but unpredictable", type: "ally", strength: 0.4, secret: false },
          "detective-oak": { label: "Partner", feeling: "Brilliant but reckless", type: "ally", strength: 0.5, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
      },
      {
        id: "mara-victor",
        name: "Mara & Victor",
        characters: ["mara", "victor-hale"],
        perspectives: {
          mara: { label: "Boss", feeling: "Fear — he knows what she's found", type: "enemy", strength: -0.6, secret: true },
          "victor-hale": { label: "Employee", feeling: "Useful asset, potential threat", type: "professional", strength: -0.2, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
      }
    ]
  };
  document.getElementById('error-screen').style.display = 'none';
  document.getElementById('loading-screen').style.display = 'flex';
  DASH.initStory(sample);
}
