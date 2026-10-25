import io

from PIL import Image, UnidentifiedImageError

from mayachitram.core.config import Settings
from mayachitram.core.errors import ImageValidationError
from mayachitram.engines.image.providers.groq_vision import GroqVisionProvider
from mayachitram.engines.image.schemas import ImageAnalysisResponse

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageEngine:
    """Validates image input and delegates inference to the configured Groq provider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def analyze(self, image_bytes: bytes, declared_content_type: str | None) -> ImageAnalysisResponse:
        if not image_bytes:
            raise ImageValidationError("The uploaded file is empty.")
        if len(image_bytes) > self._settings.max_upload_bytes:
            raise ImageValidationError("The uploaded image exceeds the configured size limit.")
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageValidationError("The uploaded file is not a valid supported image.") from exc
        mime_type = ALLOWED_FORMATS.get(image_format or "")
        if mime_type is None:
            raise ImageValidationError("Supported image formats are JPEG, PNG, and WebP.")
        # Detected format is authoritative; never trust the client MIME header alone.
        provider = GroqVisionProvider(self._settings)
        return await provider.analyze(image_bytes, mime_type)
