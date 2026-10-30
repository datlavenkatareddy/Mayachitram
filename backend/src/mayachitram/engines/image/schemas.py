from typing import Literal

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    format: str
    width: int
    height: int
    mode: str
    size_bytes: int
    aspect_ratio: float


class ResizeParams(BaseModel):
    width: int = Field(gt=0, le=8192, description="Target width in pixels")
    height: int = Field(gt=0, le=8192, description="Target height in pixels")
    preserve_aspect: bool = Field(default=True, description="Whether to preserve aspect ratio")
    fit_mode: Literal["contain", "cover", "stretch"] = Field(
        default="contain",
        description="Fit strategy when preserving aspect ratio: contain, cover, or stretch",
    )


class CropParams(BaseModel):
    left: int = Field(ge=0, description="Left coordinate of crop box")
    top: int = Field(ge=0, description="Top coordinate of crop box")
    width: int = Field(gt=0, description="Width of crop box")
    height: int = Field(gt=0, description="Height of crop box")


class RotateParams(BaseModel):
    degrees: float = Field(description="Rotation angle in degrees clockwise")
    expand: bool = Field(
        default=True, description="Whether to expand output canvas to hold rotated image"
    )


class FlipParams(BaseModel):
    horizontal: bool = Field(default=False, description="Flip horizontally")
    vertical: bool = Field(default=False, description="Flip vertically")


class ConvertFormatParams(BaseModel):
    target_format: Literal["JPEG", "PNG", "WEBP"] = Field(description="Target image format")
    quality: int = Field(default=85, ge=1, le=100, description="Compression quality (1-100)")


class CompressParams(BaseModel):
    quality: int = Field(default=80, ge=1, le=100, description="Compression quality (1-100)")
    target_format: Literal["JPEG", "WEBP", "PNG"] | None = Field(
        default=None,
        description="Target format; defaults to current or WebP for best compression",
    )


class BrightnessParams(BaseModel):
    factor: float = Field(
        ge=0.0,
        le=5.0,
        description="Brightness factor (1.0 = unchanged, <1.0 = darker, >1.0 = brighter)",
    )


class ContrastParams(BaseModel):
    factor: float = Field(ge=0.0, le=5.0, description="Contrast factor (1.0 = unchanged)")


class SaturationParams(BaseModel):
    factor: float = Field(
        ge=0.0, le=5.0, description="Color saturation factor (1.0 = unchanged, 0.0 = grayscale)"
    )


class TemperatureParams(BaseModel):
    shift: int = Field(
        ge=-100,
        le=100,
        description="Color temperature shift (-100 cooler/blue to +100 warmer/amber)",
    )


class ProcessResult(BaseModel):
    metadata: ImageMetadata
    output_bytes: bytes
    mime_type: str


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
