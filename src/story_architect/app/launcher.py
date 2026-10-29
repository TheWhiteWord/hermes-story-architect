"""Launcher CLI for the standalone app."""
from __future__ import annotations

import argparse
import socket
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from story_architect.app.config import load_config
from story_architect.app.server import create_app


def is_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "hermes":
        from story_architect.adapters.hermes.setup import setup, status
        sub = argv[1:2]
        rest = argv[2:]
        if sub and sub[0] == "status":
            return status(rest)
        return setup(rest)
    if argv and argv[0] == "seed-demo":
        # seed demo project from fixture
        parser = argparse.ArgumentParser(prog="story-architect seed-demo")
        parser.add_argument("--root", default=None)
        a = parser.parse_args(argv[1:])
        config = load_config(cli_root=a.root)
        src = Path(__file__).resolve().parents[1] / "data" / "browser-verification-test"
        # fallback search
        if not src.exists():
            for cand in Path(".").rglob("browser-verification-test"):
                if (cand / ".story" / "story.db").exists():
                    src = cand
                    break
        dest = config.root / "projects" / "demo"
        if dest.exists():
            print(f"Demo already exists at {dest}")
            return 0
        import shutil
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        print(f"Seeded demo at {dest}")
        return 0

    parser = argparse.ArgumentParser(prog="story-architect")
    parser.add_argument("--root", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--create-root", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(cli_root=args.root, cli_port=args.port, cli_no_open=args.no_open)

    if not config.root.exists():
        if args.create_root or input(f"Root {config.root} does not exist. Create? [y/N] ").strip().lower() == "y":
            config.root.mkdir(parents=True, exist_ok=True)
            (config.root / "projects").mkdir(exist_ok=True)
        else:
            print(f"Root does not exist: {config.root}")
            return 1

    if is_healthy(config.port):
        url = f"http://127.0.0.1:{config.port}"
        print(f"Already running at {url}")
        if config.open_browser:
            webbrowser.open(url)
        return 0

    s = socket.socket()
    try:
        s.settimeout(0.5)
        s.connect(("127.0.0.1", config.port))
        print(f"Port {config.port} is in use by another process. Try --port.")
        return 1
    except Exception:
        pass
    finally:
        s.close()

    app = create_app(config)
    url = f"http://127.0.0.1:{config.port}"
    print(f"Serving at {url}")
    if config.open_browser:
        def opener():
            for _ in range(50):
                if is_healthy(config.port):
                    webbrowser.open(url)
                    return
                time.sleep(0.1)
        threading.Thread(target=opener, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=config.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
