/**
 * Provider configuration for tests
 * Each provider has its models and test cases
 */

export interface ProviderConfig {
  provider: string; // Provider name as shown in UI
  language: string; // Language model name
  embedding: string; // Embedding model name
  testCase: {
    url: string;
    docName: string;
  };
  required?: boolean; // If true, test will fail if provider not configured
}

// OpenAI Configuration (Required)
export const OPENAI_CONFIG: ProviderConfig = {
  provider: "OpenAI",
  language: "gpt-5-mini",
  embedding: "text-embedding-ada-002",
  testCase: {
    url: "https://react.dev/reference/react/hooks",
    docName: "Built-in React Hooks – React",
  },
  required: true, // OpenAI is required
};

// Ollama Configuration (Optional)
export const OLLAMA_CONFIG: ProviderConfig = {
  provider: "Ollama",
  language: "qwen3:latest",
  embedding: "nomic-embed-text:latest",
  testCase: {
    url: "https://docs.python.org/3/library/functions.html",
    docName: "Built-in Functions — Python",
  },
};

// All provider configurations
export const PROVIDER_CONFIGS: ProviderConfig[] = [
  OPENAI_CONFIG,
  OLLAMA_CONFIG,
];

/**
 * Model transition sequences by provider
 * Used for model switching tests
 */
export interface ModelTransitionConfig {
  provider: string;
  languageSequence: string[];
  embeddingSequence: string[];
}

export const MODEL_TRANSITIONS: ModelTransitionConfig[] = [
  {
    provider: "OpenAI",
    languageSequence: ["gpt-4o", "gpt-4o-mini"],
    embeddingSequence: ["text-embedding-3-small", "text-embedding-3-large"],
  },
  {
    provider: "Ollama",
    languageSequence: ["qwen3:latest"],
    embeddingSequence: ["nomic-embed-text:latest", "qwen3-embedding:latest"],
  },
];
