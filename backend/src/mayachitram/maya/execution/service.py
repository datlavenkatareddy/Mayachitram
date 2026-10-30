from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mayachitram.core.errors import NotFoundError, OperationError
from mayachitram.engines.image.service import FORMAT_EXTENSIONS, ImageEngine
from mayachitram.maya.execution.workflow import WorkflowOrchestrator
from mayachitram.maya.registry.tools import ToolRegistry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import (
    PlanExecutionResult,
    PlanResponse,
    StepExecutionSummary,
    ToolExecutionResult,
    Workflow,
)
from mayachitram.projects.models import Asset
from mayachitram.projects.service import ProjectService


class ExecutionService:
    """Central execution service shared by manual UI tools, Maya AI assistant, and Workflow Orchestrator."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        project_service: ProjectService,
        image_engine: ImageEngine,
        maya_repository: MayaRepository | None = None,
        orchestrator: WorkflowOrchestrator | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.project_service = project_service
        self.image_engine = image_engine
        self.maya_repository = maya_repository
        if orchestrator:
            self.orchestrator = orchestrator
        elif maya_repository:
            self.orchestrator = WorkflowOrchestrator(
                repository=maya_repository,
                project_service=project_service,
                image_engine=image_engine,
                tool_registry=tool_registry,
            )
        else:
            self.orchestrator = None

    def execute_tool(
        self,
        project_id: str,
        tool_name: str,
        parameters: dict[str, Any],
        input_asset_id: str,
    ) -> ToolExecutionResult:
        tool = self.tool_registry.get(tool_name)
        if not tool:
            raise NotFoundError(f"Tool '{tool_name}' is not registered.")

        # Validate parameters against tool's Pydantic schema
        try:
            validated_params = tool.params_class.model_validate(parameters)
        except ValidationError as exc:
            raise OperationError(f"Invalid parameters for tool '{tool_name}': {exc}") from exc

        # Resolve input asset
        input_asset = self.project_service.get_asset(input_asset_id)
        if input_asset.project_id != project_id:
            raise OperationError(
                f"Asset '{input_asset_id}' does not belong to project '{project_id}'."
            )

        # Record operation start
        op_record = self.project_service.repository.create_operation(
            project_id=project_id,
            tool_name=tool_name,
            parameters=validated_params.model_dump(),
            input_asset_ids=[input_asset_id],
        )

        try:
            input_bytes, _, _ = self.project_service.get_asset_file_bytes(input_asset_id)

            # Execute tool handler
            output_bytes, output_meta = tool.handler(
                self.image_engine, input_bytes, validated_params
            )

            # Generate output asset name
            base_name = Path(input_asset.original_filename).stem
            tool_suffix = tool_name.split(".")[-1]
            ext = FORMAT_EXTENSIONS.get(output_meta.format, "png")
            out_filename = f"{base_name}_{tool_suffix}.{ext}"

            # Save non-destructive output asset
            output_asset = self.project_service.add_asset_from_bytes(
                project_id=project_id,
                image_bytes=output_bytes,
                original_filename=out_filename,
                parent_asset_id=input_asset_id,
                metadata={
                    "generated_by_tool": tool_name,
                    "operation_id": op_record.id,
                    **output_meta.model_dump(),
                },
            )

            # Mark operation succeeded
            self.project_service.repository.update_operation(
                operation_id=op_record.id,
                status="succeeded",
                output_asset_ids=[output_asset.id],
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                status="succeeded",
                operation_id=op_record.id,
                output_asset=output_asset,
                output_metadata=output_meta.model_dump(),
                message=f"Successfully executed {tool_name} on {input_asset.original_filename}.",
            )
        except Exception as exc:
            self.project_service.repository.update_operation(
                operation_id=op_record.id,
                status="failed",
                error=str(exc),
            )
            if isinstance(exc, OperationError | NotFoundError):
                raise
            raise OperationError(f"Failed to execute {tool_name}: {exc}") from exc

    def execute_plan(
        self,
        project_id: str,
        plan: PlanResponse,
        default_asset_id: str | None = None,
    ) -> PlanExecutionResult:
        if not plan.steps:
            return PlanExecutionResult(
                project_id=project_id,
                status="succeeded",
                steps=[],
                final_asset=None,
                summary_message="No steps to execute in plan.",
            )

        summaries: list[StepExecutionSummary] = []
        current_asset_id = default_asset_id or plan.target_asset_id
        final_asset: Asset | None = None
        overall_status: str = "succeeded"

        for step in plan.steps:
            target_asset = step.input_asset_id or current_asset_id
            if not target_asset:
                summaries.append(
                    StepExecutionSummary(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status="failed",
                        error="No input asset specified for step.",
                    )
                )
                overall_status = "partial" if summaries else "failed"
                break

            try:
                res = self.execute_tool(
                    project_id=project_id,
                    tool_name=step.tool_name,
                    parameters=step.parameters,
                    input_asset_id=target_asset,
                )
                summaries.append(
                    StepExecutionSummary(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status="succeeded",
                        result=res,
                    )
                )
                if res.output_asset:
                    current_asset_id = res.output_asset.id
                    final_asset = res.output_asset
            except Exception as exc:
                summaries.append(
                    StepExecutionSummary(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status="failed",
                        error=str(exc),
                    )
                )
                overall_status = (
                    "partial" if any(s.status == "succeeded" for s in summaries) else "failed"
                )
                break

        return PlanExecutionResult(
            project_id=project_id,
            status=overall_status,  # type: ignore[arg-type]
            steps=summaries,
            final_asset=final_asset,
            summary_message=f"Plan execution finished with status: {overall_status}.",
        )

    def execute_workflow(
        self,
        workflow: Workflow,
        default_asset_id: str | None = None,
        approved_task_ids: list[str] | None = None,
    ) -> Workflow:
        if not self.orchestrator:
            raise OperationError("Workflow orchestrator is not initialized in this execution service.")
        return self.orchestrator.execute_workflow(
            workflow=workflow,
            default_asset_id=default_asset_id,
            approved_task_ids=approved_task_ids,
        )
