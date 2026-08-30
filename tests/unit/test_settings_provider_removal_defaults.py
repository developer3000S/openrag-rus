"""Tests for default model selection when a provider is removed.

When a provider is removed and it was the active LLM or embedding provider,
the backend should fall back to another configured provider AND select a
sensible default model (not an empty string).
"""

from api.settings.helpers import (
    _default_embedding_model,
    _default_llm_model,
    _first_configured_embedding_provider,
    _first_configured_llm_provider,
)
from config.config_manager import (
    AgentConfig,
    GenericProviderConfig,
    KnowledgeConfig,
    OllamaConfig,
    OnboardingState,
    OpenAIConfig,
    OpenRAGConfig,
    ProvidersConfig,
)
from config.model_constants import OPENAI_DEFAULT_LANGUAGE_MODEL

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(
    *,
    openai=False,
    ollama=False,
    custom: list[str] | None = None,
    llm_provider="openai",
    llm_model="gpt-5.4-mini",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
) -> OpenRAGConfig:
    """Build a minimal OpenRAGConfig with the requested providers configured."""
    return OpenRAGConfig(
        providers=ProvidersConfig(
            openai=OpenAIConfig(api_key="sk-test" if openai else "", configured=openai),
            ollama=OllamaConfig(
                endpoint="http://localhost:11434" if ollama else "", configured=ollama
            ),
            custom={
                name: GenericProviderConfig(
                    credentials={"api_key": f"{name}-key", "api_base": f"https://{name}.example"},
                    configured=True,
                )
                for name in (custom or [])
            },
        ),
        knowledge=KnowledgeConfig(
            embedding_model=embedding_model,
            embedding_provider=embedding_provider,
        ),
        agent=AgentConfig(
            llm_model=llm_model,
            llm_provider=llm_provider,
        ),
        onboarding=OnboardingState(),
        edited=True,
    )


# ---------------------------------------------------------------------------
# _default_llm_model
# ---------------------------------------------------------------------------


class TestDefaultLlmModel:
    def test_openai_returns_static_default(self):
        assert _default_llm_model("openai") == OPENAI_DEFAULT_LANGUAGE_MODEL

    def test_ollama_returns_empty(self):
        assert _default_llm_model("ollama") == ""

    def test_unknown_provider_returns_empty(self):
        assert _default_llm_model("nonexistent") == ""


# ---------------------------------------------------------------------------
# _default_embedding_model
# ---------------------------------------------------------------------------


class TestDefaultEmbeddingModel:
    def test_openai_returns_empty(self):
        """ "openai" often means an internal OpenAI-compatible gateway with a
        curated model set — never guess, force an explicit, validated pick."""
        assert _default_embedding_model("openai") == ""

    def test_ollama_returns_empty(self):
        assert _default_embedding_model("ollama") == ""

    def test_unknown_provider_returns_empty(self):
        assert _default_embedding_model("nonexistent") == ""

    def test_uses_deployment_declared_default_when_set(self, monkeypatch):
        """When the deployment declares EMBEDDING_MODEL/EMBEDDING_PROVIDER
        (Helm values / operator ConfigMap), the fallback should use it
        instead of returning empty — this is what lets a correctly
        configured deployment self-heal after a provider removal."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
        assert _default_embedding_model("openai") == "text-embedding-3-large"

    def test_ignores_declared_default_for_a_different_provider(self, monkeypatch):
        """A declared default for "openai" must not leak into the fallback
        for a provider it wasn't declared for."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
        assert _default_embedding_model("gemini") == ""


# ---------------------------------------------------------------------------
# _first_configured_llm_provider
# ---------------------------------------------------------------------------


class TestFirstConfiguredLlmProvider:
    def test_excludes_removed_provider(self):
        config = _make_config(openai=True, ollama=True)
        assert _first_configured_llm_provider(config, "openai") == "ollama"

    def test_respects_priority_order(self):
        """Order is openai > ollama, then configured custom providers."""
        config = _make_config(openai=True, ollama=True, custom=["gemini"])
        assert _first_configured_llm_provider(config, "openai") == "ollama"
        assert _first_configured_llm_provider(config, "ollama") == "openai"

    def test_skips_unconfigured(self):
        config = _make_config(ollama=True)
        assert _first_configured_llm_provider(config, "openai") == "ollama"

    def test_custom_provider_is_a_fallback(self):
        config = _make_config(openai=True, ollama=True, custom=["gemini"])
        assert _first_configured_llm_provider(config, "openai") == "ollama"
        # When the first-class providers are removed/excluded, custom wins.
        config = _make_config(openai=True, custom=["gemini"])
        assert _first_configured_llm_provider(config, "openai") == "gemini"

    def test_falls_back_to_openai_when_none_configured(self):
        config = _make_config()
        assert _first_configured_llm_provider(config, "ollama") == "openai"


