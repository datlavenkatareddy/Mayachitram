from typing import TypedDict


class EngineMetadata(TypedDict):
    id: str
    name: str
    version: str
    status: str
    capabilities: list[str]


ENGINES: tuple[EngineMetadata, ...] = (
    {
        "id": "image",
        "name": "Image Engine",
        "version": "1.0.0",
        "status": "available",
        "capabilities": ["image-description", "visible-object-identification"],
    },
)


def list_engines() -> list[EngineMetadata]:
    """Return public engine metadata; business logic belongs to engine services."""
    return [dict(engine) for engine in ENGINES]
