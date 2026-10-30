import type { Asset } from "../types/asset";
import type { ImageAnalysis } from "../types/image";
import type {
  ConversationMessage,
  ConversationSession,
  CreativeRecommendation,
  ExecutionMode,
  PlanExecutionResult,
  PlanResponse,
  ProjectPreferences,
  SendMessageResponse,
  Workflow,
} from "../types/maya";
import type { OperationRecord } from "../types/operation";
import type { Project, ProjectCreate } from "../types/project";
import type { ToolDefinition, ToolExecutionResult } from "../types/tools";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error("Cannot reach the MayaChitram API. Check that the backend is running.");
  }

  if (response.status === 204) {
    return {} as T;
  }

  const payload = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) {
    const errorMsg = typeof payload.detail === "string" ? payload.detail : `Request failed (HTTP ${response.status}).`;
    throw new Error(errorMsg);
  }

  return payload as T;
}

// --- Direct Processing & Vision Analysis ---

export async function analyzeImage(file: File): Promise<ImageAnalysis> {
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/image/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the MayaChitram API. Check that the backend is running.");
  }
  const payload = await response.json().catch(() => ({})) as Partial<ImageAnalysis> & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? `Image analysis failed (HTTP ${response.status}).`);
  return payload as ImageAnalysis;
}

export async function processImageDirect(file: File, operation: string, params: Record<string, unknown>): Promise<Blob> {
  const form = new FormData();
  form.append("file", file);
  form.append("operation", operation);
  form.append("params", JSON.stringify(params));

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/image/process`, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the MayaChitram API. Check that the backend is running.");
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Operation failed." }));
    throw new Error(err.detail || `Operation failed with HTTP ${response.status}`);
  }

  return await response.blob();
}

// --- Projects ---

export async function listProjects(): Promise<Project[]> {
  return requestJson<Project[]>("/api/v1/projects");
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  return requestJson<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return requestJson<Project>(`/api/v1/projects/${projectId}`);
}

export async function deleteProject(projectId: string): Promise<void> {
  return requestJson<void>(`/api/v1/projects/${projectId}`, { method: "DELETE" });
}

// --- Assets ---

export async function listAssets(projectId: string): Promise<Asset[]> {
  return requestJson<Asset[]>(`/api/v1/projects/${projectId}/assets`);
}

export async function uploadAsset(projectId: string, file: File, parentAssetId?: string): Promise<Asset> {
  const form = new FormData();
  form.append("file", file);

  const query = parentAssetId ? `?parent_asset_id=${encodeURIComponent(parentAssetId)}` : "";
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/assets${query}`, {
      method: "POST",
      body: form,
    });
  } catch {
    throw new Error("Cannot reach the MayaChitram API. Check that the backend is running.");
  }

  const payload = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "Asset upload failed.");
  }
  return payload as unknown as Asset;
}

export async function deleteAsset(projectId: string, assetId: string): Promise<void> {
  return requestJson<void>(`/api/v1/projects/${projectId}/assets/${assetId}`, { method: "DELETE" });
}

export function getAssetFileUrl(projectId: string, assetId: string, download: boolean = false): string {
  const dl = download ? "?download=true" : "";
  return `${API_BASE_URL}/api/v1/projects/${projectId}/assets/${assetId}/file${dl}`;
}

// --- Operations History ---

export async function listOperations(projectId: string): Promise<OperationRecord[]> {
  return requestJson<OperationRecord[]>(`/api/v1/projects/${projectId}/operations`);
}

// --- Tools & Execution ---

export async function listTools(): Promise<ToolDefinition[]> {
  return requestJson<ToolDefinition[]>("/api/v1/tools");
}

export async function executeTool(
  projectId: string,
  toolName: string,
  parameters: Record<string, unknown>,
  inputAssetId: string,
): Promise<ToolExecutionResult> {
  return requestJson<ToolExecutionResult>("/api/v1/tools/execute", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      tool_name: toolName,
      parameters,
      input_asset_id: inputAssetId,
    }),
  });
}

