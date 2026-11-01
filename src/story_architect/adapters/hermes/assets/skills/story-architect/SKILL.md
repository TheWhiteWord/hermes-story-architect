---
name: story-architect
description: How to use Story Architect tools well.
metadata:
  hermes:
    tags: [story, screenplay, writing]
---

# Story Architect skill

You are collaborating on a story project through the Story Architect tools.
Work only through the tools; never invent data outside them.

## Tool names (as you see them)
admin, backup, dashboard_link, describe, draft, export, import, load, memory, retrieve, search.

## Workflow
1. Orient: `load` the project to get its structural map before answering.
2. Retrieve before answering: use `retrieve`/`search` for details; do not guess.
3. Stage changes with the draft protocol (`draft`), then `commit` only after
   the owner approves. Never commit unreviewed changes. The app shows each
   staged draft as an approval card; you are told when it is approved or
   rejected. You may still commit directly when explicitly asked.
4. When to search vs load: `load` for structure/overview; `search` for a
   specific term or scene; `retrieve` for full entity detail.
5. Point the owner at the app with `dashboard_link` (returns a URL; do not
   open a browser yourself).

## Conventions
- Propose before committing; ask when intent is unclear.
- Respect the owner's creative authority.
- Tool results with `success: false` are normal results — read them and
  report, do not retry blindly.