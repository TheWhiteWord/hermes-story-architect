"""Index generator — produce .story/index.yaml from vault notes."""
import yaml
from pathlib import Path
from .entity import extract_entity, validate_entity


def generate_index(project_path: Path) -> dict:
    """Main entry point: scan project folder, produce index dict."""
    characters = _parse_entities(project_path / "characters", "character")
    locations = _parse_entities(project_path / "locations", "location")
    worlds = _parse_entities(project_path / "worlds", "world")
    plots = _parse_entities(project_path / "plots", "plot")
    file_scenes = _parse_entities(project_path / "scenes", "scene")
    sequences = _parse_entities(project_path / "sequences", "sequence")
    acts = _parse_entities(project_path / "acts", "act")

    index = {
        "project": _parse_project(
            project_path, characters, locations, worlds, plots,
            scenes_count=len(file_scenes), sequences_count=len(sequences), acts_count=len(acts)
        ),
        "characters": characters,
        "locations": locations,
        "worlds": worlds,
        "plots": plots,
        "sequences": sequences,
        "acts": acts,
    }

    # Scenes from files only — screenplay merge removed (Phase 2).
    # Main index keeps navigation fields; dramatic metadata goes to structure-index.yaml.
    # Store full scenes for structure index generation before stripping.
    index["_full_scenes"] = file_scenes
    index["scenes"] = [_strip_scene_for_navigation(s) for s in file_scenes]

    # Populate characters.scenes[] and locations.scenes[] from scene list
    _enrich_entity_scenes(index)

    # Add labels to relationships
    _enrich_relationships(index)

    # Add descriptions to setups/payoffs
    _enrich_plots(index)

    # Add plots to scenes (reverse lookup from plot setups/payoffs)
    _enrich_scenes_with_plots(index)

    # Build derived structure lists
    _enrich_structure(index)

    # Validate
    _validate_index(index)

    return index


def _parse_project(
    project_path: Path, characters, locations, worlds, plots,
    scenes_count=0, sequences_count=0, acts_count=0
) -> dict:
    """Parse project.md and add count fields."""
    fm = project_path / "project.md"
    project = extract_entity(fm, "project") if fm.exists() else {}
    project["scene_count"] = scenes_count
    project["character_count"] = len(characters)
    project["location_count"] = len(locations)
    project["world_count"] = len(worlds)
    project["plot_count"] = len(plots)
    project["sequence_count"] = sequences_count
    project["act_count"] = acts_count
    return project


def _enrich_relationships(index: dict) -> None:
    """Add label field to relationships (defaults to empty string, user fills in editor)."""
    for char in index.get("characters", []):
        for rel in char.get("relationships", []):
            if "label" not in rel:
                rel["label"] = ""


def _enrich_plots(index: dict) -> None:
    """Normalize plot setups/payoffs to {scene_id, description}.
    plot.characters is frontmatter-only — scenes may contain passersby."""
    for plot in index.get("plots", []):
        plot["setups"] = [_normalize_plot_scene(s) for s in plot.get("setups", [])]
        plot["payoffs"] = [_normalize_plot_scene(p) for p in plot.get("payoffs", [])]
        if "characters" not in plot:
            plot["characters"] = []


def _enrich_scenes_with_plots(index: dict) -> None:
    """Add plots[] to each scene by reverse lookup from plot setups/payoffs."""
    scenes_by_id = {s.get("id"): s for s in index.get("scenes", [])}
    for plot in index.get("plots", []):
        for beat in plot.get("setups", []) + plot.get("payoffs", []):
            scene = scenes_by_id.get(beat.get("scene_id"))
            if scene:
                if "plots" not in scene:
                    scene["plots"] = []
                if plot["id"] not in scene["plots"]:
                    scene["plots"].append(plot["id"])


def _normalize_plot_scene(scene_ref):
    """Pass through {scene_id, description} from note frontmatter."""
    if isinstance(scene_ref, dict):
        return {"scene_id": scene_ref.get("scene_id", ""), "description": scene_ref.get("description", "")}
    return {"scene_id": str(scene_ref), "description": ""}


