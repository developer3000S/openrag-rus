import asyncio
import re

import httpx

from api.provider_validation import (
    _extract_error_details,
    _http_request_with_retry,
    format_provider_error_message,
)
from config.embedding_constants import OPENAI_DEFAULT_EMBEDDING_MODEL, OPENAI_EMBEDDING_MODEL_PREFIX
from config.model_constants import (
    OLLAMA_DEFAULT_LANGUAGE_MODEL_PATTERN,
    OPENAI_DEFAULT_LANGUAGE_MODEL,
)
from utils.container_utils import transform_localhost_url
from utils.logging_config import get_logger

logger = get_logger(__name__)


# OpenAI /v1/models is a flat inventory. These IDs are real products but not
# usable as OpenRAG agent LLMs (wrong modality / API surface).
_OPENAI_NON_CHAT_PREFIXES = (
    "whisper",
    "dall-e",
    "tts-",
    "davinci",
    "babbage",
    "curie",
    "sora-",
    "computer-use",
    "omni-moderation",
    "text-moderation",
    "gpt-image",
    "gpt-audio",
    "gpt-realtime",
    "chatgpt-image",
)
_OPENAI_REASONING_MODEL_RE = re.compile(r"^o\d")


def is_openai_embedding_model(model_id: str) -> bool:
    """True if the OpenAI model ID is an embedding model."""
    return OPENAI_EMBEDDING_MODEL_PREFIX in model_id or "text-similarity-" in model_id


def is_openai_non_chat_model(model_id: str) -> bool:
    """True if the ID is a known non-chat OpenAI product (junk for LLM/embedding pickers)."""
    lower = model_id.lower()
    if "-moderation" in lower:
        return True
    # Mid-string modality markers (e.g. gpt-4o-realtime-preview, gpt-4o-mini-tts)
    # that prefix checks alone miss.
    if any(marker in lower for marker in ("-realtime", "-transcribe", "-tts")):
        return True
    return any(lower.startswith(prefix) for prefix in _OPENAI_NON_CHAT_PREFIXES)


def is_openai_language_model(model_id: str) -> bool:
    """True if the OpenAI model ID is usable as a chat/agent language model.

    Classifies the live /v1/models inventory: embeddings and non-chat junk are
    excluded; gpt-*, chatgpt-*, ft:gpt-* fine-tunes, and o<digit>* reasoning
    models are included so new chat families appear without a curated allowlist.
    """
    if not model_id or is_openai_embedding_model(model_id) or is_openai_non_chat_model(model_id):
        return False
    if model_id.startswith(("gpt-", "chatgpt-", "ft:gpt-")):
        return True
    return bool(_OPENAI_REASONING_MODEL_RE.match(model_id))


def resolve_preferred_model(preferred: str, live_models: list[dict]) -> str:
    """Pick a model from a live provider list.

    Prefer ``preferred`` when it appears in the live list; otherwise the entry
    marked ``default``, otherwise the first live model. If the live list is
    empty, return ``preferred`` (may be empty).
    """
    if not live_models:
        return preferred or ""
    values = {m.get("value") for m in live_models}
    if preferred and preferred in values:
        return preferred
    for model in live_models:
        if model.get("default"):
            return model.get("value") or preferred or ""
    return live_models[0].get("value") or preferred or ""


class UnknownEmbeddingProvider(Exception):
    """Raised when a model's provider can't be resolved and the caller asked
    for strict routing. Lets callers fail fast instead of dispatching an
    unroutable request into LiteLLM's retry loop."""

    def __init__(self, model_name: str):
        super().__init__(f"No configured provider can serve embedding model '{model_name}'")
        self.model_name = model_name


