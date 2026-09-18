# SPECIALIST RESPONSE

Alright — read both files. Here's my honest take, not a survey.

## Bottom line: build it on SQLite. The current design isn't "fine at this scale," it's structurally broken, and the scale has nothing to do with it.

Your own doc says it: 5 of 7 identified problems trace back to the storage format. That's not a coincidence you should hedge around — it's a diagnosis. You've hand-built a miniature, buggy, in-memory relational database (`index.yaml` + the `_enrich_*` functions) on top of a document format that can't support relations natively. `_enrich_scenes_with_plots` is a JOIN. `_enrich_structure` is a JOIN. `_validate_index` is a foreign-key constraint. You're reimplementing SQLite's core job, by hand, in Python, without transactions, without indexes, and with a cache-invalidation story that you already admit doesn't work ("the LLM is often smart enough to note the index may be stale... but not always" — that sentence should be a five-alarm fire in any data architecture review).

So this isn't "markdown vs. SQLite, pick your trade-offs." It's "you're already building a database, just badly — use the one already sitting in the stdlib."

## Why the objections don't hold here

**"We'll lose human-readability / git diffs."** Those benefits mattered when this was an Obsidian vault meant to be hand-edited in a text editor. It isn't anymore. You said it yourself: the user doesn't need to edit in Obsidian, the dashboard provides visual access, and the format was "kept by convention, not necessity." Once that's true, git-diffability of YAML frontmatter is a benefit nobody is using, paid for by a staleness bug somebody hits every session.

**"SQLite is disruptive / heavy."** It's stdlib (`sqlite3`), zero new dependencies, and for 200 rows of data the entire migration is a one-time script using the `frontmatter` parser you already have, writing into tables. That's an afternoon, not a rewrite. You can actually *drop* `pyyaml` and most of your `regex` usage afterward — net dependency count goes down.

**"Small-data territory, linear scans are fine."** Correct, and irrelevant. The problem was never disk I/O speed. The problem is that you have no query layer, so every "need" gets served by either (a) dumping the entire graph into the LLM's context or (b) grepping every file. SQLite fixes this even at 10 rows, because the fix is structural (JOINs, indexes, FTS), not about scan speed.

## What I'd actually build

