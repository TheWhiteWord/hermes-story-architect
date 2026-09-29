# Reading the project

*Schematic draft — headings and notes only.*

Which call answers which question about a project, and what each one costs. The
parameters are in the tool schema; the routing is not.

*Sizes below are from the `save-the-children` fixture — indicative, not
promises. A real project with a full cast will be larger.*

---

## Start with the base view

*One call, no parameters beyond the project, and it opens the session.*

- The base view returns the **structure** (acts, characters, plots, worlds, and
  any orphaned locations), the **project row**, and the **whole story memory**
  with its usage count. Verified together in one response.
- **So the first call of a session is `story_load` with the project and nothing
  else.** It is both "what exists" and "what has been decided", and the memory
  comes back every time rather than needing a separate fetch.
- It is also the cheapest way to answer "where were we" — the memory is in it.
- → `story-memory.md` for what to do with what comes back.
- *The views below are all opt-in on top of this.* None of them is needed to
  begin.

## The five views

*Each answers one question. Asking a view the wrong question costs a second
call, so the routing is worth holding.*

| View | Answers | Needs |
|---|---|---|
| `story_value` | where the story's value moves, act → sequence → scene | — |
| `arc` | one character's arc, beat by beat | `character` |
| `dramatic_elements` | each scene's role and its milestones | — |
| `relationship` | every bond and both sides of each | — |
| `unfilled` | what is still missing | — or `field`, or `entity` |

- **`story_value`** states the value word **once, at the top**, and the charges
  down the hierarchy. There is no word per container, because there is no field
  for one — its absence is not a gap. → `value-system.md`
- **`arc`** is the only view that needs a parameter, and it needs a character id.
  Without one it returns every character's arc, which is a much larger answer to
  a question nobody asked. **Pass the character.**
- **`dramatic_elements`** is the structural read: what each scene is *for*. This
  is where the milestone flags surface, and it nests act → sequence → scene.
  Add `act` to narrow it, and `add_plot` only when the plot cross-references are
  the point — they roughly double the response.
- **`relationship`** is small and whole: every bond with both perspectives. It
  is the fastest way to see the cast's web. → `relationships.md`
- **`unfilled`** is the "what next?" view, and the only one that reports
  something about the project rather than about a part of it.

## `unfilled` has three shapes, and they are not the same call

*The most useful view in the set, and the one most likely to be called wrongly.*

- **Unfiltered**, it answers *"what is incomplete in this project?"* — grouped
  by field, with a count. On the fixture: 94 gaps across 23 fields.
- **It is truncated, and it says so.** The response carries a `truncated` flag
  and an `other_fields` key for what it did not show. So the unfiltered view
  tells you it is a partial list — **read the flag before treating the absence
  of a field as its absence from the project.**
- **By `field`** it answers *"who else is missing this?"* — a lookup across the
  whole project. One field, a short list. Both value prefixes are worth knowing,
  so `character_value_at_close` finds the character track and `value_at_close`
  the story's.
- **By `entity`** it answers *"what did I skip on this one?"* — the same lookup
  the other way round.
- **These two are the cheap ones** — a few hundred characters against two and a
  half thousand — and they are the ones to reach for by default. The unfiltered
  view is for a genuine sweep.

## Reading a response

- A view returns **ids**, and ids are what every other call takes. So the loop
  is: load to see what exists, view to narrow it, retrieve to read it.
- → `story_retrieve` for the content itself, which takes the ids from here.
- **Nothing in this file is about a single entity.** Reading one character's
  sections is `story_retrieve`, and the difference is the whole point: a view
  answers a question about the project's *shape*, a retrieve answers a question
  about one thing's *contents*.

---

## Open questions

- [ ] The base view returns `orphaned_locations` alongside the structure. It is
      not in the tool's description and nothing else in the skill covers it.
      Worth a line here, or does it belong with the structural files?
- [ ] The unfiltered `unfilled` view is the only one that can truncate. Say to
      prefer the filtered forms by default, or is the truncation flag enough on
      its own?
