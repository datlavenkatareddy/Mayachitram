import os
import uuid
from pathlib import Path
from typing import Protocol

from mayachitram.core.errors import StorageError


class StorageService(Protocol):
    """Protocol defining file storage operations."""

    def save(self, data: bytes, extension: str, prefix: str = "assets") -> str: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> bool: ...

    def exists(self, storage_key: str) -> bool: ...

    def get_absolute_path(self, storage_key: str) -> Path: ...


class LocalStorageService:
    """Stores binary media assets in a managed application directory with traversal safety."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> Path:
        # Prevent path traversal: normalize and ensure path is strictly under root_dir
        cleaned_key = os.path.normpath(storage_key).lstrip("\\/.")
        target_path = (self.root_dir / cleaned_key).resolve()
        try:
            target_path.relative_to(self.root_dir)
        except ValueError as exc:
            raise StorageError(f"Access denied: illegal storage key '{storage_key}'") from exc
        return target_path

    def save(self, data: bytes, extension: str, prefix: str = "assets") -> str:
        clean_ext = extension.lstrip(".").lower()
        if not clean_ext:
            clean_ext = "bin"
        filename = f"{uuid.uuid4().hex}.{clean_ext}"
        relative_key = f"{prefix}/{filename}"
        target_path = self._resolve_safe_path(relative_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            target_path.write_bytes(data)
        except OSError as exc:
            raise StorageError(f"Failed to persist asset data: {exc}") from exc
        return relative_key.replace("\\", "/")

    def read(self, storage_key: str) -> bytes:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise StorageError(f"Asset file not found at storage key: {storage_key}")
        try:
            return target_path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Failed to read asset data: {exc}") from exc

    def delete(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(storage_key)
            if target_path.is_file():
                target_path.unlink()
                return True
            return False
        except Exception:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(storage_key)
            return target_path.is_file()
        except Exception:
            return False

    def get_absolute_path(self, storage_key: str) -> Path:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise StorageError(f"Asset file does not exist at storage key: {storage_key}")
        return target_path
