from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from mayachitram.api.v1.dependencies import get_project_service
from mayachitram.core.config import get_settings
from mayachitram.core.errors import ImageValidationError
from mayachitram.projects.models import (
    Asset,
    OperationRecord,
    Project,
    ProjectCreate,
    ProjectUpdate,
)
from mayachitram.projects.service import ProjectService

router = APIRouter()


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return service.create_project(data)


@router.get("", response_model=list[Project])
def list_projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ProjectService = Depends(get_project_service),
) -> list[Project]:
    return service.list_projects(limit=limit, offset=offset)


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return service.get_project(project_id)


@router.patch("/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return service.update_project(project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Response:
    service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Asset Management ---


@router.post("/{project_id}/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    parent_asset_id: str | None = Query(default=None),
    service: ProjectService = Depends(get_project_service),
) -> Asset:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if not content:
        raise ImageValidationError("Uploaded asset file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise ImageValidationError(
            f"Uploaded asset exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    return service.add_asset_from_bytes(
        project_id=project_id,
        image_bytes=content,
        original_filename=file.filename or "image.png",
        parent_asset_id=parent_asset_id,
    )


@router.get("/{project_id}/assets", response_model=list[Asset])
def list_assets(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: ProjectService = Depends(get_project_service),
) -> list[Asset]:
    return service.list_assets(project_id=project_id, limit=limit, offset=offset)


@router.get("/{project_id}/assets/{asset_id}", response_model=Asset)
def get_asset(
    project_id: str,
    asset_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Asset:
    asset = service.get_asset(asset_id)
    if asset.project_id != project_id:
        raise ImageValidationError(f"Asset '{asset_id}' does not belong to project '{project_id}'.")
    return asset


@router.get("/{project_id}/assets/{asset_id}/file")
def get_asset_file(
    project_id: str,
    asset_id: str,
    download: bool = Query(default=False),
    service: ProjectService = Depends(get_project_service),
) -> FileResponse:
    asset = service.get_asset(asset_id)
    if asset.project_id != project_id:
        raise ImageValidationError(f"Asset '{asset_id}' does not belong to project '{project_id}'.")
    path = service.get_asset_file_path(asset_id)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{asset.original_filename}"'
    return FileResponse(
        path=path,
        media_type=asset.media_type,
        filename=asset.original_filename if download else None,
        headers=headers,
    )


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    project_id: str,
    asset_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Response:
    asset = service.get_asset(asset_id)
    if asset.project_id != project_id:
        raise ImageValidationError(f"Asset '{asset_id}' does not belong to project '{project_id}'.")
    service.delete_asset(asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Operations History ---


@router.get("/{project_id}/operations", response_model=list[OperationRecord])
def list_operations(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: ProjectService = Depends(get_project_service),
) -> list[OperationRecord]:
    return service.list_operations(project_id=project_id, limit=limit)
