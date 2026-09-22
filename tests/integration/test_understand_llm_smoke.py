"""Real-LLM smoke test for OpenAICompatibleLLMProvider — skipped by default (no
LLM_BASE_URL/LLM_MODEL in this environment or CI). Not part of the default test run;
see README.md "Running Sprint 3" for how to point this at a real endpoint (an
OpenAI-compatible host, or a local Ollama instance in OpenAI-compat mode) and run it
manually with ``pytest -m llm``.

Only checks the call succeeds and returns non-empty text — LLM output is
non-deterministic, so this deliberately does not assert on exact content (see
docs/decisions.md ADR-016, "Risks").
"""

from __future__ import annotations

import os

import pytest

from src.infrastructure.llm.openai_compatible_provider import OpenAICompatibleLLMProvider

pytestmark = pytest.mark.llm

_HAS_LLM_CONFIG = bool(os.environ.get("LLM_BASE_URL")) and bool(os.environ.get("LLM_MODEL"))


@pytest.mark.skipif(
    not _HAS_LLM_CONFIG,
    reason="requires LLM_BASE_URL and LLM_MODEL environment variables pointing at a "
    "real OpenAI-compatible endpoint",
)
def test_complete_returns_non_empty_text_from_a_real_endpoint() -> None:
    provider = OpenAICompatibleLLMProvider()

    result = provider.complete("Reply with a single short sentence.")

    assert isinstance(result, str)
    assert result.strip() != ""