class ModelsService:
    """Service for fetching available models from different AI providers and managing a model registry."""

    # Registry for caching model-to-provider mapping
    _model_provider_registry: dict[str, str] = {}
    _registry_lock = asyncio.Lock()

    def __init__(self):
        self.session_manager = None

    # Helper to add models to registry
    def add_models(self, models_res, provider, new_registry):
        if not models_res:
            return
        for m in models_res.get("language_models", []):
            new_registry[m["value"]] = provider
        for m in models_res.get("embedding_models", []):
            new_registry[m["value"]] = provider

    async def add_models_to_registry(self, models_res, provider):
        async with self._registry_lock:
            try:
                new_registry = ModelsService._model_provider_registry.copy()
                self.add_models(models_res, provider, new_registry)
                ModelsService._model_provider_registry = new_registry
            except Exception as e:
                logger.error(f"Error adding models to registry: {str(e)}")

    async def update_model_registry(self):
        """Fetch all models from all providers and update the internal registry.

        This method calls provider-specific methods to get the list of available
        models and stores the mapping in a registry for fast lookup.
        """
        from config.config_manager import config_manager

        async with self._registry_lock:
            try:
                config = config_manager.get_config()
                new_registry = {}

                # Fetch from providers

                # OpenAI
                if config.providers.openai.api_key:
                    try:
                        res = await self.get_openai_models(
                            config.providers.openai.api_key, update_index=False
                        )
                        self.add_models(res, "openai", new_registry)
                    except Exception as e:
                        logger.debug(f"Could not fetch OpenAI models for registry: {str(e)}")

                # Ollama
                if config.providers.ollama.endpoint:
                    try:
                        res = await self.get_ollama_models(
                            config.providers.ollama.endpoint, update_index=False
                        )
                        self.add_models(res, "ollama", new_registry)
                    except Exception as e:
                        logger.debug(f"Could not fetch Ollama models for registry: {str(e)}")

                from services.model_catalog import catalog

                catalog_by_provider = {entry["key"]: entry for entry in catalog()["providers"]}
                for provider, provider_config in config.providers.custom.items():
                    if not provider_config.configured:
                        continue
                    entry = catalog_by_provider.get(provider)
                    if entry is None:
                        continue
                    self.add_models(
                        {
                            "language_models": [
                                {"value": model["model"]} for model in entry["models"]
                            ],
                            "embedding_models": [
                                {"value": model["model"]} for model in entry["embedding_models"]
                            ],
                        },
                        provider,
                        new_registry,
                    )

                ModelsService._model_provider_registry = new_registry
                logger.info(
                    f"Model registry updated: {len(ModelsService._model_provider_registry)} models registered"
                )

            except Exception as e:
                logger.error(f"Error updating model registry: {str(e)}")

    async def get_litellm_model_name(
        self,
        model_name: str,
        provider: str | None = None,
        strict: bool = False,
    ) -> str:
        """Resolve ``model_name`` to a LiteLLM-routable string.

        When ``strict`` is True and the provider can't be resolved, raise
        ``UnknownEmbeddingProvider`` so the caller can short-circuit instead of
        letting LiteLLM burn a retry loop on an unroutable name. Non-strict
        callers (e.g. ingestion) keep the original best-effort behavior of
        returning the raw name.
        """

        if not model_name:
            return ""

        # Skip formatting if already has a known LiteLLM provider prefix.
        if "/" in model_name:
            from services.model_catalog import is_known_provider

            prefix = model_name.split("/", 1)[0].lower()
            if is_known_provider(prefix):
                return model_name

        # Check if provider is explicitly given and not "openai"
        provider_lower = provider.lower() if provider else None

        if provider_lower is None:
            # Try looking in registry
            provider_lower = ModelsService._model_provider_registry.get(model_name)
            if provider_lower is None:
                await self.update_model_registry()
                provider_lower = ModelsService._model_provider_registry.get(model_name)

        if provider_lower is None:
            if strict:
                # Caller wants fail-fast: the model isn't claimed by any
                # currently-configured provider. Typical trigger: corpus was
                # embedded with a model whose provider has since been removed.
                raise UnknownEmbeddingProvider(model_name)
            logger.warning(
                "Could not determine provider for model; using model name as-is",
                model_name=model_name,
            )
            return model_name  # OpenAI-compatible models work without a prefix

        return f"{provider_lower}/{model_name}" if provider_lower != "openai" else model_name

    def _openai_supports_images(self, model_id: str) -> bool:
        model_lower = model_id.lower()
        if "text-embedding" in model_lower:
            return False
        if "o1-mini" in model_lower or "o1-preview" in model_lower:
            return False
        return any(
            x in model_lower for x in ["gpt-4o", "gpt-5", "vision", "o3", "o4", "gpt-4-turbo", "o1"]
        )

    def _ollama_supports_images(self, json_data: dict) -> bool:
        capabilities = json_data.get("capabilities", [])
        if "vision" in capabilities:
            return True
        model_info = json_data.get("model_info", {})
        if any("vision" in key.lower() or "projector" in key.lower() for key in model_info.keys()):
            return True
        details = json_data.get("details", {})
        families = details.get("families", []) or []
        if any("clip" in str(fam).lower() or "vision" in str(fam).lower() for fam in families):
            return True
        return False

    async def get_openai_models(
        self, api_key: str, update_index: bool = True
    ) -> dict[str, list[dict[str, str]]]:
        """Fetch available models from OpenAI API with lightweight validation"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Lightweight validation: check if API key is valid with retry logic
            response = await _http_request_with_retry(
                "GET",
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])

                # Classify live inventory into embedding vs chat; drop non-chat junk.
                language_models = []
                embedding_models = []

                for model in models:
                    model_id = model.get("id", "")
                    if not model_id:
                        continue

                    if is_openai_embedding_model(model_id):
                        embedding_models.append(
                            {
                                "value": model_id,
                                "label": model_id,
                                "default": False,
                            }
                        )
                    elif is_openai_language_model(model_id):
                        language_models.append(
                            {
                                "value": model_id,
                                "label": model_id,
                                "default": False,
                                "supports_images": self._openai_supports_images(model_id),
                            }
                        )

                chosen_language = resolve_preferred_model(
                    OPENAI_DEFAULT_LANGUAGE_MODEL, language_models
                )
                for entry in language_models:
                    entry["default"] = entry["value"] == chosen_language

                chosen_embedding = resolve_preferred_model(
                    OPENAI_DEFAULT_EMBEDDING_MODEL, embedding_models
                )
                for entry in embedding_models:
                    entry["default"] = entry["value"] == chosen_embedding

                # Sort by name and ensure defaults are first
                language_models.sort(key=lambda x: (not x.get("default", False), x["value"]))
                embedding_models.sort(key=lambda x: (not x.get("default", False), x["value"]))

                if not language_models:
                    logger.warning("OpenAI API key is valid but no language models were found.")
                if not embedding_models:
                    logger.warning(
                        "OpenAI API key is valid but no embedding models were found matching prefix '%s'.",
                        OPENAI_EMBEDDING_MODEL_PREFIX,
                    )

                logger.info("OpenAI API key validated successfully without consuming credits")

                result = {
                    "language_models": language_models,
                    "embedding_models": embedding_models,
                }

                if update_index:
                    await self.add_models_to_registry(result, "openai")

                return result
            else:
                logger.error(f"Failed to fetch OpenAI models: {response.status_code}")
                raise Exception(format_provider_error_message(_extract_error_details(response)))

        except Exception as e:
            logger.error(f"Error fetching OpenAI models: {str(e)}")
            raise

    async def get_ollama_models(
        self, endpoint: str = None, update_index: bool = True
    ) -> dict[str, list[dict[str, str]]]:
        """Fetch available models from Ollama API with tool calling capabilities for language models"""
        try:
            ollama_url = transform_localhost_url(endpoint)

            # API endpoints
            tags_url = f"{ollama_url}/api/tags"
            show_url = f"{ollama_url}/api/show"

            # Constants for JSON parsing
            JSON_MODELS_KEY = "models"
            JSON_NAME_KEY = "name"
            JSON_CAPABILITIES_KEY = "capabilities"
            DESIRED_CAPABILITY = "completion"
            TOOL_CALLING_CAPABILITY = "tools"

            async with httpx.AsyncClient() as client:
                # Fetch available models
                tags_response = await client.get(tags_url, timeout=10.0)
                tags_response.raise_for_status()
                models_data = tags_response.json()

                logger.debug(f"Available models: {models_data}")

                # Filter models based on capabilities
                language_models = []
                embedding_models = []

                models = models_data.get(JSON_MODELS_KEY, [])

                for model in models:
                    model_name = model.get(JSON_NAME_KEY, "")

                    if not model_name:
                        continue

                    logger.debug(f"Checking model: {model_name}")

                    # Check model capabilities
                    payload = {"model": model_name}
                    try:
                        show_response = await client.post(show_url, json=payload, timeout=10.0)
                        show_response.raise_for_status()
                        json_data = show_response.json()

                        capabilities = json_data.get(JSON_CAPABILITIES_KEY, [])
                        logger.debug(f"Model: {model_name}, Capabilities: {capabilities}")

                        # Check if model has embedding capability
                        has_embedding = "embedding" in capabilities
                        # Check if model has required capabilities for language models
                        has_completion = DESIRED_CAPABILITY in capabilities
                        has_tools = TOOL_CALLING_CAPABILITY in capabilities

                        if has_embedding:
                            # Embedding models have embedding capability
                            embedding_models.append(
                                {
                                    "value": model_name,
                                    "label": model_name,
                                    "default": "nomic-embed-text" in model_name.lower(),
                                }
                            )
                        if has_completion and has_tools:
                            # Language models need both completion and tool calling
                            language_models.append(
                                {
                                    "value": model_name,
                                    "label": model_name,
                                    "default": OLLAMA_DEFAULT_LANGUAGE_MODEL_PATTERN
                                    in model_name.lower(),
                                    "supports_images": self._ollama_supports_images(json_data),
                                }
                            )
                        if not capabilities and not has_embedding:
                            # Older Ollama versions don't return a capabilities field.
                            # Register the model as a potential embedding model so
                            # search can route it through Ollama. If it can't actually
                            # embed, the LiteLLM call will fail and be caught gracefully.
                            embedding_models.append(
                                {
                                    "value": model_name,
                                    "label": model_name,
                                    "default": "nomic-embed-text" in model_name.lower(),
                                }
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to check capabilities for model {model_name}: {str(e)}"
                        )
                        continue

                # Remove duplicates and sort
                language_models = list({m["value"]: m for m in language_models}.values())
                embedding_models = list({m["value"]: m for m in embedding_models}.values())

                language_models.sort(key=lambda x: (not x.get("default", False), x["value"]))
                embedding_models.sort(key=lambda x: x["value"])

                logger.info(
                    f"Found {len(language_models)} language models with tool calling and {len(embedding_models)} embedding models"
                )

                result = {
                    "language_models": language_models,
                    "embedding_models": embedding_models,
                }

                if update_index:
                    await self.add_models_to_registry(result, "ollama")

                return result

        except Exception as e:
            logger.error(f"Error fetching Ollama models: {str(e)}")
            raise

