import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from mayachitram.maya.schemas import (
    ConversationMessage,
    ConversationSession,
    MessageType,
    ProjectPreferences,
    TaskStatus,
    Workflow,
    WorkflowStatus,
    WorkflowTask,
)
from mayachitram.projects.models import utc_now_iso


class MayaRepository:
    """SQLite-backed persistence repository for Maya conversations, workflows, tasks, and preferences."""

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
                CREATE TABLE IF NOT EXISTS maya_conversations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS maya_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES maya_conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL DEFAULT 'text',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS maya_workflows (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    execution_mode TEXT NOT NULL DEFAULT 'execute',
                    final_asset_ids TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS maya_workflow_tasks (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL REFERENCES maya_workflows(id) ON DELETE CASCADE,
                    task_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    parameters TEXT NOT NULL DEFAULT '{}',
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'pending',
                    input_asset_id TEXT,
                    output_asset_id TEXT,
                    requires_approval INTEGER NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 1,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS maya_preferences (
                    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
                    brand_colors TEXT NOT NULL DEFAULT '[]',
                    brand_fonts TEXT NOT NULL DEFAULT '[]',
                    preferred_aspect_ratios TEXT NOT NULL DEFAULT '[]',
                    preferred_export_formats TEXT NOT NULL DEFAULT '[]',
                    default_execution_mode TEXT NOT NULL DEFAULT 'execute',
                    custom_instructions TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_maya_conv_proj ON maya_conversations(project_id);
                CREATE INDEX IF NOT EXISTS idx_maya_msg_conv ON maya_messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_maya_wf_proj ON maya_workflows(project_id);
                CREATE INDEX IF NOT EXISTS idx_maya_tasks_wf ON maya_workflow_tasks(workflow_id);
            """)

    # --- Conversation Sessions & Messages ---

    def get_or_create_conversation(
        self, project_id: str, conversation_id: str | None = None, title: str = "Chat with Maya"
    ) -> ConversationSession:
        with self._get_connection() as conn:
            if conversation_id:
                row = conn.execute(
                    "SELECT id, project_id, title, created_at, updated_at FROM maya_conversations WHERE id = ? AND project_id = ?",
                    (conversation_id, project_id),
                ).fetchone()
                if row:
                    messages = self.get_messages(row["id"])
                    return ConversationSession(
                        id=row["id"],
                        project_id=row["project_id"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        messages=messages,
                    )

            # Check if there is already a conversation for this project
            existing = conn.execute(
                "SELECT id, project_id, title, created_at, updated_at FROM maya_conversations WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            if existing:
                messages = self.get_messages(existing["id"])
                return ConversationSession(
                    id=existing["id"],
                    project_id=existing["project_id"],
                    title=existing["title"],
                    created_at=existing["created_at"],
                    updated_at=existing["updated_at"],
                    messages=messages,
                )

            # Create new conversation session
            new_id = str(uuid.uuid4())
            now = utc_now_iso()
            conn.execute(
                "INSERT INTO maya_conversations (id, project_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (new_id, project_id, title, now, now),
            )
            return ConversationSession(
                id=new_id,
                project_id=project_id,
                title=title,
                created_at=now,
                updated_at=now,
                messages=[],
            )

    def list_conversations(self, project_id: str) -> list[ConversationSession]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, project_id, title, created_at, updated_at FROM maya_conversations WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
            return [
                ConversationSession(
                    id=row["id"],
                    project_id=row["project_id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    messages=[],
                )
                for row in rows
            ]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        message_type: MessageType = "text",
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        msg_id = str(uuid.uuid4())
        now = utc_now_iso()
        meta_json = json.dumps(metadata or {})
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO maya_messages (id, conversation_id, role, content, message_type, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id, conversation_id, role, content, message_type, meta_json, now),
            )
            conn.execute(
                "UPDATE maya_conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return ConversationMessage(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            created_at=now,
        )

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[ConversationMessage]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, conversation_id, role, content, message_type, metadata, created_at FROM maya_messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
            messages: list[ConversationMessage] = []
            for r in rows:
                try:
                    meta = json.loads(r["metadata"])
                except Exception:
                    meta = {}
                messages.append(
                    ConversationMessage(
                        id=r["id"],
                        conversation_id=r["conversation_id"],
                        role=r["role"],
                        content=r["content"],
                        message_type=r["message_type"],
                        metadata=meta,
                        created_at=r["created_at"],
                    )
                )
            return messages

    # --- Workflows & Tasks ---

    def create_workflow(
        self,
        project_id: str,
        title: str,
        description: str,
        tasks: list[WorkflowTask],
        execution_mode: str = "execute",
    ) -> Workflow:
        wf_id = str(uuid.uuid4())
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maya_workflows (id, project_id, title, description, status, execution_mode, final_asset_ids, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'draft', ?, '[]', ?, ?)
                """,
                (wf_id, project_id, title, description, execution_mode, now, now),
            )
            for t in tasks:
                t_row_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO maya_workflow_tasks (
                        id, workflow_id, task_id, tool_name, description, parameters, dependencies,
                        status, input_asset_id, output_asset_id, requires_approval, retry_count, max_retries, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t_row_id,
                        wf_id,
                        t.task_id,
                        t.tool_name,
                        t.description,
                        json.dumps(t.parameters),
                        json.dumps(t.dependencies),
                        t.status,
                        t.input_asset_id,
                        t.output_asset_id,
                        1 if t.requires_approval else 0,
                        t.retry_count,
                        t.max_retries,
                        t.error,
                    ),
                )
        return Workflow(
            id=wf_id,
            project_id=project_id,
            title=title,
            description=description,
            tasks=tasks,
            status="draft",
            execution_mode=execution_mode,  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
        )

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        with self._get_connection() as conn:
            wf_row = conn.execute(
                "SELECT id, project_id, title, description, status, execution_mode, final_asset_ids, created_at, updated_at, completed_at FROM maya_workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
            if not wf_row:
                return None

            task_rows = conn.execute(
                "SELECT task_id, tool_name, description, parameters, dependencies, status, input_asset_id, output_asset_id, requires_approval, retry_count, max_retries, error, started_at, completed_at FROM maya_workflow_tasks WHERE workflow_id = ? ORDER BY rowid ASC",
                (workflow_id,),
            ).fetchall()

            tasks: list[WorkflowTask] = []
            for tr in task_rows:
                tasks.append(
                    WorkflowTask(
                        task_id=tr["task_id"],
                        tool_name=tr["tool_name"],
                        description=tr["description"],
                        parameters=json.loads(tr["parameters"]),
                        dependencies=json.loads(tr["dependencies"]),
                        status=tr["status"],
                        input_asset_id=tr["input_asset_id"],
                        output_asset_id=tr["output_asset_id"],
                        requires_approval=bool(tr["requires_approval"]),
                        retry_count=tr["retry_count"],
                        max_retries=tr["max_retries"],
                        error=tr["error"],
                        started_at=tr["started_at"],
                        completed_at=tr["completed_at"],
                    )
                )

            final_asset_ids = json.loads(wf_row["final_asset_ids"])
            return Workflow(
                id=wf_row["id"],
                project_id=wf_row["project_id"],
                title=wf_row["title"],
                description=wf_row["description"],
                tasks=tasks,
                status=wf_row["status"],
                execution_mode=wf_row["execution_mode"],
                created_at=wf_row["created_at"],
                updated_at=wf_row["updated_at"],
                completed_at=wf_row["completed_at"],
                final_asset_ids=final_asset_ids,
            )

    def list_workflows(self, project_id: str, limit: int = 20) -> list[Workflow]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM maya_workflows WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
            workflows: list[Workflow] = []
            for r in rows:
                wf = self.get_workflow(r["id"])
                if wf:
                    workflows.append(wf)
            return workflows

    def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        final_asset_ids: list[str] | None = None,
        completed_at: str | None = None,
    ) -> None:
        now = utc_now_iso()
        with self._get_connection() as conn:
            if final_asset_ids is not None:
                conn.execute(
                    "UPDATE maya_workflows SET status = ?, final_asset_ids = ?, updated_at = ?, completed_at = COALESCE(?, completed_at) WHERE id = ?",
                    (status, json.dumps(final_asset_ids), now, completed_at, workflow_id),
                )
            else:
                conn.execute(
                    "UPDATE maya_workflows SET status = ?, updated_at = ?, completed_at = COALESCE(?, completed_at) WHERE id = ?",
                    (status, now, completed_at, workflow_id),
                )

    def update_task_status(
        self,
        workflow_id: str,
        task_id: str,
        status: TaskStatus,
        output_asset_id: str | None = None,
        error: str | None = None,
        retry_count: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        with self._get_connection() as conn:
            updates = ["status = ?"]
            params: list[Any] = [status]
            if output_asset_id is not None:
                updates.append("output_asset_id = ?")
                params.append(output_asset_id)
            if error is not None:
                updates.append("error = ?")
                params.append(error)
            if retry_count is not None:
                updates.append("retry_count = ?")
                params.append(retry_count)
            if started_at is not None:
                updates.append("started_at = ?")
                params.append(started_at)
            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at)
            params.extend([workflow_id, task_id])
            conn.execute(
                f"UPDATE maya_workflow_tasks SET {', '.join(updates)} WHERE workflow_id = ? AND task_id = ?",
                params,
            )

    # --- Project Preferences ---

    def get_preferences(self, project_id: str) -> ProjectPreferences:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT project_id, brand_colors, brand_fonts, preferred_aspect_ratios, preferred_export_formats, default_execution_mode, custom_instructions FROM maya_preferences WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if not row:
                return ProjectPreferences(project_id=project_id)
            return ProjectPreferences(
                project_id=row["project_id"],
                brand_colors=json.loads(row["brand_colors"]),
                brand_fonts=json.loads(row["brand_fonts"]),
                preferred_aspect_ratios=json.loads(row["preferred_aspect_ratios"]),
                preferred_export_formats=json.loads(row["preferred_export_formats"]),
                default_execution_mode=row["default_execution_mode"],
                custom_instructions=row["custom_instructions"],
            )

    def save_preferences(self, prefs: ProjectPreferences) -> ProjectPreferences:
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO maya_preferences (
                    project_id, brand_colors, brand_fonts, preferred_aspect_ratios, preferred_export_formats,
                    default_execution_mode, custom_instructions, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    brand_colors = excluded.brand_colors,
                    brand_fonts = excluded.brand_fonts,
                    preferred_aspect_ratios = excluded.preferred_aspect_ratios,
                    preferred_export_formats = excluded.preferred_export_formats,
                    default_execution_mode = excluded.default_execution_mode,
                    custom_instructions = excluded.custom_instructions,
                    updated_at = excluded.updated_at
                """,
                (
                    prefs.project_id,
                    json.dumps(prefs.brand_colors),
                    json.dumps(prefs.brand_fonts),
                    json.dumps(prefs.preferred_aspect_ratios),
                    json.dumps(prefs.preferred_export_formats),
                    prefs.default_execution_mode,
                    prefs.custom_instructions,
                    now,
                ),
            )
        return prefs
