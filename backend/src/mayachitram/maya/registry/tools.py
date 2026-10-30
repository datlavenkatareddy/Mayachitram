from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from mayachitram.engines.image.schemas import (
    BrightnessParams,
    CompressParams,
    ContrastParams,
    ConvertFormatParams,
    CropParams,
    FlipParams,
    ImageMetadata,
    ResizeParams,
    RotateParams,
    SaturationParams,
    TemperatureParams,
)
from mayachitram.maya.registry.adapters import (
    BaseEngineAdapter,
    DesignEngineAdapter,
    VideoEngineAdapter,
)


class ToolDefinition(BaseModel):
    name: str
    description: str
    category: str
    engine: str = "image"
    is_destructive: bool = False
    requires_approval: bool = False
    timeout_seconds: int = 30
    max_retries: int = 1
    version: str = "1.0.0"
    parameters_schema: dict[str, Any]
    params_class_name: str


class RegisteredTool:
    """Internal registry wrapper holding metadata and execution callable."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        params_class: type[BaseModel],
        handler: Callable[[Any, bytes, Any], tuple[bytes, ImageMetadata]],
        is_destructive: bool = False,
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        max_retries: int = 1,
        version: str = "1.0.0",
        engine: str = "image",
    ) -> None:
        self.name = name
        self.description = description
        self.category = category
        self.engine = engine
        self.params_class = params_class
        self.handler = handler
        self.is_destructive = is_destructive
        self.requires_approval = requires_approval or is_destructive
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.version = version

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            engine=self.engine,
            is_destructive=self.is_destructive,
            requires_approval=self.requires_approval,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            version=self.version,
            parameters_schema=self.params_class.model_json_schema(),
            params_class_name=self.params_class.__name__,
        )


class ToolRegistry:
    """Central registry maintaining typed tool definitions for manual UI controls and Maya AI planner."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._adapters: dict[str, BaseEngineAdapter] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        params_class: type[BaseModel],
        handler: Callable[[Any, bytes, Any], tuple[bytes, ImageMetadata]],
        is_destructive: bool = False,
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        max_retries: int = 1,
        version: str = "1.0.0",
        engine: str = "image",
    ) -> None:
        self._tools[name] = RegisteredTool(
            name=name,
            description=description,
            category=category,
            params_class=params_class,
            handler=handler,
            is_destructive=is_destructive,
            requires_approval=requires_approval,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            version=version,
            engine=engine,
        )

    def register_adapter(self, adapter: BaseEngineAdapter) -> None:
        self._adapters[adapter.engine_id] = adapter

    def get_adapter(self, engine_id: str) -> BaseEngineAdapter | None:
        return self._adapters.get(engine_id)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def list_tools(self, engine: str | None = None) -> list[ToolDefinition]:
        tools = self._tools.values()
        if engine:
            tools = [t for t in tools if t.engine == engine]
        return [tool.to_definition() for tool in tools]

    def get_definitions_for_ai(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_class.model_json_schema(),
                },
            }
            for tool in self._tools.values()
        ]


def get_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    # Register adapters
    registry.register_adapter(DesignEngineAdapter())
    registry.register_adapter(VideoEngineAdapter())

    # image.resize
    registry.register(
        name="image.resize",
        description="Resize an image to specific pixel dimensions with optional aspect-ratio preservation.",
        category="image",
        engine="image",
        params_class=ResizeParams,
        handler=lambda engine, data, params: engine.resize(data, params),
        timeout_seconds=15,
    )

    # image.crop
    registry.register(
        name="image.crop",
        description="Crop an image using rectangular bounds (left, top, width, height).",
        category="image",
        engine="image",
        params_class=CropParams,
        handler=lambda engine, data, params: engine.crop(data, params),
        timeout_seconds=15,
    )

    # image.rotate
    registry.register(
        name="image.rotate",
        description="Rotate an image clockwise by given degrees (e.g. 90, 180, 270).",
        category="image",
        engine="image",
        params_class=RotateParams,
        handler=lambda engine, data, params: engine.rotate(data, params),
        timeout_seconds=15,
    )

    # image.flip
    registry.register(
        name="image.flip",
        description="Flip an image horizontally, vertically, or both.",
        category="image",
        engine="image",
        params_class=FlipParams,
        handler=lambda engine, data, params: engine.flip(data, params),
        timeout_seconds=15,
    )

    # image.convert_format
    registry.register(
        name="image.convert_format",
        description="Convert an image to JPEG, PNG, or WebP with configurable quality.",
        category="image",
        engine="image",
        params_class=ConvertFormatParams,
        handler=lambda engine, data, params: engine.convert_format(data, params),
        timeout_seconds=20,
    )

    # image.compress
    registry.register(
        name="image.compress",
        description="Reduce file size by applying lossy compression quality settings.",
        category="image",
        engine="image",
        params_class=CompressParams,
        handler=lambda engine, data, params: engine.compress(data, params),
        timeout_seconds=20,
    )

    # image.adjust_brightness
    registry.register(
        name="image.adjust_brightness",
        description="Adjust image brightness (factor 1.0 is unchanged; <1.0 darker; >1.0 brighter).",
        category="image",
        engine="image",
        params_class=BrightnessParams,
        handler=lambda engine, data, params: engine.adjust_brightness(data, params),
        timeout_seconds=15,
    )

    # image.adjust_contrast
    registry.register(
        name="image.adjust_contrast",
        description="Adjust image contrast (factor 1.0 is unchanged; <1.0 less contrast; >1.0 more contrast).",
        category="image",
        engine="image",
        params_class=ContrastParams,
        handler=lambda engine, data, params: engine.adjust_contrast(data, params),
        timeout_seconds=15,
    )

    # image.adjust_saturation
    registry.register(
        name="image.adjust_saturation",
        description="Adjust image color saturation (factor 1.0 is unchanged; 0.0 is grayscale).",
        category="image",
        engine="image",
        params_class=SaturationParams,
        handler=lambda engine, data, params: engine.adjust_saturation(data, params),
        timeout_seconds=15,
    )

    # image.adjust_temperature
    registry.register(
        name="image.adjust_temperature",
        description="Adjust color temperature balance (-100 cooler/blue, +100 warmer/amber).",
        category="image",
        engine="image",
        params_class=TemperatureParams,
        handler=lambda engine, data, params: engine.adjust_temperature(data, params),
        timeout_seconds=15,
    )

    return registry
