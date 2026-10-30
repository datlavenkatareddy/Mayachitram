from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mayachitram.api.v1.dependencies import get_execution_service, get_tool_registry
from mayachitram.maya.execution.service import ExecutionService
from mayachitram.maya.registry.tools import ToolDefinition, ToolRegistry
from mayachitram.maya.schemas import ToolExecutionResult

router = APIRouter()


class ExecuteToolRequest(BaseModel):
    project_id: str = Field(description="Target project ID")
    tool_name: str = Field(description="Registered tool name, e.g. image.resize")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Validated tool arguments")
    input_asset_id: str = Field(description="Asset to execute the tool upon")


@router.get("", response_model=list[ToolDefinition])
def list_tools(
    registry: ToolRegistry = Depends(get_tool_registry),
) -> list[ToolDefinition]:
    return registry.list_tools()


@router.post("/execute", response_model=ToolExecutionResult)
def execute_tool(
    req: ExecuteToolRequest,
    execution_service: ExecutionService = Depends(get_execution_service),
) -> ToolExecutionResult:
    return execution_service.execute_tool(
        project_id=req.project_id,
        tool_name=req.tool_name,
        parameters=req.parameters,
        input_asset_id=req.input_asset_id,
    )
