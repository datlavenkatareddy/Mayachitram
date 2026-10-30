import io

import pytest
from PIL import Image

from mayachitram.core.config import Settings
from mayachitram.core.errors import OperationError
from mayachitram.engines.image.service import ImageEngine
from mayachitram.maya.execution.workflow import WorkflowOrchestrator
from mayachitram.maya.planner.recommendations import CreativeRecommendationService
from mayachitram.maya.planner.service import MayaPlanner
from mayachitram.maya.registry.adapters import DesignEngineAdapter, VideoEngineAdapter
from mayachitram.maya.registry.tools import get_default_tool_registry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import (
    ProjectPreferences,
    WorkflowTask,
)
from mayachitram.maya.validation.service import QualityValidationService
from mayachitram.projects.models import ProjectCreate
from mayachitram.projects.repository import ProjectRepository
from mayachitram.projects.service import ProjectService
from mayachitram.storage.service import LocalStorageService


def make_test_image(w: int = 400, h: int = 200) -> bytes:
    img = Image.new("RGB", (w, h), (100, 150, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def workflow_setup(tmp_path):
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
    rec_service = CreativeRecommendationService()

    project = project_service.create_project(ProjectCreate(name="Workflow Multi-Engine Studio"))
    asset = project_service.add_asset_from_bytes(
        project_id=project.id,
        image_bytes=make_test_image(600, 300),
        original_filename="banner.png",
    )

    return {
        "settings": settings,
        "project": project,
        "asset": asset,
        "maya_repo": maya_repo,
        "orchestrator": orchestrator,
        "planner": planner,
        "rec_service": rec_service,
        "registry": registry,
        "project_service": project_service,
    }


def test_conversation_persistence_and_multi_turn(workflow_setup):
    maya_repo = workflow_setup["maya_repo"]
    project = workflow_setup["project"]

    session = maya_repo.get_or_create_conversation(project.id)
    assert session.id is not None
    assert session.project_id == project.id

    msg1 = maya_repo.add_message(session.id, "user", "Can you make this a square?")
    assert msg1.role == "user"
    assert msg1.content == "Can you make this a square?"

    msg2 = maya_repo.add_message(
        session.id, "assistant", "I created a plan to crop to 300x300.", message_type="plan"
    )
    assert msg2.role == "assistant"
    assert msg2.message_type == "plan"

    messages = maya_repo.get_messages(session.id)
    assert len(messages) == 2
    assert messages[0].content == "Can you make this a square?"
    assert messages[1].content == "I created a plan to crop to 300x300."


def test_dag_workflow_dependency_execution(workflow_setup):
    orchestrator = workflow_setup["orchestrator"]
    project = workflow_setup["project"]
    asset = workflow_setup["asset"]
    maya_repo = workflow_setup["maya_repo"]

    # Step 1: Crop to square (300x300)
    # Step 2: Depends on Step 1 -> Convert to WebP format
    t1 = WorkflowTask(
        task_id="crop_step",
        tool_name="image.crop",
        description="Centered 300x300 square crop",
        parameters={"left": 150, "top": 0, "width": 300, "height": 300},
        input_asset_id=asset.id,
    )
    t2 = WorkflowTask(
        task_id="format_step",
        tool_name="image.convert_format",
        description="Convert output of crop_step to WebP",
        parameters={"target_format": "WEBP", "quality": 85},
        dependencies=["crop_step"],
    )

    wf = maya_repo.create_workflow(
        project_id=project.id,
        title="Square WebP Campaign Workflow",
        description="Crop then WebP",
        tasks=[t1, t2],
    )

    executed_wf = orchestrator.execute_workflow(wf, default_asset_id=asset.id)
    assert executed_wf.status == "completed"
    assert len(executed_wf.tasks) == 2
    assert executed_wf.tasks[0].status == "succeeded"
    assert executed_wf.tasks[1].status == "succeeded"

    # Step 2 used output of Step 1 as input
    out_1 = executed_wf.tasks[0].output_asset_id
    out_2 = executed_wf.tasks[1].output_asset_id
    assert out_1 is not None
    assert out_2 is not None

    asset_1 = workflow_setup["project_service"].get_asset(out_1)
    asset_2 = workflow_setup["project_service"].get_asset(out_2)
    assert asset_1.width == 300
    assert asset_1.height == 300
    assert asset_2.media_type == "image/webp"
    assert asset_2.parent_asset_id == out_1


def test_workflow_task_skipping_on_upstream_failure(workflow_setup):
    orchestrator = workflow_setup["orchestrator"]
    project = workflow_setup["project"]
    asset = workflow_setup["asset"]
    maya_repo = workflow_setup["maya_repo"]

    # Step 1 with invalid parameters (negative crop)
    t1 = WorkflowTask(
        task_id="step_fail",
        tool_name="image.crop",
        description="Invalid crop coordinates",
        parameters={"left": 9999, "top": 9999, "width": 100, "height": 100},
        input_asset_id=asset.id,
    )
    # Step 2 depends on Step 1
    t2 = WorkflowTask(
        task_id="step_dependent",
        tool_name="image.rotate",
        description="Rotate after crop",
        parameters={"degrees": 90, "expand": True},
        dependencies=["step_fail"],
    )

    wf = maya_repo.create_workflow(
        project_id=project.id,
        title="Failing Workflow",
        description="Test upstream error handling",
        tasks=[t1, t2],
    )

    result_wf = orchestrator.execute_workflow(wf, default_asset_id=asset.id)
    assert result_wf.status == "failed"
    assert result_wf.tasks[0].status == "failed"
    assert result_wf.tasks[1].status == "skipped"
    assert "upstream dependency failed" in result_wf.tasks[1].error.lower()


def test_creative_recommendations_and_workflow_generation(workflow_setup):
    rec_service = workflow_setup["rec_service"]
    project = workflow_setup["project"]
    asset = workflow_setup["asset"]

    recs = rec_service.generate_recommendations(asset)
    assert len(recs) >= 3
    rec_ids = [r.id for r in recs]
    assert "rec_square_crop" in rec_ids
    assert "rec_webp_conversion" in rec_ids

    # Build workflow from recommendation
    target_rec = next(r for r in recs if r.id == "rec_vibrant_grade")
    wf = rec_service.build_workflow_from_recommendation(target_rec, project.id, asset)
    assert len(wf.tasks) == 3
    assert wf.tasks[0].tool_name == "image.adjust_contrast"
    assert wf.tasks[1].tool_name == "image.adjust_saturation"
    assert wf.tasks[2].tool_name == "image.adjust_temperature"
    assert wf.tasks[1].dependencies == ["task_1"]
    assert wf.tasks[2].dependencies == ["task_2"]


def test_project_preferences_crud(workflow_setup):
    maya_repo = workflow_setup["maya_repo"]
    project = workflow_setup["project"]

    # Initial default preferences
    prefs = maya_repo.get_preferences(project.id)
    assert prefs.brand_colors == []
    assert prefs.default_execution_mode == "execute"

    # Save preferences
    new_prefs = ProjectPreferences(
        project_id=project.id,
        brand_colors=["#FF4500", "#1A1A2E"],
        brand_fonts=["Inter", "Playfair Display"],
        preferred_aspect_ratios=["1:1", "4:5", "16:9"],
        preferred_export_formats=["WEBP", "PNG"],
        default_execution_mode="assist",
        custom_instructions="Always crop tightly around human subjects.",
    )
    saved = maya_repo.save_preferences(new_prefs)
    assert saved.brand_colors == ["#FF4500", "#1A1A2E"]

    # Retrieve saved preferences
    retrieved = maya_repo.get_preferences(project.id)
    assert retrieved.brand_colors == ["#FF4500", "#1A1A2E"]
    assert retrieved.custom_instructions == "Always crop tightly around human subjects."
    assert retrieved.default_execution_mode == "assist"


def test_engine_adapters_and_contracts():
    design_adapter = DesignEngineAdapter()
    video_adapter = VideoEngineAdapter()

    assert design_adapter.is_available is False
    assert video_adapter.is_available is False

    # Calling unavailable operations must raise clear error instead of faking success
    with pytest.raises(OperationError) as exc_design:
        design_adapter.execute("design.create_canvas", b"", None)
    assert "Design Engine is being developed in parallel" in str(exc_design.value)

    with pytest.raises(OperationError) as exc_video:
        video_adapter.execute("video.trim", b"", None)
    assert "Video Engine is being developed in parallel" in str(exc_video.value)


def test_conversational_chat_with_maya_api(client):
    # 1. Create project & asset
    proj_res = client.post("/api/v1/projects", json={"name": "Conversational Maya API"})
    proj_id = proj_res.json()["id"]

    img_data = make_test_image(300, 150)
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/assets",
        files={"file": ("input.png", img_data, "image/png")},
    )
    asset_id = upload_res.json()["id"]

    # 2. Greeting / non-editing message
    chat_res = client.post(
        "/api/v1/maya/chat",
        json={"project_id": proj_id, "message": "Hello Maya, what can you do?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    conv_id = chat_data["conversation_id"]
    assert "assistant_message" in chat_data
    assert len(chat_data["recommendations"]) > 0

    # 3. Creative request that triggers workflow generation
    crop_res = client.post(
        "/api/v1/maya/chat",
        json={
            "project_id": proj_id,
            "conversation_id": conv_id,
            "target_asset_id": asset_id,
            "message": "Make a square crop and convert to webp",
        },
    )
    assert crop_res.status_code == 200
    crop_data = crop_res.json()
    assert crop_data["workflow"] is not None
    wf_id = crop_data["workflow"]["id"]

    # 4. Execute the workflow via /api/v1/maya/workflows/{id}/execute
    exec_res = client.post(
        f"/api/v1/maya/workflows/{wf_id}/execute",
        json={"default_asset_id": asset_id},
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "completed"
    assert len(exec_data["final_asset_ids"]) > 0

    # 5. Check preferences API
    pref_res = client.get(f"/api/v1/maya/projects/{proj_id}/preferences")
    assert pref_res.status_code == 200
    assert pref_res.json()["project_id"] == proj_id
