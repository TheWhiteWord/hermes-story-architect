"""Coherence checks — validate character arcs against structural arc data."""
from typing import Any

# Thresholds — generous defaults, tighten based on user feedback
DIRECTIONAL_ALIGNMENT_MIN_DELTA = 0.3   # net Δy below this is noise, not misalignment
ESCALATION_IMBALANCE_RATIO = 1.5        # Act N peak > 1.5× Act N+2 peak = flag
CONTROLLING_IDEA_TOLERANCE = 0.0        # zero tolerance — sign mismatch is always a flag

CHARGE_SIGN = {
    "positive": 1,
    "mixed": 0,
    "negative": -1,
    "ironic": 0,
}


# ─── Helpers ───────────────────────────────────────────────────────────────


def _beats_for_character(index: dict, character_slug: str) -> list[dict]:
    """Filter index['arcs'] by character slug, sorted by order."""
    return sorted(
        [b for b in index.get("arcs", []) if b.get("character") == character_slug],
        key=lambda b: b.get("order", 0),
    )


def _act_direction(act: dict) -> int:
    """Map act's value_open → value_close to +1, -1, or 0."""
    return _charge_delta(act.get("value_open", ""), act.get("value_close", ""))


def _protagonist_id(index: dict) -> str:
    """Find protagonist: character with story_role == 'Protagonist'. Returns '' if none."""
    for char in index.get("characters", []):
        if char.get("story_role") == "Protagonist":
            return char.get("id", "")
    return ""


def _antagonist_id(index: dict) -> str:
    """Find antagonist: character with story_role == 'Antagonist'. Returns '' if none."""
    for char in index.get("characters", []):
        if char.get("story_role") == "Antagonist":
            return char.get("id", "")
    return ""


def _y_sign(y_value: Any) -> int:
    """Map a y numeric value to +1, -1, or 0."""
    if not isinstance(y_value, (int, float)):
        return 0
    if y_value > 0:
        return 1
    if y_value < 0:
        return -1
    return 0


def _charge_to_sign(charge_str: str) -> int:
    """Map charge string to sign using CHARGE_SIGN."""
    return CHARGE_SIGN.get(charge_str, 0)


def _charge_delta(open_charge: str, close_charge: str) -> int:
    """Direction of value shift from open to close charge."""
    o = _charge_to_sign(open_charge)
    c = _charge_to_sign(close_charge)
    diff = c - o
    if diff > 0:
        return 1
    if diff < 0:
        return -1
    return 0


def _scenes_in_act(index: dict, act_id: str) -> list[str]:
    """Return list of scene IDs belonging to this act."""
    return [s.get("id") for s in index.get("scenes", []) if s.get("act_id") == act_id]


# ─── Check implementations ─────────────────────────────────────────────────


def _check_directional_alignment(index: dict, protagonist_id: str) -> list[dict]:
    """Check 1: Protagonist net Δy per act vs. act structural direction."""
    if not protagonist_id:
        return []
    beats = _beats_for_character(index, protagonist_id)
    if not beats:
        return []

    flags = []
    # Group beats by act
    act_beats: dict[str, list[dict]] = {}
    scene_to_act = {s.get("id"): s.get("act_id") for s in index.get("scenes", [])}

    for beat in beats:
        scene_id = beat.get("scene", "")
        act_id = scene_to_act.get(scene_id, "")
        if act_id:
            act_beats.setdefault(act_id, []).append(beat)

    for act in index.get("acts", []):
        act_id = act.get("id", "")
        a_beats = act_beats.get(act_id, [])
        if len(a_beats) < 1:
            continue

        # Net Δy = last y - first y (beats already sorted by order)
        net_dy = a_beats[-1].get("y", 0) - a_beats[0].get("y", 0)
        struct_dir = _act_direction(act)

        # Only flag if opposing AND above threshold
        if abs(net_dy) >= DIRECTIONAL_ALIGNMENT_MIN_DELTA:
            dy_sign = _y_sign(net_dy)
            if dy_sign != 0 and struct_dir != 0 and dy_sign != struct_dir:
                flags.append({
                    "check": "directional_alignment",
                    "severity": "warning",
                    "act": act_id,
                    "message": f"Net movement is {net_dy:+.1f} but structural value goes {act.get('value_open','')}→{act.get('value_close','')} — intentional?",
                    "data": {"net_dy": net_dy, "structural_direction": struct_dir},
                })

    return flags


def _check_escalation(index: dict, protagonist_id: str) -> list[dict]:
    """Check 2: Peak |Δy| per act should trend upward."""
    if not protagonist_id:
        return []
    beats = _beats_for_character(index, protagonist_id)
    if not beats:
        return []

    acts = index.get("acts", [])
    if len(acts) < 2:
        return []

    # Group beats by act
    act_beats: dict[str, list[dict]] = {}
    scene_to_act = {s.get("id"): s.get("act_id") for s in index.get("scenes", [])}

    for beat in beats:
        scene_id = beat.get("scene", "")
        act_id = scene_to_act.get(scene_id, "")
        if act_id:
            act_beats.setdefault(act_id, []).append(beat)

    # Compute peak |Δy| per act (largest single beat-to-beat jump)
    act_peaks: dict[str, float] = {}
    for act_id, a_beats in act_beats.items():
        if len(a_beats) < 2:
            act_peaks[act_id] = 0.0
            continue
        ys = [b.get("y", 0) for b in a_beats]
        max_jump = max(abs(ys[i+1] - ys[i]) for i in range(len(ys) - 1))
        act_peaks[act_id] = max_jump

    # Check for imbalance: earlier act peak > ratio × later act peak
    flags = []
    sorted_acts = sorted(
        [a for a in acts if a.get("id") in act_peaks],
        key=lambda a: a.get("order", 0),
    )
    for i in range(len(sorted_acts)):
        for j in range(i + 1, len(sorted_acts)):
            early_id = sorted_acts[i]["id"]
            late_id = sorted_acts[j]["id"]
            early_peak = act_peaks[early_id]
            late_peak = act_peaks[late_id]
            if late_peak > 0 and early_peak > ESCALATION_IMBALANCE_RATIO * late_peak:
                flags.append({
                    "check": "escalation",
                    "severity": "warning",
                    "act": early_id,
                    "message": f"Act {sorted_acts[i].get('title', early_id)} peak swing ({early_peak:.1f}) is >{ESCALATION_IMBALANCE_RATIO}× Act {sorted_acts[j].get('title', late_id)} peak ({late_peak:.1f}) — arc may peak too early",
                    "data": {"early_peak": early_peak, "late_peak": late_peak, "ratio": ESCALATION_IMBALANCE_RATIO},
                })

    return flags


