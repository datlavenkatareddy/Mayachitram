import io

import pytest
from PIL import Image

from mayachitram.core.config import Settings
from mayachitram.core.errors import StorageError
from mayachitram.engines.image.service import ImageEngine
from mayachitram.projects.models import ProjectCreate
from mayachitram.projects.repository import ProjectRepository
from mayachitram.projects.service import ProjectService
from mayachitram.storage.service import LocalStorageService


def make_png_bytes(width: int = 150, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), (10, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_storage_safety_and_traversal_guard(tmp_path):
    storage = LocalStorageService(root_dir=tmp_path / "storage")
    key = storage.save(b"test-bytes", "txt", prefix="assets")
    assert storage.exists(key)
    assert storage.read(key) == b"test-bytes"

    # Traversal attempt must be blocked
    with pytest.raises(StorageError):
        storage.read("../../../etc/passwd")

    with pytest.raises(StorageError):
        storage.get_absolute_path("..\\..\\windows\\system32")


def test_projects_and_assets_lifecycle(tmp_path):
    data_dir = tmp_path / "data"
    settings = Settings(MAYACHITRAM_DATA_DIR=data_dir)
    repo = ProjectRepository(db_path=settings.database_path)
    storage = LocalStorageService(root_dir=settings.storage_dir)
    engine = ImageEngine(settings=settings)
    service = ProjectService(repository=repo, storage=storage, image_engine=engine)

    # 1. Create Project
    project = service.create_project(
        ProjectCreate(name="Studio Shoot", description="Fashion photoshoot session")
    )
    assert project.id is not None
    assert project.name == "Studio Shoot"

    # 2. Add Asset
    img_data = make_png_bytes(300, 200)
    asset = service.add_asset_from_bytes(
        project_id=project.id,
        image_bytes=img_data,
        original_filename="model_raw.png",
    )
    assert asset.width == 300
    assert asset.height == 200
    assert asset.media_type == "image/png"
    assert storage.exists(asset.storage_key)

    # 3. List Assets
    assets = service.list_assets(project.id)
    assert len(assets) == 1
    assert assets[0].id == asset.id

    # 4. Read Asset File
    read_data, media_type, filename = service.get_asset_file_bytes(asset.id)
    assert len(read_data) == len(img_data)
    assert media_type == "image/png"
    assert filename == "model_raw.png"

    # 5. Simulate Server Restart: re-open repository from same SQLite db file
    reopened_repo = ProjectRepository(db_path=settings.database_path)
    reopened_project = reopened_repo.get_project(project.id)
    assert reopened_project is not None
    assert reopened_project.name == "Studio Shoot"
    assert reopened_project.asset_count == 1

    reopened_assets = reopened_repo.list_assets(project.id)
    assert len(reopened_assets) == 1
    assert reopened_assets[0].width == 300

    # 6. Delete Project (cascade clean-up)
    service.delete_project(project.id)
    assert not storage.exists(asset.storage_key)
    assert reopened_repo.get_project(project.id) is None


def test_project_api_endpoints(client):
    # Create project via API
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "API Test Project", "description": "Testing endpoints"},
    )
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Upload asset to project
    png_data = make_png_bytes(120, 80)
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/assets",
        files={"file": ("photo.png", png_data, "image/png")},
    )
    assert upload_res.status_code == 201
    asset_id = upload_res.json()["id"]
    assert upload_res.json()["width"] == 120
    assert upload_res.json()["height"] == 80

    # Get asset file
    file_res = client.get(f"/api/v1/projects/{proj_id}/assets/{asset_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "image/png"
    assert len(file_res.content) == len(png_data)

    # Clean up project
    del_res = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_res.status_code == 204
