"""Build synthetic long stories and bake them into an assembled dashboard.

The Values view only shows its long-story behaviour (level-of-detail marks, the
density hint, act focus, scroll zoom) once a story has enough scenes. This
generates that story, so a layout change can be looked at by eye instead of
argued about.

Shifts are random and deliberately not logical — this is a layout fixture.

Usage:
    # 1. assemble a dashboard from the current plugin (any project will do)
    #    -> writes ~/.hermes/cache/scratch/<project>.html
    # 2. bake synthetic stories into copies of it
    python3 make_long_story.py <assembled.html> [n ...]

    # then serve and open (file:// blocks the CDN scripts the dashboard uses)
    cd <outdir> && python3 -m http.server 8765
    open http://localhost:8765/vg-260.html
"""
import json
import pathlib
import random
import re
import sys

VALUES = [
    ("trust", "trust", "doubt", "betrayal", "paranoia"),
    ("freedom", "free", "bound", "imprisoned", "gilded-cage"),
    ("hope", "hope", "fear", "despair", "delusion"),
    ("solidarity", "unity", "division", "isolation", "mob"),
    ("truth", "truth", "denial", "lie", "fanaticism"),
    ("loyalty", "loyal", "wary", "treachery", "obsession"),
    ("mercy", "mercy", "judgement", "cruelty", "indulgence"),
]
PLOTS = [
    {"id": "the-resistance", "name": "The Resistance", "plot_scope": "main"},
    {"id": "the-scientists", "name": "The Scientists' Last Stand", "plot_scope": "sub"},
    {"id": "the-administrator", "name": "The Administrator's Gambit", "plot_scope": "sub"},
]
CHARACTERS = [
    {"id": "kael", "name": "Kael"},
    {"id": "elena", "name": "Dr. Elena Voss"},
    {"id": "admin", "name": "The Administrator"},
]
ACT_NAMES = ["Act I", "Act II", "Act III"]
SEQ_PER_ACT = 5
ROLES = ["setup", "inciting_incident", "complication", "crisis", "climax", "resolution"]
ROLE_AT = [0.02, 0.10, 0.38, 0.66, 0.86, 0.98]


def served_by(vi):
    """Each value serves two plots, so panels show two colours."""
    return [PLOTS[vi % 3]["id"], PLOTS[(vi + 1) % 3]["id"]]


def build(n, seed=42):
    rng = random.Random(seed)
    acts = [{"id": f"act-{a + 1}", "name": ACT_NAMES[a], "order": a + 1} for a in range(3)]
    sequences = [
        {"id": f"seq-{a + 1}-{q + 1}", "name": f"Sequence {q + 1}", "order": q + 1,
         "parent_id": f"act-{a + 1}"}
        for a in range(3) for q in range(SEQ_PER_ACT)
    ]
    total_seq = 3 * SEQ_PER_ACT
    counters, scenes = {}, []
    for i in range(n):
        si = (i * total_seq) // n
        a, q = si // SEQ_PER_ACT, si % SEQ_PER_ACT
        sid = f"seq-{a + 1}-{q + 1}"
        counters[sid] = counters.get(sid, 0) + 1
        scenes.append({
            "id": f"s{i + 1}", "title": f"Scene {i + 1}", "order": counters[sid],
            "sequence_id": sid, "parent_id": sid, "act_id": f"act-{a + 1}",
            "value_turns": [], "milestone": [], "plots": [],
        })

    # one line per (plot, value): irregular turns, occasional holds and jumps
    for vi, (vname, *words) in enumerate(VALUES):
        for pid in served_by(vi):
            ts = sorted(rng.sample(range(n), min(max(3, n // 14), n)))
            rung = rng.randrange(4)
            for si in ts:
                if rng.random() < 0.18:                     # same state: a hold
                    f_r = t_r = rung
                else:
                    t_r = rng.choice([r for r in range(4) if r != rung])
                    f_r = rung if rng.random() >= 0.22 else rng.choice(
                        [r for r in range(4) if r != rung])  # differs: a jump
                turn = {"plot": pid, "value": vname,
                        "from": words[f_r], "to": words[t_r], "effects": []}
                if rng.random() < 0.45:
                    ch = rng.choice(CHARACTERS)
                    turn["effects"] = [{
                        "character": ch["id"],
                        "levels": [{"conflict_level": rng.choice(
                            ["inner", "personal", "extra-personal"]),
                            "effect": f"{ch['name']} reacts."}],
                    }]
                scenes[si]["value_turns"].append(turn)
                rung = t_r

    # story-level milestones (story view) and per-plot roles (plot view)
    for role, frac in zip(ROLES, ROLE_AT):
        scenes[min(n - 1, int(n * frac))]["milestone"].append(role)
    for pi, plot in enumerate(PLOTS):
        for role, frac in zip(ROLES, ROLE_AT):
            scenes[min(n - 1, int(n * frac) + pi)]["plots"].append(
                {"id": plot["id"], "role": role})

    values = [{"id": v[0], "name": v[0], "p": v[1], "c": v[2], "cd": v[3], "nn": v[4]}
              for v in VALUES]
    plots = []
    for p in PLOTS:
        mine = [VALUES[i][0] for i in range(len(VALUES)) if p["id"] in served_by(i)]
        plots.append({**p, "status": "active",
                      "value_focus": {"major": mine[:2], "minor": mine[2:]}})
    return {
        "project": {"name": f"Synthetic {n}", "value_focus": {
            "major": [{"value": VALUES[i][0]} for i in range(3)],
            "minor": [{"value": VALUES[i][0]} for i in range(3, len(VALUES))]}},
        "acts": acts, "sequences": sequences, "scenes": scenes,
        "values": values, "plots": plots,
        "characters": CHARACTERS, "story_memory": {},
    }


def bake(src_path, n, outdir, seed=42):
    """Write a copy of the assembled dashboard whose story has n scenes."""
    src = pathlib.Path(src_path).read_text()
    pat = re.compile(r"^window\.__STORY_DATA__ = .*$", re.M)
    if len(pat.findall(src)) != 1:
        raise SystemExit(f"{src_path}: expected exactly one __STORY_DATA__ line")
    story = build(n, seed)
    dest = pathlib.Path(outdir) / f"vg-{n}.html"
    dest.write_text(pat.sub(lambda m: "window.__STORY_DATA__ = " + json.dumps(story),
                            src, count=1))
    turns = sum(len(s["value_turns"]) for s in story["scenes"])
    print(f"{dest}: {n} scenes, {turns} turns, {len(story['values'])} values, "
          f"{len(story['plots'])} plots, {len(story['acts'])} acts")
    return dest


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    ns = [int(x) for x in sys.argv[2:]] or [130, 260]
    outdir = pathlib.Path(src).parent
    for n in ns:
        bake(src, n, outdir)


if __name__ == "__main__":
    main()
