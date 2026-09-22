"""LLMProvider implementation speaking the OpenAI-compatible ``/chat/completions``
HTTP shape (ADR-016) — deliberately not the ``openai`` SDK, so this works unmodified
against any compatible endpoint (a real OpenAI-compatible host, a local Ollama
instance in OpenAI-compat mode, vLLM, etc.) without a vendor dependency.
"""

from __future__ import annotations

import os

import httpx

from src.domain.interfaces.llm_provider import LLMError, LLMProvider

DEFAULT_TIMEOUT = 60.0


class OpenAICompatibleLLMProvider(LLMProvider):
    """Calls a ``POST {base_url}/chat/completions`` endpoint.

    ``base_url``/``api_key``/``model`` fall back to the provider-neutral
    ``LLM_BASE_URL``/``LLM_API_KEY``/``LLM_MODEL`` environment variables (never
    ``OPENAI_API_KEY`` — this class is not tied to OpenAI). ``client`` is the test
    seam: pass an ``httpx.Client`` built with a ``MockTransport`` to test without
    real network calls (matches this codebase's constructor-injected-fake pattern).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        base_url = base_url or os.environ.get("LLM_BASE_URL")
        api_key = api_key or os.environ.get("LLM_API_KEY")
        model = model or os.environ.get("LLM_MODEL")

        if not base_url or not model:
            raise LLMError(
                "OpenAICompatibleLLMProvider requires base_url and model "
                "(directly, or via LLM_BASE_URL/LLM_MODEL environment variables)"
            )

        self._model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(
            base_url=base_url, headers=headers, timeout=timeout
        )

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM completion request failed: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMError(f"LLM response was not valid JSON: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"LLM response missing choices[0].message.content: {exc}") from exc

        if not isinstance(content, str):
            # Some providers return null content (e.g. a refusal or a tool-call-only
            # response with no text). Returning that as-is would hand the caller a
            # non-str where LLMProvider promises str — json.loads(None) downstream
            # raises a bare TypeError, not an LLMError, which UnderstandingPipeline's
            # per-paper `except LLMError` would not catch, crashing the whole batch
            # instead of isolating this one paper's failure.
            raise LLMError(
                f"LLM response content was not a string (got {type(content).__name__})"
            )
        return content