def _parse_entities(folder: Path, entity_type: str) -> list[dict]:
    """Parse all entities in a folder."""
    if not folder.exists():
        return []
    entities = []
    for note in sorted(folder.glob("*.md")):
        if note.name.startswith("_"):
            continue
        entity = extract_entity(note, entity_type)
        warnings = validate_entity(entity_type, entity)
        if warnings:
            print(f"Warnings for {note}: {warnings}")
        entities.append(entity)
    return entities


# Fields kept in the main index — navigation only. Dramatic metadata is in structure-index.yaml.
NAVIGATION_SCENE_FIELDS = frozenset([
    "id", "type", "title", "order", "status",
    "sequence_id", "act_id", "heading", "characters",
    "plots", "location", "sections",
])


def _strip_scene_for_navigation(scene: dict) -> dict:
    """Return a scene entry with only navigation fields for the main index."""
    return {k: v for k, v in scene.items() if k in NAVIGATION_SCENE_FIELDS}


def _enrich_entity_scenes(index: dict) -> None:
    """Build character.scenes[] and locations.scenes[] by reverse-mapping scene list."""
    char_scenes = {c["id"]: [] for c in index["characters"]}
    loc_scenes = {l["id"]: [] for l in index["locations"]}
    for scene in index.get("scenes", []):
        for char_id in scene.get("characters", []):
            if char_id in char_scenes:
                char_scenes[char_id].append({
                    "id": scene.get("id"),
                    "title": scene.get("title", ""),
                    "heading": scene.get("heading", ""),
                })
        loc_id = scene.get("location", "")
        if loc_id and loc_id in loc_scenes:
            loc_scenes[loc_id].append({
                "id": scene.get("id"),
                "title": scene.get("title", ""),
                "heading": scene.get("heading", ""),
            })
    for char in index["characters"]:
        if char_scenes.get(char["id"]):
            char["scenes"] = char_scenes[char["id"]]
    for loc in index["locations"]:
        if loc_scenes.get(loc["id"]):
            loc["scenes"] = loc_scenes[loc["id"]]


def _enrich_structure(index: dict) -> None:
    """Build derived lists: sequence.scenes_list, act.sequences_list, act.scenes_list."""
    # sequence.scenes_list (sorted by order)
    for seq in index.get("sequences", []):
        scenes_in_seq = sorted(
            [s for s in index.get("scenes", []) if s.get("sequence_id") == seq["id"]],
            key=lambda s: s.get("order", 0)
        )
        seq["scenes_list"] = [s["id"] for s in scenes_in_seq]
        seq["scene_count"] = len(seq["scenes_list"])

    # act.sequences_list (sorted by order)
    for act in index.get("acts", []):
        seqs_in_act = sorted(
            [s for s in index.get("sequences", []) if s.get("act_id") == act["id"]],
            key=lambda s: s.get("order", 0)
        )
        act["sequences_list"] = [s["id"] for s in seqs_in_act]
        # act.scenes_list (all scenes where act_id matches)
        act["scenes_list"] = sorted(
            [s["id"] for s in index.get("scenes", []) if s.get("act_id") == act["id"]],
            key=lambda sid: next((s.get("order", 0) for s in index.get("scenes", []) if s.get("id") == sid), 0)
        )
        act["sequence_count"] = len(act["sequences_list"])
        act["scene_count"] = len(act["scenes_list"])


