"""Value pass + B1/B2 field removal for the live browser-verification-test project.

Markdown is the source of truth (story_import rebuilds the DB from it, wiping
every row), so the pass edits the notes and then re-imports. Without this the
project cannot be imported at all: the importer hard-refuses the retired keys
`value_at_open/close`, `shift`, `y`, `conflict_levels` on scenes, so every live
edit through the tool chain was blocked.

The turns carry the story facts the retired fields held. The old scene `shift`
string is the value vocabulary (`trust → suspicion`), the old `conflict_levels`
say which circle each shift reached, and the plot's protagonists come from
`plot.characters`. Arc beats keep `shift`/`y` until B3.

Idempotent: a second run reports 0 changes. Run from the repo root:

    .venv/bin/python tests/live_value_pass.py            # dry run
    .venv/bin/python tests/live_value_pass.py --apply    # edit + re-import
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / "tools"), str(REPO / "tests")):
    sys.path.insert(0, p)

import types  # noqa: E402

_fake = types.ModuleType("hermes_constants")
_fake.get_hermes_home = lambda: Path.home() / ".hermes"
sys.modules.setdefault("hermes_constants", _fake)

import frontmatter  # noqa: E402
from tools.story_import import handler as import_handler  # noqa: E402
from tools.story_retrieve import handler as retrieve_handler  # noqa: E402

PROJECT = Path("/media/theww/AI/TWW/hermes-story-architect/projects/"
               "browser-verification-test")
ROOT = PROJECT.parent.parent

# Retired by B1/B2. Arc beats keep shift/y until B3 (design §4).
SCENE_OLD = ["value_at_open", "value_at_close", "shift", "y", "conflict_levels"]
PROJECT_OLD = ["story_value", "story_value_at_open", "story_value_at_close"]
CONTAINER_OLD = ["value_at_open", "value_at_close"]

# The value at stake, with the four rungs in this story's words. `trust` is the
# project's own story_value; the words come from the scene shift strings.
SCHEMAS = [
    {"value": "trust", "p": "self-trust", "c": "doubt", "cd": "suspicion",
     "nn": "self-deception",
     "note": "Whether Kael can trust their own read of the world."},
]

# scene id -> turns. `from`/`to` are schema words; the opening state of each
# turn continues the closing state of the previous one, checked against the
# retired `value_at_open`/`value_at_close` pair rather than assumed.
#
# Story order (order_key): central-room-day, central-room-night,
# garden-day, garden-dream, the-door-closes, the-core-day.
TURNS = {
    # old: positive -> negative, shift `trust → suspicion`, levels inner+personal
    "central-room-day": [
        {"plot": "the-resistance", "value": "trust", "from": "self-trust",
         "to": "suspicion", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "Kael finds the lock was never engaged and learns their own read of the world was wrong."},
                {"conflict_level": "personal",
                 "effect": "Kael has to tell Mira the suspicion was right, which puts the two of them on the same side of it."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "personal",
                 "effect": "Mira's question — 'You knew?' — makes her complicit in a secret she was not told."}]}]},
    ],
    # old: negative -> positive, shift `suspicion → self-trust`, levels personal
    "central-room-night": [
        {"plot": "the-resistance", "value": "trust", "from": "suspicion",
         "to": "self-trust", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "personal",
                 "effect": "Refusing the Administrator's comfort is Kael choosing their own judgement over the only authority they have known."}]}]},
    ],
    # old: positive -> mixed, shift `earned trust → trust with visible seams`,
    # levels personal. Opens on self-trust, closing the previous scene.
    "garden-day": [
        {"plot": "the-resistance", "value": "trust", "from": "self-trust",
         "to": "self-trust", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "personal",
                 "effect": "The state holds but the quality changes: Kael now sees the mechanism behind the garden, so the trust is intact and no longer innocent."},
                {"conflict_level": "inner",
                 "effect": "'What happens when we leave?' is Kael testing whether their own read is worth following outside the system."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "personal",
                 "effect": "Mira names the risk — 'maybe that's the problem' — and keeps coming back to Kael anyway."}]}]},
    ],
    # old: positive -> negative, no shift string, levels inner. Dream, so the
    # opening state is set by the scene itself, not by continuity: a nonlinear
    # telling that shows the doubt underneath the trust.
    "garden-dream": [
        {"plot": "the-resistance", "value": "trust", "from": "self-trust",
         "to": "doubt", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "In the dream the Garden's geometry is wrong and follows Kael's breathing, so the ground under Kael's own judgement moves."}]}]},
    ],
    # old: negative -> positive, shift `trust in the world → trust in what we
    # chose`, levels inner
    "the-door-closes": [
        {"plot": "the-resistance", "value": "trust", "from": "doubt",
         "to": "self-trust", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "inner",
                 "effect": "Kael leaves not because the system is wrong but because staying is, so the trust moves from the world to the choice itself."}]}]},
    ],
    # old: positive -> positive, shift `self-trust → earned trust in each
    # other`, levels extra-personal
    "the-core-day": [
        {"plot": "the-resistance", "value": "trust", "from": "self-trust",
         "to": "self-trust", "effects": [
            {"character": "kael", "levels": [
                {"conflict_level": "extra-personal",
                 "effect": "The sky is real and shared, so Kael's judgement is confirmed by the world rather than only by itself."},
                {"conflict_level": "inner",
                 "effect": "'We live' is Kael's read of the future becoming an ordinary fact instead of an act of faith."}]},
            {"character": "mira", "levels": [
                {"conflict_level": "extra-personal",
                 "effect": "Mira steps into the real world and her own perception is vindicated by it."}]}]},
    ],
}

SCENE_FILES = {
    "central-room-day": "Central Room - Day.md",
    "central-room-night": "Central Room - Night.md",
    "garden-day": "Garden - Day.md",
    "garden-dream": "Garden Dream.md",
    "the-door-closes": "The Door Closes.md",
    "the-core-day": "The Core - Day.md",
}


def _drop(post, keys):
    before = len(post.metadata)
    for k in keys:
        if k in post:
            del post[k]
    return before != len(post.metadata)


def apply(root: Path | None = None) -> list:
    """Write the schemas and turns onto the notes, and drop the retired keys.

    `root` is the project directory to edit — the live one by default, a copy
    when verifying. Idempotent.
    """
    root = root or PROJECT
    changed = []

    plot_file = root / "plots" / "The Resistance.md"
    plot_post = frontmatter.load(plot_file)
    if not plot_post.get("value_schemas"):
        plot_post["value_schemas"] = SCHEMAS
        frontmatter.dump(plot_post, plot_file, sort_keys=False)
        changed.append(str(plot_file))
        print("wrote value_schemas on", plot_file.name)

    for scene_id, name in SCENE_FILES.items():
        path = root / "scenes" / name
        post = frontmatter.load(path)
        touched = _drop(post, SCENE_OLD)
        if not post.get("value_turns"):
            post["value_turns"] = TURNS[scene_id]
            frontmatter.dump(post, path, sort_keys=False)
            touched = True
        if touched:
            changed.append(str(path))
            print("wrote value_turns on", path.name)

    for rel in ("project.md", "acts/Act One.md", "acts/Act II.md",
                "sequences/The Discovery.md", "sequences/The Confrontation.md"):
        path = root / rel
        if not path.exists():
            continue
        post = frontmatter.load(path)
        keys = PROJECT_OLD if rel == "project.md" else CONTAINER_OLD
        if _drop(post, keys):
            frontmatter.dump(post, path, sort_keys=False)
            changed.append(str(path))
            print("removed retired keys from", rel)

    # The resolution scene was filed in Act I / The Discovery with order 3, while
    # the scene its own note calls the last of the script sits in Act II. Story
    # order is what value_lines reads, so the trust line put the resolution
    # third and read the back half out of sequence. Move it to the end.
    core = root / "scenes" / "The Core - Day.md"
    post = frontmatter.load(core)
    if post.get("sequence_id") != "seq-confrontation" or post.get("order") != 5:
        post["sequence_id"] = "seq-confrontation"
        post["act_id"] = "act-2"
        post["order"] = 5
        frontmatter.dump(post, core, sort_keys=False)
        changed.append(str(core))
        print("moved the-core-day to the end of seq-confrontation")

    return changed


def verify() -> None:
    """Re-import a copy of the project AS IT WILL BE, then read the turns back.

    The copy carries the pass applied, so this exercises the real write path
    (validation, inline-schema registration) and the read-back. Importing the
    notes unchanged is expected to fail — the importer refuses the retired keys
    — which is the reason the pass is necessary rather than cosmetic.
    """
    work = Path(tempfile.mkdtemp(prefix="live-value-pass-"))
    proj = work / "projects" / PROJECT.name
    shutil.copytree(PROJECT, proj)
    shutil.rmtree(proj / ".story", ignore_errors=True)
    apply(proj)  # the copy, never the live notes

    result = json.loads(import_handler(
        {"project": str(proj), "confirm": True, "root_path": str(work)}))
    if not result.get("success"):
        raise SystemExit(f"import failed: {result}")
    print("\nimport: ok —", result.get("entities", "?"), "entities")

    for scene_id in TURNS:
        out = json.loads(retrieve_handler({
            "project": PROJECT.name, "entity_type": "scene", "id": [scene_id],
            "fields": ["value_turns"]}, root_path=str(work)))
        turns = out["entities"][0]["fields"]["value_turns"]
        assert len(turns) == len(TURNS[scene_id]), (scene_id, turns)
        for t in turns:
            assert t["effects"] and t["from"] and t["to"]
        print(f"  {scene_id}: {len(turns)} turn(s), "
              f"{sum(len(t['effects']) for t in turns)} effect(s)")

    plot = json.loads(retrieve_handler({
        "project": PROJECT.name, "entity_type": "plot", "id": ["the-resistance"],
        "fields": ["value_schemas", "value_lines"]}, root_path=str(work)))
    p = plot["entities"][0]["fields"]
    print("\nvalue_schemas:", [s["value"] for s in p["value_schemas"]])
    for line in p["value_lines"]:
        print(f"  {line['value']}: {len(line['turns'])} turn(s), in story order:")
        for t in line["turns"]:
            print(f"    {t['scene_id']:<20} {t['from']} -> {t['to']}")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    if "--apply" in sys.argv:
        n = len(apply())
        print(f"\n{n} note(s) changed")
    verify()
