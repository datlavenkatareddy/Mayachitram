from pydantic import BaseModel, Field


class ImageAnalysisResponse(BaseModel):
    engine: str = "image"
    provider: str
    model: str
    description: str
    objects: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(
        default_factory=lambda: [
            "Object labels are descriptive observations, not pixel-accurate bounding boxes."
        ]
    )
