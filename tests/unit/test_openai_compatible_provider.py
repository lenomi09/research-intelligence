"""Unit tests for OpenAICompatibleLLMProvider using httpx.MockTransport — no real
network calls (constructor-injected httpx.Client is the test seam)."""

from __future__ import annotations

import json

import httpx
import pytest

from src.domain.interfaces.llm_provider import LLMError
from src.infrastructure.llm.openai_compatible_provider import OpenAICompatibleLLMProvider


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://fake")


def test_complete_returns_message_content_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(200, json={"choices": [{"message": {"content": "world"}}]})

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", api_key="k", model="test-model", client=_client(handler)
    )

    assert provider.complete("hello") == "world"


def test_complete_sends_max_tokens_when_given() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["max_tokens"] == 42
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", model="test-model", client=_client(handler)
    )

    provider.complete("hello", max_tokens=42)


def test_complete_raises_llm_error_on_http_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", model="test-model", client=_client(handler)
    )

    with pytest.raises(LLMError):
        provider.complete("hello")


def test_complete_raises_llm_error_on_non_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", model="test-model", client=_client(handler)
    )

    with pytest.raises(LLMError):
        provider.complete("hello")


def test_complete_raises_llm_error_on_missing_choices() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", model="test-model", client=_client(handler)
    )

    with pytest.raises(LLMError):
        provider.complete("hello")


def test_complete_raises_llm_error_on_null_content() -> None:
    # Some providers return null content for a refusal or a tool-call-only
    # response with no text — this must not silently return None (LLMProvider
    # promises str) or crash downstream with a bare TypeError from json.loads(None).
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    provider = OpenAICompatibleLLMProvider(
        base_url="http://fake", model="test-model", client=_client(handler)
    )

    with pytest.raises(LLMError):
        provider.complete("hello")


def test_construction_without_base_url_raises_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(LLMError):
        OpenAICompatibleLLMProvider()


def test_construction_falls_back_to_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://fake")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_API_KEY", "env-key")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "env-model"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    # client is still injected here to avoid a real network call; this only
    # exercises that base_url/model/api_key are read from the env when omitted.
    provider = OpenAICompatibleLLMProvider(client=_client(handler))

    assert provider.complete("hello") == "ok"


def test_own_client_sends_authorization_header_from_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = OpenAICompatibleLLMProvider(base_url="http://fake", api_key="k", model="m")

    assert provider._client.headers["authorization"] == "Bearer k"
