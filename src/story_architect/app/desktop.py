"""Install and remove the desktop launcher entry (XDG).

The app is a local server, so the launcher starts the server and opens the
browser. Written by the app itself: no flatpak sandbox, no browser install step.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "story-architect"
NAME = "Story Architect"
COMMENT = "Story-writing environment: entities, plots, scripts and values."

_ICON_SIZES = ((192, "icon-192.png"), (512, "icon-512.png"))


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or "~/.local/share").expanduser()


def _apps_dir() -> Path:
    return _data_home() / "applications"


def _icon_dir(size: int) -> Path:
    return _data_home() / "icons" / "hicolor" / f"{size}x{size}" / "apps"


def _exec_line() -> str:
    exe = shutil.which(APP_ID)
    return exe or f"{sys.executable} -m story_architect.app.launcher"


def _desktop_file() -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.0",
        f"Name={NAME}",
        f"Comment={COMMENT}",
        f"Exec={_exec_line()}",
        f"Icon={APP_ID}",
        "Terminal=false",
        "Categories=Office;",
        "",
    ])


def _refresh() -> None:
    try:
        subprocess.run(["update-desktop-database", str(_apps_dir())],
                       capture_output=True, check=False)
    except FileNotFoundError:
        pass                                    # not every system ships it


def install() -> int:
    written = []
    apps = _apps_dir()
    apps.mkdir(parents=True, exist_ok=True)
    entry = apps / f"{APP_ID}.desktop"
    entry.write_text(_desktop_file())
    written.append(entry)

    icons = Path(__file__).resolve().parents[1] / "web" / "icons"
    for size, name in _ICON_SIZES:
        src = icons / name
        if not src.exists():
            print(f"Missing icon: {src}")
            return 1
        dst_dir = _icon_dir(size)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{APP_ID}.png"
        shutil.copyfile(src, dst)
        written.append(dst)

    _refresh()
    for p in written:
        print(f"Wrote {p}")
    return 0


def uninstall() -> int:
    removed = []
    entry = _apps_dir() / f"{APP_ID}.desktop"
    if entry.exists():
        entry.unlink()
        removed.append(entry)
    for size, _name in _ICON_SIZES:
        icon = _icon_dir(size) / f"{APP_ID}.png"
        if icon.exists():
            icon.unlink()
            removed.append(icon)

    _refresh()
    for p in removed:
        print(f"Removed {p}")
    if not removed:
        print("Nothing was installed.")
    return 0
