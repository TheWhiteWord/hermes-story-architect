### Phase 4: Screenplay Integration (Deferred)
**What:** Reintegrate screenplay import/export to work with the new scene-file architecture. **This is a separate concern — only after Phases 1-3 are complete.**
**Research areas:**
1. **Import flow: screenplay.fountain → scene files**
   - How does the parser map fountain scenes to scene slugs?
   - What happens on duplicate headings?
   - How is `## Content` populated from fountain tokens?
   - What metadata gets extracted (heading, location, time_of_day, characters)?
2. **Export flow: scene files → screenplay.fountain**
   - How do we assemble the fountain text from scene files in order?
   - What's the canonical order? (act → sequence → scene.order)
   - How do we handle scenes without content yet?
   - How do we preserve fountain formatting (title page, sections, etc.)?
3. **Planning-first workflow**
   - How do we create scenes without any screenplay content?
   - How do we handle the transition from "planned scene" to "imported scene"?
   - What happens when a user edits scene content directly vs. importing from fountain?
**Key files to investigate:**
- `core/screenplay.py` — current extraction logic
- `core/fountain_lexer.py` — token structure for reconstruction
- `tools/story_edit.py` — current `_edit_screenplay` (stub)
**Open questions to clarify:**
- Is `screenplay.fountain` a generated artifact or a user-edited file?
- How do we handle version conflicts between scene files and screenplay?
- What's the migration path for existing test projects?