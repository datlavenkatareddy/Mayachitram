import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from mayachitram.projects.models import (
    Asset,
    OperationRecord,
    Project,
    utc_now_iso,
)


class ProjectRepository:
    """SQLite-backed persistent repository for projects, assets, and operation history."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    settings TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    original_filename TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    parent_asset_id TEXT REFERENCES assets(id) ON DELETE SET NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    tool_name TEXT NOT NULL,
                    parameters TEXT NOT NULL DEFAULT '{}',
                    input_asset_ids TEXT NOT NULL DEFAULT '[]',
                    output_asset_ids TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'pending',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_assets_project_id ON assets(project_id);
                CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at);
                CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id);
                CREATE INDEX IF NOT EXISTS idx_operations_created ON operations(created_at);
            """)

    # --- Project Operations ---

    def create_project(
        self, name: str, description: str | None = None, settings: dict[str, Any] | None = None
    ) -> Project:
        project_id = str(uuid.uuid4())
        now = utc_now_iso()
        settings_json = json.dumps(settings or {})
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, settings, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, name, description, settings_json, now, now),
            )
        return Project(
            id=project_id,
            name=name,
            description=description,
            settings=settings or {},
            created_at=now,
            updated_at=now,
            asset_count=0,
        )

    def get_project(self, project_id: str) -> Project | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT p.id, p.name, p.description, p.settings, p.created_at, p.updated_at,
                       COUNT(a.id) AS asset_count
                FROM projects p
                LEFT JOIN assets a ON p.id = a.project_id
                WHERE p.id = ?
                GROUP BY p.id
                """,
                (project_id,),
            ).fetchone()
            if not row:
                return None
            return Project(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                settings=json.loads(row["settings"] or "{}"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                asset_count=row["asset_count"],
            )

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[Project]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.name, p.description, p.settings, p.created_at, p.updated_at,
                       COUNT(a.id) AS asset_count
                FROM projects p
                LEFT JOIN assets a ON p.id = a.project_id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    settings=json.loads(row["settings"] or "{}"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    asset_count=row["asset_count"],
                )
                for row in rows
            ]

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Project | None:
        current = self.get_project(project_id)
        if not current:
            return None
        updated_name = name if name is not None else current.name
        updated_desc = description if description is not None else current.description
        updated_settings = settings if settings is not None else current.settings
        now = utc_now_iso()

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE projects
                SET name = ?, description = ?, settings = ?, updated_at = ?
                WHERE id = ?
                """,
                (updated_name, updated_desc, json.dumps(updated_settings), now, project_id),
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0

    # --- Asset Operations ---

    def create_asset(
        self,
        project_id: str,
        original_filename: str,
        media_type: str,
        storage_key: str,
        file_size: int,
        width: int,
        height: int,
        parent_asset_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Asset:
        asset_id = str(uuid.uuid4())
        now = utc_now_iso()
        meta_json = json.dumps(metadata or {})
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO assets (id, project_id, original_filename, media_type, storage_key,
                                   file_size, width, height, parent_asset_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    project_id,
                    original_filename,
                    media_type,
                    storage_key,
                    file_size,
                    width,
                    height,
                    parent_asset_id,
                    meta_json,
                    now,
                ),
            )
            # Update project updated_at
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))

        return Asset(
            id=asset_id,
            project_id=project_id,
            original_filename=original_filename,
            media_type=media_type,
            storage_key=storage_key,
            file_size=file_size,
            width=width,
            height=height,
            parent_asset_id=parent_asset_id,
            metadata=metadata or {},
            created_at=now,
        )

    def get_asset(self, asset_id: str) -> Asset | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
            if not row:
                return None
            return Asset(
                id=row["id"],
                project_id=row["project_id"],
                original_filename=row["original_filename"],
                media_type=row["media_type"],
                storage_key=row["storage_key"],
                file_size=row["file_size"],
                width=row["width"],
                height=row["height"],
                parent_asset_id=row["parent_asset_id"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
            )

    def list_assets(self, project_id: str, limit: int = 100, offset: int = 0) -> list[Asset]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM assets WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (project_id, limit, offset),
            ).fetchall()
            return [
                Asset(
                    id=row["id"],
                    project_id=row["project_id"],
                    original_filename=row["original_filename"],
                    media_type=row["media_type"],
                    storage_key=row["storage_key"],
                    file_size=row["file_size"],
                    width=row["width"],
                    height=row["height"],
                    parent_asset_id=row["parent_asset_id"],
                    metadata=json.loads(row["metadata"] or "{}"),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def delete_asset(self, asset_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            return cursor.rowcount > 0

    # --- Operation Records ---

    def create_operation(
        self,
        project_id: str,
        tool_name: str,
        parameters: dict[str, Any],
        input_asset_ids: list[str],
    ) -> OperationRecord:
        op_id = str(uuid.uuid4())
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO operations (id, project_id, tool_name, parameters, input_asset_ids,
                                        output_asset_ids, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'running', ?)
                """,
                (
                    op_id,
                    project_id,
                    tool_name,
                    json.dumps(parameters),
                    json.dumps(input_asset_ids),
                    json.dumps([]),
                    now,
                ),
            )
        return OperationRecord(
            id=op_id,
            project_id=project_id,
            tool_name=tool_name,
            parameters=parameters,
            input_asset_ids=input_asset_ids,
            output_asset_ids=[],
            status="running",
            created_at=now,
        )

    def update_operation(
        self,
        operation_id: str,
        status: str,
        output_asset_ids: list[str] | None = None,
        error: str | None = None,
    ) -> OperationRecord | None:
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE operations
                SET status = ?, output_asset_ids = coalesce(?, output_asset_ids), error = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(output_asset_ids) if output_asset_ids is not None else None,
                    error,
                    now,
                    operation_id,
                ),
            )
        return self.get_operation(operation_id)

    def get_operation(self, operation_id: str) -> OperationRecord | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM operations WHERE id = ?", (operation_id,)).fetchone()
            if not row:
                return None
            return OperationRecord(
                id=row["id"],
                project_id=row["project_id"],
                tool_name=row["tool_name"],
                parameters=json.loads(row["parameters"] or "{}"),
                input_asset_ids=json.loads(row["input_asset_ids"] or "[]"),
                output_asset_ids=json.loads(row["output_asset_ids"] or "[]"),
                status=row["status"],
                error=row["error"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
            )

    def list_operations(self, project_id: str, limit: int = 50) -> list[OperationRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM operations WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
            return [
                OperationRecord(
                    id=row["id"],
                    project_id=row["project_id"],
                    tool_name=row["tool_name"],
                    parameters=json.loads(row["parameters"] or "{}"),
                    input_asset_ids=json.loads(row["input_asset_ids"] or "[]"),
                    output_asset_ids=json.loads(row["output_asset_ids"] or "[]"),
                    status=row["status"],
                    error=row["error"],
                    created_at=row["created_at"],
                    completed_at=row["completed_at"],
                )
                for row in rows
            ]
