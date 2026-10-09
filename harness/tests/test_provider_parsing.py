"""Tests for the pure response-parsing functions, using plain dicts that
mirror each SDK's response shape — no network, no SDK client involved.
"""

from __future__ import annotations

from harness.providers.anthropic_provider import parse_anthropic_message
from harness.providers.openai_provider import parse_openai_response


def test_anthropic_summarized_thinking_is_summary_visibility():
    message = {
        "content": [
            {"type": "thinking", "thinking": "Step 1... step 2...", "signature": "sig"},
            {"type": "text", "text": "The best answer is: (B)"},
        ]
    }
    answer, reasoning, visibility = parse_anthropic_message(message)
    assert answer == "The best answer is: (B)"
    assert reasoning == "Step 1... step 2..."
    assert visibility == "summary"


def test_anthropic_omitted_thinking_is_none_visibility():
    message = {
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "The best answer is: (B)"},
        ]
    }
    answer, reasoning, visibility = parse_anthropic_message(message)
    assert answer == "The best answer is: (B)"
    assert reasoning is None
    assert visibility == "none"


def test_anthropic_no_thinking_block_is_none_visibility():
    message = {"content": [{"type": "text", "text": "The best answer is: (A)"}]}
    answer, reasoning, visibility = parse_anthropic_message(message)
    assert reasoning is None
    assert visibility == "none"


def test_anthropic_never_reports_full_visibility():
    # No response shape should ever yield "full" — Claude never returns raw CoT.
    message = {
        "content": [
            {"type": "thinking", "thinking": "lots of detail", "signature": "sig"},
            {"type": "text", "text": "answer"},
        ]
    }
    _, _, visibility = parse_anthropic_message(message)
    assert visibility != "full"


def test_openai_reasoning_summary_is_summary_visibility():
    response = {
        "output": [
            {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "Thought about it."}],
            },
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "The best answer is: (C)"}],
            },
        ]
    }
    answer, reasoning, visibility = parse_openai_response(response)
    assert answer == "The best answer is: (C)"
    assert reasoning == "Thought about it."
    assert visibility == "summary"


def test_openai_no_reasoning_item_is_none_visibility():
    response = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "The best answer is: (C)"}],
            }
        ]
    }
    answer, reasoning, visibility = parse_openai_response(response)
    assert reasoning is None
    assert visibility == "none"


def test_openai_reasoning_item_with_empty_summary_is_none_visibility():
    response = {
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "The best answer is: (C)"}],
            },
        ]
    }
    _, reasoning, visibility = parse_openai_response(response)
    assert reasoning is None
    assert visibility == "none"


def test_openai_never_reports_full_visibility():
    response = {
        "output": [
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "detail"}]},
            {"type": "message", "content": [{"type": "output_text", "text": "answer"}]},
        ]
    }
    _, _, visibility = parse_openai_response(response)
    assert visibility != "full"
