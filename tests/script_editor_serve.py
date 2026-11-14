"""Serve a small real project for tests/script_editor_harness.js.

    python tests/script_editor_serve.py <port>

Prints READY once it is listening. The project has the cases the editor exists
for: a registered location with a world, a registered and an unregistered
speaker, and a scene that is still at order 0.
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

import uvicorn

from story_architect.app.config import Config
from story_architect.app.server import create_app
from story_architect.core.writes import create_entity, edit_entity


def build(root: Path) -> None:
    p = root / "projects" / "demo"
    (p / ".story").mkdir(parents=True)
    create_entity(p, "project", "demo", {"name": "Demo"})   # the dashboard reads it
    create_entity(p, "act", "act-1", {"title": "Act I"})
    create_entity(p, "sequence", "seq-1", {"title": "One", "act_id": "act-1"})
    create_entity(p, "world", "london-1950", {"name": "London 1950", "one_sentence": "T"})
    create_entity(p, "location", "kitchen", {"name": "Kitchen", "one_sentence": "T", "world": "london-1950"})
    create_entity(p, "location", "attic", {"name": "Attic", "one_sentence": "T"})
    for slug, name, role in [("mara-chen", "Mara Chen", "Protagonist"),
                             ("detective-oak", "Detective Oak", "Antagonist")]:
        create_entity(p, "character", slug, {"name": name, "story_role": role, "one_sentence": "T"})
    create_entity(p, "scene", "the-kitchen",
                  {"title": "The Kitchen", "sequence_id": "seq-1", "act_id": "act-1", "order": 2,
                   "location": "kitchen", "time_of_day": "NIGHT", "int_ext": "INT.",
                   "characters": ["mara-chen"]},
                  sections={"Content": "INT. KITCHEN - NIGHT\n\nMara stands at the counter, a ledger open.\n\n"
                                       "MARA\n(quietly)\nYou knew.\n\nLEO\nSorry.\n"})
    create_entity(p, "scene", "blank", {"title": "Blank", "sequence_id": "seq-1", "act_id": "act-1"})
    edit_entity(p, "scene", "blank", {"order": 0}, "unplace")
    create_entity(p, "scene", "locked-one", {"title": "Locked One", "sequence_id": "seq-1", "act_id": "act-1",
                                             "order": 3, "int_ext": "INT.", "location": "kitchen",
                                             "time_of_day": "DAY"},
                  sections={"Content": "INT. KITCHEN - DAY\n\nNothing moves.\n"})
    edit_entity(p, "scene", "locked-one", {"status": "locked"}, "lock")


if __name__ == "__main__":
    port = int(sys.argv[1])
    root = Path(tempfile.mkdtemp())
    build(root)
    with mock.patch("story_architect.app.token.load_api_key", lambda: "k"):
        app = create_app(Config(root=root, port=port))
        print("READY", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