// --- Maya Conversational Chat & Workflows ---

export async function chatWithMaya(
  projectId: string,
  message: string,
  targetAssetId?: string | null,
  conversationId?: string | null,
  executionMode: ExecutionMode = "execute",
): Promise<SendMessageResponse> {
  return requestJson<SendMessageResponse>("/api/v1/maya/chat", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      message,
      target_asset_id: targetAssetId,
      conversation_id: conversationId,
      execution_mode: executionMode,
    }),
  });
}

export async function listConversationMessages(conversationId: string): Promise<ConversationMessage[]> {
  return requestJson<ConversationMessage[]>(`/api/v1/maya/conversations/${conversationId}/messages`);
}

export async function listProjectConversations(projectId: string): Promise<ConversationSession[]> {
  return requestJson<ConversationSession[]>(`/api/v1/maya/projects/${projectId}/conversations`);
}

export async function createMayaPlan(
  projectId: string,
  userPrompt: string,
  targetAssetId?: string | null,
): Promise<PlanResponse> {
  return requestJson<PlanResponse>("/api/v1/maya/plan", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      user_prompt: userPrompt,
      target_asset_id: targetAssetId,
    }),
  });
}

export async function executeMayaPlan(
  projectId: string,
  plan: PlanResponse,
  targetAssetId?: string | null,
): Promise<PlanExecutionResult> {
  return requestJson<PlanExecutionResult>("/api/v1/maya/execute", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      target_asset_id: targetAssetId,
      plan,
      confirmed: true,
    }),
  });
}

export async function createWorkflow(
  projectId: string,
  userPrompt: string,
  targetAssetId?: string | null,
): Promise<Workflow> {
  return requestJson<Workflow>("/api/v1/maya/workflows", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      user_prompt: userPrompt,
      target_asset_id: targetAssetId,
    }),
  });
}

export async function getWorkflow(workflowId: string): Promise<Workflow> {
  return requestJson<Workflow>(`/api/v1/maya/workflows/${workflowId}`);
}

export async function listWorkflows(projectId: string): Promise<Workflow[]> {
  return requestJson<Workflow[]>(`/api/v1/maya/projects/${projectId}/workflows`);
}

export async function executeWorkflow(
  workflowId: string,
  defaultAssetId?: string | null,
  approvedTaskIds: string[] = [],
): Promise<Workflow> {
  return requestJson<Workflow>(`/api/v1/maya/workflows/${workflowId}/execute`, {
    method: "POST",
    body: JSON.stringify({
      default_asset_id: defaultAssetId,
      approved_task_ids: approvedTaskIds,
    }),
  });
}

export async function cancelWorkflow(workflowId: string): Promise<Workflow> {
  return requestJson<Workflow>(`/api/v1/maya/workflows/${workflowId}/cancel`, {
    method: "POST",
  });
}

export async function getRecommendations(
  projectId: string,
  assetId?: string | null,
): Promise<CreativeRecommendation[]> {
  const q = assetId ? `?asset_id=${encodeURIComponent(assetId)}` : "";
  return requestJson<CreativeRecommendation[]>(`/api/v1/maya/projects/${projectId}/recommendations${q}`);
}

export async function applyRecommendation(
  projectId: string,
  recommendationId: string,
  targetAssetId: string,
): Promise<Workflow> {
  return requestJson<Workflow>("/api/v1/maya/recommendations/apply", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      recommendation_id: recommendationId,
      target_asset_id: targetAssetId,
    }),
  });
}

export async function getProjectPreferences(projectId: string): Promise<ProjectPreferences> {
  return requestJson<ProjectPreferences>(`/api/v1/maya/projects/${projectId}/preferences`);
}

export async function updateProjectPreferences(
  projectId: string,
  preferences: ProjectPreferences,
): Promise<ProjectPreferences> {
  return requestJson<ProjectPreferences>(`/api/v1/maya/projects/${projectId}/preferences`, {
    method: "PUT",
    body: JSON.stringify(preferences),
  });
}
