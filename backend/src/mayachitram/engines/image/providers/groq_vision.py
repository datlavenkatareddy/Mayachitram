import base64
import json

from groq import AsyncGroq

from mayachitram.core.config import Settings
from mayachitram.core.errors import ProviderAnalysisError, ProviderNotConfiguredError
from mayachitram.engines.image.schemas import ImageAnalysisResponse


class GroqVisionProvider:
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise ProviderNotConfiguredError(
                "Image analysis is not configured. Set GROQ_API_KEY in backend/.env."
            )
        self._model = settings.groq_vision_model
        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=settings.groq_timeout_seconds,
        )

    async def analyze(self, image_bytes: bytes, mime_type: str) -> ImageAnalysisResponse:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        prompt = (
            "Analyze this image for general-purpose image understanding. Return only valid JSON "
            "with keys: description (string, concise factual scene description), objects (array "
            "of short visible-object labels). Do not infer sensitive traits or identify people. "
            "Do not claim precise positions or bounding boxes. Be conservative when uncertain."
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{mime_type};base64,{encoded}", "detail": "auto"
                        }},
                    ],
                }],
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            description = payload.get("description")
            objects = payload.get("objects", [])
            if not isinstance(description, str) or not isinstance(objects, list):
                raise ValueError("Unexpected model response schema")
            return ImageAnalysisResponse(
                provider=self.name,
                model=self._model,
                description=description[:5000],
                objects=[str(item)[:160] for item in objects[:100]],
            )
        except Exception as exc:
            if isinstance(exc, ProviderNotConfiguredError):
                raise
            raise ProviderAnalysisError("The vision provider could not analyze this image.") from exc