# ---------------------------------------------------------------------------
# _first_configured_embedding_provider
# ---------------------------------------------------------------------------


class TestFirstConfiguredEmbeddingProvider:
    def test_excludes_removed_provider(self):
        config = _make_config(openai=True, ollama=True)
        assert _first_configured_embedding_provider(config, "openai") == "ollama"

    def test_returns_empty_when_none_configured(self):
        config = _make_config()
        assert _first_configured_embedding_provider(config, "ollama") == ""


# ---------------------------------------------------------------------------
# Simulated provider removal: LLM model default
# ---------------------------------------------------------------------------


class TestProviderRemovalLlmDefault:
    """Simulate the provider-removal code path from endpoints.py and verify
    that the resulting llm_model is a sensible default, not empty."""

    def _simulate_llm_removal(self, config: OpenRAGConfig, removed: str):
        """Replicate the fallback logic from update_settings()."""
        if config.agent.llm_provider == removed:
            fb = _first_configured_llm_provider(config, removed)
            config.agent.llm_provider = fb
            config.agent.llm_model = _default_llm_model(fb)

    def test_remove_openai_falls_back_to_ollama_empty_model(self):
        """Ollama models are dynamic — backend returns empty, frontend picks."""
        config = _make_config(
            openai=True,
            ollama=True,
            llm_provider="openai",
            llm_model="gpt-5.4-mini",
        )
        self._simulate_llm_removal(config, "openai")
        assert config.agent.llm_provider == "ollama"
        assert config.agent.llm_model == ""

    def test_remove_ollama_falls_back_to_openai_model(self):
        config = _make_config(
            openai=True,
            ollama=True,
            llm_provider="ollama",
            llm_model="llama3.1",
        )
        self._simulate_llm_removal(config, "ollama")
        assert config.agent.llm_provider == "openai"
        assert config.agent.llm_model == OPENAI_DEFAULT_LANGUAGE_MODEL

    def test_remove_custom_provider_falls_back_to_openai_model(self):
        config = _make_config(
            openai=True,
            custom=["gemini"],
            llm_provider="gemini",
            llm_model="gemini-2.0-flash",
        )
        self._simulate_llm_removal(config, "gemini")
        assert config.agent.llm_provider == "openai"
        assert config.agent.llm_model == OPENAI_DEFAULT_LANGUAGE_MODEL

    def test_no_change_if_different_provider_removed(self):
        """If the removed provider wasn't the active one, nothing changes."""
        config = _make_config(
            openai=True,
            ollama=True,
            llm_provider="openai",
            llm_model="gpt-5.4-mini",
        )
        self._simulate_llm_removal(config, "ollama")
        assert config.agent.llm_provider == "openai"
        assert config.agent.llm_model == "gpt-5.4-mini"


# ---------------------------------------------------------------------------
# Simulated provider removal: embedding model default
# ---------------------------------------------------------------------------


class TestProviderRemovalEmbeddingDefault:
    """Simulate embedding provider fallback on removal."""

    def _simulate_embedding_removal(self, config: OpenRAGConfig, removed: str):
        if config.knowledge.embedding_provider == removed:
            fb = _first_configured_embedding_provider(config, removed)
            config.knowledge.embedding_provider = fb
            config.knowledge.embedding_model = _default_embedding_model(fb)

    def test_remove_ollama_falls_back_to_openai_empty_embedding(self):
        """OpenAI's embedding catalog isn't guessed — the admin must pick
        one the settings UI confirms is actually available."""
        config = _make_config(
            openai=True,
            ollama=True,
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
        )
        self._simulate_embedding_removal(config, "ollama")
        assert config.knowledge.embedding_provider == "openai"
        assert config.knowledge.embedding_model == ""

    def test_remove_openai_falls_back_to_ollama_empty_embedding(self):
        config = _make_config(
            openai=True,
            ollama=True,
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
        )
        self._simulate_embedding_removal(config, "openai")
        assert config.knowledge.embedding_provider == "ollama"
        assert config.knowledge.embedding_model == ""

    def test_remove_openai_falls_back_to_custom_provider_empty_embedding(self):
        config = _make_config(
            openai=True,
            ollama=True,
            custom=["gemini"],
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
        )
        self._simulate_embedding_removal(config, "openai")
        # Custom providers only qualify when the catalogue lists embedding models.
        assert config.knowledge.embedding_provider == "ollama"
        assert config.knowledge.embedding_model == ""

    def test_no_change_if_different_provider_removed(self):
        config = _make_config(
            openai=True,
            ollama=True,
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
        )
        self._simulate_embedding_removal(config, "ollama")
        assert config.knowledge.embedding_provider == "openai"
        assert config.knowledge.embedding_model == "text-embedding-3-small"