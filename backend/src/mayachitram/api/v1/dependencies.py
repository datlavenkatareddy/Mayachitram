from functools import lru_cache

from fastapi import Depends

from mayachitram.core.config import Settings, get_settings
from mayachitram.engines.image.service import ImageEngine
from mayachitram.maya.execution.service import ExecutionService
from mayachitram.maya.execution.workflow import WorkflowOrchestrator
from mayachitram.maya.planner.recommendations import CreativeRecommendationService
from mayachitram.maya.planner.service import MayaPlanner
from mayachitram.maya.registry.tools import ToolRegistry, get_default_tool_registry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.validation.service import QualityValidationService
from mayachitram.projects.repository import ProjectRepository
from mayachitram.projects.service import ProjectService
from mayachitram.storage.service import LocalStorageService, StorageService


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return LocalStorageService(root_dir=settings.storage_dir)


def get_image_engine(settings: Settings = Depends(get_settings)) -> ImageEngine:
    return ImageEngine(settings=settings)


def get_project_repository(settings: Settings = Depends(get_settings)) -> ProjectRepository:
    return ProjectRepository(db_path=settings.database_path)


def get_maya_repository(settings: Settings = Depends(get_settings)) -> MayaRepository:
    return MayaRepository(db_path=settings.database_path)


def get_project_service(
    repository: ProjectRepository = Depends(get_project_repository),
    storage: StorageService = Depends(get_storage_service),
    engine: ImageEngine = Depends(get_image_engine),
) -> ProjectService:
    return ProjectService(repository=repository, storage=storage, image_engine=engine)


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return get_default_tool_registry()


def get_validation_service(
    project_service: ProjectService = Depends(get_project_service),
) -> QualityValidationService:
    return QualityValidationService(project_service=project_service)


def get_workflow_orchestrator(
    maya_repo: MayaRepository = Depends(get_maya_repository),
    project_service: ProjectService = Depends(get_project_service),
    engine: ImageEngine = Depends(get_image_engine),
    registry: ToolRegistry = Depends(get_tool_registry),
    validation_service: QualityValidationService = Depends(get_validation_service),
) -> WorkflowOrchestrator:
    return WorkflowOrchestrator(
        repository=maya_repo,
        project_service=project_service,
        image_engine=engine,
        tool_registry=registry,
        validation_service=validation_service,
    )


def get_execution_service(
    registry: ToolRegistry = Depends(get_tool_registry),
    project_service: ProjectService = Depends(get_project_service),
    engine: ImageEngine = Depends(get_image_engine),
    maya_repo: MayaRepository = Depends(get_maya_repository),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> ExecutionService:
    return ExecutionService(
        tool_registry=registry,
        project_service=project_service,
        image_engine=engine,
        maya_repository=maya_repo,
        orchestrator=orchestrator,
    )


def get_maya_planner(
    settings: Settings = Depends(get_settings),
    registry: ToolRegistry = Depends(get_tool_registry),
    project_service: ProjectService = Depends(get_project_service),
    maya_repo: MayaRepository = Depends(get_maya_repository),
) -> MayaPlanner:
    return MayaPlanner(
        settings=settings,
        tool_registry=registry,
        project_service=project_service,
        maya_repository=maya_repo,
    )


def get_recommendations_service() -> CreativeRecommendationService:
    return CreativeRecommendationService()
