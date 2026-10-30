export interface OperationRecord {
  id: string;
  project_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  input_asset_ids: string[];
  output_asset_ids: string[];
  status: "pending" | "running" | "succeeded" | "failed";
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
}
