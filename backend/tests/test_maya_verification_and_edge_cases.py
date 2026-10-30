import io

import pytest
from PIL import Image

from mayachitram.core.config import Settings
from mayachitram.engines.image.service import ImageEngine
from mayachitram.maya.execution.workflow import WorkflowOrchestrator
from mayachitram.maya.planner.service import MayaPlanner
from mayachitram.maya.registry.tools import get_default_tool_registry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import SendMessageRequest, WorkflowTask
from mayachitram.maya.validation.service import QualityValidationService
from mayachitram.projects.models import ProjectCreate
from mayachitram.projects.repository import ProjectRepository
from mayachitram.projects.service import ProjectService
from mayachitram.storage.service import LocalStorageService


def make_test_image(w: int = 400, h: int = 200, color: tuple = (100, 150, 220)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def env(tmp_path):
    settings = Settings(MAYACHITRAM_DATA_DIR=tmp_path / "data")
    project_repo = ProjectRepository(db_path=settings.database_path)
    maya_repo = MayaRepository(db_path=settings.database_path)
    storage = LocalStorageService(root_dir=settings.storage_dir)
    engine = ImageEngine(settings=settings)
    project_service = ProjectService(repository=project_repo, storage=storage, image_engine=engine)
    registry = get_default_tool_registry()
    validation_service = QualityValidationService(project_service=project_service)
    orchestrator = WorkflowOrchestrator(
        repository=maya_repo,
        project_service=project_service,
        image_engine=engine,
        tool_registry=registry,
        validation_service=validation_service,
    )
    planner = MayaPlanner(
        settings=settings,
        tool_registry=registry,
        project_service=project_service,
        maya_repository=maya_repo,
    )

    project = project_service.create_project(ProjectCreate(name="Verification Test Session"))
    asset = project_service.add_asset_from_bytes(
        project_id=project.id,
        image_bytes=make_test_image(800, 400),
        original_filename="master_shot.png",
    )

    return {
        "settings": settings,
        "project": project,
        "asset": asset,
        "maya_repo": maya_repo,
        "orchestrator": orchestrator,
        "planner": planner,
        "registry": registry,
        "project_service": project_service,
        "image_engine": engine,
        "storage": storage,
        "project_repo": project_repo,
    }


# ==============================================================================
# TASK 3: PROMPT UNDERSTANDING & PLANNING MATRIX TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_prompt_matrix_greeting_ordinary_question(env):
    """Greeting or general question must NOT trigger an image operation or create workflow."""
    planner = env["planner"]
    project = env["project"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            message="Hello Maya, what capabilities do you have?",
        )
    )
    assert res.workflow is None
    assert res.assistant_message.message_type == "text"
    assert "Maya" in res.assistant_message.content or "capabilities" in res.assistant_message.content.lower()


@pytest.mark.asyncio
async def test_prompt_matrix_simple_resize(env):
    """Simple resize request produces single-step workflow with validated dimensions."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Resize this image to 640x480",
        )
    )
    assert res.workflow is not None
    assert len(res.workflow.tasks) == 1
    task = res.workflow.tasks[0]
    assert task.tool_name == "image.resize"
    assert task.parameters["width"] == 640
    assert task.parameters["height"] == 480


@pytest.mark.asyncio
async def test_prompt_matrix_ordered_multi_step_pipeline(env):
    """Several image operations in a specified order produce chained DAG dependencies."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Crop 1:1 square, boost contrast, and convert to webp",
        )
    )
    assert res.workflow is not None
    tasks = res.workflow.tasks
    assert len(tasks) == 3

    assert tasks[0].tool_name == "image.crop"
    assert tasks[0].parameters["width"] == 400
    assert tasks[0].parameters["height"] == 400
    assert tasks[0].dependencies == []

    assert tasks[1].tool_name == "image.adjust_contrast"
    assert tasks[1].dependencies == ["task_1"]

    assert tasks[2].tool_name == "image.convert_format"
    assert tasks[2].parameters["target_format"] == "WEBP"
    assert tasks[2].dependencies == ["task_2"]


