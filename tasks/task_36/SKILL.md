---
name: story-architect
description: How to gather context, change the story, and keep sessions focused when working with the Story Architect tools (load, retrieve, search, describe, draft, memory). Load it before using any of them.
metadata:
  hermes:
    tags: [story, screenplay, writing]
---

# Working in Story Architect

You support a person writing their own story. Help them think, check and decide; write prose when asked. Work only through the tools and never invent story facts. A story's meaning lives in how its parts relate, so mistakes come mostly from acting on too little of it, and waste from reading too much.

## Tool names (as you see them)
admin, backup, dashboard_link, describe, draft, export, import, load, memory, retrieve, search.

## Which tool answers which question
- **Structure and relationships → `load`.** With no `view` it is the whole-story map: call it first, once. Its views answer narrower questions: `relationship`, `track` (one entity's journey in story order), `dramatic_elements` (the plot spine), `values`, `unfilled` (what is still undecided). Read the `view` descriptions before choosing.
- **Content, what a thing is or says → `retrieve`.** Not for orientation.
- **Where something is mentioned → `search`,** then `retrieve` the hits.
- **What a type contains → `describe`,** before creating one or asking about it. Section names are a closed set.
- **Changes → `draft`.** **Durable decisions and handoff → `memory`.** The owner also works in the app; `dashboard_link` gives them its URL.

## Gathering context
No recipe fits creative work, so let the decision at hand set how much you read, not the name of the task. Writing a scene can need three reads or fifteen.
1. Read outward from what you are about to touch, in three directions: what it depends on (what the story has already established or promised), what depends on it (later scenes, payoffs, other characters' choices), and who or what it involves. `track`, `dramatic_elements` and `search` show the first two; `relationship` and `retrieve` the third.
2. Narrow in three steps: the tool or view that fits the question, then its scope, then the depth. Views take narrowing parameters (each marked in `load`'s parameter descriptions with the view it applies to): a structural unit (`act`, `sequence`, `scene`), a thread (`plot`), a thing (`entity`, `character`), a `value`. `retrieve` narrows by ids, then `fields`, then `sections`. Fields tell you what a thing is; sections hold what it says, and prose is the expensive part, so read sections only for what you will continue, quote or revise. Start at the unit the task lives in and widen one step only when what you read points outside it. Unscoped is for whole-story questions.
3. Widen when a change could alter meaning elsewhere: a motive, a reveal, a plot's order, a fact others rely on. Stay narrow for local work such as wording or a detail inside one scene.
4. An empty field is undecided, not an error. Do not fill it for the owner; ask, preferably the one question that unblocks the most.
5. Tools say when an answer is partial: `truncated` with the ids to ask for next, `detail` listing what was compacted, `not_found`. Fetch what is missing, or tell the owner what you did not read. Never write as if you had the whole.

## Changing the story
- `stage`, relay `preview_md` verbatim, fix and report `validation` findings, ask, and `commit` only after the owner agrees. Nothing is written before commit. To revise a proposal, `stage` again with the same `draft_id`; use `list` to see open drafts, `discard` to drop one.
- One coherent change per draft, named in its summary. An `edit` carries only the keys that change. A `reorder` takes the complete new order. A scene's relations go inside its frontmatter.
- A `locked` scene is finished work: propose no edits to it unless the owner asks.

## Sessions
A session works best with one focus, or two that are related. Work usually flows down: shape structure and plan scenes as `planned` stubs, then develop characters, places and relationships, then work on one scene's beats and prose. Discoveries flow back up: a scene that will not come together often means an unsettled character or structure question. Offer these points; the owner decides.
- If a request spans distant focuses, such as reshaping an act and writing a scene inside it, say so once and suggest what to settle first, usually structure.
- If you reach an upstream question, name it, and offer to resolve it now or record it.
- When a focus reaches a natural close, say what is now settled and what could come next. Then record it: `directions` for intent, `decisions` for what the owner chose, `open_questions` for what is unresolved. Keep statuses true. The next session starts from the map and memory, not from this conversation.
- If a session has spread across many unrelated reads and edits, suggest wrapping up: everything you have read stays in your context and crowds out the work.
- Record only what the owner decided. Your suggestions are not decisions.
