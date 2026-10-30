# MayaChitram Image Engine Documentation

The MayaChitram Image Engine is a high-performance, deterministic image processing service built on Pillow (PIL).

## 1. Safety Guardrails & Validation

Before any processing begins, every input is validated through `ImageEngine._open_and_validate()`:
- **Maximum Upload Bytes:** Enforces configurable upload size (default 20MB).
- **Decompression Bomb Protection:** Sets `Image.MAX_IMAGE_PIXELS = 50,000,000` to prevent malicious archive decompression exploits.
- **Maximum Dimensions:** Limits width and height to 8192px (`MAX_IMAGE_DIMENSION`).
- **MIME & Content Validation:** Inspects raw image bytes via `Image.open(stream).load()`. Enforces true image headers regardless of file extension or client-reported MIME headers.
- **Orientation Normalization:** Automatically applies `ImageOps.exif_transpose` so smartphone images with EXIF orientation metadata are properly rotated before coordinates are calculated.

---

## 2. Implemented Operations

| Tool Name | Parameters | Description |
|---|---|---|
| `image.resize` | `width`, `height`, `preserve_aspect`, `fit_mode` (`contain`, `cover`, `stretch`) | High-quality resampling using Lanczos filter. |
| `image.crop` | `left`, `top`, `width`, `height` | Pixel bounding box with boundary clipping and non-negative assertions. |
| `image.rotate` | `degrees`, `expand` | Clockwise rotation with Bicubic resampling; canvas expands to fit rotated boundaries when `expand=True`. |
| `image.flip` | `horizontal`, `vertical` | Lossless coordinate transpositions (`FLIP_LEFT_RIGHT`, `FLIP_TOP_BOTTOM`). |
| `image.convert_format` | `target_format` (`JPEG`, `PNG`, `WEBP`), `quality` (1-100) | Format transformation with color mode adaptations. |
| `image.compress` | `quality` (1-100), `target_format` | File size reduction using lossy encoding. |
| `image.adjust_brightness` | `factor` (0.0 to 5.0, 1.0=neutral) | Pillow `ImageEnhance.Brightness`. |
| `image.adjust_contrast` | `factor` (0.0 to 5.0, 1.0=neutral) | Pillow `ImageEnhance.Contrast`. |
| `image.adjust_saturation` | `factor` (0.0 to 5.0, 0.0=grayscale) | Pillow `ImageEnhance.Color`. |
| `image.adjust_temperature` | `shift` (-100 to +100) | Mathematical RGB lookup-table channel rebalancing. |
| `image.get_metadata` | none | Extracts dimensions, format, mode, aspect ratio, and size. |

---

## 3. Alpha Channel & Format Conversions

Converting between formats with varying alpha support can cause errors in unshielded pipelines:
- **PNG (RGBA) to JPEG:** JPEG does not support alpha channels. Attempting to save RGBA directly to JPEG raises `OSError: cannot write mode RGBA as JPEG`. MayaChitram automatically detects transparency, creates a clean white RGB canvas, and composites the transparent image over it using the alpha channel as a mask.
- **PNG to WebP:** WebP supports full 8-bit alpha transparency natively. Mode is retained as `RGBA`.
- **Palette Images:** Mode `P` images with palette transparency are converted to full `RGBA` before processing.

---

## 4. How to Add a New Image Operation

1. Define the parameter model in `engines/image/schemas.py`:
```python
class SharpnessParams(BaseModel):
    factor: float = Field(ge=0.0, le=5.0)
```
2. Implement the transformation method in `ImageEngine` (`engines/image/service.py`):
```python
def adjust_sharpness(self, image_bytes: bytes, params: SharpnessParams) -> tuple[bytes, ImageMetadata]:
    img, current_format = self._open_and_validate(image_bytes)
    enhancer = ImageEnhance.Sharpness(img)
    adjusted = enhancer.enhance(params.factor)
    return self._export_image(adjusted, current_format)
```
3. Register the tool in `maya/registry/tools.py`:
```python
registry.register(
    name="image.adjust_sharpness",
    description="Enhance or soften image sharpness.",
    category="image",
    params_class=SharpnessParams,
    handler=lambda engine, data, params: engine.adjust_sharpness(data, params),
)
```
4. Both manual UI and Maya conversational assistant will immediately recognize and execute the new tool!
