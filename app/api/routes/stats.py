from fastapi import APIRouter

from app.models import StatsResponse
from app.services import db_manager

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(
        total_size_mb=db_manager.get_total_size(),
        total_items=db_manager.get_total_songs(),
    )


@router.get("/healthz")
async def healthcheck():
    return {"status": "ok"}
