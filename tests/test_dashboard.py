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
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


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
                        lambda: {"root_path": str(v)})
    return v


def _import(vault, slug):
    from tools.story_import import handler
    handler({"project": slug, "confirm": True}, root_path=str(vault))


def _dash(vault, slug):
    from tools.story_dashboard import handler
    return json.loads(handler({"project": slug}, root_path=str(vault)))


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


class TestSceneBeatsReachTheDashboard:
    """The Beats tab reads `story.scene_beats[]` and nothing else.

    The base `story_load` map deliberately keeps the beats out — they are what
    make it large — and a scene carries only the record's *id*. So this is the
    one payload that must carry the record whole: a payload that carried the
    pointer and not the record would render a "beat list missing" empty state
    for every scene, with no error anywhere.
    """

    @pytest.fixture
    def data(self, vault):
        _make(vault, "stc")
        _import(vault, "stc")
        from core.db import get_dashboard_data
        return get_dashboard_data(vault / "projects" / "stc")["story_data"]

    def test_the_payload_carries_the_records(self, data):
        assert data["scene_beats"], "no scene_beats record reached the dashboard"

    def test_the_record_travels_whole(self, vault, data):
        """Every field written on the record reaches the payload, key for key.

        The tab reads `driver`, `scene_objective`, `turning_point`, `beats`,
        `changes` and `true_character`. A payload that trimmed any of them would
        silently drop that part of the scene.
        """
        conn = sqlite3.connect(str(vault / "projects" / "stc" / ".story" / "story.db"))
        rows = {r[0]: json.loads(r[1] or "{}") for r in conn.execute(
            "SELECT id, extra FROM entities WHERE type='scene_beats' AND is_deleted=0")}
        conn.close()
        assert rows, "the fixture has no scene_beats record to compare against"
        for rec in data["scene_beats"]:
            for key, value in rows[rec["id"]].items():
                assert rec.get(key) == value, f"{key} did not travel whole"

    def test_each_record_resolves_to_its_scene(self, data):
        """The tab finds a scene's record by `scene` OR `parent_id`.

        The record names its scene and the row links it; the two are allowed to
        disagree, so a reader must not depend on either alone. A record with
        neither renders as a missing beat list for the scene it belongs to.
        """
        for rec in data["scene_beats"]:
            assert rec.get("scene") or rec.get("parent_id"), f"unresolvable record: {rec}"

    def test_the_pointer_and_the_record_agree(self, data):
        """A scene's `scene_beats` pointer must name a record that is present."""
        ids = {r["id"] for r in data["scene_beats"]}
        for scene in data["scenes"]:
            pointer = scene.get("scene_beats", "")
            assert not pointer or pointer in ids, (
                f"scene {scene['id']} points at '{pointer}', which is not in the payload")

    def test_a_scene_carries_its_records_objective(self, data):
        """The Beats tab reads `scene_objective` off the SCENE, not the record.

        `renderSceneBeats` renders `sb.scene_objective` from the record it found
        by scene, but the tab's header chip and the character track both read it
        off the scene object the payload carries. A payload that emitted the
        records and not the scene-level field would show an empty "drives"
        header for every scene that has one — silently, since the record is
        present and the record is correct.
        """
        by_scene = {r["parent_id"]: r for r in data["scene_beats"]}
        checked = 0
        for scene in data["scenes"]:
            rec = by_scene.get(scene["id"])
            if not rec:
                continue
            checked += 1
            expected = scene.get("scene_objective", "")
            assert expected == rec.get("scene_objective", ""), (
                f"scene {scene['id']} and its record disagree on scene_objective")
        assert checked, "the fixture has no record to compare against"


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

    def test_unfilled_title_page_slot_shows_its_label(self):
        """An empty slot says which one it is, and is marked as a reminder.

        The token carries `unfilled: True` because the dashboard styles on it —
        without the flag a "Credit: N.A." reminder is typeset exactly like a
        credit, which is the defect B12b exists to remove.
        """
        from tools.story_dashboard import _build_title_page
        page = _build_title_page({"screenplay_title": "Hades"})
        by_type = {t["type"]: t for t in page["cc"] + page["bl"] + page["br"]}
        assert by_type["credit_unfilled"]["text"] == "Credit: N.A."
        assert by_type["credit_unfilled"]["unfilled"] is True
        assert by_type["author_unfilled"]["text"] == "Author: N.A."
        assert by_type["draft_unfilled"]["text"] == "Draft: N.A."
        assert by_type["contact_unfilled"]["text"] == "Contact: N.A."
        # The title is a real value, never a reminder.
        assert by_type["title"]["text"] == "Hades"
        assert "unfilled" not in by_type["title"]

    def test_an_empty_title_still_emits_a_title_token(self):
        """A slot that could vanish must not.

        screenplay_title is empty in the fixture. When the title token was
        dropped for being empty, cc[0] became the credit line and the dashboard —
        which split the block by position — typeset "Credit: N.A." as the title.
        The token is now always present, and the dashboard finds it by `type`.
        """
        from tools.story_dashboard import _build_title_page
        page = _build_title_page({"screenplay_title": "", "credit": "Written by"})
        types = [t["type"] for t in page["cc"]]
        # The suffix, because the slot is empty — the point is that a token
        # exists at all, not which spelling it has.
        assert types[0] == "title_unfilled", f"the title is not first: {types}"
        assert page["cc"][0]["unfilled"] is True
        assert page["cc"][0]["text"] == "Screenplay Title: N.A."
        # The credit is still a credit, not the title.
        assert [t for t in page["cc"] if t["type"] == "credit"][0]["text"] == "Written by"

    def test_a_filled_slot_is_not_a_reminder(self):
        from tools.story_dashboard import _build_title_page
        page = _build_title_page({"screenplay_title": "Hades", "credit": "Written by"})
        credit = next(t for t in page["cc"] if t["type"] == "credit")
        assert credit["text"] == "Written by"
        assert "unfilled" not in credit
        # The rest still show their reminders, so a partly-filled page is legible.
        assert any(t["type"] == "author_unfilled" for t in page["cc"])


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

    def test_unfilled_title_page_reminder_reaches_the_dom(self, vault, tmp_path):
        """B12b, end to end: the reminder must survive Python -> JSON -> JS.

        The unit test proves `_build_title_page` emits the token. This proves the
        dashboard's JS still renders it — the layer that used to join every
        token into one string and drop `type`, which is why the flag exists.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        # The fixture project has no credit/author, so the reminders are live.
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        served = tmp_path / "site_tp"
        served.mkdir()
        (served / "index.html").write_text(html)

        out = subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=6000", "--dump-dom",
             f"file://{served / 'index.html'}"],
            capture_output=True, text=True, timeout=120)
        assert "Uncaught" not in out.stderr, out.stderr[-800:]
        dom = out.stdout
        # The label reached the page...
        assert "Credit: N.A." in dom, "unfilled slot reminder never rendered"
        # ...and it is marked as a reminder, not typeset as a credit.
        assert "tp-unfilled" in dom, "reminder is not distinguishable from content"
        # The fixture has no screenplay_title, so the title slot is a reminder
        # too — and it must sit in the title position, not be replaced by the
        # credit line. This is the assertion that catches a positional split.
        assert "Screenplay Title: N.A." in dom, "the title slot vanished"
        assert '<span class="tp-unfilled">Credit: N.A.</span>' in dom, (
            "the credit reminder is in the title position")

    def _dom(self, html, tmp_path, name, drive_js):
        """Serve the assembled page, run `drive_js` in it, return the built DOM.

        The panels are built on click, so a role that only renders inside one
        is invisible to a plain --dump-dom. Driving the dashboard's own JS is
        the point: it is the reader that could be reading a key the backend no
        longer emits, and that mismatch is silent everywhere else.
        """
        served = tmp_path / name
        served.mkdir()
        page = html.replace("</body>", f"<script>{drive_js}</script></body>")
        (served / "index.html").write_text(page)
        out = subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=6000", "--dump-dom",
             f"file://{served / 'index.html'}"],
            capture_output=True, text=True, timeout=120)
        assert "Uncaught" not in out.stderr, out.stderr[-800:]
        return out.stdout

    def test_a_scenes_plot_role_reaches_the_dom(self, vault, tmp_path):
        """Phase 7, end to end: `scene.plots[].role` must survive Python -> JS.

        The key was `beat` while story_load already said `role`. Both names
        produced valid HTML; only the render shows which one the panel read.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_role",
                        "DASH.showScenePanel('central-room-night')")
        # The fixture gives that scene the-resistance in the `climax` role.
        assert "The Resistance" in dom, "the scene's plot never rendered"
        assert "· CLIMAX" in dom, (
            "the plot role did not render — the panel is reading a key the "
            "backend no longer emits")
        assert "· BEAT" not in dom, "the old key is still being read"

    def test_every_class_the_panels_use_exists_in_the_css(self, vault):
        """A renamed class that misses the CSS un-styles a panel, silently.

        Same failure shape as the key rename this phase fixed: the HTML is
        valid, the DOM builds, the row just loses its padding and italics.
        Nothing else in the suite can see it, so check the two lists meet.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
        js = " ".join((FIXTURE.parents[2] / "src/dashboard/js" / p).read_text()
                      for p in ["panels/entity-panels.js", "colors.js",
                                "statistics/statistics.js",
                                "panels/panel-tabs.js", "panels/scene-beats-tab.js",
                                "panels/character-journey-tab.js"])
        # Capture the whole attribute, then keep only plain class tokens —
        # skip anything holding a template hole or a space-separated group we
        # can't resolve. A regex too narrow here would skip the very class
        # names this test exists to catch.
        raw = re.findall(r'class="([^"]*)"', js)
        used = set()
        for group in raw:
            if "${" in group or "(" in group:
                continue
            used.update(c for c in group.split()
                        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", c))
        missing = sorted(c for c in used if f".{c}" not in css)
        assert used, "no class names parsed — the extractor is broken, not the CSS"
        assert not missing, f"classes used in JS but absent from the CSS: {missing}"

    def test_all_five_roles_render_in_the_plot_panel(self, vault, tmp_path):
        """One section per role, from the same list Python pins.

        Four roles render and the fifth is missing when a role is added in
        Python and forgotten in the JS list — an empty panel, no error.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_roles",
                        "DASH.loadSampleData();"
                        "DASH.showPlotPanel('brother-investigation')")
        for role in ("Setup", "Complication", "Crisis", "Climax", "Resolution"):
            assert f">{role}<" in dom, f"the {role} section is missing"

    def test_the_scene_panel_opens_with_its_beats_tab(self, vault, tmp_path):
        """End to end: the assembled page renders the Beats tab, not a stub.

        The node and Chrome harnesses of the tab work read the delivered files
        directly. This drives `story_dashboard.handler` → `assemble_dashboard` →
        the dashboard's own JS, which is the shipping path: it is the only check
        that proves the tab files are in `JS_ORDER`, that the panel-tabs wrap
        landed, and that the records actually reach the panel.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_beats",
                        "DASH.showScenePanel('central-room-day');"
                        "DASH.panelTabs.activate('beats');")
        assert "ptab-strip" in dom, "the panel opened with no tab strip — the wrap did not land"
        assert "Beats" in dom, "the Beats tab never registered"
        # The tab's own pane, not the Overview it lifted in.
        assert 'data-pane="beats"' in dom, "the Beats pane was never built"
        assert "ptab-pane" in dom
        # The pane's CONTENT. A strip that opens and an empty pane is the
        # failure this phase is about: the tab files loaded but the record
        # never reached them, which renders the shell with nothing in it.
        assert "sb-exchange" in dom, "the beat exchange never drew — no record reached the tab"
        assert "sb-beat" in dom, "no beat row rendered"
        assert "sb-gap" in dom, "a gap opened but never rendered"
        assert "Kael" in dom, "the beat participants never rendered"
        # The fixture's record names the scene's objective; the payload must
        # carry it on the scene, not only on the record.
        assert "whether the door was ever locked" in dom, (
            "the scene objective never reached the tab")

    def test_the_character_panel_opens_with_its_journey_tab(self, vault, tmp_path):
        """The Journey tab, same shipping path. Kael is the fixture's protagonist.

        The ribbon needs a value model, so this also proves `track-data.js`
        loaded after `value-graph.js` in the assembled bundle — a reorder would
        leave `D.valueModel` undefined and the pane rendering nothing.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_journey",
                        "DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
                        "DASH.panelTabs.activate('journey');")
        assert "ptab-strip" in dom, "the panel opened with no tab strip — the wrap did not land"
        assert "Journey" in dom, "the Journey tab never registered"
        assert 'data-pane="journey"' in dom, "the Journey pane was never built"
        # The ribbon is the part that needs the value model and the geometry.
        assert "jr-svg" in dom, "the journey ribbon never drew"
        # The timeline is the part that needs the payload's scenes and the
        # milestone labels; a ribbon that draws and a timeline that stays
        # empty is a half-wired tab.
        assert "jr-row" in dom, "the journey timeline never rendered a scene row"
        assert "In words" in dom, "the timeline section never rendered"
        assert "Kael" in dom, "the character never reached the pane"


