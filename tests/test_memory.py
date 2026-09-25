"""Focused tests for DB-backed story memory."""
import json

import pytest

from core.db import (
    MEMORY_CATEGORIES,
    MEMORY_CHAR_LIMIT,
    MEMORY_ENTRY_LIMIT,
    create_schema,
    empty_memory,
    get_db,
    get_project_memory,
    memory_serialized_length,
    memory_usage,
    set_project_memory,
    validate_memory,
)


@pytest.fixture
def db_project(tmp_path):
    project_path = tmp_path / "projects" / "memory-test"
    project_path.mkdir(parents=True)
    conn = get_db(project_path)
    try:
        create_schema(conn)
        conn.execute(
            "INSERT INTO entities (id, type, name, extra) VALUES (?, ?, ?, ?)",
            ("memory-test", "project", "Memory Test", "{}"),
        )
    finally:
        conn.close()
    return project_path


def test_empty_memory_has_all_categories_in_fixed_order():
    assert list(empty_memory()) == list(MEMORY_CATEGORIES)
    assert all(entries == [] for entries in empty_memory().values())


def test_validate_memory_preserves_entry_order():
    memory = {
        "decisions": ["first", "second"],
        "directions": ["direction"],
    }
    assert validate_memory(memory) == {
        "decisions": ["first", "second"],
        "directions": ["direction"],
        "open_questions": [],
        "continuity_warnings": [],
    }


def test_validate_memory_rejects_unknown_category():
    with pytest.raises(ValueError, match="Unknown memory category"):
        validate_memory({"other": []})


def test_validate_memory_rejects_empty_entry():
    with pytest.raises(ValueError, match="non-empty strings"):
        validate_memory({"decisions": [" "] })


def test_validate_memory_rejects_overlong_entry():
    with pytest.raises(ValueError, match=str(MEMORY_ENTRY_LIMIT)):
        validate_memory({"decisions": ["x" * (MEMORY_ENTRY_LIMIT + 1)]})


def test_validate_memory_rejects_duplicate_entry():
    with pytest.raises(ValueError, match="Duplicate memory entry"):
        validate_memory({"decisions": ["same", "same"]})


def test_validate_memory_rejects_total_budget_overflow():
    entries = [f"{i:03d}" + "x" * (MEMORY_ENTRY_LIMIT - 3) for i in range(10)]
    with pytest.raises(ValueError, match=str(MEMORY_CHAR_LIMIT)):
        validate_memory({"decisions": entries})


def test_memory_usage_returns_counts_and_serialized_length():
    memory = validate_memory({"decisions": ["one", "two"], "directions": ["go"]})
    usage = memory_usage(memory)
    assert usage["counts"] == {
        "decisions": 2,
        "directions": 1,
        "open_questions": 0,
        "continuity_warnings": 0,
    }
    assert usage["usage"] == memory_serialized_length(memory)
    assert usage["usage"] <= MEMORY_CHAR_LIMIT


def test_db_round_trip_and_missing_memory_is_empty(db_project):
    assert get_project_memory(db_project) == empty_memory()
    memory = {
        "decisions": ["Keep the mystery unresolved."],
        "open_questions": ["What did Victor alter?"],
    }
    assert set_project_memory(db_project, memory) == validate_memory(memory)
    assert get_project_memory(db_project) == validate_memory(memory)


def test_db_round_trip_preserves_project_extra(db_project):
    conn = get_db(db_project)
    try:
        conn.execute("UPDATE entities SET extra=? WHERE id='memory-test'", (json.dumps({"genre": "drama"}),))
    finally:
        conn.close()
    set_project_memory(db_project, {"directions": ["Stay ambiguous."]})
    conn = get_db(db_project)
    try:
        extra = json.loads(conn.execute("SELECT extra FROM entities WHERE id='memory-test'").fetchone()[0])
    finally:
        conn.close()
    assert extra["genre"] == "drama"
    assert extra["memory"]["directions"] == ["Stay ambiguous."]
