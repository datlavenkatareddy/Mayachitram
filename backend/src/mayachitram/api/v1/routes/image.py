import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError

from mayachitram.api.v1.dependencies import get_image_engine, get_tool_registry
from mayachitram.core.config import get_settings
from mayachitram.core.errors import (
    ImageValidationError,
    OperationError,
    ProviderAnalysisError,
    ProviderNotConfiguredError,
)
from mayachitram.engines.image.schemas import ImageAnalysisResponse, ImageMetadata
from mayachitram.engines.image.service import ALLOWED_FORMATS, ImageEngine
from mayachitram.maya.registry.tools import ToolRegistry

router = APIRouter()


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    engine: ImageEngine = Depends(get_image_engine),
) -> ImageAnalysisResponse:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        return await engine.analyze(content, file.content_type)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/metadata", response_model=ImageMetadata)
async def get_image_metadata(
    file: UploadFile = File(...),
    engine: ImageEngine = Depends(get_image_engine),
) -> ImageMetadata:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    return engine.get_metadata(content)


@router.post("/process")
async def process_image_direct(
    file: UploadFile = File(...),
    operation: str = Form(
        description="Operation/tool name (e.g. image.resize, image.crop, image.rotate)"
    ),
    params: str = Form(default="{}", description="JSON string of tool parameters"),
    engine: ImageEngine = Depends(get_image_engine),
    registry: ToolRegistry = Depends(get_tool_registry),
) -> Response:
    """Direct, standalone image processing: upload an image, apply an operation, and receive the processed output."""
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)

    normalized_op = operation if operation.startswith("image.") else f"image.{operation}"
    tool = registry.get(normalized_op)
    if not tool:
        raise OperationError(f"Operation '{operation}' is not recognized.")

    try:
        param_dict = json.loads(params) if params else {}
    except json.JSONDecodeError as exc:
        raise OperationError(f"Malformed JSON in 'params': {exc}") from exc

    try:
        validated_params = tool.params_class.model_validate(param_dict)
    except ValidationError as exc:
        raise OperationError(f"Invalid parameters for {operation}: {exc}") from exc

    output_bytes, metadata = tool.handler(engine, content, validated_params)
    mime_type = ALLOWED_FORMATS.get(metadata.format, "image/png")

    return Response(
        content=output_bytes,
        media_type=mime_type,
        headers={
            "X-Image-Width": str(metadata.width),
            "X-Image-Height": str(metadata.height),
            "X-Image-Format": metadata.format,
            "X-Image-Size": str(metadata.size_bytes),
        },
    )
