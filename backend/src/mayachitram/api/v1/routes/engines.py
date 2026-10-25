from fastapi import APIRouter

from mayachitram.platform.registry import list_engines

router = APIRouter()


@router.get("")
def get_engines() -> dict[str, list[dict[str, object]]]:
    return {"engines": list_engines()}
