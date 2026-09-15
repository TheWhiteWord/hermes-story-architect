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
    arcs = _parse_arcs(project_path / "arcs")

    index = {
        "project": _parse_project(
            project_path, characters, locations, worlds, plots,
            scenes_count=len(file_scenes), sequences_count=len(sequences),
            acts_count=len(acts), arcs_count=len(arcs)
        ),
        "characters": characters,
        "locations": locations,
        "worlds": worlds,
        "plots": plots,
        "acts": acts,
        "sequences": sequences,
    }

    index["scenes"] = file_scenes
    index["arcs"] = arcs

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

    # Derive plots at sequence and act level (from their scenes)
    _enrich_sequences_with_plots(index)
    _enrich_acts_with_plots(index)

    # Enrich characters with arc beats
    _enrich_characters_with_arcs(index)

    # Enrich scenes with arc beats (reverse lookup)
    _enrich_scenes_with_arcs(index)

    # Validate
    _validate_index(index)

    return index


def _parse_project(
    project_path: Path, characters, locations, worlds, plots,
    scenes_count=0, sequences_count=0, acts_count=0, arcs_count=0
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
    project["arc_count"] = arcs_count
    return project


def _parse_arcs(arcs_folder: Path) -> list[dict]:
    """Parse arc beats from nested arcs/{character}/{beat_id}.md structure."""
    if not arcs_folder.exists():
        return []
    beats = []
    for char_folder in sorted(arcs_folder.iterdir()):
        if not char_folder.is_dir() or char_folder.name.startswith("_") or char_folder.name.startswith("."):
            continue
        for note in sorted(char_folder.glob("*.md")):
            if note.name.startswith("_"):
                continue
            beat = extract_entity(note, "arc")
            # Inherit character from folder name if not in frontmatter
            if "character" not in beat or not beat["character"]:
                beat["character"] = char_folder.name
            warnings = validate_entity("arc", beat)
            if warnings:
                print(f"Warnings for {note}: {warnings}")
            beats.append(beat)
    return beats


def _enrich_characters_with_arcs(index: dict) -> None:
    """Build character.arc_beats_list and set arc_beat_count."""
    char_beats = {c["id"]: [] for c in index["characters"]}
    for beat in index.get("arcs", []):
        char_id = beat.get("character")
        if char_id in char_beats:
            char_beats[char_id].append({
                "id": beat.get("id", ""),
                "label": beat.get("label", ""),
                "scene": beat.get("scene", ""),
                "shift": beat.get("shift", ""),
                "y": beat.get("y", 0.0),
                "order": beat.get("order", 0),
                "is_crisis": beat.get("is_crisis", False),
                "is_climax": beat.get("is_climax", False),
            })
    for char in index["characters"]:
        beats = char_beats.get(char["id"], [])
        if beats:
            char["arc_beats_list"] = sorted(beats, key=lambda b: b.get("order", 0))
            char["arc_beat_count"] = len(beats)
        else:
            char["arc_beats_list"] = []
            char["arc_beat_count"] = 0


def _enrich_scenes_with_arcs(index: dict) -> None:
    """Build scene.arc_beats[] by reverse lookup from beats."""
    scene_beats = {s.get("id"): [] for s in index.get("scenes", [])}
    for beat in index.get("arcs", []):
        scene_id = beat.get("scene")
        if scene_id in scene_beats:
            scene_beats[scene_id].append({
                "character": beat.get("character", ""),
                "beat_id": beat.get("id", ""),
                "label": beat.get("label", ""),
                "y": beat.get("y", 0.0),
                "is_crisis": beat.get("is_crisis", False),
                "is_climax": beat.get("is_climax", False),
            })
    for scene in index.get("scenes", []):
        beats = scene_beats.get(scene.get("id"), [])
        if beats:
            scene["arc_beats"] = beats


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
    """Add plots[] to each scene by reverse lookup from plot setups/payoffs/crisis/climax."""
    scenes_by_id = {s.get("id"): s for s in index.get("scenes", [])}
    for plot in index.get("plots", []):
        all_beats = (
            [(b, "setup") for b in plot.get("setups", [])] +
            [(b, "crisis") for b in plot.get("crisis", [])] +
            [(b, "climax") for b in plot.get("climax", [])] +
            [(b, "payoff") for b in plot.get("payoffs", [])]
        )
        for beat, beat_type in all_beats:
            scene = scenes_by_id.get(beat.get("scene_id"))
            if scene:
                if "plots" not in scene:
                    scene["plots"] = []
                # Check if this plot is already referenced with this specific beat
                existing = None
                for i, p in enumerate(scene["plots"]):
                    pid = p.get("id") if isinstance(p, dict) else p
                    if pid == plot["id"]:
                        existing = (i, p)
                        break
                
                if existing:
                    idx, ep = existing
                    if isinstance(ep, str):
                        # Upgrade string reference to dict with beat
                        scene["plots"][idx] = {"id": ep, "beat": beat_type}
                    elif isinstance(ep, dict):
                        if not ep.get("beat"):
                            # Add beat to existing dict reference
                            ep["beat"] = beat_type
                        elif ep["beat"] != beat_type:
                            # Different beat, add as new entry
                            scene["plots"].append({"id": plot["id"], "beat": beat_type})
                        # Same beat already exists, skip
                else:
                    scene["plots"].append({"id": plot["id"], "beat": beat_type})


def _enrich_sequences_with_plots(index: dict) -> None:
    """Add plots[] to each sequence derived from its scenes, with scope+type+beats for UI."""
    plot_lookup = {p["id"]: p for p in index.get("plots", [])}
    for seq in index.get("sequences", []):
        seq_plots = {}
        for scene in index.get("scenes", []):
            if scene.get("sequence_id") != seq["id"]:
                continue
            for p in scene.get("plots", []):
                pid = p.get("id") if isinstance(p, dict) else p
                if pid not in seq_plots:
                    meta = plot_lookup.get(pid, {})
                    seq_plots[pid] = {
                        "id": pid,
                        "has_setup": False,
                        "has_crisis": False,
                        "has_climax": False,
                        "has_payoff": False,
                        "plot_scope": meta.get("plot_scope", "sub"),
                        "plot_type": meta.get("plot_type", ""),
                        "value_arc": meta.get("value_arc", ""),
                    }
                beat = p.get("beat", "") if isinstance(p, dict) else ""
                if beat == "setup":
                    seq_plots[pid]["has_setup"] = True
                elif beat == "crisis":
                    seq_plots[pid]["has_crisis"] = True
                elif beat == "climax":
                    seq_plots[pid]["has_climax"] = True
                elif beat == "payoff":
                    seq_plots[pid]["has_payoff"] = True
        seq["plots"] = sorted(seq_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))


