"""The LLMProvider interface (see architecture.md §2.3/§8, ADR-002, ADR-016).

Mirrors EmbeddingProvider's pattern: an ABC plus a small domain exception, no
vendor types leaked. Sprint 3's only implementation is OpenAICompatibleLLMProvider
(src/infrastructure/llm/openai_compatible_provider.py); nothing outside
src/infrastructure/llm may import an HTTP/LLM SDK directly.

Deliberately raw text in, raw text out — not a schema-typed "extract structured
data" method. ADR-002 already commits this same interface to comparison synthesis,
gap-hypothesis phrasing, and grounded Q&A in later sprints, none of which produce
Understanding's specific JSON shape; a method signature baked around one sprint's
schema would need to change the moment a later sprint needs free-text generation
instead. JSON-schema construction and response parsing are
src/understanding/prompting.py's job, not this interface's — see ADR-016.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(Exception):
    """Raised when a completion request fails (network/timeout/malformed response,
    or the provider rejects the request)."""


class LLMProvider(ABC):
    """Generates text from a prompt."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        raise NotImplementedError
