# Craft files — the shape

*Template and rules. This file is a guide for writing the craft files; it is
not read by the agent.*

## The process, per entity

Theory first, then the entity. The app was built on this theory, so the two
mostly agree — and where they don't, that is the finding.

**Source:** `docs/research/McKee_Story/Good_Writing.md`. One document, fifty
sections, not divided by subject. Each entity's theory is mined out of it.

1. **Mine the theory.** Read every section that touches the entity — not the
   obvious one. Include the relations *between* elements (a scene is only
   defined against the sequence around it; an act against its reversal), and
   the nuances. Write `theory/<entity>.md` as the theory stands on its own:
   no field names, no tools, no mention of the store.
2. **Cross-check against the entity.** With the theory complete, read the
   entity's fields and sections. Every decision the store asks for should be
   traceable to something in the theory.
3. **Note the gaps, both ways.**
   - a field with no theory behind it — the app encodes something the theory
     does not say. Report it.
   - a theory concept with no field — the app cannot hold something the
     theory considers essential. Report it.
   Neither is fixed silently. The gap is the finding.
4. **Write `craft/<entity>.md`** in the structure below, using the theory as
   the reason for each decision.

## Where the app narrows the theory

**The theory is the same. The app fixes what a word means, and where it could
not encode a concept, it synthesized one that still holds to the theory.** The
theory files stay as the theory stands. The craft file states the app's
meaning where a word has narrowed, so the agent does not read the theory's
general sense and apply it to a field.

The narrowed words, and what they are here:

| theory says | the app means |
|---|---|
| **beat** — an exchange of behavior, the building block of a scene's turn | two different things, and they must not be confused. A scene's `Beats` section holds the theory's sense: the exchanges of behavior inside the scene. An `arc_beat` is one moment in a single character's arc, and nothing else. |
| **the value** — one thing, at stake in the story | two tracks. The story value is the main thematic investigation. A character's value is a subtheme inside it: often the same, sometimes different, never unrelated. |
| **turn, reversal** — the moment the value changes | **`shift` is its result**, stated in the story's own words. A turn produces a shift; the shift is what gets recorded. |
| | **`y` is that same shift in numbers** — derived from the shift, not decided beside it, and read only for drawing the curve. The shift is the fact; `y` is its measurement. |
| **crisis, climax** — moments in the story | not one field. What they are depends on the entity: a scene's dramatic function, a container's pointer, the scene it points at. Decide per entity, and say which. |
| **milestone** | not a field at all. The agent never holds or writes it and does not reason in it. Leave it out entirely. |

When the app synthesizes one field out of several theory concepts, the craft
file says which concepts it covers. The agent has to know that a single field
is standing in for more than the theory's one word, or it will look for the
others and treat their absence as a gap.

## What the skill is for

The agent already has the tools, the entities, and story competence. Neither
`story_describe` nor `story_retrieve` can tell it:

1. **Who owns a decision.** The agent is capable of deciding everything, and
   will invent a plausible value the user never decided. The user cannot check
   it — they never made it.
2. **The couplings.** Facts the store holds in two places, and requirements
   that must exist before an entity can. An agent reading the schema sees
   independent fields.

A craft file covers one entity and carries exactly those two things, plus what
it takes to create the entity.

**The boundary of judgement** is a standing rule for the whole application and
lives in `SKILL.md`, once. A craft file only says which decisions of *this*
entity are the user's and which the agent's.

## Structure

    # <Entity>

    One line: what it is.

    ## Requisites
    - what must exist before this one can be created
    - the creation order

    ## Deciding it
    - the decisions, in order — the author's marked, the agent's marked
    - field names where a field needs a specific instruction
    - theory links where the reasoning matters

    ## The couplings
    - one fact stored in two places: set both, every time

    ## Consistency
    - what to read before changing this, and what it can contradict

- **Requisites** — mechanical. The write refuses without it. Present in every
  file; "none" on its own line if there are none.
- **Deciding it** — the substance. Order matters, because the write may refuse
  out of order.
- **Couplings** — the store holds one fact twice. Nothing refuses it, nothing
  warns; only knowing it prevents the half. Omit the section if there are none.
- **Consistency** — a fourth kind, and the one that needs a decision. Neither
  record is wrong, the write is accepted, and the story does not hold
  together. A coupling is fixed by writing one extra thing; this is not — it
  needs the user to say which of the two is actually true, and the agent has
  to notice first. So it is a *look before you write*, not a rule.

  One section per file rather than one file of pairs, so each entity's picture
  builds up as its file is written. State the pair from this entity's side:
  what to read, and what a change here can contradict. The other side of the
  pair gets the same relation in its own file, pointing back.

  **Every line here costs context on every read, and it buys a check the
  agent would otherwise not make — so the bar is high.** A check earns a line
  only if you can name the thing that makes it false. A check that exists
  because the section would otherwise look short is the failure this section
  is most prone to. Specifically:

  - not "is this character behaving like their `story_role`" — a role is the
    user's claim, not something to audit
  - not a chain of inference through fields whose relation you have not
    traced. A beat belongs to a character's arc; it does not thereby
    establish membership of a plot
  - not a fact about a field that belongs in the file where that field is
    decided, under *Deciding it*

  If nothing is true of an entity, the section is two lines saying so. An
  empty section is cheaper than a wrong one.

## Marking who decides

- **The boundary of judgement is stated once, in `SKILL.md`.** It applies to
  every entity, so it is not restated in every file. A craft file does not
  repeat "this is the user's" line after line — that is noise, and it trains
  the agent to skim.
- A craft file says which decisions are **specific to this entity** and who
  owns those. If a general rule would already cover it, the line does not need
  the ownership on it.
- The agent's decisions are derived from the project, never invented.
- Offering options the user picks from is not supplying a value.

## Field names

- in `craft/`: name them freely, wherever there is a specific instruction
- in `theory/`: never. Theory has no knowledge of the store.

Informational theory links may stay general and leave the agent to connect
them. Name the fields when the fact is duplicated or conditional, and there is
no reasoning left to do.

## Not in these files

- field and section lists, enums, type tables — `story_describe` has them
- tool syntax and parameters — `SKILL.md` and the tool schemas
- what the tool fails to check — a warning the agent cannot act on
- history, self-assessment, open questions
- prose. A line earns its place only if it changes what the agent does.
