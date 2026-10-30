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
    # ensure the profile has a session store (state.db). A profile created with
    # --clone lacks state.db; without it the gateway parks the profile and every
    # ticket minted for it is refused ("Invalid gateway ticket response").
    state_db = pd / "state.db"
    if not state_db.exists():
        import sqlite3
        W_home = W.hermes_home()
        candidates = [W_home / "state.db"] + [p / "state.db" for p in (W_home / "profiles").glob("*") if p.is_dir()]
        src = next((c for c in candidates if c.exists() and c != state_db), None)
        if src is not None:
            con = sqlite3.connect(str(src))
            schema = [r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') AND sql IS NOT NULL").fetchall()]
            con.close()
            out_db = sqlite3.connect(str(state_db))
            for sql in schema:
                try:
                    out_db.execute(sql)
                except Exception:
                    pass
            out_db.commit()
            out_db.close()
            try:
                state_db.chmod(0o600)
            except OSError:
                pass
            out.append("state.db initialized")
    # persona (SOUL.md) unless default profile
    soul_path = pd / "SOUL.md"
    is_default = pname == "default"
    if not is_default:
        src = ASSETS / "SOUL.md"
        content = src.read_text() if src.exists() else ""
        if soul_path.exists():
            existing = soul_path.read_text()
            foreign = MARKER not in existing
            default_soul = _profile("default") / "SOUL.md"
            identical_to_default = (default_soul.exists() and existing == default_soul.read_text())
        else:
            existing = ""
            foreign = False
            identical_to_default = False
        if foreign and not identical_to_default and not force:
            out.append("SOUL.md exists (foreign) - skipped; use --force")
        else:
            if dry:
                out.append("[dry-run] would write SOUL.md")
            else:
                if soul_path.exists() and (force or identical_to_default):
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
    # API key for Hermes API server
    api_key = T.ensure_api_key() if hasattr(T, "ensure_api_key") else None
    # ensure function added below; fallback
    if api_key is None:
        import secrets
        akp = T.config_dir() / "api_key"
        if akp.exists():
            api_key = akp.read_text().strip()
        else:
            api_key = secrets.token_urlsafe(32)
            akp.write_text(api_key)
            try:
                akp.chmod(0o600)
            except OSError:
                pass
    if dry:
        out.append("[dry-run] would write API key to .env")
    else:
        lines = env_path.read_text().splitlines() if env_path.exists() else []
        lines = [l for l in lines if not l.startswith("API_SERVER_KEY=")]
        lines.append(f"API_SERVER_KEY={api_key}")
        env_path.write_text("\n".join(lines) + "\n")
        out.append("API key written (not printed)")
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
    # remove legacy standalone/api_server shim (served via host multiplexer now)
    if isinstance(cfg.get("gateway"), dict):
        cfg["gateway"].pop("standalone", None)
        if not cfg["gateway"]:
            cfg.pop("gateway", None)
    if isinstance(cfg.get("platforms"), dict):
        cfg["platforms"].pop("api_server", None)
        if not cfg["platforms"]:
            cfg.pop("platforms", None)
    cfg["mcp_servers"]["story"] = {
        "url": f"http://127.0.0.1:{port}/mcp",
        "headers": {"Authorization": "Bearer ${STORY_ARCHITECT_TOKEN}"},
    }
    # API key for Hermes API server (served via host multiplexer at /p/<profile>/)
    api_key = T.ensure_api_key() if hasattr(T, "ensure_api_key") else None
    cfg.setdefault("agent", {})
    import sys as _sys
    _sys.path.insert(0, "/home/davide/.hermes/hermes-agent")
    try:
        import toolsets as _ts
        cfg["agent"]["disabled_toolsets"] = sorted(_ts.BUILTIN_TOOLSET_NAMES)
    except Exception:
        cfg["agent"]["disabled_toolsets"] = []
    cfg["toolsets"] = []
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
    mcp_cfg = (cfg.get("mcp_servers") or {}).get("story") or {}
    check("MCP entry", "story" in (cfg.get("mcp_servers") or {}))
    port = C.load_config().port
    expected_url = f"http://127.0.0.1:{port}/mcp"
    check("MCP URL", mcp_cfg.get("url") == expected_url, f"expected {expected_url}")
    check("token present", T.load_token() is not None)
    # app reachable
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
            app_ok = r.status == 200
    except Exception:
        app_ok = False
    check("app reachable", app_ok, "start story-architect")
    # MCP endpoint authenticates and lists expected tools
    mcp_ok = False
    tok = T.load_token()
    if app_ok and tok:
        try:
            import asyncio
            from mcp.client.streamable_http import streamable_http_client
            from mcp import ClientSession
            async def _list():
                try:
                    import httpx
                except ImportError:
                    import httpx2 as httpx
                http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {tok}"}, timeout=5.0)
                async with streamable_http_client(f"http://127.0.0.1:{port}/mcp", http_client=http_client) as (r, w):
                    async with ClientSession(r, w) as session:
                        await session.initialize()
                        res = await session.list_tools()
                        return [t.name for t in res.tools]
            names = asyncio.run(_list())
            from story_architect.app.mcp_server import build_registry
            expected = {n for n, _, _ in build_registry()}
            mcp_ok = set(names) == expected
        except Exception:
            mcp_ok = False
    check("MCP endpoint", mcp_ok, "token or tool list mismatch")
    # API server reachable + auth + model id
    api_ok = False
    model_ok = False
    gateway_ok = True
    ak = T.load_api_key()
    ap = C.load_config().hermes_api_port
    if ak:
        try:
            try:
                import httpx
            except ImportError:
                import httpx2 as httpx
            r = httpx.get(f"http://127.0.0.1:{ap}/v1/models", headers={"Authorization": f"Bearer {ak}"}, timeout=2.0)
            api_ok = r.status_code == 200
            if api_ok:
                data = r.json()
                models = [m.get("id") for m in data.get("data", [])]
                model_ok = pname in models
        except Exception:
            api_ok = False
    check("API server reachable", api_ok, "start gateway / run setup")
    check("API model id matches profile", model_ok, f"expected {pname}")
    check("builtins disabled", "terminal" in (cfg.get("agent", {}).get("disabled_toolsets") or []), "run setup")
    print("ALL OK" if ok else "FAILURES PRESENT")
    return 0 if ok else 1