def _enrich_acts_with_plots(index: dict) -> None:
    """Add plots[] to each act derived from its scenes, with scope+type+beats for UI."""
    plot_lookup = {p["id"]: p for p in index.get("plots", [])}
    for act in index.get("acts", []):
        act_plots = {}
        for scene in index.get("scenes", []):
            if scene.get("act_id") != act["id"]:
                continue
            for p in scene.get("plots", []):
                pid = p.get("id") if isinstance(p, dict) else p
                if pid not in act_plots:
                    meta = plot_lookup.get(pid, {})
                    act_plots[pid] = {
                        "id": pid,
                        "has_setup": False,
                        "has_crisis": False,
                        "has_climax": False,
                        "has_payoff": False,
                        "plot_scope": meta.get("plot_scope", "sub"),
                        "plot_type": meta.get("plot_type", ""),
                        "value_arc": meta.get("value_arc", ""),
                    }
                beat = p.get("beat", "") if isinstance(p, dict) else ""
                if beat == "setup":
                    act_plots[pid]["has_setup"] = True
                elif beat == "crisis":
                    act_plots[pid]["has_crisis"] = True
                elif beat == "climax":
                    act_plots[pid]["has_climax"] = True
                elif beat == "payoff":
                    act_plots[pid]["has_payoff"] = True
        act["plots"] = sorted(act_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))


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

    # Validate project-level scene references
    project = index.get("project", {})
    for field in ("inciting_incident_scene_id", "story_climax_scene_id"):
        scene_id = project.get(field, "")
        if scene_id and scene_id not in scene_ids:
            print(f"Warning: project.{field} references unknown scene {scene_id}")

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

    # Arc beat validation
    char_ids_set = {c["id"] for c in index["characters"]}
    scene_ids_set = {s.get("id") for s in index.get("scenes", [])}
    for beat in index.get("arcs", []):
        beat_char = beat.get("character", "")
        if beat_char and beat_char not in char_ids_set:
            print(f"Warning: arc beat {beat.get('id')} references unknown character {beat_char}")
        beat_scene = beat.get("scene", "")
        if beat_scene and beat_scene not in scene_ids_set:
            print(f"Warning: arc beat {beat.get('id')} references unknown scene {beat_scene}")
        y_val = beat.get("y", 0)
        if isinstance(y_val, (int, float)) and not (-1.0 <= float(y_val) <= 1.0):
            print(f"Warning: arc beat {beat.get('id')} y out of range: {y_val}")
        order_val = beat.get("order", 0)
        if not isinstance(order_val, (int, float)):
            print(f"Warning: arc beat {beat.get('id')} order is not numeric: {order_val}")


def write_index(index: dict, output_path: Path) -> None:
    """Write index to YAML."""
    with open(output_path, 'w') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def refresh_index(project_path: Path) -> None:
    """Regenerate and write the index for a project."""
    index_path = project_path / ".story" / "index.yaml"
    index_path.parent.mkdir(exist_ok=True)
    index = generate_index(project_path)
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

    # Plot coverage: count unique scenes per plot (not beat entries)
    plot_scene_sets = {}
    for scene in index.get("scenes", []):
        for p in scene.get("plots", []):
            pid = p.get("id") if isinstance(p, dict) else p
            if pid not in plot_scene_sets:
                plot_scene_sets[pid] = set()
            plot_scene_sets[pid].add(scene.get("id"))

    plots_lookup = {p["id"]: p for p in index.get("plots", [])}
    total_scenes = len(index.get("scenes", []))
    plot_coverage = []
    for pid, scene_set in sorted(plot_scene_sets.items(), key=lambda x: len(x[1]), reverse=True):
        pl = plots_lookup.get(pid, {})
        plot_coverage.append({
            "id": pid,
            "name": pl.get("name", pid),
            "plot_scope": pl.get("plot_scope", "sub"),
            "plot_type": pl.get("plot_type", ""),
            "value_arc": pl.get("value_arc", ""),
            "sceneCount": len(scene_set),
            "coveragePct": round((len(scene_set) / total_scenes) * 100) if total_scenes else 0,
        })

    return {
        "sceneCount": total_scenes,
        "sequenceCount": len(index.get("sequences", [])),
        "actCount": len(index.get("acts", [])),
        "sceneStatus": dict(status_counts),
        "sceneRoles": dict(role_counts),
        "plotCoverage": plot_coverage,
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
