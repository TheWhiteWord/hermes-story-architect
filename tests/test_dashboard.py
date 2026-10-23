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

    def test_the_llm_view_and_the_dashboard_agree(self, vault, data):
        """Two readers of the same rows must not disagree.

        `story_load`'s `dramatic_elements` view and `get_dashboard_data` both
        read the `scene_beats` records. The view emits the pointer and the two
        facts; the dashboard emits the record whole and the same two facts. A
        scene-first/record-fallback rule that changed in one reader only would
        give the LLM and the dashboard different objectives for the same scene,
        and nothing else in the suite would see it.
        """
        from tools.story_load import handler as load_handler

        view = json.loads(load_handler(
            {"project": "stc", "view": "dramatic_elements", "root_path": str(vault)}))
        rows = []

        def walk(node):
            if isinstance(node, dict):
                if "id" in node and "scene_beats" in node:
                    rows.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(view["acts"])
        assert rows, "the view emitted no scene carrying a scene_beats pointer"

        by_id = {r["id"]: r for r in data["scenes"]}
        records = {r["id"]: r for r in data["scene_beats"]}
        for row in rows:
            scene = by_id.get(row["id"])
            assert scene, f"the view named a scene the dashboard does not carry: {row['id']}"
            # The pointer names the same record, and the objective is the same
            # fact — the view takes the scene's own field first, the dashboard
            # the same way, so neither can drift ahead of the other.
            assert row["scene_beats"] in records, f"{row['id']}: unknown record"
            assert row.get("scene_objective", "") == scene.get("scene_objective", ""), (
                f"{row['id']}: the view and the dashboard disagree on the objective")
            assert row.get("turning_point", "") == records[row["scene_beats"]].get("turning_point", ""), (
                f"{row['id']}: the view's turning point is not the record's")

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

    def _probe(self, html, tmp_path, name, open_js, probe):
        """Run `open_js`, then `probe`, which must write JSON to `document.title`.

        `--dump-dom` returns the whole bundle, so a substring assertion over it
        can be satisfied by a string literal in the minified JS — `sb-gap` and
        `jr-row` are both literals in the tab files, and the fixture's text is in
        the injected payload. Reading the live DOM into the title is the only way
        to assert on what was actually built, and it is what makes the width and
        overlap checks possible at all.

        It is synchronous on purpose. `--dump-dom` produces no frames, so a
        `ResizeObserver` callback is never delivered and `requestAnimationFrame`
        never fires — a probe that waits for a resize-driven re-render is a flake.
        Anything that needs a different width must arrange it *before* the tab
        renders. See `test_the_beats_exchange_folds_into_one_column_when_narrow`.
        """
        served = tmp_path / name
        served.mkdir()
        # `*{transition:none}` because #detail-panel animates its width over
        # 0.2s and a synchronous read mid-transition returns 0.
        # The `;` after `open_js` is load-bearing: a newline does not terminate a
        # statement, so without it `open_js` followed by an IIFE parses as one
        # call — `showScenePanel('x')(function () {...})` — which throws and
        # leaves the title unset, looking exactly like a probe that never ran.
        page = html.replace(
            "</body>",
            "<style>*{transition:none !important;}</style>"
            f"<script>{open_js};\n{probe}</script></body>")
        (served / "index.html").write_text(page)
        out = subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=6000", "--dump-dom",
             f"file://{served / 'index.html'}"],
            capture_output=True, text=True, timeout=120)
        assert "Uncaught" not in out.stderr, out.stderr[-800:]
        m = re.search(r"<title>(\{.*?\})</title>", out.stdout, re.S)
        assert m, f"the probe never ran\n{out.stdout[-600:]}"
        return json.loads(m.group(1))

    # Each pane is probed in its own page: `mount()` replaces the whole panel
    # body, so opening a second panel destroys the first one's panes.
    _BEATS_PROBE = r"""
(function () {
  var pane = document.querySelector('.ptab-pane[data-pane="beats"]');
  if (!pane) { document.title = JSON.stringify({ error: 'no beats pane' }); return; }
  var q = s => pane.querySelector(s), qa = s => pane.querySelectorAll(s);
  var self = q('.sb-link.is-self');
  var tip = self ? self.querySelector('.sb-tip') : null;
  document.title = JSON.stringify({
    paneW: pane.clientWidth,
    lanes: qa('.sb-lane').length,
    beats: qa('.sb-beat').length,
    gaps: qa('.sb-gap').length,
    selfLinks: qa('.sb-link.is-self').length,
    selfPath: self ? self.querySelector('path').getAttribute('d') : null,
    selfTip: tip ? tip.style.left : null,
    cracks: qa('.sb-crack').length,
    exchange: q('.sb-exchange') ? q('.sb-exchange').className : '',
    empty: q('.panel-empty') ? q('.panel-empty').className : '',
    emptyText: q('.panel-empty') ? q('.panel-empty').textContent.replace(/\s+/g, ' ').trim() : '',
    laneNames: Array.prototype.map.call(qa('.sb-lane span'), e => e.textContent),
    objective: q('.sb-objective') ? q('.sb-objective').textContent : '',
    changes: qa('.sb-change-text').length,
    choices: qa('.sb-choice').length,
    notes: qa('.sb-notes').length,
    rhythm: q('.sb-rhythm') ? q('.sb-rhythm').textContent.replace(/\\s+/g, ' ').slice(0, 60) : '',
  });
})();
"""

    _JOURNEY_PROBE = r"""
(function () {
  var pane = document.querySelector('.ptab-pane[data-pane="journey"]');
  if (!pane) { document.title = JSON.stringify({ error: 'no journey pane' }); return; }
  var q = s => pane.querySelector(s), qa = s => pane.querySelectorAll(s);
  var svg = q('svg.jr-svg'), scroll = q('.jr-scroll');
  var box = el => { if (!el) return null; var r = el.getBoundingClientRect();
    return { l: r.left, r: r.right, w: r.width }; };
  var sr = box(scroll), vr = box(svg);
  var hits = Array.prototype.map.call(qa('.jr-hit'), box).filter(Boolean);
  var texts = Array.prototype.map.call(qa('svg.jr-svg text'), t => {
    var r = t.getBoundingClientRect();
    return { l: r.left, r: r.right, t: r.top, b: r.bottom, s: (t.textContent || '').slice(0, 24) };
  });
  var overlap = [];
  for (var i = 0; i < texts.length; i++) {
    for (var j = i + 1; j < texts.length; j++) {
      var a = texts[i], b = texts[j];
      if (a.l >= b.r || a.r <= b.l || a.t >= b.b || a.b <= b.t) continue;
      overlap.push([a.s, b.s]);
    }
  }
  var hit = q('.jr-hit.has');
  if (hit) hit.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 200, clientY: 200 }));
  var tip = document.querySelector('.jr-tip');
  document.title = JSON.stringify({
    paneW: pane.clientWidth,
    svgW: vr ? Math.round(vr.w) : null,
    scrollClientW: scroll ? scroll.clientWidth : null,
    scrollScrollW: scroll ? scroll.scrollWidth : null,
    overflow: scroll ? scroll.scrollWidth > scroll.clientWidth : null,
    hits: hits.length,
    hitsOutside: hits.filter(h => sr && (h.l < sr.l - 0.5 || h.r > sr.r + 0.5)).length,
    labelsPastRight: texts.filter(t => vr && t.r > vr.r + 0.5).length,
    overlaps: overlap.length, overlapSample: overlap.slice(0, 3),
    rows: qa('.jr-row').length,
    milestones: Array.prototype.map.call(qa('.tag-struct'), e => e.textContent),
    stats: qa('.jr-stat').length,
    focus: qa('.jr-focus').length,
    tip: tip ? { display: tip.style.display, text: (tip.textContent || '').replace(/\\s+/g, ' ').slice(0, 90) } : null,
  });
})();
"""

    def test_the_beats_pane_renders_the_exchange(self, vault, tmp_path):
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
        g = self._probe(html, tmp_path, "site_beats",
                        "DASH.showScenePanel('central-room-day');"
                        "DASH.panelTabs.activate('beats');", self._BEATS_PROBE)
        assert "error" not in g, g
        # The strip and the pane are the wrap; the pane's CONTENT is the tab.
        assert g["beats"] == 2, "the beat exchange never drew — no record reached the tab"
        assert g["gaps"] == 1, "a gap opened but never rendered"
        assert g["changes"] == 2, "the closing changes never rendered"
        assert g["choices"] == 1, "the true-character card never rendered"
        assert g["notes"] == 1, "the analysis notes never rendered"
        assert g["lanes"] == 2, f"the lanes never drew: {g['laneNames']}"
        assert g["laneNames"] == ["Kael", "The Central Room"], g["laneNames"]
        assert "whether the door was ever locked" in g["objective"], (
            "the scene objective never reached the tab — the payload carries it "
            "on the scene, not only on the record")
        assert g["exchange"] == "sb-exchange", g["exchange"]
        assert g["empty"] == "", "a scene with a beat list must not show an empty state"

    def test_the_self_directed_arrow_draws_with_its_head_at_the_turn(self, vault, tmp_path):
        """The fixture's first beat is Kael answering himself.

        The head belongs at the turn, not on the answering bubble: a self-directed
        arrow is the one beat whose path comes back to the lane it left, so a tip
        at the answering coordinate sits where the path never reaches.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, "site_beats_self",
                        "DASH.showScenePanel('central-room-day');"
                        "DASH.panelTabs.activate('beats');", self._BEATS_PROBE)
        assert g["selfLinks"] == 1, "the inner-conflict beat did not draw its own arrow"
        assert g["cracks"] == 1, "the gap's crack marker did not draw"
        m = re.search(r"C ([\d.]+) ", g["selfPath"])
        assert m, g["selfPath"]
        assert g["selfTip"] == m.group(1) + "%", (
            f"the head is at {g['selfTip']}, the turn is at {m.group(1)}%")

    _OVERVIEW_PROBE = r"""