One SQLite file per project (or one DB, projects as a column — doesn't matter much at your scale). Rough shape:

```sql
CREATE TABLE entities (
  id TEXT PRIMARY KEY,
  type TEXT,           -- character, location, scene, plot, ...
  name TEXT,
  one_sentence TEXT,
  order_key INTEGER,
  status TEXT,
  parent_id TEXT,       -- scene->sequence, sequence->act
  location_id TEXT,
  extra JSON            -- schema-specific fields you don't want columns for
);

CREATE TABLE relations (        -- characters<->scenes, plots<->scenes, etc.
  from_id TEXT, to_id TEXT, kind TEXT,
  PRIMARY KEY (from_id, to_id, kind)
);

CREATE TABLE sections (         -- replaces ## heading parsing
  entity_id TEXT, heading TEXT, body TEXT,
  PRIMARY KEY (entity_id, heading)
);

CREATE VIRTUAL TABLE sections_fts USING fts5(body, content='sections', content_rowid='rowid');
```

That `extra JSON` column matters — SQLite's `json_extract`/`json_each` mean you don't have to fully normalize plot setups/payoffs or arc-beat fields into their own tables unless you want to; you get schema flexibility without giving up queryability.

This single schema replaces: `index.yaml`, the enrichment pipeline, the section-parser regex, and the staleness-refresh hooks. Not "simplifies" — *replaces*, because there's no longer a second representation of the data to go stale. `story_retrieve("dr-elena-voss", "Voice")` is `SELECT body FROM sections WHERE entity_id=? AND heading=?`. `character.scenes[]` is a JOIN at read time, always current, no enrichment step needed. There is no `story_index` tool anymore, because there's nothing to re-index — the query results *are* current by construction.

## Your core tension — I think it's a false dilemma

You're asking "is there a better balance between full-index awareness and context cost." No — full-index-load is dominated on both axes simultaneously by query-driven access. It's not a trade-off, it's a strictly worse option:

- **Cost**: 30-70K tokens for data the agent uses fragments of, every single session, whether or not the task touches most of it.
- **Freshness**: even when you pay that cost, it goes stale mid-session the moment `story_edit` fires — you told me this yourself in section 5.1 of the architecture doc.

Replace it with:

1. **Session start** — a genuinely tiny summary: project meta + flat `(id, type, name, one_sentence)` for every entity. This is a few KB, not 50K tokens, because you're not pulling scenes[], arc_beats[], plots[] arrays into it.
2. **On-demand queries** — tool functions like `get_scenes_for_character(id)`, `get_scenes_in_sequence(id)`, `search(text, entity_type=None, section=None)` — each a parameterized SQL query, each a few hundred tokens back, each always correct because there's no cache to go stale.

This is your "layered + query-driven" options from section 5.2, combined — and it's not a compromise, it's just correct once relationships live in a real relational store instead of a denormalized YAML blob.

## Search (5.3)

FTS5, not embeddings. You get ranked results (BM25), snippet extraction, and — the thing your current search structurally can't do — filtering by section name or entity type, because `sections` is a real table with real columns, not a flat grep target. No new dependency chain, no ONNX runtime. This directly kills "irrelevant hits drown relevant ones."

## The dashboard question

This isn't premature optimization — it's the same decision as the storage question, just viewed from the other side. Right now dashboard-as-editor requires a translation layer (dashboard writes → note writer → frontmatter/section serialization → index refresh). With SQLite, dashboard and agent read/write the *same rows*. You don't need to build the editor now, but choosing SQLite is what keeps that door open for free instead of behind another abstraction layer later. Choosing to stay on markdown is what *closes* it.

## What I'd push back on in your own framing

Don't build the "standalone index DB, keep markdown notes" hybrid from your table. It's the worst option on the list — you'd keep the staleness problem (now between three representations instead of two: notes, index.yaml, AND a SQLite index) while adding a database. If you're taking on SQLite's complexity, take the win that comes with it — single source of truth — don't half-step into "SQLite as yet another cache."

Also: don't over-normalize on day one. Keep `extra JSON` for the odd fields (arc beat `y`/`shift`, plot setups/payoffs) rather than designing five more join tables for a 200-row personal project. You can normalize incrementally if a query pattern actually demands it.

## Honest costs

- Migration: one-time script, bounded, maybe a day including testing.
- You lose casual `cat scene.md` inspection — mitigate with a `story_export` command that dumps the DB back to markdown for git snapshots/backup, on demand, not as the live format.
- You lose "someone unfamiliar with the codebase can open a note in a text editor and understand it" — for a solo personal tool with a dashboard, I don't think this cost is real.

That's my actual opinion, not a hedge: markdown+frontmatter was the right choice for an Obsidian plugin and is the wrong choice for a Hermes Desktop plugin with a dashboard. The dashboard already made the decision for you; the storage format just hasn't caught up yet.


--------------

## FOLLOW UP QUESTIONS

+Thanks for the clear response. A few follow-ups where we need clarification before we can commit to the schema:
+
+**1. The `extra JSON` column and FTS5**
+You said keep arc beat `y`/`shift`, plot setups/payoffs in `extra JSON`. But FTS5 indexes the `sections` table — can it also index JSON content in the `entities.extra` column? Or do we need a separate FTS table for that? If not, how do we search inside JSON fields?
+
+**2. Migration path for existing tools**
+`story_edit`, `story_create`, and `story_dashboard` all currently read/write markdown files. With SQLite:
+- Does `story_edit` now write to the DB instead of frontmatter + sections?
+- Does `story_create` insert rows instead of writing `.md` files?
+- Does `story_dashboard` query the DB instead of reading `index.yaml` + note sections?
+- Or do we keep a thin markdown-compatibility layer for the dashboard?
+
+**3. The `story_export` command**
+You mentioned dumping the DB back to markdown for git snapshots. Is this:
+- A new tool the agent calls on demand?
+- A separate CLI script?
+- Automatic (e.g., on every write)?
+And does it produce the same markdown+frontmatter+`##` sections format we have now?
+
+**4. Multi-project support**
+You said "one SQLite file per project (or one DB, projects as a column — doesn't matter much)." Which do you recommend, and why? If one DB per project, how does the agent switch between projects — a new `story_switch_project` tool? If one DB with a project column, does every query need a `WHERE project_id = ?` clause?
+
+**5. The `relations` table vs. `extra JSON` with relational semantics**
+Plot setups/payoffs reference scenes (`scene_id`). Arc beats reference scenes. Are these:
+- In the `relations` table (with `kind = 'plot_setup'`, `kind = 'arc_scene'`, etc.)?
+- In `extra JSON` (as arrays of `{scene_id, description}`)?
+- A mix?
+This affects whether we can JOIN on them or have to parse JSON at query time.
+
+**6. Concurrent access**
+Single user, single agent — but what if the user edits in the dashboard while the agent is mid-query? SQLite handles concurrent reads fine, but what about writes? Do we need `WAL` mode, or is the risk low enough to ignore?
+
+**7. The `story_load` replacement**
+You said "session start — a genuinely tiny summary: project meta + flat `(id, type, name, one_sentence)` for every entity." Is this a new tool? Or does `story_load` now return this instead of the full index? And how does the agent know which entities to query for details — does it ask, or does it get a hint from the summary?
+
+**8. Backup and recovery**
+The SQLite file is just a file in the project directory. If it gets corrupted, is the `story_export` output the recovery path? Or do we rely on git history of the markdown files (which would mean keeping the export in sync with every write)?

--------------

Good questions — these are exactly the decisions that determine whether this becomes a clean system or a new mess. Going through them in order.

## 1. FTS5 and the `extra` JSON column

FTS5 only indexes what you explicitly insert into it — it has no visibility into a JSON blob sitting in another table's column. `json_extract()` lets you filter/index on specific JSON *fields* (exact or range matches), but that's not full-text search, and querying inside JSON at scale is exactly the kind of thing that should make you reconsider what's going into JSON in the first place.

So the real fix is: **don't put searchable prose in `extra`.** Split by what you actually need to do with the field:

- **Scalar/display data nobody searches or joins on** (arc beat `y`, `shift`, `is_crisis`, `is_climax`, `arc_type`) → stays in `extra JSON`. Fine as-is.
- **Descriptive text tied to a relationship** (plot setup/payoff descriptions, arc beat "action"/"gap"/"choice" prose) → this is exactly the kind of thing you'll want to search ("where does the door setup happen") and it's inherently relational (setup belongs to a plot, points at a scene). It shouldn't be JSON at all — see #5 below, it belongs in `relations.note`, which you *do* index with FTS5.

Rule of thumb: if you can imagine typing it into a search box, it doesn't go in JSON.

## 2. Migration path for existing tools

Yes to all three, and no compatibility layer for the dashboard — that layer is the thing you're trying to eliminate.

- **`story_edit`** — becomes `UPDATE`/`INSERT`/`DELETE` against `entities`/`sections`/`relations`. No file write, no index refresh, because there's no second representation to refresh. This is where most of your current code complexity disappears — no frontmatter serialization, no section-splice-and-rewrite.
- **`story_create`** — becomes `INSERT` rows across the same tables. Simpler than today's template-based file generation.
- **`story_dashboard`** — queries the DB directly for `__STORY_DATA__`/`__SECTIONS__`/etc. This is actually a small win for the dashboard too: right now it's parsing prose plus reading precomputed index YAML; with SQL it can pull exactly the shape it wants with a JOIN instead of consuming a document format designed for the agent.

The only place markdown parsing survives at all is the one-time migration script and the export tool (#3) — nothing in the live read/write path touches `.md` files anymore.

## 3. `story_export`

**On-demand, not automatic.** Automatic-on-every-write puts you right back where you started — two representations that can drift, just with extra steps. Make it a tool the agent (or you) triggers explicitly: "back this up," "I want to commit to git," end of a session, whatever cadence you like. It should be idempotent — running it twice in a row produces the same files, no diff.

Format: yes, same markdown+frontmatter+`##` sections as today. Two reasons: it keeps your git history readable as a continuous story rather than a hard cutover, and it doubles as a disaster-recovery path *and* an escape hatch if you ever want to abandon the DB and go back to files — you can always regenerate the full vault from the DB.

Pair it with a `story_import` in the same script (reverse direction) — you need that for the initial migration anyway, and it's cheap insurance to keep both directions working.

## 4. Multi-project: one file per project

One SQLite file per project, not one DB with a `project_id` column. Reasons:

- It maps directly onto your existing `<vault>/projects/<slug>/` layout — `story.db` just replaces `.story/index.yaml` inside the same folder. Nothing about project resolution changes conceptually.
- No `WHERE project_id = ?` on every single query, ever. Simpler code, and a bug or corruption in one project's file can't touch another's.
- You explicitly said cross-project queries are rare/out of scope. A shared DB only pays for itself if you need to query *across* projects — you don't.
- **No new tool needed.** `story_resolve` already finds the project folder from a slug/name; it just needs to point at `<folder>/.story/story.db` instead of `<folder>/.story/index.yaml`. "Switching projects" was already a solved problem — you're not adding a concept, you're changing what file gets opened.

## 5. `relations` vs JSON — go relational

Setups/payoffs and arc-beat/scene links go in `relations`, not JSON, specifically so they're joinable and searchable:

```
relations(from_id, to_id, kind, note, "order")
-- ('the-resistance', 'central-room-day', 'plot_setup',  'Kael discovers the door isn't locked', 1)
-- ('the-resistance', 'the-core-day',     'plot_payoff', '...', 1)
-- ('dr-elena-voss',  'central-room-day', 'arc_beat',    'The Choice', 1)
```

This gives you both directions for free: "scenes for this plot" is `WHERE from_id = plot_id`, "plots touching this scene" is `WHERE to_id = scene_id AND kind LIKE 'plot_%'` — no reverse-lookup enrichment step, because JOINs are inherently bidirectional. It also means `relations.note` can sit in an FTS5 table alongside `sections`, so "find the scene where the door setup happens" actually works as a search.

`extra JSON` on the `entities` row is left for genuinely entity-scoped scalars that nothing else ever needs to join or search against — coordinates, flags, enum-ish fields.

## 6. Concurrent access — WAL mode, and that's it

Turn on `PRAGMA journal_mode=WAL;` once at DB creation and set `PRAGMA busy_timeout=3000;` (or similar) so a brief lock contention waits instead of erroring. That's the entire concurrency story you need here. WAL lets readers (dashboard) and a writer (agent tool call) coexist without blocking each other; your actual write transactions are single-row, sub-millisecond operations, so real contention risk is negligible even in the worst case of "user clicks save in the dashboard at the same instant the agent calls `story_edit`."

Don't build anything beyond this — no app-level locking, no daemon, no queueing. That would be solving a concurrency problem you don't have (single user, single agent, no server) with infrastructure that belongs to a different kind of system. One practical habit: open a short-lived connection per tool call (open → execute → commit → close) rather than holding one connection open for the process lifetime, so nothing goes stale in an in-process cache.

## 7. `story_load` — same tool, new payload

Keep the name and the tool schema — no reason to churn the agent-facing API. What changes is what it returns: instead of the full index, it runs the summary query (`id, type, name, one_sentence` for every entity, plus project metadata and counts). Same entry point, radically smaller payload.

On "how does the agent know what to query for detail" — it doesn't need a hint mechanism beyond the summary itself plus normal tool use. The summary already tells it what exists (names, types, one-liners); when the task needs depth, the agent calls `get_scenes_for_character`, `story_retrieve`, or `search` the way it already calls tools for everything else. This *is* what layered loading means — the agent asks follow-up questions instead of being handed the whole graph pre-emptively. If you want a cheap discoverability boost, add one structural hint to the summary (e.g., act→sequence→scene ordering, since that's navigation scaffolding rather than per-entity enrichment) — but resist the urge to make that hint grow back into the full index.

## 8. Backup and recovery — the `.db` file is the source of truth, back up the file

Don't lean on `story_export` for recovery — that reintroduces the sync problem you're trying to kill if you start treating "keep the export current" as a requirement. Instead:

- Back up the SQLite file directly. It's just a file — a timestamped copy (`shutil.copy`, or `VACUUM INTO` for a guaranteed-consistent snapshot) before risky multi-step operations, or on a coarse schedule, is trivial and needs zero new dependencies. This is your actual disaster-recovery path.
- SQLite itself is quite robust against corruption in a single-writer local setup (atomic commits, WAL) — real corruption is rare here; the backup is cheap insurance, not a response to a known fragility.
- `story_export` stays what it was in #3: a human-readable, git-trackable *secondary* artifact — good for reading diffs of prose over time, good as a last-resort format-independent escape hatch, but triggered on-demand, not something you architect your recovery story around.

Anything in here you want me to turn into the actual migration script and tool function signatures, or is the schema settled enough to build against now?s Desktop plugin with a dashboard. The dashboard already made the decision for you; the storage format just hasn't caught up yet.


