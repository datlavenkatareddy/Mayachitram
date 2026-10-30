from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from mayachitram.core.errors import OperationError
from mayachitram.engines.image.schemas import (
    ImageMetadata,
)
from mayachitram.engines.image.service import ImageEngine


class BaseEngineAdapter(ABC):
    """Abstract base adapter for all creative engines communicating with Maya."""

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Engine identifier (e.g. 'image', 'design', 'video')."""
        pass

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Human-readable engine name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if the engine backend implementation is present and operational."""
        pass

    @abstractmethod
    def get_supported_operations(self) -> list[str]:
        """List of operations currently implemented and callable."""
        pass


class ImageEngineAdapter(BaseEngineAdapter):
    """Engine adapter for the local Pillow-based Image Engine."""

    def __init__(self, image_engine: ImageEngine) -> None:
        self.image_engine = image_engine

    @property
    def engine_id(self) -> str:
        return "image"

    @property
    def engine_name(self) -> str:
        return "Image Engine"

    @property
    def is_available(self) -> bool:
        return True

    def get_supported_operations(self) -> list[str]:
        return [
            "image.resize",
            "image.crop",
            "image.rotate",
            "image.flip",
            "image.convert_format",
            "image.compress",
            "image.adjust_brightness",
            "image.adjust_contrast",
            "image.adjust_saturation",
            "image.adjust_temperature",
        ]

    def execute(
        self, tool_name: str, input_bytes: bytes, validated_params: BaseModel
    ) -> tuple[bytes, ImageMetadata]:
        op_handlers = {
            "image.resize": lambda data, p: self.image_engine.resize(data, p),
            "image.crop": lambda data, p: self.image_engine.crop(data, p),
            "image.rotate": lambda data, p: self.image_engine.rotate(data, p),
            "image.flip": lambda data, p: self.image_engine.flip(data, p),
            "image.convert_format": lambda data, p: self.image_engine.convert_format(data, p),
            "image.compress": lambda data, p: self.image_engine.compress(data, p),
            "image.adjust_brightness": lambda data, p: self.image_engine.adjust_brightness(data, p),
            "image.adjust_contrast": lambda data, p: self.image_engine.adjust_contrast(data, p),
            "image.adjust_saturation": lambda data, p: self.image_engine.adjust_saturation(data, p),
            "image.adjust_temperature": lambda data, p: self.image_engine.adjust_temperature(data, p),
        }
        handler = op_handlers.get(tool_name)
        if not handler:
            raise OperationError(f"Image Engine operation '{tool_name}' not implemented.")
        return handler(input_bytes, validated_params)


# --- Collaborator Engine Interface Specifications ---

class DesignEngineAdapter(BaseEngineAdapter):
    """
    Adapter for the Design Engine.
    Developed in parallel by collaborator.
    Documents the required contract methods without mock or simulated execution.
    """

    def __init__(self, design_service: Any = None) -> None:
        self.design_service = design_service

    @property
    def engine_id(self) -> str:
        return "design"

    @property
    def engine_name(self) -> str:
        return "Design Engine"

    @property
    def is_available(self) -> bool:
        return self.design_service is not None and getattr(self.design_service, "is_ready", False)

    def get_supported_operations(self) -> list[str]:
        if not self.is_available:
            return []
        return [
            "design.create_canvas",
            "design.add_text",
            "design.apply_template",
            "design.export",
        ]

    def execute(self, tool_name: str, input_bytes: bytes, validated_params: BaseModel) -> Any:
        if not self.is_available:
            raise OperationError(
                f"Design Engine operation '{tool_name}' is currently unavailable. "
                "The Design Engine is being developed in parallel by collaborator. "
                "See docs/DESIGN_ENGINE_CONTRACT.md for the integration contract."
            )
        return self.design_service.execute(tool_name, input_bytes, validated_params)


class VideoEngineAdapter(BaseEngineAdapter):
    """
    Adapter for the Video Engine.
    Developed in parallel by collaborator.
    Documents the required contract methods without mock or simulated execution.
    """

    def __init__(self, video_service: Any = None) -> None:
        self.video_service = video_service

    @property
    def engine_id(self) -> str:
        return "video"

    @property
    def engine_name(self) -> str:
        return "Video Engine"

    @property
    def is_available(self) -> bool:
        return self.video_service is not None and getattr(self.video_service, "is_ready", False)

    def get_supported_operations(self) -> list[str]:
        if not self.is_available:
            return []
        return [
            "video.trim",
            "video.concat",
            "video.add_subtitles",
            "video.export",
        ]

    def execute(self, tool_name: str, input_bytes: bytes, validated_params: BaseModel) -> Any:
        if not self.is_available:
            raise OperationError(
                f"Video Engine operation '{tool_name}' is currently unavailable. "
                "The Video Engine is being developed in parallel by collaborator. "
                "See docs/VIDEO_ENGINE_CONTRACT.md for the integration contract."
            )
        return self.video_service.execute(tool_name, input_bytes, validated_params)