(function () {
  var body = document.getElementById('panel-body');
  if (!body) { document.title = JSON.stringify({ error: 'no panel body' }); return; }
  document.title = JSON.stringify({
    placeholders: (body.innerHTML.match(/\[placeholder/g) || []).length,
    titles: Array.prototype.map.call(body.querySelectorAll('.panel-section-title'), e => e.textContent),
    muted: Array.prototype.map.call(body.querySelectorAll('.panel-muted'), e => e.textContent),
  });
})();
"""

    @pytest.mark.parametrize("open_js,name", [
        ("DASH.showScenePanel('central-room-day')", "ov_scene"),
        ("DASH.showPlotPanel('the-resistance')", "ov_plot"),
        ("DASH.showSequencePanel('seq-discovery')", "ov_seq"),
    ])
    def test_a_placeholder_is_not_rendered_as_content(self, vault, tmp_path, open_js, name):
        """`[placeholder — type/Section]` is a marker, not something the author wrote.

        The fixture's scene, sequence and plot files carry them, and the payload
        carries them too — so this asserts on the **rendered pane**, never on the
        page. An instruction to the writer must not be typeset as the writer's own
        prose, in any panel.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, name, open_js, self._OVERVIEW_PROBE)
        assert "error" not in g, g
        assert g["placeholders"] == 0, f"{name}: a placeholder reached the panel"

    def test_the_overview_keeps_the_sections_that_are_real(self, vault, tmp_path):
        """Dropping the placeholders must not drop the content beside them.

        The fixture's scene has three placeholder sections and three real ones;
        only the placeholders go.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, "ov_real",
                        "DASH.showScenePanel('central-room-day')", self._OVERVIEW_PROBE)
        assert "error" not in g, g
        # The panel has other section titles of its own (Characters, Location…),
        # so assert on what must be there and what must not.
        assert "Dramatic Function" in g["titles"] and "Notes" in g["titles"], g["titles"]
        assert not {"Objective", "Value Turn", "Production"} & set(g["titles"]), (
            f"a placeholder section was rendered: {g['titles']}")

    def test_the_scene_content_is_the_same_rule(self, vault, tmp_path):
        """A scene's Content is read outside the section renderer, so it needs the
        same guard — a `[placeholder — scene/Content]` would otherwise render as
        the scene's screenplay.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        # The fixture's scenes all have real Content; swap one for a placeholder
        # in the injected page and read the pane the panel built.
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text().replace(
            "The children step through the door. Blinking. Silent. The sky is impossibly large.",
            "[placeholder — scene/Content]")
        g = self._probe(html, tmp_path, "ov_content",
                        "DASH.showScenePanel('the-core-day')", self._OVERVIEW_PROBE)
        assert "error" not in g, g
        assert g["placeholders"] == 0, g
        # A placeholder Content falls back to the "nothing here" state rather
        # than typesetting the marker as the scene's screenplay.
        assert "No content yet." in g["muted"], g

    def test_the_beats_pane_says_when_a_scene_has_no_beat_list(self, vault, tmp_path):
        """The fixture's other two records are placeholders, on purpose.

        The pane is not empty — the scene's value turns still render — so an
        empty state keyed on the whole pane would stay silent while the strip's
        dot warns about exactly that. This is the real page, not a synthetic story.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, "site_beats_empty",
                        "DASH.showScenePanel('central-room-night');"
                        "DASH.panelTabs.activate('beats');", self._BEATS_PROBE)
        assert "error" not in g, g
        assert g["beats"] == 0 and g["lanes"] == 0, "the placeholder record drew an exchange"
        assert "is-missing" in g["empty"], f"the pane did not say the list is missing: {g['empty']!r}"
        assert "Beat list missing" in g["emptyText"], g["emptyText"]

    def test_the_beats_exchange_folds_into_one_column_when_narrow(self, vault, tmp_path):
        """Lane mode needs room, so the exchange folds at a narrow pane.

        `panel-tabs.js` opens a `wide: true` tab at the wide panel, so the widen
        button *narrows* it — a probe that assumes the opposite measures nothing.

        The panel is narrowed **before** the tab is activated, so the tab's first
        render is the narrow one. `--dump-dom` produces no frames, which means the
        `ResizeObserver` that would redraw it never fires: waiting for that
        re-render is a flake, not a test.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        wide = self._probe(html, tmp_path, "site_beats_wide",
                           "DASH.showScenePanel('central-room-day');"
                           "DASH.panelTabs.activate('beats');", self._BEATS_PROBE)
        assert wide["exchange"] == "sb-exchange", wide["exchange"]
        narrow = self._probe(html, tmp_path, "site_beats_narrow",
                             "DASH.showScenePanel('central-room-day');"
                             "document.querySelector('.ptab-widen').click();"
                             "DASH.panelTabs.activate('beats');", self._BEATS_PROBE)
        assert "is-stacked" in narrow["exchange"], (
            f"the exchange did not fold at a {narrow.get('paneW')}px pane: "
            f"{narrow['exchange']!r}")
        assert narrow["paneW"] < 480, f"the panel did not narrow: {narrow.get('paneW')}px"

    def test_a_chip_opens_that_entitys_own_panel(self, vault, tmp_path):
        """`data-ent="type:id"` is the protocol between a chip and its panel.

        A chip that renders but does not route leaves the tab a dead end, with no
        error anywhere.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(
            html, tmp_path, "site_beats_chip",
            "DASH.showScenePanel('central-room-day');"
            "DASH.panelTabs.activate('beats');",
            "var c = document.querySelector('.ptab-pane[data-pane=\"beats\"] [data-ent]');"
            "var ref = c && c.getAttribute('data-ent');"
            "if (c) c.click();"
            "document.title = JSON.stringify({ ref: ref,"
            "  after: document.getElementById('panel-name').textContent,"
            "  type: document.getElementById('panel-type').textContent });")
        assert g["ref"] == "character:kael", f"the chip does not name its entity: {g}"
        assert g["after"] == "Kael", f"the chip opened {g['after']!r}, not Kael's panel"
        assert g["type"] == "Protagonist", g

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
        g = self._probe(html, tmp_path, "site_journey",
                        "DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
                        "DASH.panelTabs.activate('journey');", self._JOURNEY_PROBE)
        assert "error" not in g, g
        assert g["paneW"] > 0, "the journey pane has no width"
        assert g["rows"] == 3, f"the journey timeline rendered {g['rows']} of 3 scene rows"
        assert g["stats"] == 4, "the coverage stats never rendered"
        assert g["hits"] == 3, f"{g['hits']} hit columns for 3 scenes"
        # The milestone labels are D.milestoneLabel's output, not the raw keys.
        assert g["milestones"] == ["Inciting Incident", "Climax", "Resolution"], g["milestones"]
        assert g["svgW"] == g["paneW"], (
            f"the ribbon is {g['svgW']}px of a {g['paneW']}px pane — it no longer fills it")

    def test_the_ribbon_does_not_overflow_and_no_labels_overlap(self, vault, tmp_path):
        """The four invariants Phase 3 measured, now permanent.

        Overflow, a hit column outside the scroll box, a label past the ribbon's
        right edge, and two labels sharing space. Only a browser can see any of
        them, and the last is the one that mattered: comparing text against marks
        gives false positives, because a label sitting on the mark it labels is
        normal chart practice.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        open_js = ("DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
                   "DASH.panelTabs.activate('journey');")
        for label, drive in (("wide", open_js),
                             ("narrow", open_js + "document.querySelector('.ptab-widen').click();")):
            g = self._probe(html, tmp_path, f"site_journey_{label}", drive, self._JOURNEY_PROBE)
            assert "error" not in g, g
            assert not g["overflow"], f"{label}: the ribbon overflows its pane"
            assert g["hitsOutside"] == 0, f"{label}: {g['hitsOutside']} hit columns outside the scroll box"
            assert g["labelsPastRight"] == 0, f"{label}: {g['labelsPastRight']} labels past the ribbon's right edge"
            assert g["overlaps"] == 0, f"{label}: overlapping labels: {g['overlapSample']}"
            assert g["svgW"] == g["paneW"], f"{label}: the ribbon is {g['svgW']}px of {g['paneW']}px"

    def test_the_journey_hover_card_shows_the_scene_behind_a_hit_column(self, vault, tmp_path):
        """Hover is the ribbon's only detail view; it must name the scene.

        A card that appears but is empty, or that never appears, is invisible to
        every other check here.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, "site_journey_hover",
                        "DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
                        "DASH.panelTabs.activate('journey');", self._JOURNEY_PROBE)
        assert g["tip"], "the hover card never appeared"
        assert g["tip"]["display"] == "block", g["tip"]
        assert "Central Room" in g["tip"]["text"], g["tip"]

    def test_the_journey_hover_card_is_quiet_without_a_hit_column(self, vault, tmp_path):
        """`mouseleave` must hide it, or the card follows the cursor for good."""
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(
            html, tmp_path, "site_journey_leave",
            "DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
            "DASH.panelTabs.activate('journey');",
            "var p = document.querySelector('.ptab-pane[data-pane=\"journey\"]');"
            "var h = p.querySelector('.jr-hit.has');"
            "h.dispatchEvent(new MouseEvent('mousemove', {bubbles:true, clientX:200, clientY:200}));"
            "var shown = document.querySelector('.jr-tip').style.display;"
            "p.dispatchEvent(new MouseEvent('mouseleave'));"
            "document.title = JSON.stringify({ shown: shown,"
            "  after: document.querySelector('.jr-tip').style.display });")
        assert g["shown"] == "block", g
        assert g["after"] == "none", f"the card stayed up: {g}"

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
        """The strip and the pane are the wrap; the wrap must be there.

        Content is `test_the_beats_pane_renders_the_exchange` — this one only
        proves the panel-tabs wrap landed, which is what `JS_ORDER` buys.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_strip",
                        "DASH.showScenePanel('central-room-day');"
                        "DASH.panelTabs.activate('beats');")
        assert "ptab-strip" in dom, "the panel opened with no tab strip — the wrap did not land"
        assert "Beats" in dom, "the Beats tab never registered"
        assert 'data-pane="beats"' in dom, "the Beats pane was never built"

    def test_the_character_panel_opens_with_its_journey_tab(self, vault, tmp_path):
        """The same wrap on the character panel. Content is the probe's.

        A character panel opens with no tabs at all when the wrap is missing, and
        it renders exactly as it did before — no error.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        dom = self._dom(html, tmp_path, "site_strip_char",
                        "DASH.showCharacterPanel(DASH.story.characters.find(c=>c.id==='kael'));"
                        "DASH.panelTabs.activate('journey');")
        assert "ptab-strip" in dom, "the panel opened with no tab strip — the wrap did not land"
        assert "Journey" in dom, "the Journey tab never registered"
        assert 'data-pane="journey"' in dom, "the Journey pane was never built"


    _SCENES_PROBE = r"""
