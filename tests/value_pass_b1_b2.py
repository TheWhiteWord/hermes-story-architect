"""Phase 7 value pass over the save-the-children fixture.

Markdown is the fixture's source of truth (conftest builds the DB from it), so
the pass writes the notes, then a COPY is imported to exercise the real write
path (validation + inline-schema registration) and read the results back.

Two values are declared on the main plot `the-resistance`, whose protagonists
are kael and mira:
  freedom  p free, c dependent, cd imprisoned, nn gilded cage
  trust    p open, c wary, cd deceived, nn exploited

Run from the repo root with the venv python.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / "tools"), str(REPO / "tests")):
    sys.path.insert(0, p)

from tools.story_import import handler as import_handler  # noqa: E402
from tools.story_retrieve import handler as retrieve_handler  # noqa: E402

# `hermes_constants` only exists inside the Hermes runtime; the suite stubs it
# the same way (see test_root_path_config.py). Stub it before any config read.
import types  # noqa: E402

_fake = types.ModuleType("hermes_constants")
_fake.get_hermes_home = lambda: Path.home() / ".hermes"
sys.modules.setdefault("hermes_constants", _fake)

FIXTURE = REPO / "tests" / "fixtures" / "save-the-children"

SCHEMAS = [
    {"value": "freedom",
     "p": "free", "c": "dependent", "cd": "imprisoned", "nn": "gilded cage",
     "note": "Whether the children may choose their own life."},
    {"value": "trust",
     "p": "open", "c": "wary", "cd": "deceived", "nn": "exploited",
     "note": "Whether the system they live in tells them the truth."},
]

# scene id -> the turns recorded on it
TURNS = {
    "central-room-day": [
        {"plot": "the-resistance", "value": "freedom", "from": "imprisoned",
         "to": "free", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "Kael realises the lock was never engaged, and his own acceptance of it was the cage."},
                {"conflict_level": "personal",
                 "effect": "Kael's hand on the handle is a public refusal to stay."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "extra-personal",
                 "effect": "The system that holds the children is shown, for the first time, to be only a story they were told."}]}]},
        {"plot": "the-resistance", "value": "trust", "from": "deceived",
         "to": "open", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "Every guard Kael had been told about is a lie; he can no longer tell which of his beliefs is his own."},
                {"conflict_level": "personal",
                 "effect": "The Institute's authority over Kael collapses with the lock."}]}]},
    ],
    "central-room-night": [
        {"plot": "the-resistance", "value": "freedom", "from": "free",
         "to": "free", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "Refusing the offer is the deepening: the change is in how the choice lands, not in the state — freedom now has a cost attached to it."},
                {"conflict_level": "personal",
                 "effect": "The offer makes the known world real again by putting a price on leaving it."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "inner",
                 "effect": "Mira, unseen in the room, is given the same choice and must answer it alone."}]}]},
        {"plot": "the-resistance", "value": "trust", "from": "open",
         "to": "open", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "The Administrator speaks with a reasonable voice, so Kael's judgement of it has to become his own rather than borrowed."}]}]},
    ],
    "the-core-day": [
        {"plot": "the-resistance", "value": "freedom", "from": "free",
         "to": "free", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "extra-personal",
                 "effect": "The real world is wider than the system ever let them imagine, so freedom stops being an idea and becomes weather."},
                {"conflict_level": "inner",
                 "effect": "Kael has to become someone who lives outside the system, not someone who left it."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "extra-personal",
                 "effect": "Mira steps into the sky she was told did not exist and inherits the burden of believing her own eyes."}]}]},
        {"plot": "the-resistance", "value": "trust", "from": "open",
         "to": "open", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "The truth holds: the world outside is real, so the doubt earned in the Central Room is replaced by judgement."}]}]},
    ],
}


def apply_turns() -> list:
    """Write the schemas and turns onto the fixture markdown via the frontmatter lib."""
    import frontmatter

    # The first turn of the first scene declares both values; the plot is edited
    # to carry the schemas so the scenes never need an inline `schema`.
    plot_file = FIXTURE / "plots" / "The Resistance.md"
    post = frontmatter.load(plot_file)
    post["value_schemas"] = SCHEMAS
    frontmatter.dump(post, plot_file)
    print("wrote value_schemas on", plot_file.name)

    changed = []
    for scene_id, turns in TURNS.items():
        name = {"central-room-day": "Central Room - Day",
                "central-room-night": "Central Room - Night",
                "the-core-day": "The Core - Day"}[scene_id]
        scene_file = FIXTURE / "scenes" / f"{name}.md"
        post = frontmatter.load(scene_file)
        post["value_turns"] = turns
        frontmatter.dump(post, scene_file)
        changed.append(str(scene_file))
        print("wrote value_turns on", scene_file.name)
    return changed


def verify(root: Path) -> None:
    """Import a copy, then read the turns back through the real read path."""
    work = Path(tempfile.mkdtemp(prefix="value-pass-"))
    proj = work / "projects" / "save-the-children"
    shutil.copytree(FIXTURE, proj)
    shutil.rmtree(proj / ".story", ignore_errors=True)
    (work / "projects").mkdir(exist_ok=True)
    shutil.move(proj, proj)

    result = json.loads(import_handler(
        {"project": str(proj), "confirm": True, "root_path": str(work)}))
    if not result.get("success"):
        raise SystemExit(f"import failed: {result}")
    print("\nimport: ok —", result.get("scenes", "?"), "scenes")

    for scene_id in TURNS:
        out = json.loads(retrieve_handler({
            "project": "save-the-children",
            "entity_type": "scene", "id": [scene_id],
            "fields": ["value_turns"]}, root_path=str(work)))
        turns = out["entities"][0]["fields"]["value_turns"]
        assert len(turns) == len(TURNS[scene_id]), (scene_id, turns)
        for t in turns:
            assert t["effects"] and t["from"] and t["to"]
        print(f"retrieve {scene_id}: {len(turns)} turn(s), "
              f"{sum(len(t['effects']) for t in turns)} effect(s)")

    plot = json.loads(retrieve_handler({
        "project": "save-the-children", "entity_type": "plot",
        "id": ["the-resistance"],
        "fields": ["value_schemas", "value_lines"]}, root_path=str(work)))
    p = plot["entities"][0]["fields"]
    print("\nplot value_schemas:", [s["value"] for s in p["value_schemas"]])
    for line in p["value_lines"]:
        print(f"  {line['value']}: {len(line['turns'])} turn(s)")
        for t in line["turns"]:
            print(f"    {t['scene_id']}: {t['from']} -> {t['to']}")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply_turns()
    if "--verify" in sys.argv or "--apply" in sys.argv:
        verify(REPO)
    if len(sys.argv) == 1:
        print("usage: python <this> [--apply] [--verify]")
