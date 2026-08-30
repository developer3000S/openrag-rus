"""Langflow talks to the OpenRAG LLM proxy with a hop token, not provider keys."""

from types import SimpleNamespace

import pytest

from services.langflow_llm_token_service import LangflowLlmTokenService
from utils.langflow_headers import (
    add_provider_credentials_to_headers,
    build_model_provider_headers,
)


def test_build_model_provider_headers_forces_openai_client():
    config = SimpleNamespace(
        knowledge=SimpleNamespace(
            embedding_model="text-embedding-3-small", embedding_provider="ollama"
        ),
        agent=SimpleNamespace(llm_model="gpt-4o-mini", llm_provider="openai"),
    )
    headers = build_model_provider_headers(config)
    assert headers["X-LANGFLOW-GLOBAL-VAR-SELECTED_LANGUAGE_MODEL"] == "gpt-4o-mini"
    assert headers["X-LANGFLOW-GLOBAL-VAR-SELECTED_LANGUAGE_MODEL_PROVIDER"] == "OpenAI"
    assert headers["X-LANGFLOW-GLOBAL-VAR-SELECTED_EMBEDDING_MODEL"] == "text-embedding-3-small"
    assert headers["X-LANGFLOW-GLOBAL-VAR-SELECTED_EMBEDDING_MODEL_PROVIDER"] == "OpenAI"


@pytest.mark.asyncio
async def test_add_provider_credentials_injects_hop_token_not_jwt_or_provider_keys(
    monkeypatch,
):
    monkeypatch.setattr(
        "config.settings.get_langflow_llm_base_url",
        lambda: "http://openrag-backend:8000/v1",
    )
    monkeypatch.setattr("config.settings.get_langflow_opensearch_url", lambda: "")
    monkeypatch.setattr("config.settings.get_langflow_docling_url", lambda: "")
    monkeypatch.setattr("config.settings.get_index_name", lambda: "")
    monkeypatch.setattr("config.settings.IBM_AUTH_ENABLED", False)

    config = SimpleNamespace(
        providers=SimpleNamespace(
            openai=SimpleNamespace(api_key="sk-real-openai"),
            ollama=SimpleNamespace(endpoint="http://localhost:11434"),
        )
    )
    headers = {}
    await add_provider_credentials_to_headers(
        headers, config, jwt_token="Bearer user-jwt-token", user_id="alice"
    )
    hop = headers["X-LANGFLOW-GLOBAL-VAR-OPENRAG_LLM_TOKEN"]
    assert hop != "user-jwt-token"
    user = LangflowLlmTokenService().validate_token(hop)
    assert user.user_id == "alice"
    assert user.provider == "langflow_llm"
    assert headers["X-LANGFLOW-GLOBAL-VAR-OPENRAG_LLM_BASE_URL"] == "http://openrag-backend:8000/v1"
    # Chat (`/v1/chat/completions`) and embeddings (`/v1/embeddings`) share these.
    assert headers["X-LANGFLOW-GLOBAL-VAR-OPENAI_API_KEY"] == hop
    assert "X-LANGFLOW-GLOBAL-VAR-OPENRAG_LLM_TOKEN" in headers
    # Match on the serialized headers: `in headers.values()` compares whole
    # values, so a secret embedded in a larger value ("Bearer sk-real-openai")
    # would slip past the very leak this test exists to catch.
    serialized = "\n".join(f"{name}: {value}" for name, value in headers.items())
    for secret in ("sk-real-openai",):
        assert secret not in serialized


@pytest.mark.asyncio
async def test_hop_token_is_minted_when_caller_only_has_ibm_basic():
    """Basic OpenSearch creds cannot be an OpenAI api_key; mint a hop token instead."""
    from unittest.mock import patch

    with (
        patch(
            "config.settings.get_langflow_llm_base_url", lambda: "http://openrag-backend:8000/v1"
        ),
        patch("config.settings.get_langflow_opensearch_url", lambda: ""),
        patch("config.settings.get_langflow_docling_url", lambda: ""),
        patch("config.settings.get_index_name", lambda: ""),
        patch("config.settings.IBM_AUTH_ENABLED", False),
    ):
        headers = {}
        await add_provider_credentials_to_headers(
            headers, SimpleNamespace(), jwt_token="Basic dXNlcjpwYXNz", user_id="ibm-user"
        )
    hop = headers["X-LANGFLOW-GLOBAL-VAR-OPENRAG_LLM_TOKEN"]
    user = LangflowLlmTokenService().validate_token(hop)
    assert user.user_id == "ibm-user"
    assert not hop.startswith("Basic ")
    assert headers["X-LANGFLOW-GLOBAL-VAR-OPENAI_API_KEY"] == hop
