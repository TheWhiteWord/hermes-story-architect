# Hermes Agent built-in memory research

**Scope:** Hermes Agent's built-in persistent memory only (`MEMORY.md`, `USER.md`, and the `memory` tool). External providers, broader memory architectures, and Story Architect comparison are intentionally excluded from this first pass.

**Sources:**

- Official documentation: [Persistent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- Official documentation: [Which File Does What?](https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what)
- Official source: [`tools/memory_tool.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/memory_tool.py)
- Official source: [`tools/memory_tool_store.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/memory_tool_store.py)
- Official source: [`agent/prompt_builder.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/agent/prompt_builder.py)

The source was inspected as the current upstream implementation; the documentation and source may change independently.

## 1. What Hermes means by memory

Hermes memory is **bounded, curated, prompt-resident memory**, not a complete history of conversations and not an authoritative continuity database.

Its purpose is to carry a small set of high-signal facts across session boundaries so they are immediately available in the next session's system prompt. Detailed historical recall is delegated to `session_search`, which searches stored sessions on demand.

The built-in system has two independent stores:

| Store | Purpose | Default limit |
|---|---|---:|
| `MEMORY.md` | Agent notes: environment, project conventions, tool quirks, lessons learned | 2,200 characters |
| `USER.md` | User profile: identity, role, preferences, communication style, expectations | 1,375 characters |

Both are stored under the active Hermes profile's memories directory. Memory is profile-scoped; it is not automatically shared between profiles.

A useful shorthand from the official file map is:

- `SOUL.md`: who the agent is; user-authored identity/personality.
- `USER.md`: who the user is; agent-maintained profile facts.
- `MEMORY.md`: what the agent has learned; agent-maintained notes.
- `AGENTS.md` / `.hermes.md`: project instructions; user/project-authored context.

Hermes therefore deliberately separates durable identity, user profile, agent notes, and project rules. A fact placed in the wrong file does not automatically feed the others.

## 2. The stored representation

The two files are plain text. Their entries are separated by the full delimiter:

```text
\n§\n
```

Conceptually:

```markdown
First compact memory entry.

§

Second compact memory entry.
```

The entries are not structured records. They are opaque strings whose meaning is determined by their text. There are no built-in fields for:

- importance or confidence;
- source or provenance;
- creation time or last-use time;
- project/entity scope;
- validity period;
- contradiction or supersession relationships;
- usage frequency;
- lifecycle state;
- structured links to other memories.

The store deduplicates exact duplicate entries while loading. It preserves order and keeps the first occurrence.

The file is rewritten from the parsed entry list on mutation. The implementation uses a separate lock file, reloads the file under the lock, and writes atomically through a temporary file plus rename. Mutation paths also guard against unreadable files and external formatting drift to avoid silently destroying memory.

## 3. The memory tool contract

The agent uses one `memory` tool with two possible targets:

```text
target = "memory"  -> MEMORY.md
target = "user"    -> USER.md
```

The basic operations are:

### `add`

Adds one complete entry.

- Empty content is rejected.
- Content is trimmed.
- Exact duplicates are accepted as a successful no-op.
- Threat-pattern scanning runs before acceptance.
- An add that would exceed the target's character limit is rejected.

### `replace`

Replaces one complete entry.

- `old_text` is a short unique substring used only to locate the entry.
- `content` is the complete replacement entry, not a span patch.
- Whole-entry exact matches take priority over substring matches.
- Ambiguous substring matches are rejected.
- The replacement must fit within the limit.

### `remove`

Removes one entry located by a unique `old_text` substring.

### Batch operations

The tool also accepts an `operations` list:

```text
operations: [
  { action: "remove", old_text: "..." },
  { action: "replace", old_text: "...", content: "..." },
  { action: "add", content: "..." }
]
```

Batch operations are all-or-nothing. They are validated against the final character count, so a single call can free space and add a new fact atomically. This is the preferred shape for consolidation.

## 4. Capacity management

The character limits are hard product constraints, not soft warnings. They keep memory small because the content is injected into the system prompt of every new session.

Default limits:

```text
MEMORY.md: 2,200 characters
USER.md:    1,375 characters
```

The system prompt displays current usage and percentage. When an add or replace would exceed the limit, the tool returns an error containing current usage and, for ordinary consolidation attempts, the current entries so the agent can decide what to remove or shorten.

The intended maintenance model is explicit consolidation:

1. Inspect the current entries.
2. Remove stale or low-value entries.
3. Merge related facts into shorter entries.
4. Add the new fact.
5. Prefer one atomic batch operation when several changes are needed.

There is no automatic eviction policy. Hermes does not silently choose which memory to drop. The agent must perform the curation decision.

The implementation also limits repeated failed consolidation attempts within one turn. This prevents a model from looping indefinitely on a stubborn memory operation and failing to answer the user.

## 5. Prompt injection into the next session

At session start, the store loads the entries and renders a block for each enabled target. The format is approximately:

```text
══════════════════════════════════════════════
MEMORY (your personal notes) [67% — 1,474/2,200 chars]
══════════════════════════════════════════════
Entry one
§
Entry two
```

The important mechanism is the **frozen snapshot**:

- The memory file is read when the session starts.
- The rendered memory block becomes part of the system prompt at that point.
- A write during the session changes the file immediately.
- The current system prompt does not change mid-session.
- The updated block is available in the next session.

This is deliberate: it preserves the provider's prompt-prefix cache. It also creates an important semantic distinction:

> Persistence is immediate; visibility in the already-running prompt is deferred to the next session.

The live in-session context still contains what was just said in the conversation, but a newly written memory entry is not retroactively injected into that same prompt.

## 6. What belongs in memory

Hermes' guidance is narrow. The built-in store is for durable facts that matter across sessions.

Examples from the official guidance:

- environment facts;
- project conventions;
- tool quirks and workarounds;
- durable lessons learned;
- stable user preferences;
- explicit user requests to remember something.

Examples that should not be stored:

- trivial or vague observations;
- facts easy to rediscover from the repository or web;
- raw code, logs, or data tables;
- temporary paths and session-specific ephemera;
- completed-work logs and temporary task state;
- information already supplied by project context files;
- reusable procedures, which belong in skills rather than the always-injected memory prompt.

The current source makes the routing principle even clearer: memory is the narrow exception for facts that apply to every session regardless of task. Procedures, pitfalls, and task-specific lessons belong in skills, where they are loaded only when relevant.

Entries should be compact and information-dense. Hermes recommends declarative facts rather than imperative instructions, because memory is injected as context and imperative phrasing can be interpreted as a standing directive.

Good:

```text
Project ~/code/api uses Go 1.22, sqlc for DB queries, chi router. Run tests with 'make test'. CI uses GitHub Actions.
```

Bad:

```text
On January 5th the user asked me to inspect the project and I discovered that it uses Go version 1.22 and several other things that should be remembered for future work.
```

The first is compact and actionable. The second is a transcript summary, not memory.

## 7. Trust and safety model

Because memory becomes system-prompt context across future sessions, writes are treated as a trust boundary.

The implementation scans incoming entries for strict threat patterns, including prompt injection, credential exfiltration, SSH-backdoor patterns, and invisible Unicode characters. Threat-matching content is rejected.

On load, detected dangerous entries are replaced with a blocked placeholder in the system-prompt snapshot, while the original live entry is retained so it can be inspected and explicitly removed. This prevents silently hiding a poisoned entry while preventing it from entering future prompts.

The system also protects against data loss:

- writes are serialized with a lock;
- existing files are re-read under the lock;
- unreadable files are not treated as empty;
- atomic replacement prevents partial-file writes;
- external drift is detected before destructive operations;
- staged destructive operations pin the full entry that was reviewed.

These are implementation safeguards, not higher-level semantic guarantees. A fact can be structurally safe and still be false.

## 8. Approval and review controls

Memory writes can be configured to require approval:

```yaml
memory:
  write_approval: true
```

With approval enabled:

- interactive foreground writes prompt for review;
- gateway, messaging-platform, script, and background-review writes are staged;
- staged writes can be listed, approved, or rejected.

For replace/remove operations, approval can record the complete entry selected at staging time. If the entry changes before approval, the staged operation is rejected rather than applied to a different entry that happens to contain the same substring.

Background review is allowed to add entries but destructive consolidation operations are staged rather than applied unattended. This is a deliberate distinction: adding a new compact fact is less destructive than deleting or rewriting existing memory.

## 9. Session boundaries and historical recall

Hermes positions memory around the end of a session:

- current conversation context serves the active task;
- memory carries only the curated essentials into a new session;
- `session_search` retrieves specific older conversations when needed.

This avoids putting unlimited history into every prompt. The trade-off is that memory is not a transcript and does not preserve every detail.

The built-in memory is therefore best understood as:

```text
always-loaded index of high-signal facts
```

not:

```text
complete record of what happened
```

A saved memory entry is also not necessarily a fact the agent verified. It is a compact note selected by the agent from prior interaction. The system's main protections are boundedness, curation, security scanning, and optional approval—not truth validation.

## 10. The learning loop

The official current source describes a background self-improvement review after a turn. It can save durable memory entries and patch or create skills. The review may run on the main model or a configured auxiliary model.

The loop conceptually behaves like this:

```text
conversation
    ↓
background review
    ↓
durable memory or reusable skill
    ↓
new session reads the curated result
```

The review is not required to make the core built-in memory mechanism work. It is an additional mechanism for extracting durable knowledge from completed work.

The design boundary is important:

- memory stores facts needed broadly;
- skills store procedures needed for a class of tasks;
- session search stores actual historical conversations;
- context files store project instructions supplied by the user/project.

## 11. Configuration surface

The relevant built-in settings are:

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  write_approval: false
```

If both built-in stores are disabled, the built-in `memory` tool and its guidance are removed from the runtime. If only one is enabled, the tool schema advertises only the enabled target.

The memory tool is not an always-available storage API. Availability depends on the runtime configuration and the target store.

## 12. Short evaluation of the Hermes direction

The Hermes design is a strong example of a **minimal memory layer with explicit scope and bounded attention cost**.

### What works well

1. **Clear purpose** — memory carries high-signal cross-session facts, not everything.
2. **Low implementation complexity** — two plain files plus a small mutation tool.
3. **Attention control** — hard character limits prevent unbounded prompt growth.
4. **Explicit curation** — the agent must remove or merge stale content; nothing is silently evicted.
5. **Stable prompt behavior** — the frozen snapshot protects prefix caching and makes session semantics predictable.
6. **Human control** — optional approval, staging, and review are available for risky or automated writes.
7. **Security awareness** — memory receives a strict scan because it enters the system prompt.
8. **Separation of concerns** — user profile, agent notes, skills, project context, and session history have distinct homes.

### Important limitations

1. **No semantic structure** — entries are opaque strings, so the system cannot reliably reason about scope, confidence, contradiction, or supersession.
2. **No automatic importance model** — importance and relevance are delegated to the writing model.
3. **No temporal or version semantics** — an updated fact can overwrite an old one, but the store does not preserve a structured history.
4. **No entity-level state model** — it cannot represent a character's or location's changing state.
5. **No retrieval inside memory** — everything in the store is injected; the design assumes the entire curated set is small enough to always load.
6. **Factuality is not guaranteed** — a concise note can still be wrong, and the system has no truth oracle.
7. **Agent-dependent curation** — weak tool-calling or poor review behavior can produce missed saves, incorrect saves, or bad consolidation.
8. **Frozen visibility can surprise users** — a successful write is not visible in the current prompt, only in the next session.

### Central design principle

Hermes solves the problem by choosing a very narrow definition of memory:

> If a fact is not important enough to occupy the permanently injected prompt budget, it does not belong in built-in memory.

That is a coherent and conservative answer. It avoids pretending that a small note store can provide full narrative continuity. It also makes the trade-off visible: **less context, less attention spent, but only a curated subset of history is automatically available**.

## 13. Implications to carry into a later design discussion

This first pass does not decide what Story Architect should implement. It provides the Hermes baseline for that later comparison.

The questions to evaluate next are:

- Should the app's memory be a single always-loaded store, or should it be divided by type or scope?
- What is the minimum durable information worth paying prompt/context cost for?
- Does the app need a single `memory.md`, or a small set of purpose-specific stores?
- Should entries be free text, typed records, or a hybrid?
- Is a simple manual/explicit write model sufficient, or is promotion/demotion needed?
- What should be excluded by design to prevent a continuity engine from contaminating the main generation context?
- Should memory be a project-level sidecar, like Story Architect's current `.story/memory.md`, or an always-injected plugin context block?
- What are the acceptance and removal rules for a memory entry?
- How should memory changes be reviewed and audited?

## Source index

| Source | Contribution |
|---|---|
| [Official Persistent Memory documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) | User-facing purpose, limits, tool actions, curation, session boundaries, approval, security, configuration |
| [Official Which File Does What?](https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what) | Separation of `SOUL.md`, `USER.md`, `MEMORY.md`, and project context |
| [`tools/memory_tool.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/memory_tool.py) | Tool schema, mutation API, batch semantics, approval/staging, background-review gates |
| [`tools/memory_tool_store.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/memory_tool_store.py) | File format, entry parsing, character budgets, atomic persistence, locking, drift protection, threat scanning, snapshot rendering |
| [`agent/prompt_builder.py`](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/agent/prompt_builder.py) | Frozen prompt snapshot and memory guidance placement |

## Research status

- Hermes built-in memory mechanism: **researched**.
- External memory providers: **intentionally excluded**.
- Other memory architectures: **intentionally excluded**.
- Story Architect comparison: **deferred to the next phase**.
