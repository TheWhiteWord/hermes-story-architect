"""Response budget and act/sequence scoping for story_load.

A feature-length story outgrows any host cap: the base map costs a few hundred
characters per developed scene, so ~100 scenes is already ~50k chars. Hermes
swaps an over-cap MCP result for a ~1.5k preview plus a file path, and these
agents have no file tools to read it. So the TOOL keeps to a budget and says,
in its own words, what it compacted and how to expand it.

The contract these tests pin:
  * a response that fits is unchanged — small projects see no difference;
  * over budget, trailing sequences compact; nothing is removed; `detail` names
    them and the expand call works;
  * `sequence=` is an explicit request and is always answered in full;
  * `act=` / `sequence=` put full rows where the work is, compact rows elsewhere.
"""

import json
import re
import shutil
from pathlib import Path

import pytest

from story_architect.core import budget
from story_architect.core.db import get_project_summary
from story_architect.tools.story_load import handler as load_handler

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"
N_SEQ, PER_SEQ = 6, 8          # 48 scenes: enough to overflow a small budget
SMALL = "6000"                 # chars; forces compaction without a huge project


def _sub(text, **kv):
    for k, v in kv.items():
        text = re.sub(rf"^{k}: .*$", f"{k}: {v}", text, flags=re.M, count=1)
    return text


def _grow(project_dir: Path):
    """Add N_SEQ sequences of PER_SEQ developed scenes, cloned from the
    fixture's own files so every field and relation is shaped like real data."""
    seq_tpl = (project_dir / "sequences" / "The Discovery.md").read_text()
    scene_tpl = (project_dir / "scenes" / "Central Room - Day.md").read_text()
    beats_tpl = (project_dir / "scene_beats" / "Central Room - Day.md").read_text()
    n = 0
    for s in range(N_SEQ):
        (project_dir / "sequences" / f"Gen Seq {s}.md").write_text(
            _sub(seq_tpl, id=f"gen-seq-{s}", order=100 + s, title=f"Gen Seq {s}"))
        for _ in range(PER_SEQ):
            (project_dir / "scenes" / f"Gen Scene {n}.md").write_text(
                _sub(scene_tpl, id=f"gen-scene-{n}", order=1000 + n,
                     title=f"Gen Scene {n}", heading=f"INT. ROOM {n} - DAY",
                     sequence_id=f"gen-seq-{s}"))
            (project_dir / "scene_beats" / f"Gen Scene {n}.md").write_text(
                _sub(beats_tpl, id=f"gen-scene-{n}-beats", scene=f"gen-scene-{n}"))
            n += 1


def _import(vault: Path, monkeypatch):
    import story_architect.core.config
    monkeypatch.setattr(story_architect.core.config, "load_plugin_config",
                        lambda: {"root_path": str(vault)})
    from story_architect.tools.story_import import handler as import_handler
    result = json.loads(import_handler(
        {"project": "save-the-children", "confirm": True}, root_path=str(vault)))
    assert "error" not in result, result


@pytest.fixture
def small(tmp_path, monkeypatch):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault / "projects" / "save-the-children")
    _import(vault, monkeypatch)
    return vault / "projects" / "save-the-children"


@pytest.fixture
def big(tmp_path, monkeypatch):
    vault = tmp_path / "v"
    proj = vault / "projects" / "save-the-children"
    shutil.copytree(FIXTURE, proj)
    _grow(proj)
    _import(vault, monkeypatch)
    return proj


def load(project, **args):
    vault = str(project.parent.parent)
    return json.loads(load_handler({"project": "save-the-children", **args},
                                   root_path=vault))


def scenes_of(result):
    return {s["id"]: s for a in result["acts"] for q in a["sequences"]
            for s in q["scenes"]}


def seq_ids(result):
    return [q["id"] for a in result["acts"] for q in a["sequences"]]


COMPACT_KEYS = {"id", "title", "status"}


# ── the helper ──────────────────────────────────────────────────────────────

class TestBudgetHelper:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    @pytest.mark.parametrize("bad", ["", "abc", "-5", "10", "1e5"])
    def test_bad_values_fall_back(self, monkeypatch, bad):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", bad)
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    def test_env_value_is_used(self, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "12345")
        assert budget.max_response_chars() == 12345

    def test_largest_fitting_is_exact(self):
        # unit i costs 100 chars full, 10 compact; 10 units, budget for 4 full
        def build(k):
            return {"u": ["x" * 100 if i < k else "x" * 10 for i in range(10)]}
        base = budget.json_size(build(0))
        per_full = budget.json_size(build(1)) - base
        k, out = budget.largest_fitting(build, 10, base + 4 * per_full)
        assert k == 4 and budget.json_size(out) <= base + 4 * per_full
        assert budget.largest_fitting(build, 10, 10**9)[0] == 10

    def test_floor_is_zero_not_an_error(self):
        k, out = budget.largest_fitting(lambda k: {"u": "x" * (50 + k)}, 3, 5)
        assert k == 0 and out is not None


# ── base map ────────────────────────────────────────────────────────────────

