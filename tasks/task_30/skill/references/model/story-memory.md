# Story memory

*Schematic draft — headings and notes only.*

What goes in story memory, and when. The parameters, the categories and the
limits are all in the tool schema and in what `story_load` returns — this file
is about the judgement, which is the part no tool has an opinion about.

---

## Why it exists

- Memory is how a fact outlives the conversation. The failure mode is **silence**:
  the agent and the user settle something in chat, nothing is written, and the
  next session starts blank with no sign it was ever decided.
- It is not a transcript and not a log. It is the short list of things that would
  be expensive to rediscover.
- **Memory is advisory.** Where it disagrees with the entities, the entities are
  what happened — report the conflict, do not silently rewrite either side.
  Nothing derives canon from memory.

## The four categories

*A decision about which one, not a list to memorise.*

| Category | For | Test |
|---|---|---|
| `decisions` | a choice that has been made and closed | would you be surprised if it changed? |
| `directions` | intent for the story that is not yet a decision | is the user steering rather than settling? |
| `open_questions` | something genuinely unresolved | is it still open? |
| `continuity_warnings` | a fact that must not be contradicted | would breaking it be a mistake? |

- The two that get confused: a **direction** is not yet a decision, and an
  **open question** is not a direction. If the user has chosen, it is a decision;
  if they are still weighing, it is one of the other two.
- `continuity_warnings` is the durable half of continuity. There is no tool that
  audits a story for contradictions, so this is where a fact that must hold gets
  recorded once and comes back on every later load. **Write the warning when the
  user states the fact**, not at the end as a sweep.

## One entry is one thing

- An entry is a **reminder to a future session**, not prose. If it needs a
  paragraph, it is two or three entries, or it belongs in a section.
- Write it as the fact, not as a discussion of the fact: "Kael dies in act
  three", not "we discussed whether Kael should die in act three and decided…".
- A resolved `open_question` does not become a `decision` by rewriting. Remove
  it and add the decision — one entry, one category, no history.

## The budget is small and shared

*Verified: 3000 characters across all four categories together, 300 per entry.*

- **The budget is counted in characters, not entries**, so "how many entries fit"
  is the wrong question. Measured: forty-two entries of ~63 characters filled it;
  126 short ones, or 304 very short ones, filled the same space. **3000
  characters is roughly 500 words** — about a page.
- That is the real constraint, and it is why this file is about choosing rather
  than recording. There is no room to be thorough.
- **The budget is shared, not per category.** Verified: with `decisions` full, an
  add to `directions` fails with the same error. There is no room to be generous
  in one and careful in another.
- So the test for an entry is: **would I regret not having this next month?**
  Anything that fails it does not go in, however true it is today.
- Reaching the limit is not a failure to retry. The error comes back with the
  current entries and the usage count — **read it, then consolidate**: merge
  entries that say one thing, and remove what the entities now record anyway.
- *A decision that has become a fact about an entity does not need to be in
  memory twice.* If the logline records it, the memory entry is redundant.

## Writing and changing entries

- **`remove` and `replace` need the exact existing text.** A paraphrase returns
  "Entry not found in category" and the current entries, so **read before you
  write** — one `story_load` gets the text you need.
- **Adding a duplicate is a silent no-op**, not an error: it succeeds and changes
  nothing. Re-adding is therefore harmless, which makes "just add it again" a
  safe way to be sure.
- A `replace` that would create a duplicate is refused. Merge or remove the old
  one first.
- **One call, one entry.** There is no batch action, so recording four decisions
  is four calls. Worth knowing before promising the user "I'll note that down" in
  a list.

## Which project

- The project name is matched **fuzzily** when it is not exact, and a close
  enough match writes **silently**. Verified: "children" resolves to
  `save-the-children` at the threshold with no warning.
- A match below the threshold comes back with a warning — but only on a
  **successful** write, so the entry has already landed. Check the resolved name
  if the response carries one.
- With one project this never bites. With two similarly named ones, **use the
  exact slug** rather than the display name.

## Reading it back

- `story_load` returns the whole memory in its base view, with a usage count and
  a per-category count. That is the cheapest way to see what is recorded, and it
  comes back on every load — so **read it at the start of a session**, not only
  when the user asks.
- A full memory is a signal, not an error. It means the project has accumulated
  more standing guidance than fits, and some of it is probably now in the data.
- *Not in this file:* the action names, the category names and the limits — the
  tool schema and the base view both carry them.
