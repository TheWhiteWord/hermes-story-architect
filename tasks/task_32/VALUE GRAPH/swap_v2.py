"""Swap the specialist's v2 value-graph files into a copy of an assembled
dashboard, so the zoom can be exercised live without touching src/.

Reads the CSS/JS out of the assembled HTML (they are inlined verbatim), so the
copy differs from the real dashboard ONLY in the two value-graph files.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
DEV = pathlib.Path("/media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect")


def main():
    assembled = pathlib.Path(sys.argv[1])
    dest = pathlib.Path(sys.argv[2])
    html = assembled.read_text()

    old_css = (DEV / "src/dashboard/css/value-graph.css").read_text()
    old_js = (DEV / "src/dashboard/js/graph/value-graph.js").read_text()
    new_css = (HERE / "value-graph_edit2.css").read_text()
    new_js = (HERE / "value-graph_edit2.js").read_text()

    for label, needle in (("css", old_css), ("js", old_js)):
        if html.count(needle) != 1:
            raise SystemExit(f"{label}: expected 1 verbatim copy, found {html.count(needle)}")

    html = html.replace(old_css, new_css).replace(old_js, new_js)
    dest.write_text(html)
    print(f"{dest}: swapped value-graph.css and value-graph.js")


if __name__ == "__main__":
    main()