def _validate_index(index: dict) -> None:
    """Validate cross-references."""
    char_ids = {c["id"] for c in index["characters"]}
    loc_ids = {l["id"] for l in index["locations"]}
    plot_ids = {p["id"] for p in index["plots"]}
    seq_ids = {s["id"] for s in index.get("sequences", [])}
    act_ids = {a["id"] for a in index.get("acts", [])}
    scene_ids = {s.get("id") for s in index.get("scenes", [])}

    for char in index["characters"]:
        for rel in char.get("relationships", []):
            if rel["id"] not in char_ids:
                print(f"Warning: {char['id']} references unknown character {rel['id']}")

    for plot in index["plots"]:
        for char_id in plot.get("characters", []):
            if char_id not in char_ids:
                print(f"Warning: {plot['id']} references unknown character {char_id}")
        for beat in plot.get("setups", []) + plot.get("payoffs", []):
            if beat.get("scene_id") and beat["scene_id"] not in scene_ids:
                print(f"Warning: {plot['id']} references unknown scene {beat['scene_id']}")

    for seq in index.get("sequences", []):
        if seq.get("act_id") and seq["act_id"] not in act_ids:
            print(f"Warning: sequence {seq['id']} references unknown act {seq['act_id']}")

    for act in index.get("acts", []):
        if act.get("climax_scene_id") and act["climax_scene_id"] not in scene_ids:
            print(f"Warning: act {act['id']} references unknown climax scene {act['climax_scene_id']}")

    scenes_list = index.get("scenes", [])
    seqs_list = index.get("sequences", [])
    seq_lookup = {s["id"]: s for s in seqs_list}
    for scene in scenes_list:
        sid = scene.get("id")
        if scene.get("sequence_id") and scene["sequence_id"] not in seq_ids:
            print(f"Warning: scene {sid} references unknown sequence {scene['sequence_id']}")
        if scene.get("act_id") and scene["act_id"] not in act_ids:
            print(f"Warning: scene {sid} references unknown act {scene['act_id']}")
        # Cross-check: scene.act_id matches sequence.act_id
        if scene.get("sequence_id") and scene.get("act_id"):
            seq = seq_lookup.get(scene["sequence_id"])
            if seq and seq.get("act_id") and seq["act_id"] != scene["act_id"]:
                print(f"Warning: scene {sid} act_id={scene['act_id']} != sequence.act_id={seq['act_id']}")


def write_index(index: dict, output_path: Path) -> None:
    """Write index to YAML."""
    with open(output_path, 'w') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_structure_index(index: dict) -> dict:
    """Generate the structure index sidecar from the main index.

    Only file scenes have dramatic metadata. Reads from _full_scenes (stored
    before navigation stripping) so dramatic metadata is available here.
    """
    # Use _full_scenes (preserved before stripping) to access dramatic metadata.
    source_scenes = index.get("_full_scenes", index.get("scenes", []))
    return {
        "scenes": [
            {
                "id": scene["id"],
                "value": scene.get("value", ""),
                "value_open": scene.get("value_open", ""),
                "value_close": scene.get("value_close", ""),
                "conflict_levels": scene.get("conflict_levels", []),
                "dramatic_role": scene.get("dramatic_role", ""),
                "is_inciting_incident": bool(scene.get("is_inciting_incident", False)),
                "is_sequence_climax": bool(scene.get("is_sequence_climax", False)),
                "is_act_climax": bool(scene.get("is_act_climax", False)),
                "is_story_climax": bool(scene.get("is_story_climax", False)),
                "arc_beat_refs": [],
            }
            for scene in source_scenes
        ],
        "sequences": [
            {
                "id": seq["id"],
                "value": seq.get("value", ""),
                "value_open": seq.get("value_open", ""),
                "value_close": seq.get("value_close", ""),
                "climax_scene_id": seq.get("climax_scene_id", ""),
            }
            for seq in index.get("sequences", [])
        ],
        "acts": [
            {
                "id": act["id"],
                "value": act.get("value", ""),
                "value_open": act.get("value_open", ""),
                "value_close": act.get("value_close", ""),
                "climax_scene_id": act.get("climax_scene_id", ""),
            }
            for act in index.get("acts", [])
        ],
    }


