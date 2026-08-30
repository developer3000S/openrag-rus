import type { Dispatch, SetStateAction } from "react";
import { useEffect } from "react";
import type { OnboardingVariables } from "../../api/mutations/useOnboardingMutation";

interface ConfigValues {
  apiKey?: string;
  /** When true, clear the provider key (e.g. environment-key mode). */
  clearApiKey?: boolean;
  endpoint?: string;
  /** When true, clear the provider endpoint (e.g. environment-credentials mode). */
  clearEndpoint?: boolean;
  languageModel?: string;
  embeddingModel?: string;
}

function resolveApiKey(
  apiKey: string | undefined,
  clearApiKey: boolean | undefined,
  previous: string | undefined,
): string {
  if (clearApiKey) {
    return "";
  }
  // Explicit empty clears a typed key; omit (undefined) to reuse previous.
  if (apiKey !== undefined) {
    return apiKey;
  }
  return previous || "";
}

function resolveEndpoint(
  endpoint: string | undefined,
  clearEndpoint: boolean | undefined,
  previous: string | undefined,
): string {
  if (clearEndpoint) {
    return "";
  }
  if (endpoint !== undefined) {
    return endpoint;
  }
  return previous || "";
}

export function useUpdateSettings(
  provider: string,
  config: ConfigValues,
  setSettings: Dispatch<SetStateAction<OnboardingVariables>>,
  isEmbedding?: boolean,
) {
  useEffect(() => {
    setSettings((prev) => {
      const updatedSettings: OnboardingVariables = {
        ...prev,
        embedding_model: config.embeddingModel || prev.embedding_model || "",
        llm_model: config.languageModel || prev.llm_model || "",
      };

      // Set provider field based on whether this is for embedding or LLM
      if (isEmbedding) {
        updatedSettings.embedding_provider = provider;
      } else {
        updatedSettings.llm_provider = provider;
      }

      // Map provider-specific API keys. undefined preserves prior credentials;
      // "" or clearApiKey clears; a non-empty string replaces.
      if (provider === "openai") {
        updatedSettings.openai_api_key = resolveApiKey(
          config.apiKey,
          config.clearApiKey,
          prev.openai_api_key,
        );
      }

      if (provider === "omniroute") {
        updatedSettings.omniroute_api_key = resolveApiKey(
          config.apiKey,
          config.clearApiKey,
          prev.omniroute_api_key,
        );
        updatedSettings.omniroute_endpoint = resolveEndpoint(
          config.endpoint,
          config.clearEndpoint,
          prev.omniroute_endpoint,
        );
      }

      // Map provider-specific endpoints
      if (config.endpoint && provider === "ollama") {
        updatedSettings.ollama_endpoint = config.endpoint;
      }

      return updatedSettings;
    });
  }, [
    provider,
    config.apiKey,
    config.clearApiKey,
    config.endpoint,
    config.clearEndpoint,
    config.languageModel,
    config.embeddingModel,
    setSettings,
    isEmbedding,
  ]);
}
