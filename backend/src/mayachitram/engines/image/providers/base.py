from typing import Protocol

from mayachitram.engines.image.schemas import ImageAnalysisResponse


class VisionProvider(Protocol):
    name: str

    async def analyze(self, image_bytes: bytes, mime_type: str) -> ImageAnalysisResponse:
        ...