def write_structure_index(structure_index: dict, output_path: Path) -> None:
    """Write structure index to YAML."""
    with open(output_path, 'w') as f:
        yaml.dump(structure_index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def update_structure_index_scene(project_path: Path, scene_id: str) -> None:
    """Lightweight single-scene update to structure-index.yaml.

    Reads scene file frontmatter, finds entry by id, updates dramatic
    metadata fields, writes back. O(1) vs O(N) rebuild. No-op if
    structure-index.yaml or scene file doesn't exist.
    """
    import frontmatter

    structure_path = project_path / ".story" / "structure-index.yaml"
    if not structure_path.exists():
        return

    scene_path = project_path / "scenes" / f"{scene_id}.md"
    if not scene_path.exists():
        return

    with open(structure_path) as f:
        structure_index = yaml.safe_load(f)

    post = frontmatter.load(scene_path)
    meta = dict(post.metadata)

    for entry in structure_index.get("scenes", []):
        if entry.get("id") == scene_id:
            entry["value"] = meta.get("value", "")
            entry["value_open"] = meta.get("value_open", "")
            entry["value_close"] = meta.get("value_close", "")
            entry["conflict_levels"] = meta.get("conflict_levels", [])
            entry["dramatic_role"] = meta.get("dramatic_role", "")
            entry["is_inciting_incident"] = bool(meta.get("is_inciting_incident", False))
            entry["is_sequence_climax"] = bool(meta.get("is_sequence_climax", False))
            entry["is_act_climax"] = bool(meta.get("is_act_climax", False))
            entry["is_story_climax"] = bool(meta.get("is_story_climax", False))
            break

    write_structure_index(structure_index, structure_path)


def refresh_index(project_path: Path) -> None:
    """Regenerate and write the index and structure index for a project.
    Ensures .story/ directory exists before writing.
    Raises exceptions on failure so callers can handle/report."""
    index_path = project_path / ".story" / "index.yaml"
    index_path.parent.mkdir(exist_ok=True)

    index = generate_index(project_path)
    
    # Generate structure index from full scenes (with dramatic metadata)
    structure_index = generate_structure_index(index)
    structure_path = project_path / ".story" / "structure-index.yaml"
    write_structure_index(structure_index, structure_path)
    
    # Remove internal _full_scenes key before writing main index
    index.pop("_full_scenes", None)
    write_index(index, index_path)


def assemble_scene_content(index: dict, project_path: Path) -> str:
    """Concatenate scene ## Content sections into a single Fountain text string.
    
    Used to feed _compute_screenplay_stats() so all existing screenplay stats
    (length, duration, character speaking time, INT/EXT, location stats)
    AND scriptHtml are produced from scene content instead of screenplay.fountain.
    
    This eliminates the need for a separate assemble_script_from_scenes() function —
    _compute_screenplay_stats() already calls tokens_to_html() internally.
    """
    from .section_parser import get_section
    
    scenes = index.get("scenes", [])
    sequences = {s["id"]: s for s in index.get("sequences", [])}
    acts = {a["id"]: a for a in index.get("acts", [])}
    
    scenes_by_seq = {}
    for scene in scenes:
        sid = scene.get("sequence_id", "")
        scenes_by_seq.setdefault(sid, []).append(scene)
    for sid in scenes_by_seq:
        scenes_by_seq[sid].sort(key=lambda s: s.get("order", 0))
    
    content_parts = []
    for act_id, act in sorted(acts.items(), key=lambda x: x[1].get("order", 0)):
        seqs_in_act = sorted(
            [s for s in index.get("sequences", []) if s.get("act_id") == act_id],
            key=lambda s: s.get("order", 0)
        )
        for seq in seqs_in_act:
            for scene in scenes_by_seq.get(seq["id"], []):
                note_path = project_path / "scenes" / f"{scene['id']}.md"
                if not note_path.exists():
                    continue
                import frontmatter
                post = frontmatter.load(note_path)
                content = get_section(post.content, "Content")
                if not content:
                    continue
                if content.startswith("## "):
                    nl = content.find("\n")
                    if nl != -1:
                        content = content[nl + 1:]
                content_parts.append(content.strip())
    
    return "\n\n".join(content_parts)


def compute_structural_stats(index: dict) -> dict:
    """Compute structural stats for dashboard injection."""
    from collections import Counter

    status_counts = Counter()
    role_counts = Counter()
    for scene in index.get("scenes", []):
        status_counts[scene.get("status", "planned")] += 1
        role_counts[scene.get("dramatic_role", "") or "unset"] += 1

    return {
        "sceneCount": len(index.get("scenes", [])),
        "sequenceCount": len(index.get("sequences", [])),
        "actCount": len(index.get("acts", [])),
        "sceneStatus": dict(status_counts),
        "sceneRoles": dict(role_counts),
        "acts": [
            {
                "id": act["id"],
                "title": act["title"],
                "sceneCount": act.get("scene_count", 0),
                "sequenceCount": act.get("sequence_count", 0),
            }
            for act in index.get("acts", [])
        ],
    }