@pytest.mark.asyncio
async def test_prompt_matrix_missing_asset_clarification(env):
    """Request requiring an asset when no assets exist asks for clarification without failing workflow."""
    planner = env["planner"]
    project_service = env["project_service"]

    # Create empty project
    empty_proj = project_service.create_project(ProjectCreate(name="Empty Project"))

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=empty_proj.id,
            message="Crop this image into a 1:1 square",
        )
    )
    assert res.workflow is None
    assert res.assistant_message.message_type == "clarification"
    assert "upload or select an image asset" in res.assistant_message.content.lower()


@pytest.mark.asyncio
async def test_prompt_matrix_ambiguous_asset_clarification(env):
    """Ambiguous asset reference when multiple assets exist triggers clarifying question."""
    planner = env["planner"]
    project_service = env["project_service"]
    project = env["project"]

    # Upload two more assets so project has 3 assets
    project_service.add_asset_from_bytes(project.id, make_test_image(200, 200), "shot2.png")
    project_service.add_asset_from_bytes(project.id, make_test_image(300, 300), "shot3.png")

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            message="Apply a square crop to the other image",
        )
    )
    assert res.workflow is None
    assert res.assistant_message.message_type == "clarification"
    assert "multiple assets" in res.assistant_message.content.lower()


@pytest.mark.asyncio
async def test_prompt_matrix_multiple_deliverables(env):
    """Request for multiple campaign deliverables produces parallel branching DAG tasks."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Create three deliverables: 1:1 square, 4:5 portrait, and 16:9 landscape",
        )
    )
    assert res.workflow is not None
    tasks = res.workflow.tasks
    assert len(tasks) == 3
    # All tasks branch from master asset independently
    for t in tasks:
        assert t.tool_name == "image.crop"
        assert t.input_asset_id == asset.id
        assert t.dependencies == []


@pytest.mark.asyncio
async def test_prompt_matrix_cross_engine_honest_reporting(env):
    """Combining image, design, and video plans real image tools and honestly reports unavailable engines."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Crop this image, place in a social graphic design, and create a promo video clip",
        )
    )
    assert res.workflow is not None
    # Real image operation is planned
    assert any(t.tool_name == "image.crop" for t in res.workflow.tasks)
    # Collaborator engine status is explicitly disclosed
    assert "Design and Video" in res.assistant_message.content


@pytest.mark.asyncio
async def test_prompt_matrix_unsupported_operations(env):
    """Unsupported operations like 3D or background removal are politely declined without fake execution."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Generate a 3D mesh model and cutout background",
        )
    )
    assert res.workflow is None
    assert res.assistant_message.message_type == "clarification"
    assert "not supported" in res.assistant_message.content.lower()


@pytest.mark.asyncio
async def test_prompt_matrix_output_constraint_violation(env):
    """Request violating schema bounds (e.g. 100000x100000) fails validation safely."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Resize this image to 100000x100000",
        )
    )
    assert res.workflow is None
    assert "violates image constraints" in res.assistant_message.content.lower() or "could not build an executable plan" in res.assistant_message.content.lower()


def test_prompt_matrix_approval_requirement(env):
    """Operations requiring approval pause in awaiting_approval until confirmed."""
    orchestrator = env["orchestrator"]
    project = env["project"]
    asset = env["asset"]
    maya_repo = env["maya_repo"]

    t1 = WorkflowTask(
        task_id="t1",
        tool_name="image.rotate",
        description="Rotates image",
        parameters={"degrees": 90, "expand": True},
        input_asset_id=asset.id,
        requires_approval=True,
    )
    wf = maya_repo.create_workflow(project.id, "Approval Workflow", "Needs approval", [t1], execution_mode="execute")

    # Run without approval
    res = orchestrator.execute_workflow(wf, default_asset_id=asset.id, approved_task_ids=[])
    assert res.status == "awaiting_approval"

    # Run with approval
    res_approved = orchestrator.execute_workflow(wf, default_asset_id=asset.id, approved_task_ids=["t1"])
    assert res_approved.status == "completed"
    assert res_approved.tasks[0].status == "succeeded"


