"""Tests for Field descriptor declaration (FR-01).

Tests verify that Field() returns a FieldDescriptor with all expected
attributes, and that optional attributes have sensible defaults.
"""

import pytest

from configsloader import Field


@pytest.mark.unit
class TestFieldDescriptorAllAttributes:
    """AC-01.1: Field() returns a descriptor with all attributes retrievable."""

    def test_field_stores_default_value(self):
        fd = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL",
                   section="provider", description="LLM model to use",
                   required=False, validator=lambda v: bool(v))
        assert fd.default == "gemma4"

    def test_field_stores_flags_list(self):
        fd = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL",
                   section="provider", description="LLM model to use")
        assert fd.flags == ["--model", "-m"]

    def test_field_stores_env_attribute(self):
        fd = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL",
                   section="provider", description="LLM model to use")
        assert fd.env == "APP_MODEL"

    def test_field_stores_section_attribute(self):
        fd = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL",
                   section="provider", description="LLM model to use")
        assert fd.section == "provider"

    def test_field_stores_description(self):
        fd = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL",
                   section="provider", description="LLM model to use")
        assert fd.description == "LLM model to use"

    def test_field_stores_required_flag(self):
        fd = Field(default="gemma4", flags=["--model"], required=True)
        assert fd.required is True

    def test_field_stores_validator_callable(self):
        v = lambda val: val > 0
        fd = Field(default=1, flags=["--count"], validator=v)
        assert fd.validator is v


@pytest.mark.unit
class TestFieldDescriptorDefaults:
    """AC-01.2: Omitted optional attributes default to None/empty."""

    def test_default_is_none_when_omitted(self):
        fd = Field()
        assert fd.default is None

    def test_flags_is_empty_list_when_omitted(self):
        fd = Field()
        assert fd.flags == []

    def test_env_is_none_when_omitted(self):
        fd = Field()
        assert fd.env is None

    def test_section_is_none_when_omitted(self):
        fd = Field()
        assert fd.section is None

    def test_description_is_empty_string_when_omitted(self):
        fd = Field()
        assert fd.description == ""

    def test_required_is_false_when_omitted(self):
        fd = Field()
        assert fd.required is False

    def test_validator_is_none_when_omitted(self):
        fd = Field()
        assert fd.validator is None


@pytest.mark.unit
class TestFieldRequiredDeclaration:
    """AC-01.3: required=True is properly stored and retrievable."""

    def test_required_field_has_required_true(self):
        fd = Field(required=True, flags=["--host"], description="Server host")
        assert fd.required is True

    def test_non_required_field_has_required_false(self):
        fd = Field(required=False, flags=["--host"])
        assert fd.required is False
