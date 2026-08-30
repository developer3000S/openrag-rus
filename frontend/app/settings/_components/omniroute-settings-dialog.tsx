import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { toast } from "sonner";
import {
  type AffectedEmbeddingModel,
  isEmbeddingProviderInUseError,
  useUpdateSettingsMutation,
} from "@/app/api/mutations/useUpdateSettingsMutation";
import { useGetSettingsQuery } from "@/app/api/queries/useGetSettingsQuery";
import type { ProviderHealthResponse } from "@/app/api/queries/useProviderHealthQuery";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/auth-context";
import ModelProviderDialogFooter from "./model-provider-dialog-footer";
import {
  OmniRouteSettingsForm,
  type OmniRouteSettingsFormData,
} from "./omniroute-settings-form";

const OmniRouteSettingsDialog = ({
  open,
  setOpen,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
}) => {
  const { isAuthenticated, isNoAuthMode } = useAuth();
  const queryClient = useQueryClient();
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
  const [affectedModels, setAffectedModels] = useState<
    AffectedEmbeddingModel[] | undefined
  >(undefined);
  const router = useRouter();

  const { data: settings = {} } = useGetSettingsQuery({
    enabled: isAuthenticated || isNoAuthMode,
  });

  const isOmniRouteConfigured =
    settings.providers?.omniroute?.configured === true;

  const canRemoveOmniRoute =
    isOmniRouteConfigured &&
    (settings.providers?.openai?.configured === true ||
      settings.providers?.ollama?.configured === true);

  const methods = useForm<OmniRouteSettingsFormData>({
    mode: "onSubmit",
    defaultValues: {
      endpoint: settings.providers?.omniroute?.endpoint ?? "",
      apiKey: "",
    },
  });

  useEffect(() => {
    if (open) {
      methods.reset({
        endpoint: settings.providers?.omniroute?.endpoint ?? "",
        apiKey: "",
      });
    }
  }, [open, methods.reset, settings.providers?.omniroute?.endpoint]);

  const { handleSubmit } = methods;

  const settingsMutation = useUpdateSettingsMutation({
    onSuccess: () => {
      // Update provider health cache to healthy since backend validated the setup
      const healthData: ProviderHealthResponse = {
        status: "healthy",
        message: "Provider is configured and working correctly",
        provider: "omniroute",
      };
      queryClient.setQueryData(["provider", "health"], healthData);

      toast.message("OMNIROUTE successfully configured", {
        description:
          "You can now use the language models served by this endpoint.",
        duration: Infinity,
        closeButton: true,
        action: {
          label: "Settings",
          onClick: () => {
            router.push("/settings/agent?focusLlmModel=true");
          },
        },
      });
      setOpen(false);
    },
  });

  const removeMutation = useUpdateSettingsMutation({
    onSuccess: () => {
      toast.success("OMNIROUTE configuration removed");
      setShowRemoveConfirm(false);
      setAffectedModels(undefined);
      setOpen(false);
    },
    onError: (err) => {
      if (isEmbeddingProviderInUseError(err)) {
        setAffectedModels(err.affectedModels);
      }
    },
  });

  const onSubmit = async (data: OmniRouteSettingsFormData) => {
    const credentials: Record<string, string> = {
      api_base: data.endpoint.trim(),
    };
    if (data.apiKey.trim()) {
      credentials.api_key = data.apiKey.trim();
    }
    settingsMutation.mutate({
      provider_credentials: { omniroute: credentials },
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setShowRemoveConfirm(false);
        setAffectedModels(undefined);
        setOpen(o);
      }}
    >
      <DialogContent autoFocus={false} className="max-w-2xl overflow-hidden">
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="grid min-w-0 gap-4"
          >
            <DialogHeader className="mb-2">
              <DialogTitle className="flex items-center gap-3">
                <div className="w-8 h-8 rounded flex items-center justify-center bg-[#7C3AED]">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="w-4 h-4 text-white"
                  >
                    <circle cx="6" cy="19" r="3" />
                    <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15" />
                    <circle cx="18" cy="5" r="3" />
                  </svg>
                </div>
                OMNIROUTE Setup
              </DialogTitle>
            </DialogHeader>

            <OmniRouteSettingsForm />

            <AnimatePresence mode="wait">
              {settingsMutation.isError && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <p className="rounded-lg border border-destructive p-4 min-w-0 [overflow-wrap:anywhere]">
                    {settingsMutation.error?.message}
                  </p>
                </motion.div>
              )}
              {removeMutation.isError &&
                !isEmbeddingProviderInUseError(removeMutation.error) && (
                  <motion.div
                    key="remove-error"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                  >
                    <p className="rounded-lg border border-destructive p-4 min-w-0 [overflow-wrap:anywhere]">
                      {removeMutation.error?.message}
                    </p>
                  </motion.div>
                )}
            </AnimatePresence>

            <ModelProviderDialogFooter
              showRemoveConfirm={showRemoveConfirm}
              onCancelRemove={() => {
                setShowRemoveConfirm(false);
                setAffectedModels(undefined);
              }}
              onConfirmRemove={() =>
                removeMutation.mutate({
                  remove_provider_config: "omniroute",
                  force_remove: !!affectedModels,
                })
              }
              isRemovePending={removeMutation.isPending}
              isConfigured={isOmniRouteConfigured}
              canRemove={canRemoveOmniRoute}
              providerKey="omniroute"
              removeDisabledTooltip="Configure another model provider before removing OMNIROUTE"
              onRequestRemove={() => setShowRemoveConfirm(true)}
              onCancel={() => setOpen(false)}
              isSavePending={settingsMutation.isPending}
              isValidating={false}
              affectedModels={affectedModels}
            />
          </form>
        </FormProvider>
      </DialogContent>
    </Dialog>
  );
};

export default OmniRouteSettingsDialog;
