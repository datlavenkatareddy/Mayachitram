from typing import Any, Literal

from pydantic import BaseModel, Field

from mayachitram.projects.models import Asset

# --- Execution & Safety Modes ---
ExecutionMode = Literal["assist", "execute", "autonomous"]

# --- Tool Execution Results ---
class ToolExecutionResult(BaseModel):
    tool_name: str
    status: Literal["succeeded", "failed"]
    operation_id: str
    output_asset: Asset | None = None
    output_metadata: dict[str, Any] | None = None
    message: str
    error: str | None = None


# --- Planned Step (Single tool invocation in a plan) ---
class PlannedStep(BaseModel):
    step_id: int
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    input_asset_id: str | None = None
    requires_confirmation: bool = False
    dependencies: list[int] = Field(default_factory=list)
    is_branch: bool = False


# --- Plan Response ---
class PlanResponse(BaseModel):
    project_id: str
    target_asset_id: str | None = None
    user_prompt: str
    summary: str
    steps: list[PlannedStep] = Field(default_factory=list)
    missing_information: str | None = None
    can_execute: bool = True
    execution_mode: ExecutionMode = "execute"


# --- Execute Plan Request ---
class ExecutePlanRequest(BaseModel):
    project_id: str
    target_asset_id: str | None = None
    plan: PlanResponse
    confirmed: bool = True
    execution_mode: ExecutionMode = "execute"


# --- Step Execution Summary ---
class StepExecutionSummary(BaseModel):
    step_id: int
    tool_name: str
    status: Literal["succeeded", "failed", "skipped"]
    result: ToolExecutionResult | None = None
    error: str | None = None


# --- Plan Execution Result ---
class PlanExecutionResult(BaseModel):
    project_id: str
    status: Literal["succeeded", "partial", "failed"]
    steps: list[StepExecutionSummary]
    final_asset: Asset | None = None
    summary_message: str


# --- Multi-Step Workflow Model (DAG Orchestrator) ---
WorkflowStatus = Literal[
    "draft",
    "awaiting_approval",
    "ready",
    "running",
    "completed",
    "partially_completed",
    "failed",
    "cancelled",
]

TaskStatus = Literal["pending", "ready", "running", "succeeded", "failed", "skipped", "cancelled"]


class WorkflowTask(BaseModel):
    task_id: str
    tool_name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = "pending"
    input_asset_id: str | None = None
    output_asset_id: str | None = None
    requires_approval: bool = False
    retry_count: int = 0
    max_retries: int = 1
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class Workflow(BaseModel):
    id: str
    project_id: str
    title: str
    description: str = ""
    tasks: list[WorkflowTask] = Field(default_factory=list)
    status: WorkflowStatus = "draft"
    execution_mode: ExecutionMode = "execute"
    created_at: str
    updated_at: str
    completed_at: str | None = None
    final_asset_ids: list[str] = Field(default_factory=list)


# --- Creative Recommendations ---
class CreativeRecommendation(BaseModel):
    id: str
    category: str
    title: str
    description: str
    trade_offs: str | None = None
    suggested_prompt: str
    applicable_tools: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


# --- Quality Validation ---
class QualityValidationCheck(BaseModel):
    name: str
    passed: bool
    expected: Any
    actual: Any
    details: str


class QualityValidationReport(BaseModel):
    asset_id: str
    passed: bool
    checks: list[QualityValidationCheck] = Field(default_factory=list)
    summary: str


# --- Conversational Messages & Sessions ---
MessageType = Literal["text", "plan", "workflow", "recommendation", "clarification", "execution_result"]


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    message_type: MessageType = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ConversationSession(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ConversationMessage] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    project_id: str
    message: str = Field(min_length=1, max_length=2000)
    target_asset_id: str | None = None
    conversation_id: str | None = None
    execution_mode: ExecutionMode = "execute"


class SendMessageResponse(BaseModel):
    conversation_id: str
    user_message: ConversationMessage
    assistant_message: ConversationMessage
    workflow: Workflow | None = None
    recommendations: list[CreativeRecommendation] = Field(default_factory=list)


# --- Project Creative Preferences & Brand Memory ---
class ProjectPreferences(BaseModel):
    project_id: str
    brand_colors: list[str] = Field(default_factory=list)
    brand_fonts: list[str] = Field(default_factory=list)
    preferred_aspect_ratios: list[str] = Field(default_factory=list)
    preferred_export_formats: list[str] = Field(default_factory=list)
    default_execution_mode: ExecutionMode = "execute"
    custom_instructions: str | None = None
