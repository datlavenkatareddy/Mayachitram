import io

import pytest
from PIL import Image

from mayachitram.core.config import Settings
from mayachitram.core.errors import ImageValidationError, OperationError
from mayachitram.engines.image.schemas import (
    BrightnessParams,
    ContrastParams,
    ConvertFormatParams,
    CropParams,
    FlipParams,
    ResizeParams,
    RotateParams,
    SaturationParams,
    TemperatureParams,
)
from mayachitram.engines.image.service import ImageEngine


def create_test_image_bytes(
    format: str = "PNG",
    size: tuple[int, int] = (200, 100),
    color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 0, 0),
    mode: str = "RGB",
) -> bytes:
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def image_engine(tmp_path):
    settings = Settings(
        MAYACHITRAM_DATA_DIR=tmp_path / "data",
        MAX_UPLOAD_BYTES=5 * 1024 * 1024,
        MAX_IMAGE_PIXELS=1000000,
        MAX_IMAGE_DIMENSION=4096,
    )
    return ImageEngine(settings)


def test_metadata_extraction(image_engine):
    data = create_test_image_bytes("PNG", size=(300, 150))
    meta = image_engine.get_metadata(data)
    assert meta.format == "PNG"
    assert meta.width == 300
    assert meta.height == 150
    assert meta.aspect_ratio == 2.0


def test_resize_contain_and_cover(image_engine):
    data = create_test_image_bytes("PNG", size=(200, 100))

    # Contain: within 100x100 -> should result in 100x50
    out_bytes, meta = image_engine.resize(
        data,
        ResizeParams(width=100, height=100, preserve_aspect=True, fit_mode="contain"),
    )
    assert meta.width == 100
    assert meta.height == 50

    # Stretch: explicitly 80x80
    out_bytes, meta = image_engine.resize(
        data,
        ResizeParams(width=80, height=80, preserve_aspect=False, fit_mode="stretch"),
    )
    assert meta.width == 80
    assert meta.height == 80


def test_crop_bounds(image_engine):
    data = create_test_image_bytes("PNG", size=(200, 200))
    out_bytes, meta = image_engine.crop(
        data,
        CropParams(left=50, top=50, width=80, height=60),
    )
    assert meta.width == 80
    assert meta.height == 60


def test_crop_invalid_coordinates(image_engine):
    data = create_test_image_bytes("PNG", size=(100, 100))
    with pytest.raises(OperationError):
        image_engine.crop(data, CropParams(left=200, top=200, width=50, height=50))


def test_rotate_and_flip(image_engine):
    data = create_test_image_bytes("PNG", size=(200, 100))

    # 90 degrees clockwise -> dimensions swap to 100x200
    out_bytes, meta = image_engine.rotate(data, RotateParams(degrees=90, expand=True))
    assert meta.width == 100
    assert meta.height == 200

    # Flip horizontal
    out_bytes, meta = image_engine.flip(data, FlipParams(horizontal=True, vertical=False))
    assert meta.width == 200
    assert meta.height == 100


def test_format_conversion_and_alpha_flattening(image_engine):
    # Create RGBA PNG with transparency
    rgba_data = create_test_image_bytes("PNG", size=(100, 100), color=(0, 255, 0, 128), mode="RGBA")

    # Convert to JPEG (must handle alpha gracefully without crashing)
    out_bytes, meta = image_engine.convert_format(
        rgba_data,
        ConvertFormatParams(target_format="JPEG", quality=80),
    )
    assert meta.format == "JPEG"
    assert meta.width == 100
    assert meta.height == 100

    # Convert to WebP
    out_bytes, meta = image_engine.convert_format(
        rgba_data,
        ConvertFormatParams(target_format="WEBP", quality=85),
    )
    assert meta.format == "WEBP"


def test_adjustments(image_engine):
    data = create_test_image_bytes("PNG", size=(100, 100))

    # Brightness
    out_bytes, meta = image_engine.adjust_brightness(data, BrightnessParams(factor=1.5))
    assert meta.width == 100

    # Contrast
    out_bytes, meta = image_engine.adjust_contrast(data, ContrastParams(factor=1.2))
    assert meta.width == 100

    # Saturation (grayscale = 0.0)
    out_bytes, meta = image_engine.adjust_saturation(data, SaturationParams(factor=0.0))
    assert meta.width == 100

    # Temperature (+30 warmer)
    out_bytes, meta = image_engine.adjust_temperature(data, TemperatureParams(shift=30))
    assert meta.width == 100


def test_rejects_unsupported_format(image_engine):
    # BMP is not in ALLOWED_FORMATS (JPEG, PNG, WEBP)
    bmp_data = create_test_image_bytes("BMP", size=(50, 50))
    with pytest.raises(ImageValidationError):
        image_engine.get_metadata(bmp_data)


def test_direct_process_endpoint(client):
    png_data = create_test_image_bytes("PNG", size=(200, 100))
    response = client.post(
        "/api/v1/image/process",
        data={
            "operation": "image.resize",
            "params": '{"width": 80, "height": 40, "preserve_aspect": false}',
        },
        files={"file": ("test.png", png_data, "image/png")},
    )
    assert response.status_code == 200
    assert response.headers["X-Image-Width"] == "80"
    assert response.headers["X-Image-Height"] == "40"
    assert len(response.content) > 0
