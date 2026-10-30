from abc import ABC, abstractmethod
from enum import Enum


class ModelCapability(str, Enum):
    TEXT_GENERATION = "text_generation"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    VISION_UNDERSTANDING = "vision_understanding"


class BaseModelProvider(ABC):
    """Abstract base provider for LLM inference in Maya AI."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def get_capabilities(self) -> list[ModelCapability]:
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """Generate response text or JSON string from provider."""
        pass