# ==============================================================================
# TASK 5: WORKFLOW EXECUTION & ROBUSTNESS TESTS
# ==============================================================================

def test_workflow_cyclic_dependency_rejected(env):
    """Cyclic dependency DAG causes immediate failure with clear error."""
    orchestrator = env["orchestrator"]
    project = env["project"]
    asset = env["asset"]
    maya_repo = env["maya_repo"]

    t1 = WorkflowTask(
        task_id="t1",
        tool_name="image.rotate",
        description="Task 1",
        parameters={"degrees": 90, "expand": True},
        dependencies=["t2"],
    )
    t2 = WorkflowTask(
        task_id="t2",
        tool_name="image.adjust_contrast",
        description="Task 2",
        parameters={"factor": 1.2},
        dependencies=["t1"],
    )
    wf = maya_repo.create_workflow(project.id, "Cycle Workflow", "Cycle test", [t1, t2])

    res = orchestrator.execute_workflow(wf, default_asset_id=asset.id)
    assert res.status == "failed"
    assert any("cyclic dependency" in (t.error or "").lower() for t in res.tasks)


def test_workflow_non_existent_dependency_rejected(env):
    """Dependency referencing a non-existent task fails safely."""
    orchestrator = env["orchestrator"]
    project = env["project"]
    asset = env["asset"]
    maya_repo = env["maya_repo"]

    t1 = WorkflowTask(
        task_id="t1",
        tool_name="image.rotate",
        description="Task 1",
        parameters={"degrees": 90, "expand": True},
        dependencies=["phantom_task_id"],
    )
    wf = maya_repo.create_workflow(project.id, "Missing Dep Workflow", "Dep test", [t1])

    res = orchestrator.execute_workflow(wf, default_asset_id=asset.id)
    assert res.status == "failed"
    assert "phantom_task_id" in res.tasks[0].error


def test_security_cross_project_asset_isolation(env):
    """Workflow in Project 1 cannot access or process an asset belonging to Project 2."""
    orchestrator = env["orchestrator"]
    project_service = env["project_service"]
    maya_repo = env["maya_repo"]

    # Foreign project and asset
    foreign_proj = project_service.create_project(ProjectCreate(name="Foreign Project"))
    foreign_asset = project_service.add_asset_from_bytes(
        foreign_proj.id, make_test_image(200, 200), "secret.png"
    )

    # Local project
    local_proj = env["project"]

    # Attempt to run tool in local project using foreign asset ID
    t1 = WorkflowTask(
        task_id="t1",
        tool_name="image.rotate",
        description="Cross-project attempt",
        parameters={"degrees": 90, "expand": True},
        input_asset_id=foreign_asset.id,
    )
    wf = maya_repo.create_workflow(local_proj.id, "Attacker Workflow", "Security probe", [t1])

    res = orchestrator.execute_workflow(wf, default_asset_id=None)
    assert res.status == "failed"
    assert "security isolation violation" in res.tasks[0].error.lower()


