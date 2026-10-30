import logging
from collections import defaultdict, deque
from pathlib import Path

from pydantic import ValidationError

from mayachitram.core.errors import OperationError
from mayachitram.engines.image.service import FORMAT_EXTENSIONS, ImageEngine
from mayachitram.maya.registry.tools import ToolRegistry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import TaskStatus, Workflow, WorkflowTask
from mayachitram.maya.validation.service import QualityValidationService
from mayachitram.projects.models import Asset, utc_now_iso
from mayachitram.projects.service import ProjectService

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Durable DAG workflow orchestrator for multi-step creative pipelines.
    Manages task dependencies, state transitions, asset lineage, retries, and quality verification.
    """

    def __init__(
        self,
        repository: MayaRepository,
        project_service: ProjectService,
        image_engine: ImageEngine,
        tool_registry: ToolRegistry,
        validation_service: QualityValidationService | None = None,
    ) -> None:
        self.repository = repository
        self.project_service = project_service
        self.image_engine = image_engine
        self.tool_registry = tool_registry
        self.validation_service = validation_service or QualityValidationService(project_service)

    def topological_sort(self, tasks: list[WorkflowTask]) -> list[WorkflowTask]:
        """Return tasks ordered such that all dependencies appear before dependent tasks."""
        task_map = {t.task_id: t for t in tasks}
        in_degree: dict[str, int] = defaultdict(int)
        adj: dict[str, list[str]] = defaultdict(list)

        # Validate dependency integrity: all dependencies must reference existing tasks
        for t in tasks:
            in_degree[t.task_id] = in_degree[t.task_id]  # ensure entry exists
            for dep in t.dependencies:
                if dep not in task_map:
                    raise OperationError(
                        f"Task '{t.task_id}' references non-existent dependency '{dep}'."
                    )
                adj[dep].append(t.task_id)
                in_degree[t.task_id] += 1

        queue = deque([t_id for t_id in task_map if in_degree[t_id] == 0])
        sorted_tasks: list[WorkflowTask] = []

        while queue:
            curr = queue.popleft()
            sorted_tasks.append(task_map[curr])
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_tasks) != len(tasks):
            raise OperationError("Cyclic dependency detected in workflow DAG.")

        return sorted_tasks

    def execute_workflow(
        self,
        workflow: Workflow,
        default_asset_id: str | None = None,
        approved_task_ids: list[str] | None = None,
    ) -> Workflow:
        """Execute a multi-step DAG workflow according to dependency order and execution constraints."""
        approved_set = set(approved_task_ids or [])
        approve_all = "__ALL__" in approved_set
        project_id = workflow.project_id

        # Update workflow to running
        self.repository.update_workflow_status(workflow.id, "running")
        workflow.status = "running"

        # Validate DAG structure (detect cycles and non-existent dependencies)
        try:
            sorted_tasks = self.topological_sort(workflow.tasks)
        except OperationError as exc:
            workflow.status = "failed"
            now = utc_now_iso()
            workflow.completed_at = now
            for t in workflow.tasks:
                if t.status == "pending":
                    t.status = "failed"
                    t.error = str(exc)
                    self.repository.update_task_status(
                        workflow_id=workflow.id,
                        task_id=t.task_id,
                        status="failed",
                        error=t.error,
                        completed_at=now,
                    )
            self.repository.update_workflow_status(
                workflow_id=workflow.id,
                status="failed",
                completed_at=now,
            )
            return workflow

        task_outputs: dict[str, str] = {}  # task_id -> output_asset_id
        task_status: dict[str, TaskStatus] = {}

        # Prepopulate outputs for already succeeded tasks (e.g. resumption after interruption)
        for t in workflow.tasks:
            if t.status == "running":
                # Interrupted running task reset to pending
                t.status = "pending"
                self.repository.update_task_status(workflow.id, t.task_id, "pending")
            if t.output_asset_id:
                task_outputs[t.task_id] = t.output_asset_id
            task_status[t.task_id] = t.status

        final_assets: list[str] = []

        for task in sorted_tasks:
            # If already succeeded, skip re-execution
            if task.status == "succeeded" and task.output_asset_id:
                final_assets.append(task.output_asset_id)
                continue

            # Check upstream dependencies
            dep_failed = False
            for dep_id in task.dependencies:
                dep_st = task_status.get(dep_id, "pending")
                if dep_st in ("failed", "skipped", "cancelled"):
                    dep_failed = True
                    break

            if dep_failed:
                task.status = "skipped"
                task.error = "Skipped because upstream dependency failed."
                task_status[task.task_id] = "skipped"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="skipped",
                    error=task.error,
                )
                continue

            # Check approval requirements
            if (
                task.requires_approval
                and workflow.execution_mode != "autonomous"
                and not approve_all
                and task.task_id not in approved_set
            ):
                task.status = "pending"
                self.repository.update_workflow_status(workflow.id, "awaiting_approval")
                workflow.status = "awaiting_approval"
                return workflow

            # Resolve input asset
            input_asset_id = task.input_asset_id
            if not input_asset_id and task.dependencies:
                last_dep = task.dependencies[-1]
                input_asset_id = task_outputs.get(last_dep)
            if not input_asset_id:
                input_asset_id = default_asset_id

            if not input_asset_id:
                task.status = "failed"
                task.error = "No input asset available for task execution."
                task_status[task.task_id] = "failed"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                )
                continue

            # Verify input asset exists
            try:
                input_asset = self.project_service.get_asset(input_asset_id)
            except Exception as exc:
                task.status = "failed"
                task.error = f"Input asset {input_asset_id} not found: {exc}"
                task_status[task.task_id] = "failed"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                )
                continue

            # Security: Cross-project boundary enforcement
            if input_asset.project_id != project_id:
                task.status = "failed"
                task.error = (
                    f"Security isolation violation: Asset '{input_asset_id}' belongs to project "
                    f"'{input_asset.project_id}', not '{project_id}'."
                )
                task_status[task.task_id] = "failed"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                )
                continue

            # Lookup tool in registry
            tool = self.tool_registry.get(task.tool_name)
            if not tool:
                task.status = "failed"
                task.error = f"Tool '{task.tool_name}' is not registered."
                task_status[task.task_id] = "failed"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                )
                continue

            # Validate tool parameters
            try:
                validated_params = tool.params_class.model_validate(task.parameters)
            except ValidationError as exc:
                task.status = "failed"
                task.error = f"Parameter validation failed: {exc}"
                task_status[task.task_id] = "failed"
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                )
                continue

            # Mark task running
            now_iso = utc_now_iso()
            task.status = "running"
            task.started_at = now_iso
            self.repository.update_task_status(
                workflow_id=workflow.id,
                task_id=task.task_id,
                status="running",
                started_at=now_iso,
            )

            # Record operation in ProjectRepository for non-destructive audit log
            op_record = self.project_service.repository.create_operation(
                project_id=project_id,
                tool_name=task.tool_name,
                parameters=validated_params.model_dump(),
                input_asset_ids=[input_asset_id],
            )

            # Execute tool with retries
            success = False
            last_err: str | None = None
            out_asset: Asset | None = None

            for attempt in range(task.max_retries + 1):
                task.retry_count = attempt
                try:
                    input_bytes, _, _ = self.project_service.get_asset_file_bytes(input_asset_id)
                    output_bytes, output_meta = tool.handler(
                        self.image_engine, input_bytes, validated_params
                    )

                    # Compute output filename
                    base_name = Path(input_asset.original_filename).stem
                    tool_suffix = task.tool_name.split(".")[-1]
                    ext = FORMAT_EXTENSIONS.get(output_meta.format, "png")
                    out_filename = f"{base_name}_{tool_suffix}.{ext}"

                    # Store new versioned asset
                    out_asset = self.project_service.add_asset_from_bytes(
                        project_id=project_id,
                        image_bytes=output_bytes,
                        original_filename=out_filename,
                        parent_asset_id=input_asset_id,
                        metadata={
                            "generated_by_tool": task.tool_name,
                            "workflow_id": workflow.id,
                            "task_id": task.task_id,
                            "operation_id": op_record.id,
                            **output_meta.model_dump(),
                        },
                    )

                    # Validate quality
                    val_report = self.validation_service.validate_asset(
                        asset=out_asset,
                        expected_project_id=project_id,
                    )

                    if not val_report.passed:
                        last_err = f"Quality check failed: {val_report.summary}"
                        continue

                    # Mark operation succeeded
                    self.project_service.repository.update_operation(
                        operation_id=op_record.id,
                        status="succeeded",
                        output_asset_ids=[out_asset.id],
                    )

                    success = True
                    break
                except Exception as exc:
                    last_err = str(exc)

            if success and out_asset:
                task.status = "succeeded"
                task.output_asset_id = out_asset.id
                task.completed_at = utc_now_iso()
                task_outputs[task.task_id] = out_asset.id
                task_status[task.task_id] = "succeeded"
                final_assets.append(out_asset.id)
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="succeeded",
                    output_asset_id=out_asset.id,
                    completed_at=task.completed_at,
                )
            else:
                task.status = "failed"
                task.error = last_err or "Unknown tool execution failure."
                task.completed_at = utc_now_iso()
                task_status[task.task_id] = "failed"
                self.project_service.repository.update_operation(
                    operation_id=op_record.id,
                    status="failed",
                    error=task.error,
                )
                self.repository.update_task_status(
                    workflow_id=workflow.id,
                    task_id=task.task_id,
                    status="failed",
                    error=task.error,
                    completed_at=task.completed_at,
                )

        # Final workflow status assessment
        all_succeeded = all(t.status == "succeeded" for t in workflow.tasks)
        any_succeeded = any(t.status == "succeeded" for t in workflow.tasks)
        completed_at = utc_now_iso()

        if all_succeeded:
            workflow.status = "completed"
        elif any_succeeded:
            workflow.status = "partially_completed"
        else:
            workflow.status = "failed"

        workflow.completed_at = completed_at
        workflow.final_asset_ids = final_assets

        self.repository.update_workflow_status(
            workflow_id=workflow.id,
            status=workflow.status,
            final_asset_ids=final_assets,
            completed_at=completed_at,
        )

        return workflow
