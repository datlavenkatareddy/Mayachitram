from fastapi import APIRouter

from mayachitram.api.v1.routes.engines import router as engines_router
from mayachitram.api.v1.routes.image import router as image_router
from mayachitram.api.v1.routes.maya import router as maya_router
from mayachitram.api.v1.routes.projects import router as projects_router
from mayachitram.api.v1.routes.tools import router as tools_router

router = APIRouter()
router.include_router(engines_router, prefix="/engines", tags=["engines"])
router.include_router(image_router, prefix="/image", tags=["image-engine"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(maya_router, prefix="/maya", tags=["maya"])
