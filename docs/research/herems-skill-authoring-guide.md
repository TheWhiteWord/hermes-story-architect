# Skill Authoring Guide for Hermes Agent

*A practical standard for writing SKILL.md files and the resources that support them — general principles plus Hermes-specific mechanics.*

This guide has two parts. **Part 1** is a platform-agnostic authoring standard based on Anthropic's Agent Skills format — now published as the open [Agent Skills standard](https://agentskills.io) — covering how to structure knowledge across SKILL.md and its bundled files, regardless of which agent runs them. **Part 2** is specific to [Hermes Agent](https://hermes-agent.nousresearch.com) (Nous Research): Hermes's SKILL.md is a superset of the open standard (it's explicitly built to be `agentskills.io`-compatible), and Hermes adds its own frontmatter fields, loading tools, plugin-provided skill mechanics, and distribution system on top. Part 1 tells you *how to write good skill content*; Part 2 tells you *what Hermes-specific machinery is available to you and how to wire it up*, with a focus on plugin-provided skills and the technical build details, since that's what's most likely to differ from what you already know.

---

## 1. The mental model: skills are an onboarding packet, not a manual

The most useful way to think about a skill is as **the onboarding packet you'd hand a new, highly competent hire** — not a textbook. A new hire who is already an expert doesn't need the basics explained; they need the few things that are specific to *this* team: where things live, what the non-obvious rules are, and where to look for detail when they hit a specific situation.

Two consequences fall out of this:

- **Assume competence.** The agent is already smart. Only include what it couldn't infer or already know.
- **Don't hand over the whole filing cabinet at once.** Give the overview first, and point to the drawers. This is the **progressive disclosure** principle that everything else in this guide serves.

---

## 2. The file types and what each one is *for*

A skill is a directory. Only `SKILL.md` is required; everything else is optional and earns its place only when SKILL.md would otherwise get bloated or when a task genuinely needs deterministic code.

```
skill-name/
├── SKILL.md            (required — overview, triggers, core workflow)
├── references/          (optional — docs loaded into context as needed)
├── scripts/             (optional — executable code, runs without loading into context)
└── assets/ or templates/ (optional — output material: files used in, not read into, the result)
```

| File type | Purpose | When the agent loads it | Judgment test |
|---|---|---|---|
| **SKILL.md** | The index and the *common-path* instructions. Says what the skill does, when to trigger, and walks through the workflow that applies almost every time it's used. | Always, in full, the moment the skill triggers | "Would this be true and needed on nearly every invocation?" |
| **references/** | Facts, specs, schemas, API docs, domain data — things the agent needs to *look up*, not reason through. | Only when a specific task needs that specific file | "Is this something to consult, not something to always know?" |
| **scripts/** | Deterministic, repeatable operations: parsing, validation, format conversion, anything better done by running code than by generating tokens. | Executed via the shell; the code itself never enters context — only stdout/stderr does | "Would I rather this be reliable and reusable than re-derived by the model every time?" |
| **templates/** | Output skeletons the agent fills in or copies from — config file templates, boilerplate, starter structures. | Read/copied when producing a deliverable | "Is this a starting shape for the output?" |
| **examples/** | Fully worked example inputs/outputs the skill's instructions point to. | Read when the agent needs to see a concrete worked case, not just a pattern | "Is this a complete case study, bigger than an inline example pair belongs in SKILL.md?" |
| **assets/** | Supplementary files that don't fit the other buckets — logos, fonts, static data files, anything else shipped alongside the skill. | Used directly when producing a deliverable | "Does this get *shipped*, rather than *read as instructions*?" |

Hermes recognizes all five bundle folders (`references/`, `scripts/`, `templates/`, `examples/`, `assets/`) under a skill directory. Not every skill needs all five — most need one or two. `templates/` and `examples/` are worth calling out because they're easy to conflate: a **template** is unfinished (the agent completes it), an **example** is finished (the agent studies it as a pattern to imitate).

### Skill-level scripts vs. plugin-level scripts

Hermes plugins can bundle multiple skills alongside other components (tools, hooks, slash commands). Scripts live at two different levels, and they mean different things:

- **`skill-name/scripts/`** — code that belongs to *one skill's workflow*. It's referenced directly from that skill's SKILL.md, solves a specific step in that skill's task (e.g., `search_arxiv.py` inside the arXiv skill), and has no reason to exist outside that skill's context.
- **`plugin-name/tools.py` / plugin-level Python** — code that supports the *plugin as a whole*: a registered tool, a hook handler, shared logic used by several of the plugin's skills. This is the plugin's own capability surface, not domain instructions for a single task.

Rule of thumb: **if a script is only ever invoked from one SKILL.md's procedure, it belongs in that skill's `scripts/` folder. If the same logic needs to be exposed as a first-class, always-available capability the model can call directly (a real tool, not a document), it belongs in the plugin's Python code as a registered tool, not as a skill script.** Never put task-specific domain instructions in plugin registration code just because it's convenient — instructions belong in SKILL.md where they're loaded on demand, not baked into always-present tool descriptions. See §14 for exactly how Hermes plugins bundle skills technically.

---

## 3. Progressive disclosure: the cascade of knowledge

This is the core design principle everything else follows from. Knowledge cascades through three levels, each more expensive to load than the last, and each loaded only when the previous level makes it necessary:

| Level | Content | Loaded | Rough budget |
|---|---|---|---|
| **1 — Metadata** | `name` + `description` from the YAML frontmatter | Always, for every installed skill, at startup | ~100 tokens per skill |
| **2 — SKILL.md body** | The workflow, the common case, pointers to everything else | Only when the skill triggers | Aim under 500 lines |
| **3 — Bundled resources** | references/, scripts/, assets/ | Only when the specific task needs that specific file | Effectively unlimited — zero cost until touched |

Because Level 3 costs nothing until it's actually opened, **there is no penalty for bundling comprehensive material** — a skill can ship dozens of reference files, large schemas, or extensive examples, as long as SKILL.md doesn't force the agent to read all of them at once. The discipline isn't "keep the skill small." It's "**keep what's *always loaded* small, and let the rest sit on disk until it's needed.**"

### Where "cascade" most often breaks down

The most common authoring mistake is writing a SKILL.md that reads like a reference manual rather than an index. Signs a SKILL.md has slipped from Level 2 into Level 3 material:

- It contains a full API reference, when 90% of tasks only touch two or three methods.
- It walks through a rare edge case in exhaustive detail "just in case."
- It repeats content that also lives in a reference file (now there are two sources of truth).
- It includes long domain background the agent doesn't need to *act*, only to *understand* — understanding it can already do.

**Before (knowledge at the wrong level):**

```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are several available, but pdfplumber is recommended
because it's well-maintained and handles most real-world PDFs well. First
install it with pip. Then open the file and iterate over each page...
```

**After (SKILL.md stays an index; the "why" is assumed, not explained):**

```markdown
## Extract PDF text

Use pdfplumber:
​```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
​```
For scanned PDFs needing OCR, see [references/ocr.md](references/ocr.md).
```

The test for "does this belong in SKILL.md" isn't *is it true and useful* — almost everything in a skill is true and useful. It's: **does the agent need this on (close to) every invocation, at the moment the skill triggers?** If not, it belongs one hop away, behind a pointer.

---

## 4. The role and the limits of SKILL.md

**SKILL.md's job is narrow and specific: get the agent from "this skill is relevant" to "I know the common workflow and where to go for anything unusual," in as few tokens as possible.**

What belongs there:

- The name and description (frontmatter) — this is the *only* thing loaded before the skill triggers, so it carries the full weight of discovery. It must say both **what** the skill does and **when** to use it.
- The workflow for the common case, written so it can be followed directly.
- Explicit pointers to every reference file, script, and asset, with a one-line description of when to open each one.
- Anything that's genuinely needed on nearly every invocation — a non-obvious constraint, a rule that's easy to forget, a required first step.

What does **not** belong there:

- Full API/schema documentation → `references/`
- Domain background the agent already knows → cut entirely
- Rare edge cases and legacy behavior → `references/` (or a collapsed "old patterns" section, see §8)
- Long code samples used only in specific scenarios → `scripts/` (executable) or `references/` (read-as-pattern)
- Content already stated in a reference file → a pointer, not a copy

**A useful discipline:** after drafting, read SKILL.md as if you were the agent seeing it for the first time on a random, typical request. If a whole section wouldn't matter for that typical request, it's Level 3 material wearing a Level 2 costume — move it out.

SKILL.md is also *not* the place to over-specify freedom. See §6 below — how much you constrain the agent should match how fragile the task is, not default to maximal detail everywhere.

---

## 5. Within-file conventions: sequencing and clarity

Use a consistent internal shape for SKILL.md so agents (and humans) can predict where to look:

1. **Title** (H1) — matches the skill name.
2. **One-line purpose statement** — expand on the frontmatter description if useful; don't repeat it verbatim.
3. **Quick start / common workflow** — the thing that happens 80% of the time, written so it can be executed directly (code, exact steps, or both).
4. **Decision points / branches** — "if X, do this; if Y, see [file]" — keep these visible near the top of the relevant section, not buried in prose.
5. **Pointers to bundled resources** — one line per file: what it contains and when to open it.
6. **Edge cases / advanced usage** — kept short in SKILL.md, or moved out entirely if substantial.

Apply the same top-down shape to reference files: **state what the file covers before the detail**, and for anything longer than ~100 lines, open with a table of contents so the agent can jump to a section even on a partial read (see §7 — agents sometimes preview files with something like `head -100` before deciding whether to read further; a missing table of contents means they may never discover what's further down).

**Clarity rules that consistently matter:**

- Prefer the imperative ("Extract the text with pdfplumber") over passive or hedged phrasing ("The text could be extracted using...").
- State the *why* briefly when a rule isn't self-evident — a sentence of reasoning generalizes better than a bare command, because the agent can apply the reasoning to cases you didn't anticipate. Reserve hard, unexplained imperatives ("ALWAYS," "NEVER") for the rare cases where the reasoning genuinely doesn't matter — a wall of unexplained MUSTs is a sign the instructions need rethinking, not reinforcing.
- Use one term per concept and hold it for the whole skill and its reference files (see §7).
- Don't offer a menu of options where one default plus a named exception would do ("Use pdfplumber. For scanned PDFs, use pdf2image with OCR instead" beats listing five libraries).

---

## 6. Setting the right degree of freedom

Match how tightly you constrain the workflow to how much the task can tolerate variation:

| Freedom | Use when | Looks like |
|---|---|---|
| **High** | Multiple approaches are valid; judgment matters; context should drive the decision | Numbered general steps ("Analyze structure, check for bugs, suggest improvements") |
| **Medium** | A preferred pattern exists but some variation is fine | Pseudocode or a parameterized template the agent adapts |
| **Low** | The operation is fragile, order-dependent, or destructive; consistency matters more than flexibility | An exact command to run, explicitly told not to be modified |

Think of it as a path: an **open field** (many routes succeed — give direction, trust judgment) versus a **narrow bridge over a cliff** (one safe way forward — give an exact script and say don't deviate). Most skills mix both: high freedom for judgment calls, low freedom for the one step that must not go wrong (a migration, a destructive file operation, a formatted output that a downstream system parses).

---

## 7. Cross-file conventions

**One source of truth per fact.** If a schema, a rule, or a code pattern is documented in a reference file, SKILL.md should point to it, not restate it. Duplication rots — one copy gets updated and the other doesn't, and now the agent has two conflicting instructions.

**Keep references one hop deep.** Every reference file should be linked directly from SKILL.md. Avoid chains like SKILL.md → advanced.md → details.md. When agents encounter nested references, they sometimes preview rather than fully read a file (partial reads via something like `head -100`), so information buried two links deep may simply never surface. Flatten the structure: SKILL.md links to every file that matters, even if several of those files are conceptually "advanced."

**Table of contents for anything over ~100 lines.** Same reasoning — a partial read should still reveal the full scope of what's available.

**Domain/variant organization when a skill spans several contexts.** If a skill covers multiple frameworks, providers, or domains that are rarely needed together, split them into parallel reference files rather than one large one, so a task about "sales metrics" never has to load the finance or marketing sections:

```
bigquery-skill/
├── SKILL.md              (overview + which file to open)
└── reference/
    ├── finance.md
    ├── sales.md
    ├── product.md
    └── marketing.md
```

**Consistent formatting across every file in a skill.** Same heading levels for the same kind of section, same code-fence conventions, same way of marking "run this" vs. "read this," same terminology. A skill with five files that each format things differently reads like five different authors — because inconsistency, not just verbosity, is what makes an agent misparse or skim past something important.

**Naming that describes content, not position.** `form_validation_rules.md`, not `doc2.md`. `reference/finance.md`, not `docs/file1.md`. This is a cross-file convention because it's what makes the pointers in SKILL.md legible at a glance.

**Always forward slashes in paths** (`scripts/helper.py`), even if the target environment is Windows — this is what makes paths portable across execution environments.

---

## 8. Placement of code and examples: reference vs. inline

The question to ask before pasting any code or example into a markdown file: **does the agent need to *run* this, *read* this as reference, or *pattern-match* against this?** Each answer implies a different placement.

- **Needs to run it, deterministically, every time** → `scripts/`, executed directly. Don't inline the code in SKILL.md at all — just the one-line invocation and what it outputs. The code never has to enter context; only its result does.
- **Needs to read the logic to adapt it** → a reference file, or a short snippet directly in SKILL.md if it's genuinely part of the common-path workflow (a handful of lines, not a wall).
- **Needs to see the desired *style* or *shape* of an output** → an input/output example pair, kept short, placed near the instruction it illustrates. Examples are often clearer than descriptions of style — a commit-message skill benefits more from three example pairs than from a paragraph describing "conventional commit style."

**The wall-of-code test:** if a code block in SKILL.md is long enough that scrolling past it disrupts the surrounding instructions, or if it would only be relevant to a subset of invocations, it almost certainly belongs in `scripts/` (if it runs) or `references/` (if it's read). SKILL.md should read as a workflow with short illustrative snippets, not as a source file with commentary.

**Be explicit about execute-vs-read.** Every script reference should make clear which mode applies:

- *"Run `scripts/validate_fields.py fields.json` before continuing."* (execute — most common, most reliable)
- *"See `scripts/parser.py` for the field-extraction algorithm if you need to replicate its logic elsewhere."* (read as reference — reserve for genuinely complex logic the agent needs to understand, not just invoke)

Prefer execution over regeneration for anything deterministic: a pre-written, tested script is more reliable, cheaper (no code generation, no context spent on the code itself), and consistent across every run — three properties a freshly generated script can't guarantee.

---

## 9. Formatting rules and conventions

- **Headers**: H1 for the skill/file title (one per file). H2 for major sections (Quick start, Workflow, Reference, Edge cases). H3 for subsections within those. Don't skip levels, and don't use heading depth beyond H3 inside SKILL.md — if you need a fourth level, the section is probably dense enough to move to its own reference file.
- **Numbered lists vs. bullets**: numbers for anything **sequential or order-dependent** (workflow steps, a migration procedure); bullets for anything **order-independent** (available options, a set of considerations, pointers to files). If reordering the list would change its meaning, it must be numbered.
- **Checklists for multi-step workflows**: for anything with more than ~3 sequential steps, provide a literal Markdown checklist the agent can copy into its own working notes and check off as it progresses (`- [ ] Step 1: ...`). This measurably reduces skipped steps in longer procedures.
- **Code fences**: always specify the language for syntax highlighting and clarity (` ```python `, ` ```bash `). Keep fenced examples short (see §8) — a fence is for "here is the exact pattern," not "here is the whole module."
- **Bold** for the specific action or term being called out inline ("**Run** `validate.py` before continuing"); avoid bolding whole sentences, which defeats the purpose of emphasis.
- **Tables** for anything genuinely tabular — field mappings, comparisons, decision matrices. Don't force prose into a table, and don't leave a naturally tabular comparison as a wall of bullets.
- **One terminology choice per concept, everywhere.** Pick "API endpoint," not sometimes "endpoint," sometimes "URL," sometimes "route." Pick "extract," not a rotating set of "pull / get / retrieve." This holds across every file in the skill, not just within one.
- **No time-sensitive claims stated as current fact.** Don't write "if before/after [date], use X" — that instruction is correct for a shrinking window and wrong forever after. Instead, keep the *current* method as the default instruction, and — if the history matters — move the deprecated version into a clearly labeled, collapsed "legacy" or "old patterns" section so it doesn't clutter the default path.

---

## 10. Presenting processes so they run consistently

When a process must be followed the same way every time, three patterns make that reliable:

**1. The checklist-and-steps pattern.** State the checklist up front, then walk through each numbered step with just enough detail to execute it — what to run or do, and what "done" looks like for that step. This is the default shape for any multi-step SKILL.md workflow (see the template in §9).

**2. The feedback-loop / validate pattern.** For anything where mistakes are easy and costly, build in a **run → check → fix → recheck** loop rather than a single linear pass:

```markdown
1. Make the edit
2. Validate: `python scripts/validate.py output/`
3. If validation fails: read the error, fix the specific issue, validate again
4. Only proceed once validation passes
```

This works whether the "validator" is a script or a checklist the agent compares its own output against — the structural pattern (do → verify → correct → re-verify) is what matters, not whether code is involved.

**3. The plan-validate-execute pattern**, for batch or destructive operations. Instead of applying changes directly, have the agent first write out an intended-changes file (e.g., a JSON plan), validate *that plan* against the real data, and only then execute it:

`analyze → write plan → validate plan → execute → verify output`

This catches an entire class of errors (referencing something that doesn't exist, conflicting edits, missed required fields) before anything irreversible happens, and gives a specific, machine-checkable point of failure to debug from rather than a mid-execution error.

**Choosing between them:** use the plain checklist for anything moderately complex but low-risk; add the feedback loop wherever output quality is easy to get subtly wrong; add the plan-validate-execute pattern specifically for batch changes, destructive operations, or anything where a mistake is expensive to undo.

---

## 11. Naming and description conventions

- **Skill (directory) names**: lowercase, hyphenated, descriptive. Gerund form (`processing-pdfs`, `analyzing-spreadsheets`) reads most naturally as "the activity this skill performs" and is a solid default; plain noun phrases (`pdf-processing`) or action phrases (`process-pdfs`) are acceptable as long as the convention is consistent across your whole skill library. Avoid vague names (`helper`, `utils`, `tools`) — they tell the agent nothing at the point where it matters most: discovery. Hermes additionally organizes skills into **category subdirectories** (`mlops/axolotl/`, `research/arxiv/`, `devops/deploy-k8s/`) — the category isn't part of the skill's identifier (you still invoke it as `/axolotl`, not `/mlops-axolotl`), but it keeps the skill list navigable as it grows and is how the bundled catalog itself is organized. Pick categories that mirror how your team already talks about domains, and keep the set small — a skill collection with twenty single-skill categories is no more organized than a flat list.
- **The `description` field carries the whole weight of discovery.** It's the only thing loaded before a skill is triggered, so it must state **both** what the skill does **and** the specific contexts/phrases that should trigger it. Write it in the third person ("Extracts text and tables from PDF files..."), not first or second person — mixed point of view across many skills' descriptions in the same system prompt causes discovery problems.
  - Weak: `description: Helps with documents`
  - Strong: `description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.`
- **Reference/script/asset file names**: name by content, not by position (`form_validation_rules.md`, not `doc2.md`; `finance.md`, not `file1.md`). This is what makes a one-line pointer in SKILL.md ("See `reference/finance.md` for revenue metrics") legible without opening the file.

---

## 12. Testing, iteration, and security — briefly

These aren't the user's core ask here, but they round out a working standard, so a short version:

- **Build a few realistic test scenarios before writing extensive documentation.** Write the skill to close specific, observed gaps rather than to cover every case you can imagine. Establish what the agent does *without* the skill first, so you know what the skill actually needs to add.
- **Watch how the agent actually navigates the skill** — which files it opens, which it ignores, where it gets confused — and revise based on that observed behavior rather than on guesses about what it needs.
- **Treat skills as installable software from a trust standpoint.** Audit every bundled file (SKILL.md, scripts, assets) before using a skill from an untrusted source, and be specifically wary of skills that fetch from external URLs, since that content could carry instructions the skill's author never intended.

---

## 13. Worked example: a complete, well-formed skill

```
extracting-invoice-data/
├── SKILL.md
├── references/
│   ├── field_schema.md        (all extractable fields, one place)
│   └── edge_cases.md          (multi-page invoices, scanned docs, etc.)
├── scripts/
│   ├── extract_fields.py      (deterministic extraction — run, don't read)
│   └── validate_totals.py     (checks line items sum to the stated total)
└── assets/
    └── output_template.json   (the exact shape downstream systems expect)
```

```markdown
---
name: extracting-invoice-data
description: Extracts vendor, line items, and totals from invoice PDFs or images into structured JSON. Use whenever the user shares an invoice, asks for invoice data extraction, or needs invoice totals reconciled against line items.
---

# Extracting Invoice Data

## Quick start
1. Run `python scripts/extract_fields.py <input>` — outputs raw fields as JSON.
2. Run `python scripts/validate_totals.py <output.json>` — confirms line items sum to the stated total.
3. If validation fails, review the flagged field, correct it in the JSON, and re-run step 2.
4. Match the final output to `assets/output_template.json` before returning it.

## Field reference
Full field list and types: see [references/field_schema.md](references/field_schema.md).

## Edge cases
Multi-page invoices, handwritten totals, non-English documents: see [references/edge_cases.md](references/edge_cases.md).
```

This is deliberately small: the common path is fully executable from SKILL.md alone, the schema (which changes independently and is looked up, not reasoned about) lives in a reference file, the deterministic work is in scripts, and the exact output shape is an asset rather than a paragraph of prose describing it.

---
