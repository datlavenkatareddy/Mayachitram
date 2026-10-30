import type { Asset } from "./asset";
import type { ToolExecutionResult } from "./tools";

export type ExecutionMode = "assist" | "execute" | "autonomous";

export interface PlannedStep {
  step_id: number;
  tool_name: string;
  parameters: Record<string, unknown>;
  rationale: string;
  input_asset_id?: string | null;
  requires_confirmation?: boolean;
  dependencies?: number[];
}

export interface PlanResponse {
  project_id: string;
  target_asset_id?: string | null;
  user_prompt: string;
  summary: string;
  steps: PlannedStep[];
  missing_information?: string | null;
  can_execute: boolean;
  execution_mode?: ExecutionMode;
}

export interface StepExecutionSummary {
  step_id: number;
  tool_name: string;
  status: "succeeded" | "failed" | "skipped";
  result?: ToolExecutionResult | null;
  error?: string | null;
}

export interface PlanExecutionResult {
  project_id: string;
  status: "succeeded" | "partial" | "failed";
  steps: StepExecutionSummary[];
  final_asset?: Asset | null;
  summary_message: string;
}

export type WorkflowStatus =
  | "draft"
  | "awaiting_approval"
  | "ready"
  | "running"
  | "completed"
  | "partially_completed"
  | "failed"
  | "cancelled";

export type TaskStatus =
  | "pending"
  | "ready"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped"
  | "cancelled";

export interface WorkflowTask {
  task_id: string;
  tool_name: string;
  description: string;
  parameters: Record<string, unknown>;
  dependencies: string[];
  status: TaskStatus;
  input_asset_id?: string | null;
  output_asset_id?: string | null;
  requires_approval: boolean;
  retry_count: number;
  max_retries: number;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface Workflow {
  id: string;
  project_id: string;
  title: string;
  description: string;
  tasks: WorkflowTask[];
  status: WorkflowStatus;
  execution_mode: ExecutionMode;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  final_asset_ids: string[];
}

export interface CreativeRecommendation {
  id: string;
  category: string;
  title: string;
  description: string;
  trade_offs?: string | null;
  suggested_prompt: string;
  applicable_tools: string[];
  parameters: Record<string, unknown>;
}

export type MessageType = "text" | "plan" | "workflow" | "recommendation" | "clarification" | "execution_result";

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  message_type: MessageType;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ConversationSession {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface SendMessageResponse {
  conversation_id: string;
  user_message: ConversationMessage;
  assistant_message: ConversationMessage;
  workflow?: Workflow | null;
  recommendations: CreativeRecommendation[];
}

export interface ProjectPreferences {
  project_id: string;
  brand_colors: string[];
  brand_fonts: string[];
  preferred_aspect_ratios: string[];
  preferred_export_formats: string[];
  default_execution_mode: ExecutionMode;
  custom_instructions?: string | null;
}
