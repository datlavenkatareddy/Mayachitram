from fastapi import APIRouter

from mayachitram.api.v1.routes.engines import router as engines_router
from mayachitram.api.v1.routes.image import router as image_router

router = APIRouter()
router.include_router(engines_router, prefix="/engines", tags=["engines"])
router.include_router(image_router, prefix="/image", tags=["image-engine"])
