"""story_dashboard must either render, or say why it can't.

The tool's failure mode is a silent one: it assembles HTML by string
substitution and reports `success: true` regardless. Two defects pinned here
were both invisible at the call site:

1. The output file was named after the project *title*, so two projects sharing
   a title wrote the same file — the second dashboard rendered the first
   project's data under its own name.
2. The injection anchor is a comment inside core.js. A silent .replace() meant
   that rewording it left __STORY_DATA__ unset and produced an empty dashboard
   that still reported success.
"""

import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _make(vault_root, slug, project_name=None):
    dest = vault_root / "projects" / slug
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(FIXTURE), str(dest))
    return dest


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "v"
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config",
                        lambda: {"vault_path": str(v)})
    return v


def _import(vault, slug):
    from tools.story_import import handler
    handler({"project": slug, "confirm": True}, vault_path=str(vault))


def _dash(vault, slug):
    from tools.story_dashboard import handler
    return json.loads(handler({"project": slug}, vault_path=str(vault)))


class TestAssemblesAndInjects:
    @pytest.fixture
    def rendered(self, vault):
        _make(vault, "stc")
        _import(vault, "stc")
        r = _dash(vault, "stc")
        assert r.get("success"), r
        return Path(r["dashboard_url"].split("?")[0].replace("file://", ""))

    def test_returns_a_file_url(self, vault):
        _make(vault, "stc")
        _import(vault, "stc")
        assert _dash(vault, "stc")["dashboard_url"].startswith("file://")

    def test_all_placeholders_are_replaced(self, rendered):
        html = rendered.read_text()
        for marker in ("<!-- CSS_PLACEHOLDER -->", "<!-- JS_PLACEHOLDER -->",
                       "<!-- SCREENPLAY_CSS_PLACEHOLDER -->"):
            assert marker not in html, f"{marker} left unreplaced"

    @pytest.mark.parametrize("global_name", [
        "__STORY_DATA__", "__SECTIONS__", "__SCREENPLAY_STATS__",
        "__STRUCTURAL_STATS__"])
    def test_each_injection_is_valid_json(self, rendered, global_name):
        """A malformed injection renders a blank panel, not an error."""
        html = rendered.read_text()
        m = re.search(r"window\.%s = (\{.*?\});\n" % global_name, html, re.S)
        assert m, f"{global_name} never injected"
        assert isinstance(json.loads(m.group(1)), dict)

    def test_story_data_carries_the_actual_story(self, rendered):
        html = rendered.read_text()
        m = re.search(r"window\.__STORY_DATA__ = (\{.*?\});\n", html, re.S)
        assert m
        data = json.loads(m.group(1))
        assert data["characters"], "no characters reached the dashboard"
        assert data["scenes"], "no scenes reached the dashboard"


class TestProjectSlugNotTitle:
    """The file must be per-project, or two projects share one dashboard."""

    def test_same_title_projects_get_different_files(self, vault):
        made = []
        for slug in ("alpha", "beta"):
            _make(vault, slug)
            _import(vault, slug)
            db = vault / "projects" / slug / ".story" / "story.db"
            conn = sqlite3.connect(str(db))
            conn.execute("UPDATE entities SET name='The Film' WHERE type='project'")
            conn.commit()
            conn.close()
            made.append(_dash(vault, slug)["dashboard_url"].split("?")[0])
        assert made[0] != made[1], "both projects wrote the same HTML file"

    def test_file_is_named_after_the_folder(self, vault):
        _make(vault, "stc")
        _import(vault, "stc")
        assert "stc" in _dash(vault, "stc")["dashboard_url"]

    def test_a_title_with_punctuation_cannot_break_the_filename(self, vault):
        _make(vault, "weird")
        _import(vault, "weird")
        url = _dash(vault, "weird")["dashboard_url"]
        assert url.rsplit("/", 1)[-1].split("?")[0] == "weird.html"


class TestCacheBuster:
    def test_reopening_yields_a_fresh_url(self, vault):
        import time
        _make(vault, "stc")
        _import(vault, "stc")
        first = _dash(vault, "stc")["dashboard_url"]
        time.sleep(1.1)
        second = _dash(vault, "stc")["dashboard_url"]
        assert first != second, "url unchanged, so an edited dashboard may be cached"

    def test_url_carries_a_timestamp(self, vault):
        _make(vault, "stc")
        _import(vault, "stc")
        assert "t=" in _dash(vault, "stc")["dashboard_url"]


class TestFailuresAreLoud:
    def test_missing_project_errors(self, vault):
        _make(vault, "stc")
        assert "error" in _dash(vault, "nonexistent")

    def test_missing_database_errors(self, vault):
        (vault / "projects" / "empty").mkdir(parents=True)
        assert "error" in _dash(vault, "empty")

    def test_a_lost_boot_marker_is_reported_not_swallowed(self, vault, monkeypatch):
        """The regression guard for the silent-empty-dashboard defect."""
        import tools.story_dashboard as sd
        monkeypatch.setattr(sd, "assemble_dashboard",
                            lambda d: "<html>// some reworded comment</html>")
        _make(vault, "stc")
        _import(vault, "stc")
        result = _dash(vault, "stc")
        assert "error" in result, "reported success with no data injected"
        assert "marker" in result["error"]


class TestScreenplayStats:
    def test_empty_text_yields_zeroed_stats_not_a_crash(self):
        from tools.story_dashboard import _compute_screenplay_stats
        stats = _compute_screenplay_stats("")
        assert stats["characterStats"]["characterCount"] == 0
        assert stats["sceneStats"]["scenes"] == []

    def test_scene_headings_are_counted(self):
        from tools.story_dashboard import _compute_screenplay_stats
        text = "INT. THE ROOM - DAY\n\nShe waits.\n\nINT. THE HALL - NIGHT\n\nHe runs.\n"
        stats = _compute_screenplay_stats(text)
        assert stats["sceneStats"]["scenes"], "no scene headings parsed"

    def test_duration_buckets_are_always_full_length(self):
        """The chart expects a fixed bucket count; a short token list would
        otherwise hand the JS a ragged array."""
        from tools.story_dashboard import _compute_screenplay_stats
        stats = _compute_screenplay_stats("INT. A - DAY\n\nOne line.\n")
        assert len(stats["durationStats"]["lengthchart_action"]) == 20
        assert len(stats["durationStats"]["lengthchart_dialogue"]) == 20

    def test_title_page_comes_from_project_data(self):
        from tools.story_dashboard import _build_title_page
        page = _build_title_page({"screenplay_title": "Hades", "author": "A"})
        assert any("Hades" == t["text"] for t in page["cc"])


@pytest.mark.skipif(not shutil.which("google-chrome"),
                    reason="headless chrome not available")
class TestActuallyRenders:
    """The strongest check available: run the page and inspect the built DOM.

    Everything above inspects strings. This executes the dashboard's own JS, so
    an injection that parses but that the bundle cannot consume still fails.
    """

    def test_page_executes_and_renders_story_content(self, vault, tmp_path):
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]

        html = Path(url.replace("file://", "")).read_text()
        served = tmp_path / "site"
        served.mkdir()
        (served / "index.html").write_text(html)

        out = subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=6000", "--dump-dom",
             f"file://{served / 'index.html'}"],
            capture_output=True, text=True, timeout=120)
        dom = out.stdout
        assert "Uncaught" not in out.stderr, out.stderr[-800:]
        # The DOM must be larger than the static file: the JS built it.
        assert len(dom) > len(html), "dashboard JS did not build any DOM"
        assert "Kael" in dom, "story content never rendered"
