"""Hermes setup command implementation."""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from story_architect.adapters.hermes import wrapper as W
from story_architect.app import config as C
from story_architect.app import token as T


MARKER = "<!-- story-architect adapter -->"
ASSETS = Path(__file__).resolve().parent / "assets"


def _profile(name):
    return W.profile_dir(name)


def setup(argv=None, dry_run=False, force=False, profile_name="story-architect"):
    parser = argparse.ArgumentParser(prog="story-architect hermes setup")
    parser.add_argument("--profile", default=profile_name)
    parser.add_argument("--dry-run", action="store_true", default=dry_run)
    parser.add_argument("--force", action="store_true", default=force)
    args = parser.parse_args(argv or [])
    dry = args.dry_run
    force = args.force
    pname = args.profile
    out = []
    # 1. hermes present
    exe = W.find_hermes()
    if exe is None:
        print("ERROR: hermes executable not found on PATH")
        return 1
    ver = W.version()
    out.append(f"hermes: {ver}")
    # 2. create profile if missing
    pd = _profile(pname)
    if not pd.exists():
        if dry:
            out.append(f"[dry-run] would create profile {pname}")
        else:
            rc, o, e = W.run_hermes("profile", "create", pname, "--clone")
            if rc != 0:
                out.append(f"ERROR creating profile: {e.strip()}")
                print("\n".join(out))
                return 1
            out.append(f"created profile {pname}")
    else:
        out.append(f"profile {pname} exists (skipped)")
    # persona (SOUL.md) unless default profile
    soul_path = pd / "SOUL.md"
    is_default = pname == "default"
    if not is_default:
        src = ASSETS / "SOUL.md"
        content = src.read_text() if src.exists() else ""
        if soul_path.exists() and MARKER not in soul_path.read_text() and not force:
            out.append("SOUL.md exists (foreign) - skipped; use --force")
        else:
            if dry:
                out.append("[dry-run] would write SOUL.md")
            else:
                if force and soul_path.exists():
                    shutil.copy2(soul_path, soul_path.with_suffix(".md.bak"))
                soul_path.parent.mkdir(parents=True, exist_ok=True)
                soul_path.write_text(MARKER + "\n" + content)
                out.append("SOUL.md written")
    else:
        out.append("default profile: skipping persona")
    # skill
    skill_dir = pd / "skills" / "story-architect"
    src_skill = ASSETS / "skills" / "story-architect"
    if dry:
        out.append("[dry-run] would install skill")
    else:
        skill_dir.mkdir(parents=True, exist_ok=True)
        if src_skill.exists():
            for f in src_skill.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src_skill)
                    dst = skill_dir / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_text(f.read_text())
        out.append("skill installed")
    # token
    tok = T.ensure_token()
    env_path = pd / ".env"
    if dry:
        out.append("[dry-run] would write token to .env")
    else:
        lines = env_path.read_text().splitlines() if env_path.exists() else []
        lines = [l for l in lines if not l.startswith("STORY_ARCHITECT_TOKEN=")]
        lines.append(f"STORY_ARCHITECT_TOKEN={tok}")
        env_path.write_text("\n".join(lines) + "\n")
        out.append("token written (not printed)")
    # MCP registration via YAML safe edit
    import yaml
    cfg_path = pd / "config.yaml"
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            cfg = {}
    port = C.load_config().port
    cfg.setdefault("mcp_servers", {})
    cfg["mcp_servers"]["story"] = {
        "url": f"http://127.0.0.1:{port}/mcp",
        "headers": {"Authorization": "Bearer ${STORY_ARCHITECT_TOKEN}"},
    }
    if dry:
        out.append("[dry-run] would register MCP server")
    else:
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        out.append("MCP server registered")
    print("\n".join(out))
    return 0


def status(argv=None, profile_name="story-architect"):
    parser = argparse.ArgumentParser(prog="story-architect hermes status")
    parser.add_argument("--profile", default=profile_name)
    args = parser.parse_args(argv or [])
    pname = args.profile
    ok = True
    def check(label, cond, hint=""):
        nonlocal ok
        mark = "OK" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"{mark:4} {label}" + (f"  ({hint})" if hint and not cond else ""))
    exe = W.find_hermes()
    check("hermes found", exe is not None)
    ver = W.version() if exe else None
    check("hermes version", ver is not None, "install hermes")
    pd = _profile(pname)
    check("profile exists", pd.exists())
    check("SOUL.md present", (pd / "SOUL.md").exists() if pd.exists() else False)
    check("skill present", (pd / "skills" / "story-architect" / "SKILL.md").exists() if pd.exists() else False)
    cfg = {}
    cp = pd / "config.yaml" if pd.exists() else None
    if cp and cp.exists():
        import yaml
        try:
            cfg = yaml.safe_load(cp.read_text()) or {}
        except Exception:
            cfg = {}
    check("MCP entry", "story" in (cfg.get("mcp_servers") or {}))
    check("token present", T.load_token() is not None)
    # app reachable
    import urllib.request
    port = C.load_config().port
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
            app_ok = r.status == 200
    except Exception:
        app_ok = False
    check("app reachable", app_ok, "start story-architect")
    print("ALL OK" if ok else "FAILURES PRESENT")
    return 0 if ok else 1
