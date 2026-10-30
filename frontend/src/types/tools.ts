import type { Asset } from "./asset";

export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  is_destructive: boolean;
  parameters_schema: Record<string, unknown>;
  params_class_name: string;
}

export interface ToolExecutionResult {
  tool_name: string;
  status: "succeeded" | "failed";
  operation_id: string;
  output_asset?: Asset | null;
  output_metadata?: Record<string, unknown> | null;
  message: string;
  error?: string | null;
}
