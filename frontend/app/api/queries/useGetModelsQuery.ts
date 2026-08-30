import {
  type UseQueryOptions,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { CatalogModel } from "@/app/settings/_helpers/catalog-models";
import { formatProviderErrorMessage } from "@/lib/chat-stream-errors";
import { useGetSettingsQuery } from "./useGetSettingsQuery";

export interface ModelOption {
  value: string;
  label: string;
  default?: boolean;
  supports_images?: boolean;
}

export interface ModelsResponse {
  language_models: ModelOption[];
  embedding_models: ModelOption[];
}

export interface OpenAIModelsParams {
  apiKey?: string;
  /** When true, omit api_key so the backend uses configured/env credentials. */
  useEnvKey?: boolean;
}

export interface OllamaModelsParams {
  endpoint?: string;
}

async function throwModelsFetchError(
  response: Response,
  fallback: string,
): Promise<never> {
  const data = await response.json().catch(() => ({}));
  const raw =
    data && typeof data === "object" && typeof data.error === "string"
      ? data.error
      : fallback;
  throw new Error(formatProviderErrorMessage(raw));
}

export const useGetOpenAIModelsQuery = (
  params?: OpenAIModelsParams,
  options?: Omit<UseQueryOptions<ModelsResponse>, "queryKey" | "queryFn">,
) => {
  const queryClient = useQueryClient();
  const useEnvKey = !!params?.useEnvKey;
  const apiKey = useEnvKey ? "" : params?.apiKey || "";

  return useQuery(
    {
      queryKey: ["models", "openai", useEnvKey, apiKey] as const,
      queryFn: async (): Promise<ModelsResponse> => {
        const body: { api_key?: string } = {};
        if (!useEnvKey && apiKey) {
          body.api_key = apiKey;
        }

        const response = await fetch("/api/models/openai", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (response.ok) {
          return (await response.json()) as ModelsResponse;
        }
        return throwModelsFetchError(response, "Failed to fetch OpenAI models");
      },
      staleTime: 0,
      gcTime: 0,
      retry: false,
      ...options,
    },
    queryClient,
  );
};

export const useGetOllamaModelsQuery = (
  params?: OllamaModelsParams,
  options?: Omit<UseQueryOptions<ModelsResponse>, "queryKey" | "queryFn">,
) => {
  const queryClient = useQueryClient();
  const endpoint = params?.endpoint || "";

  return useQuery(
    {
      queryKey: ["models", "ollama", endpoint] as const,
      queryFn: async (): Promise<ModelsResponse> => {
        const url = new URL("/api/models/ollama", window.location.origin);
        if (endpoint) {
          url.searchParams.set("endpoint", endpoint);
        }

        const response = await fetch(url.toString());
        if (response.ok) {
          return (await response.json()) as ModelsResponse;
        }
        return throwModelsFetchError(response, "Failed to fetch Ollama models");
      },
      staleTime: 0,
      gcTime: 0,
      retry: false,
      ...options,
    },
    queryClient,
  );
};

export interface CatalogCredentialField {
  key: string;
  label: string;
  placeholder?: string | null;
  tooltip?: string | null;
  required: boolean;
  field_type: string;
  options?: unknown;
  default_value?: unknown;
}

export interface CatalogProvider {
  key: string;
  name: string;
  credential_fields: CatalogCredentialField[];
  model_placeholder: string | null;
  models: CatalogModel[];
  embedding_models: CatalogModel[];
}

export interface ModelCatalogResponse {
  providers: CatalogProvider[];
}

/**
 * LiteLLM's bundled model list, grouped by provider. Static for the tab's
 * lifetime — same as openrag-next's `/agent/model-catalog` fetch.
 */
export const useGetModelCatalogQuery = (
  options?: Omit<UseQueryOptions<ModelCatalogResponse>, "queryKey" | "queryFn">,
) => {
  const queryClient = useQueryClient();

  return useQuery(
    {
      queryKey: ["models", "catalog"] as const,
      queryFn: async (): Promise<ModelCatalogResponse> => {
        const response = await fetch("/api/models/catalog");
        if (response.ok) {
          return (await response.json()) as ModelCatalogResponse;
        }
        return throwModelsFetchError(
          response,
          "Failed to fetch the model catalogue",
        );
      },
      staleTime: Number.POSITIVE_INFINITY,
      gcTime: Number.POSITIVE_INFINITY,
      refetchOnWindowFocus: false,
      retry: false,
      ...options,
    },
    queryClient,
  );
};
