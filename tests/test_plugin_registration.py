"""The plugin must register tools in the shape Hermes actually reads.

Hermes reads ``schema["parameters"]`` (tools/registry.py:670). Tool modules
declare a plain JSON Schema with ``properties`` at the top level. Passing that
straight through registered every story tool with ZERO parameters and an empty
description — the model had no idea what to pass, and had to guess.

This is the check that would have caught it.
"""
import importlib
import json

import pytest

import importlib.util
import sys
from pathlib import Path

# The repo root IS the plugin package; Hermes imports it under this name.
_spec = importlib.util.spec_from_file_location(
    "hermes_story_architect", Path(__file__).parent.parent / "__init__.py",
    submodule_search_locations=[str(Path(__file__).parent.parent)],
)
plugin = importlib.util.module_from_spec(_spec)
sys.modules["hermes_story_architect"] = plugin
_spec.loader.exec_module(plugin)

TOOLS = [
    "story_backup", "story_create", "story_dashboard", "story_describe", "story_edit",
    "story_export", "story_import", "story_load", "story_memory", "story_retrieve",
    "story_search",
]


class TestRegisteredSchemaShape:
    @pytest.mark.parametrize("name", TOOLS)
    def test_has_parameters_object(self, name):
        """The key Hermes reads. Absent means the model sees no parameters at all."""
        wrapped = plugin._tool_schema(importlib.import_module(f"tools.{name}").SCHEMA)
        params = wrapped.get("parameters")
        assert isinstance(params, dict), f"{name}: no parameters object"
        assert params.get("type") == "object"
        assert params["properties"], f"{name}: registered with zero parameters"

    @pytest.mark.parametrize("name", TOOLS)
    def test_has_a_description(self, name):
        wrapped = plugin._tool_schema(importlib.import_module(f"tools.{name}").SCHEMA)
        assert len(wrapped["description"]) > 20, f"{name}: no usable description"

    def test_required_is_a_list(self):
        for name in TOOLS:
            params = plugin._tool_schema(importlib.import_module(f"tools.{name}").SCHEMA)["parameters"]
            assert isinstance(params["required"], list), f"{name}: required must be a list"

    def test_every_property_keeps_its_description(self):
        """A property without a description is a parameter the model cannot use."""
        missing = []
        for name in TOOLS:
            schema = importlib.import_module(f"tools.{name}").SCHEMA
            for prop, spec in schema.get("properties", {}).items():
                if not spec.get("description") or not spec.get("type"):
                    missing.append(f"{name}.{prop}")
        assert not missing, f"properties missing a description or type: {missing}"


class TestRegistryIntegration:
    def test_registry_actually_receives_the_parameters(self):
        """End-to-end: run register() for real and read back every schema."""
        registered = {}

        class FakeCtx:
            def register_tool(self, name, toolset, schema, handler, **kw):
                registered[name] = schema

            def register_skill(self, *a, **kw):
                pass

            def register_hook(self, *a, **kw):
                pass

            def get_config(self, key, default=None):
                return default

        plugin.register(FakeCtx())

        assert len(registered) == 11
        for name, schema in registered.items():
            assert schema["parameters"]["properties"], f"{name} registered with no parameters"
            assert schema["description"], f"{name} registered with no description"

    def test_search_limit_now_visible_to_the_model(self):
        wrapped = plugin._tool_schema(importlib.import_module("tools.story_search").SCHEMA)
        assert "limit" in wrapped["parameters"]["properties"]
        assert wrapped["parameters"]["required"] == ["project", "query"]
