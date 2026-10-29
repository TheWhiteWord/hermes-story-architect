"""No entity type may declare an `id` field — the row key already is the id.

`id` is in FIELDS_TO_SKIP, so the write path discards it: a model that sets it
gets silence. But it was still in four schemas, where it did two kinds of harm.
It appeared in `fields: ["all"]` as an empty string, reading as "this beat has
no id" when the id is right there in the entry, and story_describe advertised it
as required, so a model could try to write it and watch it vanish.

Retrieval and editing address an entity by the entry's `id`, which is the row
key — never by a field. So the field carried nothing but a wrong-looking blank.
"""

import pytest


from story_architect.core.constants import ENTITY_SCHEMAS
from story_architect.core.entity import FIELDS_TO_SKIP

from story_architect.tools.story_retrieve import handler


@pytest.fixture
def project_root(fixture_path):
    """The copied fixture under a `projects/` dir, which resolve_project expects.

    The returned path is the parent of `projects`: the handler appends that
    segment itself, so handing it the projects dir would look for projects/projects.
    """
    projects = fixture_path.parent / "projects"
    projects.mkdir()
    fixture_path.rename(projects / "save-the-children")
    return fixture_path.parent


def test_no_schema_declares_a_field_the_write_path_discards():
    """The trap in one assertion: a field the caller can set but is dropped.

    `type` is the exception that proves the rule. It is in FIELDS_TO_SKIP too,
    but declaring it is honest — it documents that a scene's type is "scene" —
    and story_describe labels it as such. What must not be declared is an `id`:
    the row key already is the id, so the field could only ever be blank.
    """
    offenders = [f"{t}.{f}" for t, schema in ENTITY_SCHEMAS.items()
                 for f in schema if f in FIELDS_TO_SKIP and f != "type"]
    assert offenders == [], f"declared but discarded on write: {offenders}"


@pytest.mark.parametrize("entity_type,slug", [
    ("scene", "central-room-day"),
    ("act", "act-1"),

])
def test_every_type_that_had_an_id_field_is_still_retrievable(
        project_root, entity_type, slug):
    """Deleting the field must not cost the entity its identity."""
    import json
    out = json.loads(str(handler(
        {"project": "save-the-children", "entity_type": entity_type,
         "id": [slug], "fields": ["all"]},
        root_path=str(project_root),
    )))
    assert out["entities"][0]["id"] == slug
