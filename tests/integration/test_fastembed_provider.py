"""Integration tests: real FastEmbedProvider (real ONNX model, may download on
first run — see pyproject.toml's ``integration`` marker)."""

from __future__ import annotations

import pytest

from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def provider() -> FastEmbedProvider:
    return FastEmbedProvider()


def test_dimension_is_a_real_positive_int(provider: FastEmbedProvider) -> None:
    assert isinstance(provider.dimension, int)
    assert provider.dimension > 0


def test_embed_documents_returns_one_vector_per_text(provider: FastEmbedProvider) -> None:
    vectors = provider.embed_documents(["hello world", "another sentence"])

    assert len(vectors) == 2
    assert all(len(v) == provider.dimension for v in vectors)
    assert all(isinstance(x, float) for x in vectors[0])


def test_embed_documents_on_empty_list_returns_empty_list(provider: FastEmbedProvider) -> None:
    assert provider.embed_documents([]) == []


def test_embed_query_returns_one_vector_of_correct_dimension(
    provider: FastEmbedProvider,
) -> None:
    vector = provider.embed_query("what dataset was used?")
    assert len(vector) == provider.dimension


def test_embedding_is_deterministic(provider: FastEmbedProvider) -> None:
    first = provider.embed_query("a repeated question")
    second = provider.embed_query("a repeated question")
    assert first == second
