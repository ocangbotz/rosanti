"""Economic calendar / news filter endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db, require_api_key
from app.database.models.news import NewsEvent
from app.schemas.news import NewsCheckResponse, NewsEventRead
from app.services.news.service import get_upcoming_high_impact, refresh_calendar

router = APIRouter(prefix="/news", tags=["news"], dependencies=[Depends(require_api_key)])


@router.get("/upcoming", response_model=NewsCheckResponse)
def get_upcoming(lookahead_minutes: int | None = None, db=Depends(get_db)) -> NewsCheckResponse:
    return get_upcoming_high_impact(db, lookahead_minutes)


@router.post("/refresh", response_model=list[NewsEventRead])
async def post_refresh(db=Depends(get_db)) -> list[NewsEvent]:
    return await refresh_calendar(db)


@router.get("/events", response_model=list[NewsEventRead])
def list_events(limit: int = 100, db=Depends(get_db)) -> list[NewsEvent]:
    return list(db.query(NewsEvent).order_by(NewsEvent.event_time.asc()).limit(limit).all())
