# final_tools — one file per finalized tool

A file exists here **only when the tool is done**: verified by running it, defects fixed,
regression-tested. The filename is the tool name. This folder is the source of truth for
writing skills against — what the tool does, what it returns, what it refuses to do.

**Not finalized yet?** No file. The working review lives in `../tools/`.

## Progress

**7 of 11 finalized.**

| Tool | File |
|---|---|
| `story_search` | [story_search.md](story_search.md) |
| `story_describe` | [story_describe.md](story_describe.md) |
| `story_import` | [story_import.md](story_import.md) |
| `story_retrieve` | [story_retrieve.md](story_retrieve.md) |
| `story_create` | [story_create.md](story_create.md) |
| `story_edit` | [story_edit.md](story_edit.md) |
| `story_load` | [story_load.md](story_load.md) — base view + 5 extended views |

## Still to do

| Tool | Status |
|---|---|
| `story_memory` | Verified — no defects in the tool. See the resolver fix below. |
| `story_backup` | Works, no defects. Needs verification + wiring into import/delete. |
| `story_dashboard` | Verified — 2 silent-failure defects fixed. |
| `story_backup` | Copy fixed (WAL + collisions). Backs up catastrophic loss only. |
| `story_backup` | Last — needs discussion (wiring into import/delete). |

## Done before skills can be written

- ~~`plugin.yaml` omits `story_memory`~~ — **fixed**
- ~~7 of 11 tools have no `description`~~ — **fixed**, every tool now says what it is for
  *and when not to use it*. `story_import`'s leads with `DESTRUCTIVE`.

## story_import is not a recovery step

It deletes every row and rebuilds from Markdown — and Markdown is the *stale* projection. It is now
guarded (`dry_run`, `confirm`, automatic backup) but it is still the wrong tool for "the database
looks wrong". Prefer `story_edit`, `story_create`, or `story_backup`.

## The shared rule

`.story/story.db` is the source of truth. Markdown is read and written **only** by `story_import`
and `story_export`. No other tool may fall back to it.

---

## Reference: captured shapes of tools not yet finalized

Kept here so nothing observed is lost. **Not a finalized contract** — see `../tools/` for the
per-tool review. Move these into a per-tool file when that tool is finalized.

`story_load` — 4,542 chars on the fixture
```
{loaded, confirmation,
 project: {name, logline, status, genre, setting, spine, controlling_idea,
           value, value_at_open, value_at_close, structure_type, act_count},
 acts: [ {id, title, status, sequences: [ {id, title, status, scenes: [...]} ]} ],
 characters: [...], plots: [...],
 worlds: [ {id, name, one_sentence, locations: [...], period} ],
 memory: {status, usage, counts, categories},
 orphaned_locations: [...]   // only when some exist
}
```

`story_retrieve` — `sections=["all"]` → 1,968 chars
```
{entity_type, slug, sections: [heading, ...], content: "## H\n...\n\n## H2\n...", unfilled_fields: [...]}
```
`sections=["Goals"]` returns `{sections: {"Goals": "## Goals\n..."}}` instead. A missing section
returns the available list as the *value* of the requested name.
