import pathlib
import re


def test_no_hermes_imports():
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "story_architect"
    for p in root.rglob("*.py"):
        text = p.read_text()
        assert "hermes" not in text.lower(), f"hermes reference in {p}"
