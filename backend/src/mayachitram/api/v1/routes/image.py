from fastapi import APIRouter, File, HTTPException, UploadFile, status

from mayachitram.core.config import get_settings
from mayachitram.core.errors import (
    ImageValidationError,
    ProviderAnalysisError,
    ProviderNotConfiguredError,
)
from mayachitram.engines.image.schemas import ImageAnalysisResponse
from mayachitram.engines.image.service import ImageEngine

router = APIRouter()


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)) -> ImageAnalysisResponse:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        return await ImageEngine(settings).analyze(content, file.content_type)
    except ImageValidationError as exc:
        text = str(exc)
        code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "exceeds" in text or "size limit" in text
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=text) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
