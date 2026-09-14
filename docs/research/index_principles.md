# Index Design Principles

> A reference guide for making decisions about what belongs in an index, what stays in source files, and where to draw the boundary between storage and retrieval.

---

## 1. The Core Principle

**The index holds what's needed to make retrieval decisions. The source holds what's retrieved.**

This is a functional definition, not a structural one. It means the index answers: "What exists? How does it connect? Where do I find more?" It does not answer: "What does the content say?" — that's the source's job.

If the consumer can always correctly decide *which file* and *which section* to fetch next using only the index, the index is complete. If it sometimes can't — if it needs to read content to decide whether it needs to read more — that's a signal the index summaries are too thin, not that you should add full body content.

---

## 2. Storage Boundaries Follow Production Boundaries

A storage boundary (separate files, separate tables, separate services) is only justified when it reflects a real production difference. Production differences are:

| Production difference | Storage boundary justified? |
|----------------------|----------------------------|
| Different writers (two pipelines, two teams) | **Yes** — merge-responsibility problem is real |
| Different volatility (one changes hourly, one weekly) | **Yes** — caching and churn implications |
| Different access control (one consumer must not see certain fields) | **Yes** — enforceable without reader logic |
| Different read patterns across hardware (hot/cold storage, different services) | **Yes** — I/O and size class implications |
| Different consumption patterns within the same process | **No** — filter at the consumer |
| Conceptual categories that exist only in the developer's model | **No** — this is a consumer concern |

**The test:** If two artifacts are always written together, always read together, and have the same lifecycle, they are not two artifacts — they are one.

---

## 3. Filter at the Consumer, Not at the Source

This is the default. It holds until a production boundary (Section 2) actually emerges.

**Why it's the default:**
- Consumer filtering is strictly more general than storage splitting. Splitting can only separate by file. Filtering can separate by field, by task context, by access control, by size budget.
- Storage splitting moves the filter boundary from the tool layer (flexible, testable, reversible) to the filesystem (rigid, requires regeneration, creates sync obligations).
- The "filter at consumer" approach lets you add new consumption patterns without touching the storage layer.

**When to split instead:**
- Different writers need different files (merge-responsibility problem)
- Different volatility requires different caching behavior
- Different access control requirements exist
- Different read patterns cross hardware/I/O boundaries

---

## 4. Classification Costs Compound

Every new field in a split architecture requires a decision: "Which file does this belong to?" This cost does not amortize away. It's a permanent tax on schema evolution.

**The real risk isn't the clear cases** — it's the fields that are 60/40, where you make a call, and three months later discover a consumer pattern that makes the opposite choice more natural. Now you either:
- Move the field (a migration)
- Live with it in the wrong file (conceptual debt that silently misleads future readers)

**Cross-category fields in a split architecture are a structural smell.** If you already see several, the schema is telling you the categories aren't real partitions — they're just consumption views, which belong in the consumer layer.

---

## 5. The Index Is a Map, Not Territory

The index is a navigation structure. It describes what exists and how things connect. It does not contain the things themselves.

**This holds regardless of dataset size.** "Small enough to fit in context" is a moving target in two directions: the dataset grows as the project matures, and context windows change across model versions. Designing the index boundary around current size builds a constraint that silently breaks when either shifts.

**The "single read" efficiency argument is usually wrong.** In most LLM tool-call architectures, the cost of an additional file read is negligible compared to the cost of carrying unnecessary content in context across multiple calls. If the index is always loaded, every token of body content in every index entry is paid on every interaction — whether or not that content is needed.

---

## 6. No Stable Middle Ground with Body Content

You cannot have all three of these properties simultaneously:
1. The index holds body content
2. The source files remain authoritative
3. The index is always current

You can have any two, not all three. The default architecture (files are authoritative, index holds derived metadata) avoids the problem by never putting content in the index at all.

**The "rewrite the full body" case doesn't break this.** That task requires the full body to be current and authoritative — which means reading from the source, not the index. If the index holds a copy, you now have to decide which copy is canonical, and you've entered cache-invalidation territory.

---

## 7. Summaries Belong in the Index; Full Body Doesn't

A one-sentence summary in the index is not a cache of the body — it's a derived metadata field, like a label or a count. It doesn't go stale the same way because it's not trying to be a faithful reproduction of the source.

The staleness risk of a summary is: "the summary no longer accurately reflects the body after a major edit." That's a real risk, but it's manageable with a regeneration trigger, and it doesn't create the write-amplification problem that full body storage does.

**The boundary shifts toward the index only when retrieval decisions genuinely require content that can't be summarized without loss.** A one-sentence summary is almost always sufficient for retrieval decisions. The full body is almost never needed until after the retrieval decision is made.

---

## 8. When Body-in-Index Is Actually Correct

There are legitimate cases. The conditions:

| Condition | Why it works |
|-----------|--------------|
| The index is the source of truth, not a derivative | Entities are defined in the index; files (if they exist) are generated from it |
| Single writer, no external editing | Body content is only written through a controlled pipeline that also updates the index atomically |
| Read-heavy, write-rare, with bounded growth | Reference data systems (taxonomies, glossaries) where sync cost is acceptable and read latency matters |
| The content IS the navigation structure | "Body" is short and structured enough that the line between metadata and content disappears |

**These conditions are almost never true for creative project files**, which are write-frequent by nature and where the source files are the natural authoring surface.

---

## 9. Decision Checklist

When deciding whether to add something to an index, ask:

1. **Is this needed to make a retrieval decision?** If yes, it belongs in the index. If no, it probably doesn't.
2. **Does this change independently from the rest of the index?** If yes, consider whether a storage boundary reflects a real production difference (Section 2).
3. **Is this a summary or a reproduction?** Summaries are metadata; reproductions are caches. Caches need invalidation logic.
4. **Will this field always clearly belong to one category?** If it's 60/40, the split is wrong.
5. **Am I optimizing for read cost or context cost?** If the index is always loaded, context cost usually dominates.
6. **Is the dataset size stable and permanently small?** If not, size-based reasoning will break.

---

## 10. The Underlying Pattern

All these principles are instances of one idea: **denormalization is a trade-off you make for a specific reason, not a default you relax when it's convenient.**

- Splitting files is denormalization across storage boundaries.
- Storing body in the index is denormalization across retrieval boundaries.
- Both are valid when the trade-off is explicit and the reason is a production constraint, not a conceptual preference.

The default is always: single source of truth, derived views at the consumer. Deviate only when you can name the production reason.
