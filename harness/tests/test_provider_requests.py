"""Tests for the pure request-building functions (no client, no network)."""

from __future__ import annotations

from harness.providers.anthropic_provider import build_request as build_anthropic_request
from harness.providers.openai_provider import build_request as build_openai_request


def test_openai_request_includes_configured_reasoning_effort(small_config):
    request = build_openai_request(small_config.models.openai, "a prompt")
    assert request["reasoning"]["effort"] == small_config.models.openai.reasoning.effort


def test_openai_request_uses_configured_model_id(small_config):
    request = build_openai_request(small_config.models.openai, "a prompt")
    assert request["model"] == small_config.models.openai.model_id


def test_anthropic_request_includes_configured_effort(small_config):
    request = build_anthropic_request(small_config.models.anthropic, "a prompt")
    assert request["output_config"]["effort"] == small_config.models.anthropic.effort
