"""Where the response budget comes from, and the Hermes percentage helper.

The budget has to sit under the host's per-result cap, and that cap scales with
the model's context window, which the plugin cannot see. So it is a setting
(env var, then config.toml, then a default), and the Hermes adapter can work the
number out from a model's context size.
"""

import importlib
import sys

import pytest

from story_architect.core import budget
from story_architect.adapters.hermes import budget as hb

ENV = "STORY_ARCHITECT_MAX_RESPONSE_CHARS"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv(ENV, raising=False)
    (tmp_path / "story-architect").mkdir()
    return tmp_path / "story-architect"


def write_toml(home, body):
    (home / "config.toml").write_text(body)


class TestResolution:
    def test_default_when_nothing_is_set(self):
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    def test_config_file_is_used(self, home):
        write_toml(home, "[story_architect]\nmax_response_chars = 17000\n")
        assert budget.max_response_chars() == 17000

    def test_env_beats_config_file(self, home, monkeypatch):
        write_toml(home, "[story_architect]\nmax_response_chars = 17000\n")
        monkeypatch.setenv(ENV, "25000")
        assert budget.max_response_chars() == 25000

    def test_a_bad_env_value_falls_through_to_the_file(self, home, monkeypatch):
        write_toml(home, "[story_architect]\nmax_response_chars = 17000\n")
        monkeypatch.setenv(ENV, "banana")
        assert budget.max_response_chars() == 17000

    @pytest.mark.parametrize("bad", ["max_response_chars = 10",
                                     "max_response_chars = true",
                                     "max_response_chars = 15000.5",
                                     'max_response_chars = "lots"',
                                     "max_response_chars = -3"])
    def test_a_bad_file_value_means_not_set(self, home, bad):
        write_toml(home, f"[story_architect]\n{bad}\n")
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    def test_a_malformed_file_means_not_set(self, home):
        write_toml(home, "this is [not toml")
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    def test_other_tables_and_keys_are_ignored(self, home):
        write_toml(home, "[other]\nmax_response_chars = 9000\n[story_architect]\nport = 1\n")
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS


class TestCoreDoesNotReadHostConfig:
    """The budget was once derived by parsing the host's config.yaml. That value
    is only one of the host's inputs (the model window is the other, and the
    one that matters), so it gave a wrong number — and a bare `except` hid a
    missing import so it silently did nothing. The core must not do this."""

    def test_a_host_config_yaml_has_no_effect(self, tmp_path, monkeypatch):
        host = tmp_path / "host"
        host.mkdir()
        (host / "config.yaml").write_text(
            "tool_budget:\n  mcp_result_size_chars: 100000\n")
        monkeypatch.setenv("HERMES_HOME", str(host))
        assert budget.max_response_chars() == budget.DEFAULT_MAX_RESPONSE_CHARS

    def test_core_budget_names_no_host(self):
        src = importlib.util.find_spec("story_architect.core.budget").origin
        assert "hermes" not in open(src).read().lower()


class TestHermesPercentage:
    # What Hermes enforces, computed from tools/budget_config.py:
    #   min(mcp cap (50000), clamp(0.15 * window_tokens * 4, 8000, 100000))
    @pytest.mark.parametrize("ctx, threshold, suggested", [
        (8_000,     8_000,  7_000),    # floor: a tiny model still gets 8k
        (32_000,   19_200, 17_000),
        (65_000,   39_000, 35_000),
        (128_000,  50_000, 45_000),
        (200_000,  50_000, 45_000),
        (1_000_000, 50_000, 45_000),
    ])
    def test_known_windows(self, ctx, threshold, suggested):
        assert hb.hermes_spill_threshold(ctx) == threshold
        assert hb.suggest_budget(ctx) == suggested

    def test_a_smaller_configured_cap_wins(self):
        assert hb.hermes_spill_threshold(200_000, mcp_cap=30_000) == 30_000
        assert hb.suggest_budget(200_000, mcp_cap=30_000) == 27_000

    def test_a_larger_configured_cap_cannot_beat_the_window(self):
        """The very mistake of reading the config key alone: raising it to
        100000 does not lift a 65k-token model past its 15% window share."""
        assert hb.hermes_spill_threshold(65_000, mcp_cap=100_000) == 39_000

    def test_the_suggestion_is_always_under_the_threshold_and_sane(self):
        for ctx in range(4_000, 400_000, 3_000):
            for cap in (None, 20_000, 50_000, 100_000):
                t = hb.hermes_spill_threshold(ctx, cap)
                s = hb.suggest_budget(ctx, cap)
                assert s < t
                assert s >= budget._MIN_SANE or t < 2_500

    def test_cli_prints_the_toml_line(self, capsys):
        assert hb.main(["65000"]) == 0
        out = capsys.readouterr().out
        assert "39,000" in out and "[story_architect]" in out
        assert "max_response_chars = 35000" in out

    def test_the_cli_output_round_trips_through_the_resolver(self, capsys, home):
        hb.main(["32000"])
        toml = capsys.readouterr().out.split("\n\n", 1)[1]
        write_toml(home, toml)
        assert budget.max_response_chars() == hb.suggest_budget(32_000)

    def test_cli_rejects_a_non_positive_window(self):
        with pytest.raises(SystemExit):
            hb.main(["0"])