(function () {
  var body = document.getElementById('panel-body');
  if (!body) { document.title = JSON.stringify({ error: 'no panel body' }); return; }
  var qa = s => body.querySelectorAll(s);
  document.title = JSON.stringify({
    titles: Array.prototype.map.call(qa('.panel-section-title'), e => e.textContent),
    rows: qa('.jr-row').length,
    changes: Array.prototype.map.call(qa('.jr-line'), e => e.textContent.replace(/\s+/g, ' ').trim()),
    scenes: Array.prototype.map.call(qa('.jr-scene'), e => e.getAttribute('data-ent')),
  });
})();
"""

    # The location, world and relationship panels have no tab of their own, so
    # their scene list lives in the Overview pane. This is the shipping path:
    # payload -> panel function -> the shared rows.
    @pytest.mark.parametrize("open_js,name,want_rows,want_changes,want_title", [
        ("DASH.showLocationPanel('the-central-room')", "scenes_loc", 2, 1, True),
        ("DASH.showWorldPanel('the-i')", "scenes_world", 3, 0, True),
        ("DASH.showRelationshipPanel(DASH.story.relationships.find(r=>r.id==='kael-mira'))",
         "scenes_rel", 0, 0, False),
    ])
    def test_the_panel_lists_its_scenes_and_changes(self, vault, tmp_path, open_js, name,
                                                    want_rows, want_changes, want_title):
        """Every scene the entity is in, and the change under the one that has it.

        The relationship case is the fixture's own shape: it declares `scenes` but
        records no change for any of them, so there is no section at all — a
        relationship has no scene link of its own, the closing change is it.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, name, open_js, self._SCENES_PROBE)
        assert "error" not in g, g
        assert ("Scenes" in g["titles"]) is want_title, f"{name}: {g['titles']}"
        assert g["rows"] == want_rows, f"{name}: {g['rows']} rows, wanted {want_rows}"
        assert len(g["changes"]) == want_changes, g["changes"]

    def test_a_location_shows_the_change_recorded_for_it(self, vault, tmp_path):
        """The change line is the record's sentence, not a paraphrase.

        `.jr-k` is a styled span, so the label and the sentence are adjacent in
        `textContent` — the space is the span's margin, not a character.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(html, tmp_path, "scenes_loc_change",
                        "DASH.showLocationPanel('the-central-room');", self._SCENES_PROBE)
        assert g["changes"] == ["nowStops being a boundary and becomes an exit."], g["changes"]

    def test_a_scene_link_opens_that_scene_from_a_panel_without_tabs(self, vault, tmp_path):
        """`data-ent` is the panel-wide protocol, not a tab's.

        The location panel registers no tabs, so the delegated click handler was
        never installed for it — the links rendered and did nothing.
        """
        _make(vault, "stc")
        _import(vault, "stc")
        url = _dash(vault, "stc")["dashboard_url"].split("?")[0]
        html = Path(url.replace("file://", "")).read_text()
        g = self._probe(
            html, tmp_path, "scenes_loc_click",
            "DASH.showLocationPanel('the-central-room');"
            "document.querySelector('#panel-body .jr-scene').click();",
            "document.title = JSON.stringify({"
            "  type: document.getElementById('panel-type').textContent,"
            "  name: document.getElementById('panel-name').textContent });")
        assert g["type"] == "Scene", g
        assert g["name"] == "Central Room - Day", g


class TestTheShellIsOpaque:
    """Every full-canvas surface must paint an opaque background.

    The dashboard runs in a frame that paints its own background behind the
    document. A surface left transparent — or set to `var(--card)`, which is
    `rgba(255,255,255,0.04)` — lets that light background through, and the
    panels read as white cards while the detail panel beside them stays dark.
    This failed once, visibly, after a refactor that added a new surface.

    Checked as text, not pixels: the failure mode is exactly a rule whose
    declaration is present but transparent, and a screenshot would be needed to
    catch a colour. The guard is the declaration itself.
    """

    # The surfaces that cover the whole viewport. Anything here that is
    # transparent shows the frame's background instead of the dashboard's.
    SURFACES = {
        "html, body": "base.css",
        "#sidebar": "base.css",
        "#main": "base.css",
        ".view": "base.css",
        "#loading-screen": "components.css",
        ".graph-tabs": "graph.css",
        "#script-view .view-body": "views.css",
    }

    @pytest.fixture
    def css_by_file(self):
        css_dir = Path(__file__).parent.parent / "src" / "dashboard" / "css"
        return {f: (css_dir / f).read_text() for f in set(self.SURFACES.values())}

    def _rule(self, css: str, selector: str) -> str:
        """The full declaration block for `selector`, or '' when absent."""
        m = re.search(rf"(?m)^{re.escape(selector)}\s*\{{(.*?)\}}", css, re.S)
        return m.group(1) if m else ""

    @pytest.mark.parametrize("selector", sorted(SURFACES))
    def test_a_surface_paints_an_opaque_background(self, css_by_file, selector):
        css = css_by_file[self.SURFACES[selector]]
        block = self._rule(css, selector)
        assert block, f"{selector} has no rule in {self.SURFACES[selector]}"
        bg = re.search(r"background(?:-color)?\s*:\s*([^;]+);", block)
        assert bg, f"{selector} declares no background — it shows the frame"
        value = bg.group(1).strip()
        assert "transparent" not in value, f"{selector} is transparent: {value}"
        # var(--card) is the translucent-white trap, not a colour.
        assert "--card" not in value, (
            f"{selector} uses --card ({value}), which is translucent white"
        )

    def test_no_surface_uses_the_translucent_card_token_as_a_surface(self, css_by_file):
        """One sweep: `--card` may tint a row, never carry a viewport surface."""
        offenders = []
        for filename, css in css_by_file.items():
            for selector in self.SURFACES:
                block = self._rule(css, selector)
                if re.search(r"background(?:-color)?\s*:\s*var\(--card\)", block):
                    offenders.append(f"{filename}: {selector}")
        assert not offenders, f"translucent surfaces: {offenders}"


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
