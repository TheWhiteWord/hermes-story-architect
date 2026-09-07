# Task 4: Retrieval Engine — FINAL DECISIONS

> All subtasks resolved.

---

## Status: RESOLVED

| Subtask | Status |
|---------|--------|
| 01_retrieval_engine.md | RESOLVED |

---

## 1. Tool Schema

```python
{
    "name": "story_retrieve",
    "description": "Retrieve specific sections from a story project note.",
    "parameters": {
        "entity_type": {"type": "string", "enum": ["character", "location", "world", "plot", "project"]},
        "slug": {"type": "string"},
        "sections": {"type": "array", "items": {"type": "string"}}
    }
}
```

---

## 2. Retrieval Flow

```
Index (always loaded) → LLM identifies entity + sections → story_retrieve() → returns targeted prose
```

---

## 3. Reuses section_parser.py

`get_section()` from Task 2 — no reinvention.

---

## 4. Error Handling

| Error | Response |
|-------|----------|
| Entity not found | Error message |
| Section not found | Return available sections list |
| File read error | Error message |

---

## What happens next

1. Implement `plugin/tools/story_retrieve.py`
2. Test with a real project
3. Proceed to **Task 5 (Action Protocol)**
