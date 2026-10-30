import io

from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

from mayachitram.core.config import Settings
from mayachitram.core.errors import ImageValidationError, OperationError
from mayachitram.engines.image.providers.groq_vision import GroqVisionProvider
from mayachitram.engines.image.schemas import (
    BrightnessParams,
    CompressParams,
    ContrastParams,
    ConvertFormatParams,
    CropParams,
    FlipParams,
    ImageAnalysisResponse,
    ImageMetadata,
    ResizeParams,
    RotateParams,
    SaturationParams,
    TemperatureParams,
)

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
FORMAT_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class ImageEngine:
    """Core image processing service providing verified, deterministic Pillow transformations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _open_and_validate(self, image_bytes: bytes) -> tuple[Image.Image, str]:
        if not image_bytes:
            raise ImageValidationError("The uploaded file is empty.")
        if len(image_bytes) > self._settings.max_upload_bytes:
            raise ImageValidationError(
                f"The uploaded image exceeds the maximum limit of {self._settings.max_upload_bytes // (1024 * 1024)} MB."
            )

        # Decompression bomb guard
        Image.MAX_IMAGE_PIXELS = self._settings.max_image_pixels

        try:
            stream = io.BytesIO(image_bytes)
            img = Image.open(stream)
            img.load()  # Read image content to catch truncated/corrupted files
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageValidationError("The uploaded file is not a valid supported image.") from exc

        raw_format = (img.format or "").upper()
        if raw_format == "JPG":
            raw_format = "JPEG"

        if raw_format not in ALLOWED_FORMATS:
            raise ImageValidationError(
                f"Unsupported image format '{raw_format}'. Supported formats are JPEG, PNG, and WebP."
            )

        if (
            img.width > self._settings.max_image_dimension
            or img.height > self._settings.max_image_dimension
        ):
            raise ImageValidationError(
                f"Image dimensions ({img.width}x{img.height}) exceed maximum allowed dimension of {self._settings.max_image_dimension}px."
            )

        # Normalize EXIF orientation if present
        try:
            img = ImageOps.exif_transpose(img) or img
        except Exception:
            pass

        return img, raw_format

    def _export_image(
        self,
        img: Image.Image,
        target_format: str,
        quality: int = 85,
    ) -> tuple[bytes, ImageMetadata]:
        target_format = target_format.upper()
        if target_format == "JPG":
            target_format = "JPEG"

        if target_format not in ALLOWED_FORMATS:
            target_format = "PNG"

        out_img = img
        save_kwargs: dict[str, object] = {}

        if target_format == "JPEG":
            save_kwargs["quality"] = max(1, min(100, quality))
            save_kwargs["optimize"] = True
            # JPEG cannot store alpha channel; composite over white
            if out_img.mode in ("RGBA", "LA") or (
                out_img.mode == "P" and "transparency" in out_img.info
            ):
                rgba = out_img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[3])
                out_img = background
            elif out_img.mode != "RGB":
                out_img = out_img.convert("RGB")
        elif target_format == "WEBP":
            save_kwargs["quality"] = max(1, min(100, quality))
            save_kwargs["method"] = 4
            if out_img.mode not in ("RGB", "RGBA"):
                out_img = out_img.convert("RGBA")
        elif target_format == "PNG":
            save_kwargs["optimize"] = True
            if out_img.mode not in ("RGB", "RGBA", "L"):
                out_img = out_img.convert("RGBA")

        buffer = io.BytesIO()
        try:
            out_img.save(buffer, format=target_format, **save_kwargs)
        except OSError as exc:
            raise OperationError(f"Failed to encode image as {target_format}: {exc}") from exc

        output_bytes = buffer.getvalue()
        metadata = ImageMetadata(
            format=target_format,
            width=out_img.width,
            height=out_img.height,
            mode=out_img.mode,
            size_bytes=len(output_bytes),
            aspect_ratio=round(out_img.width / out_img.height, 4) if out_img.height > 0 else 1.0,
        )
        return output_bytes, metadata

    def get_metadata(self, image_bytes: bytes) -> ImageMetadata:
        img, raw_format = self._open_and_validate(image_bytes)
        return ImageMetadata(
            format=raw_format,
            width=img.width,
            height=img.height,
            mode=img.mode,
            size_bytes=len(image_bytes),
            aspect_ratio=round(img.width / img.height, 4) if img.height > 0 else 1.0,
        )

    def resize(self, image_bytes: bytes, params: ResizeParams) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        src_w, src_h = img.width, img.height
        dst_w, dst_h = params.width, params.height

        if not params.preserve_aspect or params.fit_mode == "stretch":
            result = img.resize((dst_w, dst_h), resample=Image.Resampling.LANCZOS)
        elif params.fit_mode == "cover":
            # Scale up to cover dst, then crop center
            scale = max(dst_w / src_w, dst_h / src_h)
            scaled_w, scaled_h = int(round(src_w * scale)), int(round(src_h * scale))
            scaled = img.resize((scaled_w, scaled_h), resample=Image.Resampling.LANCZOS)
            left = (scaled_w - dst_w) // 2
            top = (scaled_h - dst_h) // 2
            result = scaled.crop((left, top, left + dst_w, top + dst_h))
        else:
            # "contain" fit: thumbnail within bounds
            scale = min(dst_w / src_w, dst_h / src_h)
            new_w = max(1, int(round(src_w * scale)))
            new_h = max(1, int(round(src_h * scale)))
            result = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        return self._export_image(result, current_format)

    def crop(self, image_bytes: bytes, params: CropParams) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        if params.left < 0 or params.top < 0:
            raise OperationError("Crop coordinates must not be negative.")
        if params.left >= img.width or params.top >= img.height:
            raise OperationError("Crop coordinates fall outside image boundaries.")

        right = min(img.width, params.left + params.width)
        bottom = min(img.height, params.top + params.height)

        if right <= params.left or bottom <= params.top:
            raise OperationError("Crop box has zero or negative area.")

        cropped = img.crop((params.left, params.top, right, bottom))
        return self._export_image(cropped, current_format)

    def rotate(self, image_bytes: bytes, params: RotateParams) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        # Pillow rotate is counter-clockwise by default, so invert to make clockwise intuitive
        rotated = img.rotate(
            -params.degrees, expand=params.expand, resample=Image.Resampling.BICUBIC
        )
        return self._export_image(rotated, current_format)

    def flip(self, image_bytes: bytes, params: FlipParams) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        res = img
        if params.horizontal:
            res = res.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if params.vertical:
            res = res.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return self._export_image(res, current_format)

    def convert_format(
        self, image_bytes: bytes, params: ConvertFormatParams
    ) -> tuple[bytes, ImageMetadata]:
        img, _ = self._open_and_validate(image_bytes)
        return self._export_image(img, params.target_format, quality=params.quality)

    def compress(self, image_bytes: bytes, params: CompressParams) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        target = params.target_format or current_format
        return self._export_image(img, target, quality=params.quality)

    def adjust_brightness(
        self, image_bytes: bytes, params: BrightnessParams
    ) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        enhancer = ImageEnhance.Brightness(img)
        adjusted = enhancer.enhance(params.factor)
        return self._export_image(adjusted, current_format)

    def adjust_contrast(
        self, image_bytes: bytes, params: ContrastParams
    ) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        enhancer = ImageEnhance.Contrast(img)
        adjusted = enhancer.enhance(params.factor)
        return self._export_image(adjusted, current_format)

    def adjust_saturation(
        self, image_bytes: bytes, params: SaturationParams
    ) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        enhancer = ImageEnhance.Color(img)
        adjusted = enhancer.enhance(params.factor)
        return self._export_image(adjusted, current_format)

    def adjust_temperature(
        self, image_bytes: bytes, params: TemperatureParams
    ) -> tuple[bytes, ImageMetadata]:
        img, current_format = self._open_and_validate(image_bytes)
        if params.shift == 0:
            return self._export_image(img, current_format)

        # Convert to RGB/RGBA for channel manipulation
        has_alpha = img.mode in ("RGBA", "LA")
        alpha = img.split()[-1] if has_alpha else None
        rgb_img = img.convert("RGB")

        r, g, b = rgb_img.split()
        shift_ratio = params.shift / 100.0  # -1.0 to +1.0
        r_scale = 1.0 + (shift_ratio * 0.22)
        g_scale = 1.0 + (shift_ratio * 0.05)
        b_scale = 1.0 - (shift_ratio * 0.22)

        r_lut = [min(255, max(0, int(i * r_scale))) for i in range(256)]
        g_lut = [min(255, max(0, int(i * g_scale))) for i in range(256)]
        b_lut = [min(255, max(0, int(i * b_scale))) for i in range(256)]

        r = r.point(r_lut)
        g = g.point(g_lut)
        b = b.point(b_lut)

        merged = Image.merge("RGB", (r, g, b))
        if has_alpha and alpha:
            merged = Image.merge("RGBA", (*merged.split(), alpha))

        return self._export_image(merged, current_format)

    async def analyze(
        self, image_bytes: bytes, declared_content_type: str | None
    ) -> ImageAnalysisResponse:
        _, raw_format = self._open_and_validate(image_bytes)
        mime_type = ALLOWED_FORMATS.get(raw_format, "image/png")
        provider = GroqVisionProvider(self._settings)
        return await provider.analyze(image_bytes, mime_type)
