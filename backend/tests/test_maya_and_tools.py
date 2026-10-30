import asyncio
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from mayachitram.core.config import Settings
from mayachitram.core.errors import OperationError
from mayachitram.engines.image.service import ImageEngine
from mayachitram.maya.execution.service import ExecutionService
from mayachitram.maya.planner.service import MayaPlanner
from mayachitram.maya.registry.tools import get_default_tool_registry
from mayachitram.projects.models import ProjectCreate
from mayachitram.projects.repository import ProjectRepository
from mayachitram.projects.service import ProjectService
from mayachitram.storage.service import LocalStorageService


def make_test_image(w: int = 400, h: int = 200) -> bytes:
    img = Image.new("RGB", (w, h), (120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def test_setup(tmp_path):
    settings = Settings(
        MAYACHITRAM_DATA_DIR=tmp_path / "data",
        GROQ_API_KEY="test-mock-key",
    )
    repo = ProjectRepository(db_path=settings.database_path)
    storage = LocalStorageService(root_dir=settings.storage_dir)
    engine = ImageEngine(settings=settings)
    project_service = ProjectService(repository=repo, storage=storage, image_engine=engine)
    registry = get_default_tool_registry()
    execution_service = ExecutionService(
        tool_registry=registry,
        project_service=project_service,
        image_engine=engine,
    )
    planner = MayaPlanner(
        settings=settings,
        tool_registry=registry,
        project_service=project_service,
    )

    # Seed project with asset
    project = project_service.create_project(ProjectCreate(name="Maya Creative Session"))
    asset = project_service.add_asset_from_bytes(
        project_id=project.id,
        image_bytes=make_test_image(400, 200),
        original_filename="sample.png",
    )

    return {
        "settings": settings,
        "project": project,
        "asset": asset,
        "registry": registry,
        "execution_service": execution_service,
        "planner": planner,
        "project_service": project_service,
    }


def test_tool_registry_enumeration(test_setup):
    registry = test_setup["registry"]
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "image.resize" in tool_names
    assert "image.crop" in tool_names
    assert "image.rotate" in tool_names
    assert "image.flip" in tool_names
    assert "image.convert_format" in tool_names
    assert "image.compress" in tool_names
    assert "image.adjust_brightness" in tool_names
    assert "image.adjust_contrast" in tool_names
    assert "image.adjust_saturation" in tool_names
    assert "image.adjust_temperature" in tool_names


def test_execution_service_runs_tool_non_destructively(test_setup):
    exec_service = test_setup["execution_service"]
    project = test_setup["project"]
    asset = test_setup["asset"]

    result = exec_service.execute_tool(
        project_id=project.id,
        tool_name="image.rotate",
        parameters={"degrees": 90, "expand": True},
        input_asset_id=asset.id,
    )

    assert result.status == "succeeded"
    assert result.output_asset is not None
    assert result.output_asset.parent_asset_id == asset.id
    # Rotated 400x200 becomes 200x400
    assert result.output_asset.width == 200
    assert result.output_asset.height == 400

    # Original asset is preserved
    original = test_setup["project_service"].get_asset(asset.id)
    assert original.width == 400
    assert original.height == 200

    # Operation history is logged
    ops = test_setup["project_service"].list_operations(project.id)
    assert len(ops) >= 1
    assert ops[0].status == "succeeded"
    assert ops[0].tool_name == "image.rotate"


def test_execution_rejects_invalid_parameters(test_setup):
    exec_service = test_setup["execution_service"]
    project = test_setup["project"]
    asset = test_setup["asset"]

    with pytest.raises(OperationError):
        exec_service.execute_tool(
            project_id=project.id,
            tool_name="image.resize",
            parameters={"width": -50, "height": 0},  # Negative/zero width invalid
            input_asset_id=asset.id,
        )


def test_maya_fallback_planning_square_and_rotate(test_setup):
    planner = test_setup["planner"]
    project = test_setup["project"]
    asset = test_setup["asset"]

    # Request square version
    plan_square = asyncio.run(
        planner.plan(
            project_id=project.id,
            user_prompt="Make a square version of this photo",
            target_asset_id=asset.id,
        )
    )
    assert plan_square.can_execute is True
    assert len(plan_square.steps) == 1
    assert plan_square.steps[0].tool_name == "image.crop"
    assert plan_square.steps[0].parameters["width"] == 200  # min(400, 200)
    assert plan_square.steps[0].parameters["height"] == 200

    # Request rotation
    plan_rotate = asyncio.run(
        planner.plan(
            project_id=project.id,
            user_prompt="Rotate this 90 degrees",
            target_asset_id=asset.id,
        )
    )
    assert plan_rotate.can_execute is True
    assert plan_rotate.steps[0].tool_name == "image.rotate"
    assert plan_rotate.steps[0].parameters["degrees"] == 90.0


def test_maya_groq_mocked_plan_and_execution(test_setup):
    planner = test_setup["planner"]
    exec_service = test_setup["execution_service"]
    project = test_setup["project"]
    asset = test_setup["asset"]

    # Mock Groq client response
    mock_choice = MagicMock()
    mock_choice.message.content = """{
        "summary": "Resize to 300x150 and convert to WebP",
        "steps": [
            {
                "step_id": 1,
                "tool_name": "image.resize",
                "parameters": {"width": 300, "height": 150, "preserve_aspect": false},
                "rationale": "Resize image"
            },
            {
                "step_id": 2,
                "tool_name": "image.convert_format",
                "parameters": {"target_format": "WEBP", "quality": 80},
                "rationale": "Convert to WebP"
            }
        ]
    }"""
    mock_completion = MagicMock(choices=[mock_choice])
    planner._groq_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    plan = asyncio.run(
        planner.plan(
            project_id=project.id,
            user_prompt="Resize to 300x150 and make it webp",
            target_asset_id=asset.id,
        )
    )

    assert plan.can_execute is True
    assert len(plan.steps) == 2
    assert plan.steps[0].tool_name == "image.resize"
    assert plan.steps[1].tool_name == "image.convert_format"

    # Execute plan
    exec_result = exec_service.execute_plan(
        project_id=project.id,
        plan=plan,
        default_asset_id=asset.id,
    )
    assert exec_result.status == "succeeded"
    assert len(exec_result.steps) == 2
    assert exec_result.final_asset is not None
    assert exec_result.final_asset.width == 300
    assert exec_result.final_asset.height == 150
    assert exec_result.final_asset.media_type == "image/webp"


def test_api_tool_and_maya_endpoints(client):
    # 1. Create project
    proj_res = client.post("/api/v1/projects", json={"name": "Tools API Test"})
    proj_id = proj_res.json()["id"]

    # 2. Upload asset
    img_data = make_test_image(200, 100)
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/assets",
        files={"file": ("orig.png", img_data, "image/png")},
    )
    asset_id = upload_res.json()["id"]

    # 3. List tools
    tools_res = client.get("/api/v1/tools")
    assert tools_res.status_code == 200
    assert any(t["name"] == "image.rotate" for t in tools_res.json())

    # 4. Execute tool via /api/v1/tools/execute
    exec_res = client.post(
        "/api/v1/tools/execute",
        json={
            "project_id": proj_id,
            "tool_name": "image.rotate",
            "parameters": {"degrees": 90, "expand": True},
            "input_asset_id": asset_id,
        },
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "succeeded"
    new_asset_id = exec_res.json()["output_asset"]["id"]
    assert new_asset_id != asset_id

    # 5. Plan via /api/v1/maya/plan
    plan_res = client.post(
        "/api/v1/maya/plan",
        json={
            "project_id": proj_id,
            "user_prompt": "Make a square crop",
            "target_asset_id": asset_id,
        },
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["can_execute"] is True
    assert plan_data["steps"][0]["tool_name"] == "image.crop"

    # 6. Execute plan via /api/v1/maya/execute
    plan_exec_res = client.post(
        "/api/v1/maya/execute",
        json={
            "project_id": proj_id,
            "target_asset_id": asset_id,
            "plan": plan_data,
            "confirmed": True,
        },
    )
    assert plan_exec_res.status_code == 200
    assert plan_exec_res.json()["status"] == "succeeded"