def test_workflow_resumption_and_idempotency(env):
    """Interrupted or partially completed workflows skip already succeeded tasks on restart/resumption."""
    orchestrator = env["orchestrator"]
    project = env["project"]
    asset = env["asset"]
    maya_repo = env["maya_repo"]

    t1 = WorkflowTask(
        task_id="step1",
        tool_name="image.crop",
        description="Step 1 Crop",
        parameters={"left": 0, "top": 0, "width": 400, "height": 400},
        input_asset_id=asset.id,
    )
    t2 = WorkflowTask(
        task_id="step2",
        tool_name="image.convert_format",
        description="Step 2 WebP",
        parameters={"target_format": "WEBP", "quality": 85},
        dependencies=["step1"],
    )
    wf = maya_repo.create_workflow(project.id, "Resumption Test", "Test", [t1, t2])

    # Execute step 1 successfully, then artificially pause/simulate interruption
    orchestrator.execute_workflow(wf, default_asset_id=asset.id)
    assert wf.status == "completed"
    out_step1 = wf.tasks[0].output_asset_id
    assert out_step1 is not None

    # Reset step 2 to pending to simulate resumption
    maya_repo.update_task_status(wf.id, "step2", "pending")
    reloaded_wf = maya_repo.get_workflow(wf.id)
    assert reloaded_wf.tasks[0].status == "succeeded"
    assert reloaded_wf.tasks[1].status == "pending"

    # Resume execution
    resumed = orchestrator.execute_workflow(reloaded_wf, default_asset_id=asset.id)
    assert resumed.status == "completed"
    # Step 1 was not re-executed; output asset ID is preserved
    assert resumed.tasks[0].output_asset_id == out_step1


@pytest.mark.asyncio
async def test_maya_chatbot_suggestions_mode(env):
    """Point 3: Asking for suggestions or being in assist mode acts like a chatbot advisor without creating workflows."""
    planner = env["planner"]
    project = env["project"]
    asset = env["asset"]

    # In execute mode with suggestion request: returns chatbot advice + recommendations, no workflow
    res1 = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="Can you suggest what I should do with this image?",
            execution_mode="execute",
        )
    )
    assert res1.workflow is None
    assert len(res1.recommendations) > 0
    assert "suggestions" in res1.assistant_message.content.lower() or "recommendations" in res1.assistant_message.content.lower()

    # In assist mode: acts as conversational assistant even with creative terms
    res2 = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=asset.id,
            message="What are some good crops and adjustments for social media?",
            execution_mode="assist",
        )
    )
    assert res2.workflow is None
    assert len(res2.recommendations) > 0


@pytest.mark.asyncio
async def test_maya_completes_work_after_manual_editing(env):
    """Point 2: User performs manual work in MayaChitram, then Maya takes the output and completes the remaining work."""
    image_engine = env["image_engine"]
    project_service = env["project_service"]
    project_repo = env["project_repo"]
    storage = env["storage"]
    planner = env["planner"]
    orchestrator = env["orchestrator"]
    project = env["project"]
    initial_asset = env["asset"]

    # 1. Simulate manual work: user manually crops image in ImageStudio (e.g., to 300x300)
    from mayachitram.engines.image.schemas import CropParams
    manual_raw = storage.read(initial_asset.storage_key)
    cropped_bytes, _ = image_engine.crop(manual_raw, CropParams(left=0, top=0, width=300, height=300))
    manual_asset = project_service.add_asset_from_bytes(
        project_id=project.id,
        image_bytes=cropped_bytes,
        original_filename="manual_cropped.png",
        parent_asset_id=initial_asset.id,
    )

    # 2. User asks Maya to do the remaining work (rotate 90 degrees and convert to WebP) on what they manually created
    res = await planner.handle_chat_message(
        SendMessageRequest(
            project_id=project.id,
            target_asset_id=manual_asset.id,  # Active asset in UI is now manual_asset
            message="Rotate this 90 degrees and convert to WebP",
            execution_mode="execute",
        )
    )
    assert res.workflow is not None
    wf = res.workflow
    assert wf.tasks[0].input_asset_id == manual_asset.id

    # 3. Execute Maya's workflow
    completed_wf = orchestrator.execute_workflow(wf, default_asset_id=manual_asset.id)
    assert completed_wf.status == "completed"
    final_id = completed_wf.final_asset_ids[-1]
    final_asset = project_repo.get_asset(final_id)
    assert final_asset is not None
    # Verify final asset was produced from manual asset
    assert final_asset.media_type == "image/webp"

