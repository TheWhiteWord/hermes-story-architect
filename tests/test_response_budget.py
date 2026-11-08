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

@pytest.fixture(autouse=True)
def _no_user_config(tmp_path, monkeypatch):
    """A developer's own ~/.config/story-architect/config.toml must not change
    what these tests expect from the default budget."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)


@pytest.fixture(autouse=True)
def _no_user_config(tmp_path, monkeypatch):
    """A developer's own ~/.config/story-architect/config.toml must not change
    what these tests expect from the default budget."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)


FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"
N_SEQ, PER_SEQ = 6, 8          # 48 scenes: enough to overflow a small budget
N_REL_COPIES = 10              # 3 real relationships x 10 = 33 total
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
    # A larger cast: ten copies of each of the fixture's three relationships,
    # so which characters they involve is real, not invented.
    for tpl_file in sorted((project_dir / "relationships").glob("*.md")):
        tpl = tpl_file.read_text()
        for r in range(N_REL_COPIES):
            (project_dir / "relationships" / f"{tpl_file.stem} {r}.md").write_text(
                _sub(_sub(tpl, id=f"{tpl_file.stem.lower().replace(' ', '-')}-{r}"),
                     name=f"{tpl_file.stem} {r}"))
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


# ── story_retrieve ──────────────────────────────────────────────────────────

def retrieve(project, ids, entity_type="scene", **extra):
    from story_architect.tools.story_retrieve import handler
    args = {"project": "save-the-children", "entity_type": entity_type, "id": ids,
            "sections": ["all"], "fields": ["all"], **extra}
    return json.loads(handler(args, root_path=str(project.parent.parent)))


def gen_ids():
    return [f"gen-scene-{i}" for i in range(N_SEQ * PER_SEQ)]


def unbudgeted(project, monkeypatch, ids):
    """Ground truth: every entity, read with a budget too big to bite. The
    default budget would truncate the truth itself."""
    monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "100000000")
    r = retrieve(project, ids)
    assert "truncated" not in r
    return {e["id"]: e for e in r["entities"]}


class TestRetrieveBudget:
    def test_fitting_response_is_unchanged(self, small, monkeypatch):
        monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)
        r = retrieve(small, ["central-room-day", "central-room-night"])
        assert len(r["entities"]) == 2
        assert not {"truncated", "deferred_ids", "hint", "over_budget"} & r.keys()

    def test_over_budget_returns_whole_entities_then_defers_the_tail(
            self, big, monkeypatch):
        ids = gen_ids()
        truth = unbudgeted(big, monkeypatch, ids)
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        r = retrieve(big, ids)

        assert r["truncated"] is True
        got = [e["id"] for e in r["entities"]]
        assert got and r["deferred_ids"]
        assert got + r["deferred_ids"] == ids, "contiguous, in request order"
        for e in r["entities"]:
            assert e == truth[e["id"]], "an entity is whole or absent, never cut"
        assert len(json.dumps(r)) <= int(SMALL)
        assert "deferred_ids" in r["hint"]

    def test_following_deferred_ids_reads_everything_exactly_once(
            self, big, monkeypatch):
        ids = gen_ids()
        truth = unbudgeted(big, monkeypatch, ids)
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        pending, seen, calls = ids, [], 0
        while pending:
            r = retrieve(big, pending)
            calls += 1
            assert calls < 100, "paging must make progress"
            seen += [e["id"] for e in r["entities"]]
            pending = r.get("deferred_ids", [])
        assert seen == ids and calls > 1
        assert set(seen) == set(truth) and len(seen) == len(set(seen))

    def test_first_entity_is_returned_even_if_it_alone_is_too_big(
            self, big, monkeypatch):
        import sqlite3
        db = big / ".story" / "story.db"
        conn = sqlite3.connect(db)
        conn.execute("UPDATE sections SET body=? WHERE entity_id='gen-scene-0' "
                     "AND rowid=(SELECT min(rowid) FROM sections "
                     "WHERE entity_id='gen-scene-0')", ("x" * 20000,))
        conn.commit(); conn.close()
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "8000")

        r = retrieve(big, ["gen-scene-0", "gen-scene-1"])
        assert [e["id"] for e in r["entities"]] == ["gen-scene-0"]
        assert r["deferred_ids"] == ["gen-scene-1"]
        assert r["over_budget"]["id"] == "gen-scene-0"
        assert max(r["over_budget"]["section_sizes"].values()) >= 20000
        assert "one section at a time" in r["hint"]

        alone = retrieve(big, ["gen-scene-0"])
        assert [e["id"] for e in alone["entities"]] == ["gen-scene-0"]
        assert "deferred_ids" not in alone and "over_budget" in alone

    def test_not_found_and_deferral_both_reported(self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        r = retrieve(big, ["no-such-scene"] + gen_ids())
        assert [n["id"] for n in r["not_found"]] == ["no-such-scene"]
        assert r["truncated"] is True
        assert "story_load" in r["hint"] and "deferred_ids" in r["hint"]

    def test_a_scoped_request_is_never_truncated(self, big, monkeypatch):
        """Asking for one section is the way to stay under budget."""
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", SMALL)
        r = retrieve(big, gen_ids()[:3], sections=["Content"], fields=None)
        assert len(r["entities"]) == 3 and "truncated" not in r


# ── relationship view ───────────────────────────────────────────────────────

class TestRelationshipViewBudget:
    @staticmethod
    def rels(project, **args):
        return load(project, view="relationship", **args)

    def test_fitting_view_is_unchanged(self, small, monkeypatch):
        monkeypatch.delenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", raising=False)
        r = self.rels(small)
        assert "detail" not in r and r["relationships"]
        assert all("perspectives" in x for x in r["relationships"])

    def test_over_budget_compacts_but_lists_every_relationship(
            self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "100000000")
        full = self.rels(big)["relationships"]
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "6000")
        r = self.rels(big)

        assert [x["id"] for x in r["relationships"]] == [x["id"] for x in full]
        compacted = r["detail"]["compacted"]
        assert compacted, "33 relationships should overflow a 6000 budget"
        by_id = {x["id"]: x for x in full}
        for x in r["relationships"]:
            if x["id"] in compacted:
                assert set(x) == {"id", "name", "characters"}
                assert x["characters"] == by_id[x["id"]]["characters"]
            else:
                assert x == by_id[x["id"]]
        assert len(json.dumps(r)) < len(json.dumps({"relationships": full}))

    def test_character_filter_returns_that_characters_relationships_in_full(
            self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "100000000")
        full = self.rels(big)["relationships"]
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "2000")  # ignored
        r = self.rels(big, character="kael")
        expected = [x for x in full if "kael" in x["characters"]]
        assert expected and r["relationships"] == expected
        assert r["character"] == "kael" and "detail" not in r
        assert len(expected) < len(full), "the filter must actually narrow"

    def test_the_expand_hint_actually_expands(self, big, monkeypatch):
        monkeypatch.setenv("STORY_ARCHITECT_MAX_RESPONSE_CHARS", "6000")
        r = self.rels(big)
        left_out = [x for x in r["relationships"] if x["id"] in r["detail"]["compacted"]]
        char = left_out[0]["characters"][0]
        again = self.rels(big, character=char)["relationships"]
        assert all("perspectives" in x for x in again)
        assert {x["id"] for x in left_out if char in x["characters"]} <= \
            {x["id"] for x in again}

    def test_unknown_character_says_so(self, big):
        r = self.rels(big, character="nobody")
        assert r["relationships"] == [] and "nobody" in r["note"]
