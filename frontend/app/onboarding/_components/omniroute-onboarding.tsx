import type { Dispatch, SetStateAction } from "react";
import { useEffect, useState } from "react";
import OmnirouteLogo from "@/components/icons/omniroute-logo";
import { LabelInput } from "@/components/label-input";
import { LabelWrapper } from "@/components/label-wrapper";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useDebouncedValue } from "@/lib/debounce";
import type { OnboardingVariables } from "../../api/mutations/useOnboardingMutation";
import { useGetOmnirouteModelsQuery } from "../../api/queries/useGetModelsQuery";
import { useModelSelection } from "../_hooks/useModelSelection";
import { useUpdateSettings } from "../_hooks/useUpdateSettings";
import { ModelSelector } from "./model-selector";

export function OmnirouteOnboarding({
  setSettings,
  isEmbedding = false,
  hasEnvCredentials = false,
  alreadyConfigured = false,
  existingEndpoint,
}: {
  setSettings: Dispatch<SetStateAction<OnboardingVariables>>;
  isEmbedding?: boolean;
  hasEnvCredentials?: boolean;
  alreadyConfigured?: boolean;
  existingEndpoint?: string;
}) {
  const [endpoint, setEndpoint] = useState(
    alreadyConfigured ? undefined : existingEndpoint || "",
  );
  const [apiKey, setApiKey] = useState("");
  const [useEnv, setUseEnv] = useState(hasEnvCredentials && !alreadyConfigured);
  const debouncedEndpoint = useDebouncedValue(endpoint, 500);
  const debouncedApiKey = useDebouncedValue(apiKey, 500);

  const {
    data: modelsData,
    isLoading: isLoadingModels,
    error: modelsError,
  } = useGetOmnirouteModelsQuery(
    useEnv
      ? { useEnvCredentials: true }
      : debouncedEndpoint
        ? {
            endpoint: debouncedEndpoint,
            apiKey: debouncedApiKey,
            useEnvCredentials: false,
          }
        : undefined,
    { enabled: useEnv || !!debouncedEndpoint || alreadyConfigured },
  );

  const {
    languageModel,
    embeddingModel,
    setLanguageModel,
    setEmbeddingModel,
    languageModels,
    embeddingModels,
  } = useModelSelection(modelsData, isEmbedding);

  const handleUseEnvChange = (next: boolean) => {
    setUseEnv(next);
    if (next) {
      setApiKey("");
    }
  };

  useUpdateSettings(
    "omniroute",
    {
      endpoint: useEnv ? undefined : endpoint,
      apiKey: useEnv || alreadyConfigured ? undefined : apiKey,
      clearApiKey: useEnv,
      clearEndpoint: useEnv,
      languageModel,
      embeddingModel,
    },
    setSettings,
    isEmbedding,
  );

  const isConnecting = (useEnv || !!debouncedEndpoint) && isLoadingModels;
  const [connectingVisibleAfterDelay, setConnectingVisibleAfterDelay] =
    useState(false);
  useEffect(() => {
    if (!isConnecting) {
      return;
    }
    const timeoutId = setTimeout(() => {
      setConnectingVisibleAfterDelay(true);
    }, 500);
    return () => {
      clearTimeout(timeoutId);
      setConnectingVisibleAfterDelay(false);
    };
  }, [isConnecting]);
  const showConnecting = isConnecting && connectingVisibleAfterDelay;

  const hasConnectionError = (useEnv || debouncedEndpoint) && modelsError;

  return (
    <div className="space-y-4">
      {!alreadyConfigured && (
        <LabelWrapper
          label="Use environment OMNIROUTE credentials"
          id="use-env-credentials"
          description="Reuse the endpoint and API key from your environment config. Turn off to enter different values."
          flex
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <Switch
                  checked={useEnv}
                  data-testid="omniroute-use-env-switch"
                  onCheckedChange={handleUseEnvChange}
                  disabled={!hasEnvCredentials}
                />
              </div>
            </TooltipTrigger>
            {!hasEnvCredentials && (
              <TooltipContent>
                OMNIROUTE credentials not detected in the environment.
              </TooltipContent>
            )}
          </Tooltip>
        </LabelWrapper>
      )}
      {(!useEnv || alreadyConfigured) && (
        <>
          <div className="space-y-1">
            <LabelInput
              label="OMNIROUTE endpoint"
              helperText="OpenAI-compatible base URL of your OMNIROUTE deployment"
              id="omniroute-endpoint"
              type="text"
              placeholder={
                alreadyConfigured
                  ? "https://••••••••••••••••••••"
                  : "https://<host>/api/v1"
              }
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              disabled={alreadyConfigured}
            />
            {alreadyConfigured && (
              <p className="text-mmd text-muted-foreground">
                Reusing endpoint from model provider selection.
              </p>
            )}
          </div>
          {(!alreadyConfigured || !useEnv) && (
            <div className="space-y-1">
              <LabelInput
                label="OMNIROUTE API key"
                helperText="The API key for your OMNIROUTE account"
                id="omniroute-api-key"
                type="password"
                placeholder={
                  alreadyConfigured
                    ? "sk-•••••••••••••••••••••••••••••••••••••••••"
                    : "sk-..."
                }
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={alreadyConfigured}
              />
            </div>
          )}
        </>
      )}
      {showConnecting && (
        <p className="text-mmd text-muted-foreground">
          Connecting to OMNIROUTE endpoint...
        </p>
      )}
      {hasConnectionError && (
        <p className="text-mmd text-accent-amber-foreground">
          {modelsError.message}
        </p>
      )}
      {isEmbedding && setEmbeddingModel && (
        <LabelWrapper
          label="Embedding model"
          helperText="Model used for knowledge ingest and retrieval"
          id="omniroute-embedding-model"
          required={true}
        >
          <ModelSelector
            options={embeddingModels}
            data-testid="omniroute-embedding-model-selector"
            icon={<OmnirouteLogo className="w-4 h-4" />}
            noOptionsPlaceholder={
              isLoadingModels
                ? "Loading models..."
                : "No embedding models detected. Configure an embedding model on the endpoint to continue."
            }
            value={embeddingModel}
            onValueChange={setEmbeddingModel}
          />
        </LabelWrapper>
      )}
      {!isEmbedding && setLanguageModel && (
        <LabelWrapper
          label="Language model"
          helperText="Model used for chat"
          id="omniroute-language-model"
          required={true}
        >
          <ModelSelector
            options={languageModels}
            data-testid="omniroute-language-model-selector"
            icon={<OmnirouteLogo className="w-4 h-4" />}
            noOptionsPlaceholder={
              isLoadingModels
                ? "Loading models..."
                : "No language models detected. Configure a language model on the endpoint to continue."
            }
            value={languageModel}
            onValueChange={setLanguageModel}
          />
        </LabelWrapper>
      )}
    </div>
  );
}
