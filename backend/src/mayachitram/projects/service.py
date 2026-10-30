from pathlib import Path
from typing import Any

from mayachitram.core.errors import NotFoundError
from mayachitram.engines.image.service import FORMAT_EXTENSIONS, ImageEngine
from mayachitram.projects.models import (
    Asset,
    OperationRecord,
    Project,
    ProjectCreate,
    ProjectUpdate,
)
from mayachitram.projects.repository import ProjectRepository
from mayachitram.storage.service import StorageService


class ProjectService:
    """Coordinates project management, asset ingestion, and persistence."""

    def __init__(
        self,
        repository: ProjectRepository,
        storage: StorageService,
        image_engine: ImageEngine,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.image_engine = image_engine

    def create_project(self, data: ProjectCreate) -> Project:
        return self.repository.create_project(
            name=data.name,
            description=data.description,
            settings=data.settings,
        )

    def get_project(self, project_id: str) -> Project:
        project = self.repository.get_project(project_id)
        if not project:
            raise NotFoundError(f"Project '{project_id}' does not exist.")
        return project

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[Project]:
        return self.repository.list_projects(limit=limit, offset=offset)

    def update_project(self, project_id: str, data: ProjectUpdate) -> Project:
        updated = self.repository.update_project(
            project_id=project_id,
            name=data.name,
            description=data.description,
            settings=data.settings,
        )
        if not updated:
            raise NotFoundError(f"Project '{project_id}' does not exist.")
        return updated

    def delete_project(self, project_id: str) -> None:
        # Delete project assets from storage first
        assets = self.repository.list_assets(project_id, limit=5000)
        for asset in assets:
            self.storage.delete(asset.storage_key)
        deleted = self.repository.delete_project(project_id)
        if not deleted:
            raise NotFoundError(f"Project '{project_id}' does not exist.")

    def add_asset_from_bytes(
        self,
        project_id: str,
        image_bytes: bytes,
        original_filename: str,
        parent_asset_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Asset:
        # Ensure project exists
        self.get_project(project_id)

        # Validate with image engine
        meta = self.image_engine.get_metadata(image_bytes)
        ext = FORMAT_EXTENSIONS.get(meta.format, "png")
        media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"

        storage_key = self.storage.save(image_bytes, extension=ext, prefix=f"projects/{project_id}")

        meta_dict = meta.model_dump()
        if metadata:
            meta_dict.update(metadata)

        return self.repository.create_asset(
            project_id=project_id,
            original_filename=original_filename,
            media_type=media_type,
            storage_key=storage_key,
            file_size=len(image_bytes),
            width=meta.width,
            height=meta.height,
            parent_asset_id=parent_asset_id,
            metadata=meta_dict,
        )

    def get_asset(self, asset_id: str) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if not asset:
            raise NotFoundError(f"Asset '{asset_id}' does not exist.")
        return asset

    def get_asset_file_bytes(self, asset_id: str) -> tuple[bytes, str, str]:
        asset = self.get_asset(asset_id)
        data = self.storage.read(asset.storage_key)
        return data, asset.media_type, asset.original_filename

    def get_asset_file_path(self, asset_id: str) -> Path:
        asset = self.get_asset(asset_id)
        return self.storage.get_absolute_path(asset.storage_key)

    def list_assets(self, project_id: str, limit: int = 100, offset: int = 0) -> list[Asset]:
        self.get_project(project_id)
        return self.repository.list_assets(project_id, limit=limit, offset=offset)

    def delete_asset(self, asset_id: str) -> None:
        asset = self.get_asset(asset_id)
        self.storage.delete(asset.storage_key)
        self.repository.delete_asset(asset_id)

    def list_operations(self, project_id: str, limit: int = 50) -> list[OperationRecord]:
        self.get_project(project_id)
        return self.repository.list_operations(project_id, limit=limit)
