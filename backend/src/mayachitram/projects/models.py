from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Project(BaseModel):
    id: str
    name: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    asset_count: int = 0


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    settings: dict[str, Any] | None = None


class Asset(BaseModel):
    id: str
    project_id: str
    original_filename: str
    media_type: str
    storage_key: str
    file_size: int
    width: int
    height: int
    parent_asset_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class OperationRecord(BaseModel):
    id: str
    project_id: str
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_asset_ids: list[str] = Field(default_factory=list)
    output_asset_ids: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending | running | succeeded | failed
    error: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
