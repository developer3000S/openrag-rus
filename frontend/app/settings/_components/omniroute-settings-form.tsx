import { useFormContext } from "react-hook-form";
import { LabelWrapper } from "@/components/label-wrapper";
import { Input } from "@/components/ui/input";

export interface OmniRouteSettingsFormData {
  endpoint: string;
  apiKey: string;
}

export function OmniRouteSettingsForm() {
  const {
    register,
    formState: { errors },
  } = useFormContext<OmniRouteSettingsFormData>();

  return (
    <div className="min-w-0 space-y-4">
      <div className="min-w-0 space-y-2">
        <LabelWrapper
          label="API endpoint"
          helperText="OpenAI-compatible base URL, e.g. https://host/api/v1"
          required
          id="omniroute-endpoint"
        >
          <Input
            {...register("endpoint", {
              required: "API endpoint is required",
            })}
            className={errors.endpoint ? "!border-destructive" : ""}
            id="omniroute-endpoint"
            type="text"
            autoComplete="off"
            placeholder="https://.../api/v1"
          />
        </LabelWrapper>
        {errors.endpoint && (
          <p
            data-testid="provider-connection-error"
            className="text-sm text-destructive min-w-0 [overflow-wrap:anywhere]"
          >
            {errors.endpoint.message}
          </p>
        )}
      </div>
      <div className="min-w-0 space-y-2">
        <LabelWrapper
          label="API key"
          helperText="The API key for your OMNIROUTE account"
          id="omniroute-api-key"
        >
          <Input
            {...register("apiKey")}
            className={errors.apiKey ? "!border-destructive" : ""}
            id="omniroute-api-key"
            type="password"
            autoComplete="new-password"
            placeholder="sk-..."
          />
        </LabelWrapper>
        {errors.apiKey && (
          <p
            data-testid="provider-connection-error"
            className="text-sm text-destructive min-w-0 [overflow-wrap:anywhere]"
          >
            {errors.apiKey.message}
          </p>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        Model {"free-stack"} is made available by the endpoint; configure it in
        the Settings page after saving.
      </p>
    </div>
  );
}
