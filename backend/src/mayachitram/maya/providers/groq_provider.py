import logging
from typing import Any

from groq import AsyncGroq, AuthenticationError, InternalServerError, RateLimitError

from mayachitram.core.errors import ProviderAnalysisError, ProviderNotConfiguredError
from mayachitram.maya.providers.base import BaseModelProvider, ModelCapability

logger = logging.getLogger(__name__)


class GroqModelProvider(BaseModelProvider):
    """Groq API provider for fast open-weight model inference."""

    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile", timeout_seconds: float = 30.0) -> None:
        if not api_key:
            raise ProviderNotConfiguredError("GROQ_API_KEY is not configured.")
        self._model_name = model_name
        self._client = AsyncGroq(api_key=api_key, timeout=timeout_seconds)

    @property
    def provider_id(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model_name

    def get_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.TOOL_CALLING,
        ]

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        all_messages: list[dict[str, str]] = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": all_messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except RateLimitError as exc:
            logger.warning("Groq rate limit exceeded: %s", exc)
            raise ProviderAnalysisError("AI provider rate limit reached. Please retry in a few moments.") from exc
        except AuthenticationError as exc:
            logger.error("Groq authentication failure: %s", exc)
            raise ProviderNotConfiguredError("Invalid AI provider credentials.") from exc
        except InternalServerError as exc:
            logger.error("Groq internal server error: %s", exc)
            raise ProviderAnalysisError("AI provider is temporarily unavailable.") from exc
        except Exception as exc:
            logger.error("Groq inference error: %s", exc)
            raise ProviderAnalysisError(f"AI inference error: {exc}") from exc
