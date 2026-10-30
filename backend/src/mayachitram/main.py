from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mayachitram.api.v1.router import router as v1_router
from mayachitram.core.config import get_settings
from mayachitram.core.errors import MayaChitramError

settings = get_settings()

app = FastAPI(
    title="MayaChitram API",
    version="1.0.0",
    description="MayaChitram extensible AI creative platform API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Image-Width",
        "X-Image-Height",
        "X-Image-Format",
        "X-Image-Size",
        "Content-Disposition",
    ],
)


@app.exception_handler(MayaChitramError)
async def mayachitram_exception_handler(_: Request, exc: MayaChitramError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mayachitram-api"}
