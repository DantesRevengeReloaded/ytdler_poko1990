from fastapi import APIRouter

from app.core.config import get_settings
from app.models import StatsBreakdownResponse, StatsBreakdownItem, StatsResponse
from app.services import db_manager

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(
        total_size_mb=db_manager.get_total_size(),
        total_items=db_manager.get_total_songs(),
    )


@router.get("/stats/breakdown", response_model=StatsBreakdownResponse)
async def get_stats_breakdown():
    settings = get_settings()
    breakdown = db_manager.get_stats_breakdown()
    storage = db_manager.get_storage_stats(settings.download_dir)
    return StatsBreakdownResponse(
        breakdown=[StatsBreakdownItem(**item) for item in breakdown],
        storage=storage,
    )


@router.get("/healthz")
async def healthcheck():
    return {"status": "ok"}