def _check_crisis_placement(index: dict, protagonist_id: str) -> list[dict]:
    """Check 3: is_crisis must not be in final act; is_climax must be in final act."""
    if not protagonist_id:
        return []
    beats = _beats_for_character(index, protagonist_id)
    if not beats:
        return []

    acts = index.get("acts", [])
    if not acts:
        return []

    # Sort acts by order to find final act
    sorted_acts = sorted(acts, key=lambda a: a.get("order", 0))
    final_act = sorted_acts[-1]
    final_act_id = final_act.get("id", "")

    scene_to_act = {s.get("id"): s.get("act_id") for s in index.get("scenes", [])}
    flags = []

    for beat in beats:
        scene_id = beat.get("scene", "")
        act_id = scene_to_act.get(scene_id, "")

        if beat.get("is_crisis") and act_id == final_act_id:
            flags.append({
                "check": "crisis_placement",
                "severity": "warning",
                "act": act_id,
                "message": f"Crisis beat '{beat.get('label', beat.get('id',''))}' is in final act — should crisis precede climax?",
                "data": {"beat_id": beat.get("id", ""), "scene": scene_id},
            })

        if beat.get("is_climax") and act_id != final_act_id:
            flags.append({
                "check": "crisis_placement",
                "severity": "warning",
                "act": act_id,
                "message": f"Climax beat '{beat.get('label', beat.get('id',''))}' is not in final act — should climax land at the end?",
                "data": {"beat_id": beat.get("id", ""), "scene": scene_id},
            })

    return flags


def _check_controlling_idea(index: dict, protagonist_id: str) -> list[dict]:
    """Check 4: Protagonist y_final sign vs. project value_at_close sign."""
    if not protagonist_id:
        return []
    beats = _beats_for_character(index, protagonist_id)
    if not beats:
        return []

    project = index.get("project", {})
    value_close = project.get("value_at_close", "")
    if not value_close:
        return []

    y_final = beats[-1].get("y", 0)
    y_sign = _y_sign(y_final)
    project_sign = _charge_to_sign(value_close)

    if y_sign != 0 and project_sign != 0 and y_sign != project_sign:
        return [{
            "check": "controlling_idea",
            "severity": "warning",
            "act": "project",
            "message": f"Protagonist final value ({y_final:+.1f}) contradicts project value_at_close ({value_close}) — intentional?",
            "data": {"y_final": y_final, "value_at_close": value_close},
        }]

    return []


def _check_antagonist_divergence(index: dict, protagonist_id: str, antagonist_id: str) -> list[dict]:
    """Check 5: At structural climax, P and A should move in opposite directions."""
    if not protagonist_id or not antagonist_id:
        return []
    p_beats = _beats_for_character(index, protagonist_id)
    a_beats = _beats_for_character(index, antagonist_id)
    if not p_beats or not a_beats:
        return []

    acts = index.get("acts", [])
    if not acts:
        return []

    sorted_acts = sorted(acts, key=lambda a: a.get("order", 0))
    final_act = sorted_acts[-1]
    climax_scene_id = final_act.get("climax_scene_id", "")
    if not climax_scene_id:
        return []

    # Find P and A Δy at the climax scene
    p_beat = next((b for b in p_beats if b.get("scene") == climax_scene_id), None)
    a_beat = next((b for b in a_beats if b.get("scene") == climax_scene_id), None)
    if not p_beat or not a_beat:
        return []

    p_y = p_beat.get("y", 0)
    a_y = a_beat.get("y", 0)

    p_sign = _y_sign(p_y)
    a_sign = _y_sign(a_y)

    if p_sign != 0 and a_sign != 0 and p_sign == a_sign:
        return [{
            "check": "antagonist_divergence",
            "severity": "warning",
            "act": final_act.get("id", ""),
            "message": f"Protagonist and antagonist both move {'+' if p_sign > 0 else ''}{p_y:.1f} at climax — should diverge?",
            "data": {"protagonist_dy": p_y, "antagonist_dy": a_y},
        }]

    return []


# ─── Public API ─────────────────────────────────────────────────────────────


def compute_coherence(index: dict) -> list[dict]:
    """Run all 5 coherence checks. Returns list of flag dicts (empty = all clear)."""
    protagonist_id = _protagonist_id(index)
    if not protagonist_id:
        return []

    antagonist_id = _antagonist_id(index)

    flags = []
    flags.extend(_check_directional_alignment(index, protagonist_id))
    flags.extend(_check_escalation(index, protagonist_id))
    flags.extend(_check_crisis_placement(index, protagonist_id))
    flags.extend(_check_controlling_idea(index, protagonist_id))
    flags.extend(_check_antagonist_divergence(index, protagonist_id, antagonist_id))

    return flags
