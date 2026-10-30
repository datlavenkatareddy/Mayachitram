from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mayachitram.api.v1.dependencies import (
    get_execution_service,
    get_maya_planner,
    get_maya_repository,
    get_project_service,
    get_recommendations_service,
    get_workflow_orchestrator,
)
from mayachitram.maya.execution.service import ExecutionService
from mayachitram.maya.execution.workflow import WorkflowOrchestrator
from mayachitram.maya.planner.recommendations import CreativeRecommendationService
from mayachitram.maya.planner.service import MayaPlanner
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import (
    ConversationMessage,
    ConversationSession,
    CreativeRecommendation,
    ExecutePlanRequest,
    PlanExecutionResult,
    PlanResponse,
    ProjectPreferences,
    SendMessageRequest,
    SendMessageResponse,
    Workflow,
)
from mayachitram.projects.service import ProjectService

router = APIRouter()


class CreatePlanRequest(BaseModel):
    project_id: str
    user_prompt: str = Field(min_length=2, max_length=1000)
    target_asset_id: str | None = None


class ExecuteWorkflowRequest(BaseModel):
    default_asset_id: str | None = None
    approved_task_ids: list[str] = Field(default_factory=list)
    approve_all: bool = True


class ApplyRecommendationRequest(BaseModel):
    project_id: str
    recommendation_id: str
    target_asset_id: str


# --- Conversational Endpoints ---

@router.post("/chat", response_model=SendMessageResponse)
async def chat_with_maya(
    req: SendMessageRequest,
    planner: MayaPlanner = Depends(get_maya_planner),
) -> SendMessageResponse:
    """Send natural-language message to Maya; handles multi-turn conversation and workflow planning."""
    return await planner.handle_chat_message(req)


@router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessage])
def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> list[ConversationMessage]:
    return maya_repo.get_messages(conversation_id, limit=limit)


@router.get("/projects/{project_id}/conversations", response_model=list[ConversationSession])
def list_project_conversations(
    project_id: str,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> list[ConversationSession]:
    return maya_repo.list_conversations(project_id)


# --- Legacy Linear Planning & Execution (Preserved for backward compatibility) ---

@router.post("/plan", response_model=PlanResponse)
async def create_plan(
    req: CreatePlanRequest,
    planner: MayaPlanner = Depends(get_maya_planner),
) -> PlanResponse:
    return await planner.plan(
        project_id=req.project_id,
        user_prompt=req.user_prompt,
        target_asset_id=req.target_asset_id,
    )


@router.post("/execute", response_model=PlanExecutionResult)
def execute_plan(
    req: ExecutePlanRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> PlanExecutionResult:
    return execution_service.execute_plan(
        project_id=req.project_id,
        plan=req.plan,
        default_asset_id=req.target_asset_id,
    )


# --- Durable DAG Workflow Endpoints ---

@router.post("/workflows", response_model=Workflow)
async def create_workflow(
    req: CreatePlanRequest,
    planner: MayaPlanner = Depends(get_maya_planner),
) -> Workflow:
    """Generate a durable multi-step DAG workflow from a natural-language prompt."""
    return await planner.plan_workflow(
        project_id=req.project_id,
        user_prompt=req.user_prompt,
        target_asset_id=req.target_asset_id,
    )


@router.get("/workflows/{workflow_id}", response_model=Workflow)
def get_workflow(
    workflow_id: str,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> Workflow:
    wf = maya_repo.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return wf


@router.get("/projects/{project_id}/workflows", response_model=list[Workflow])
def list_workflows(
    project_id: str,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> list[Workflow]:
    return maya_repo.list_workflows(project_id)


@router.post("/workflows/{workflow_id}/execute", response_model=Workflow)
def execute_workflow(
    workflow_id: str,
    req: ExecuteWorkflowRequest,
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> Workflow:
    wf = maya_repo.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    approved = list(req.approved_task_ids)
    if req.approve_all and "__ALL__" not in approved:
        approved.append("__ALL__")

    return orchestrator.execute_workflow(
        workflow=wf,
        default_asset_id=req.default_asset_id,
        approved_task_ids=approved,
    )


@router.post("/workflows/{workflow_id}/cancel", response_model=Workflow)
def cancel_workflow(
    workflow_id: str,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> Workflow:
    wf = maya_repo.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    maya_repo.update_workflow_status(workflow_id, "cancelled")
    wf.status = "cancelled"
    return wf


# --- Creative Recommendations Endpoints ---

@router.get("/projects/{project_id}/recommendations", response_model=list[CreativeRecommendation])
def get_recommendations(
    project_id: str,
    asset_id: str | None = None,
    project_service: ProjectService = Depends(get_project_service),
    rec_service: CreativeRecommendationService = Depends(get_recommendations_service),
) -> list[CreativeRecommendation]:
    asset = None
    if asset_id:
        try:
            asset = project_service.get_asset(asset_id)
        except Exception:
            asset = None
    if not asset:
        assets = project_service.list_assets(project_id, limit=1)
        if assets:
            asset = assets[0]
    return rec_service.generate_recommendations(asset)


@router.post("/recommendations/apply", response_model=Workflow)
def apply_recommendation(
    req: ApplyRecommendationRequest,
    project_service: ProjectService = Depends(get_project_service),
    rec_service: CreativeRecommendationService = Depends(get_recommendations_service),
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> Workflow:
    asset = project_service.get_asset(req.target_asset_id)
    recommendations = rec_service.generate_recommendations(asset)
    target_rec = next((r for r in recommendations if r.id == req.recommendation_id), None)
    if not target_rec:
        raise HTTPException(
            status_code=404, detail=f"Recommendation '{req.recommendation_id}' not found for asset."
        )

    wf_transient = rec_service.build_workflow_from_recommendation(
        recommendation=target_rec,
        project_id=req.project_id,
        asset=asset,
    )

    persisted_wf = maya_repo.create_workflow(
        project_id=req.project_id,
        title=wf_transient.title,
        description=wf_transient.description,
        tasks=wf_transient.tasks,
        execution_mode="execute",
    )
    return persisted_wf


# --- Project Creative Preferences & Brand Memory ---

@router.get("/projects/{project_id}/preferences", response_model=ProjectPreferences)
def get_project_preferences(
    project_id: str,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> ProjectPreferences:
    return maya_repo.get_preferences(project_id)


@router.put("/projects/{project_id}/preferences", response_model=ProjectPreferences)
def update_project_preferences(
    project_id: str,
    prefs: ProjectPreferences,
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> ProjectPreferences:
    prefs.project_id = project_id
    return maya_repo.save_preferences(prefs)