class TestAssembledOrder:
    """`CSS_ORDER`/`JS_ORDER` are the only thing that loads the tab files.

    They are edited by hand and nothing reads them until the dashboard is
    assembled, so a typo'd entry or a wrong position is found at render time —
    or not at all: a JS reorder leaves the panel rendering exactly as it did
    before, with no error. Both lists are therefore checked against the source
    tree and against each other, here.
    """

    @pytest.fixture
    def orders(self):
        from tools.story_dashboard import CSS_ORDER, JS_ORDER
        return CSS_ORDER, JS_ORDER

    def test_every_css_file_in_css_order_exists(self, orders):
        """A typo'd entry only surfaces when the dashboard is assembled."""
        css_order, _ = orders
        dashboard_dir = FIXTURE.parents[2] / "src" / "dashboard"
        missing = [f for f in css_order if not (dashboard_dir / "css" / f).exists()]
        assert not missing, f"CSS_ORDER names files that do not exist: {missing}"

    def test_every_js_file_in_the_order_exists(self, orders):
        """The same guard for the scripts, which is the list more likely to drift."""
        _, js_order = orders
        dashboard_dir = FIXTURE.parents[2] / "src" / "dashboard"
        missing = [f for f in js_order if not (dashboard_dir / "js" / f).exists()]
        assert not missing, f"JS_ORDER names files that do not exist: {missing}"

    def test_no_file_is_loaded_twice(self, orders):
        css_order, js_order = orders
        for name, order in (("CSS_ORDER", css_order), ("JS_ORDER", js_order)):
            dupes = sorted({f for f in order if order.count(f) > 1})
            assert not dupes, f"{name} loads these more than once: {dupes}"

    def test_js_order_satisfies_the_tab_dependencies(self, orders):
        """Every wrap must be in place before the module that needs it runs.

        `panel-tabs.js` replaces `openPanel`, `closePanel` and the `show*Panel`
        functions at load time, so it must come after all of them. The two tab
        modules call `D.panelTabs.register` at load time and read
        `D.valueModel`, so they come after `panel-tabs.js` and `track-data.js`.
        """
        _, js_order = orders
        at = lambda f: js_order.index(f)
        assert at("panels/panel-manager.js") < at("panels/panel-tabs.js"), (
            "panel-tabs.js wraps openPanel, so it must load after panel-manager.js")
        assert at("panels/entity-panels.js") < at("panels/panel-tabs.js"), (
            "panel-tabs.js wraps show*Panel, so it must load after entity-panels.js")
        assert at("graph/value-graph.js") < at("graph/track-data.js"), (
            "track-data.js reads D.valueModel, defined in value-graph.js")
        for tab in ("panels/scene-beats-tab.js", "panels/character-journey-tab.js"):
            assert at("panels/panel-tabs.js") < at(tab), (
                f"{tab} registers into panel-tabs.js at load time")
            assert at("graph/track-data.js") < at(tab), (
                f"{tab} reads the character track, derived in track-data.js")