class TestBaseMapBudget:
    def test_fitting_response_is_unchanged(self, small, monkeypatch):
        """A small project must not see the budget at all."""
        monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)
        assert load(small) == get_project_summary(small)
        assert "detail" not in load(small) and "scope" not in load(small)

    def test_over_budget_compacts_from_the_end_and_removes_nothing(
            self, big, monkeypatch):
        full = get_project_summary(big)                       # unbudgeted truth
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        result = load(big)

        assert scenes_of(result).keys() == scenes_of(full).keys()   # complete
        compacted = result["detail"]["compacted"]
        assert compacted, "this project should overflow a 6000-char budget"
        order = seq_ids(result)
        assert compacted == order[len(order) - len(compacted):], \
            "compaction must be a suffix of the story, not a scatter"
        for q in (q for a in result["acts"] for q in a["sequences"]
                  if q["id"] in compacted):
            for s in q["scenes"]:
                assert set(s) <= COMPACT_KEYS | {"characters"}
        assert len(json.dumps(result)) < len(json.dumps(full))

    def test_leading_sequences_keep_full_rows(self, big, monkeypatch):
        full = scenes_of(get_project_summary(big))
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "20000")
        result = load(big)
        compacted = set(result.get("detail", {}).get("compacted", []))
        kept = [q for a in result["acts"] for q in a["sequences"]
                if q["id"] not in compacted]
        assert kept, "a 20000 budget should hold at least one full sequence"
        for q in kept:
            for s in q["scenes"]:
                assert s == full[s["id"]]

    def test_the_expand_hint_actually_expands(self, big, monkeypatch):
        full = scenes_of(get_project_summary(big))
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        target = load(big)["detail"]["compacted"][-1]
        expanded = load(big, sequence=target)
        rows = [s for a in expanded["acts"] for q in a["sequences"]
                if q["id"] == target for s in q["scenes"]]
        assert rows and all(s == full[s["id"]] for s in rows)

    def test_sequence_scope_ignores_the_budget(self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "2000")
        result = load(big, sequence="gen-seq-2")
        assert "detail" not in result
        assert result["scope"]["sequence"] == "gen-seq-2"
        full = scenes_of(get_project_summary(big))
        for q in (q for a in result["acts"] for q in a["sequences"]):
            for s in q["scenes"]:
                if q["id"] == "gen-seq-2":
                    assert s == full[s["id"]]
                else:
                    assert set(s) <= COMPACT_KEYS | {"characters"}

    def test_scoped_map_is_still_complete(self, big):
        full = get_project_summary(big)
        assert scenes_of(load(big, sequence="gen-seq-4")).keys() == \
            scenes_of(full).keys()

    def test_act_scope(self, big):
        act_id = load(big)["acts"][0]["id"]
        result = load(big, act=act_id)
        assert result["scope"]["act"] == act_id

    def test_unknown_ids_name_the_valid_ones(self, big):
        bad = load(big, sequence="nope")
        assert "error" in bad and "gen-seq-0" in bad["valid_sequences"]
        bad = load(big, act="nope")
        assert "error" in bad and bad["valid_acts"]


# ── dramatic_elements ───────────────────────────────────────────────────────

class TestDramaticElementsScopeAndBudget:
    @staticmethod
    def _seqs(result):
        return [q for a in result["acts"] for q in a["sequences"]]

    def test_fitting_view_has_no_detail_and_keeps_scenes(self, small, monkeypatch):
        monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)
        result = load(small, view="dramatic_elements")
        assert "detail" not in result
        assert all("scenes" in q for q in self._seqs(result))

    def test_sequence_scope_returns_only_that_sequence(self, big):
        result = load(big, view="dramatic_elements", sequence="gen-seq-3")
        seqs = self._seqs(result)
        assert [q["id"] for q in seqs] == ["gen-seq-3"]
        assert len(seqs[0]["scenes"]) == PER_SEQ
        assert result["sequence"] == "gen-seq-3"

    def test_sequence_scope_ignores_the_budget(self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "2000")
        result = load(big, view="dramatic_elements", sequence="gen-seq-3")
        assert "detail" not in result
        assert len(self._seqs(result)[0]["scenes"]) == PER_SEQ

    def test_over_budget_collapses_to_counts_with_a_hint(self, big, monkeypatch):
        full = load(big, view="dramatic_elements")
        n_full = {q["id"]: len(q["scenes"]) for q in self._seqs(full)}
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "9000")
        result = load(big, view="dramatic_elements")
        compacted = result["detail"]["compacted"]
        assert compacted
        for q in self._seqs(result):
            if q["id"] in compacted:
                assert "scenes" not in q and q["scene_count"] == n_full[q["id"]]
            else:
                assert len(q["scenes"]) == n_full[q["id"]]
        # nothing vanished: every sequence is still listed
        assert [q["id"] for q in self._seqs(result)] == \
            [q["id"] for q in self._seqs(full)]

    def test_unknown_sequence_names_the_valid_ones(self, big):
        bad = load(big, view="dramatic_elements", sequence="nope")
        assert "error" in bad and "gen-seq-0" in bad["valid_sequences"]
