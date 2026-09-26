"""Project resolution must fail loudly rather than write to the wrong story.

The bug: FUZZY_THRESHOLD is 40, shared with screenplay title matching. At 40 an
unrelated project name scores high enough to be accepted — "ghost" scored 72
against a short slug "stc" — so story_memory wrote to the wrong project and
reported success. Resolving to the wrong project is worse than failing, because
a successful-looking write is the one the agent will not double-check.

Threshold is local to story_resolve (PROJECT_THRESHOLD), not the shared constant.
"""

import json
import shutil

import pytest

from core.db import get_project_memory
from tools.story_import import handler as import_handler
from tools.story_memory import handler as memory_handler
from tools.story_resolve import PROJECT_THRESHOLD, resolve_project


@pytest.fixture
def vault(tmp_path):
    """Two projects, so a fuzzy match has somewhere wrong to land."""
    v = tmp_path / "v"
    for slug in ("stc", "save-the-children"):
        dest = v / "projects" / slug
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            str(__import__("pathlib").Path(__file__).parent / "fixtures"
                / "save-the-children"), str(dest))
    import core.config
    import pytest as _p
    _monkey = _p.MonkeyPatch()
    _monkey.setattr(core.config, "load_plugin_config",
                    lambda: {"root_path": str(v)})
    yield v
    _monkey.undo()


def _mem(vault, **args):
    return json.loads(memory_handler(args, root_path=str(vault)))


class TestThreshold:
    def test_project_threshold_is_stricter_than_the_shared_one(self):
        from core.constants import FUZZY_THRESHOLD
        assert PROJECT_THRESHOLD > FUZZY_THRESHOLD

    def test_exact_slug_still_resolves(self, vault):
        assert resolve_project("stc", vault).name == "stc"

    def test_unrelated_name_is_rejected_not_guessed(self, vault):
        with pytest.raises(ValueError, match="No project matching"):
            resolve_project("ghost", vault)

    def test_rejection_lists_the_real_projects(self, vault):
        """The error must be actionable, not just a refusal."""
        with pytest.raises(ValueError) as exc:
            resolve_project("blah", vault)
        assert "save-the-children" in str(exc.value)

    def test_legitimate_near_match_still_resolves(self, vault):
        """Tightening the threshold must not break real fuzzy use."""
        assert resolve_project("the children", vault).name == "save-the-children"

    def test_screenplay_threshold_is_untouched(self):
        """The shared constant belongs to screenplay matching; we only added
        a local one, so a screenplay title match behaves exactly as before."""
        from core.constants import FUZZY_THRESHOLD
        assert FUZZY_THRESHOLD == 40


class TestNoWriteToWrongProject:
    def test_rejected_name_writes_nothing(self, vault):
        _mem(vault, action="add", project="ghost", category="decisions",
             entry="should never land")
        for slug in ("stc", "save-the-children"):
            memory = get_project_memory(vault / "projects" / slug)
            assert memory["decisions"] == []

    def test_rejection_is_an_error_not_a_success(self, vault):
        r = _mem(vault, action="add", project="ghost", category="decisions",
                 entry="x")
        assert r.get("success") is not True
        assert "No project matching" in r["error"]


class TestMatchConfidence:
    def test_exact_project_gets_no_warning(self, vault):
        assert "warning" not in _mem(
            vault, action="add", project="stc", category="decisions", entry="A.")

    def test_weak_match_is_reported(self, vault):
        r = _mem(vault, action="add", project="the children",
                 category="decisions", entry="B.")
        assert r["resolved_project"] == "save-the-children"
        assert r["match_score"] < 90
        assert "warning" in r

    def test_warning_says_where_it_wrote(self, vault):
        """The point of the warning: the agent can tell the user which story."""
        r = _mem(vault, action="add", project="the children",
                 category="decisions", entry="C.")
        assert "save-the-children" in r["warning"]

    def test_warning_is_reported_on_remove_and_replace_too(self, vault):
        _mem(vault, action="add", project="the children", category="decisions",
             entry="D.")
        removed = _mem(vault, action="remove", project="the children",
                       category="decisions", old_entry="D.")
        assert "warning" in removed
        replaced = _mem(vault, action="add", project="the children",
                        category="decisions", entry="E.")
        assert "warning" in replaced
        rep = _mem(vault, action="replace", project="the children",
                   category="decisions", old_entry="E.", new_entry="F.")
        assert "warning" in rep

    def test_failures_are_not_double_reported(self, vault):
        """A failed call already lists the alternatives; no warning needed."""
        r = _mem(vault, action="add", project="the children",
                 category="decisions", entry="   ")
        assert r["success"] is False
        assert "warning" not in r
