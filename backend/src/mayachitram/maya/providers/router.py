import logging

from mayachitram.core.config import Settings
from mayachitram.maya.providers.base import BaseModelProvider
from mayachitram.maya.providers.groq_provider import GroqModelProvider
from mayachitram.maya.providers.rule_based_provider import RuleBasedSemanticProvider

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Intelligent provider router with automatic fallback and error normalization."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.fallback_provider = RuleBasedSemanticProvider()
        self.primary_provider: BaseModelProvider | None = None

        if settings.groq_api_key:
            try:
                self.primary_provider = GroqModelProvider(
                    api_key=settings.groq_api_key,
                    model_name=settings.groq_chat_model,
                    timeout_seconds=settings.groq_timeout_seconds,
                )
            except Exception as exc:
                logger.warning("Could not initialize primary Groq provider: %s", exc)
                self.primary_provider = None

    @property
    def active_provider_id(self) -> str:
        return self.primary_provider.provider_id if self.primary_provider else self.fallback_provider.provider_id

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        """
        Returns (content, provider_used).
        Tries primary provider first, falls back to local semantic provider on error.
        """
        if self.primary_provider:
            try:
                content = await self.primary_provider.generate_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    json_mode=json_mode,
                    temperature=temperature,
                )
                return content, self.primary_provider.provider_id
            except Exception as exc:
                logger.warning("Primary provider failed, invoking fallback: %s", exc)

        # Fallback
        content = await self.fallback_provider.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            json_mode=json_mode,
            temperature=temperature,
        )
        return content, self.fallback_provider.provider_id
