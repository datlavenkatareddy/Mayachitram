from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mayachitram.api.v1.router import router as v1_router
from mayachitram.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="MayaChitram API",
    version="1.0.0",
    description="Modular multi-engine AI platform; Image Engine is the first engine.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mayachitram-api"}
