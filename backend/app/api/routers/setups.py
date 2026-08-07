"""Smart Trade Setup endpoints: generate (and persist) a confluence-scored
setup, list/inspect past setups, and update a setup's lifecycle status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.analysis.engine import MarketAnalysisEngine
from app.api.deps import get_app_settings, get_db, get_market_data_service, require_api_key
from app.config import Settings
from app.core.exceptions import AIProviderError, NotFoundError
from app.database.models.setup import SetupStatus, TradeSetup
from app.schemas.common import Page
from app.schemas.setup import GenerateSetupRequest, TradeSetupRead, TradeSetupSummary
from app.services.ai.factory import get_llm_provider
from app.services.ai.narrator import MarketNarrator
from app.services.market_data import MarketDataService
from app.strategies.setup_generator import TradeSetupGenerator

router = APIRouter(prefix="/setups", tags=["setups"], dependencies=[Depends(require_api_key)])


@router.post("/generate", response_model=TradeSetupRead)
async def generate_setup(
    request: GenerateSetupRequest,
    db=Depends(get_db),
    market_data: MarketDataService = Depends(get_market_data_service),
    settings: Settings = Depends(get_app_settings),
) -> TradeSetup:
    df = market_data.get_ohlc(request.symbol.upper(), request.timeframe)
    analysis = MarketAnalysisEngine().analyze(df, request.symbol.upper(), request.timeframe)
    result = TradeSetupGenerator().generate(analysis)

    ai_narrative: str | None = None
    if request.include_ai_narrative:
        try:
            narrator = MarketNarrator(get_llm_provider(settings))
            ai_narrative = await narrator.narrate(analysis, result.setup)
        except AIProviderError:
            # Narration is best-effort — a missing/failing AI provider must
            # never block a setup from being generated, since the
            # deterministic score/reasons are already complete without it.
            ai_narrative = None

    if not result.has_valid_setup or result.setup is None:
        row = TradeSetup(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            direction=result.dominant_direction,
            entry_price=analysis.indicators.price,
            stop_loss=analysis.indicators.price,
            take_profit=analysis.indicators.price,
            risk_reward=0.0,
            confidence_score=result.confidence,
            reasons=[r.model_dump(mode="json") for r in result.reasons],
            structure_snapshot=analysis.model_dump(mode="json"),
            ai_narrative=ai_narrative or result.rejection_reason,
            status=SetupStatus.INVALIDATED,
        )
    else:
        setup = result.setup
        row = TradeSetup(
            symbol=setup.symbol,
            timeframe=setup.timeframe,
            direction=setup.direction,
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit,
            risk_reward=setup.risk_reward,
            confidence_score=setup.confidence_score,
            reasons=[r.model_dump(mode="json") for r in setup.reasons],
            structure_snapshot=setup.structure_snapshot,
            ai_narrative=ai_narrative,
            status=SetupStatus.PROPOSED,
        )

    db.add(row)
    db.flush()
    db.refresh(row)
    return row


@router.get("", response_model=Page[TradeSetupSummary])
def list_setups(
    symbol: str | None = None,
    status_filter: SetupStatus | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_db),
) -> Page[TradeSetupSummary]:
    query = db.query(TradeSetup)
    if symbol:
        query = query.filter(TradeSetup.symbol == symbol.upper())
    if status_filter:
        query = query.filter(TradeSetup.status == status_filter)

    total = query.count()
    rows = (
        query.order_by(TradeSetup.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [TradeSetupSummary.model_validate(row) for row in rows]
    return Page[TradeSetupSummary](items=items, total=total, page=page, page_size=page_size)


@router.get("/{setup_id}", response_model=TradeSetupRead)
def get_setup(setup_id: int, db=Depends(get_db)) -> TradeSetup:
    row = db.get(TradeSetup, setup_id)
    if row is None:
        raise NotFoundError(f"Trade setup {setup_id} not found.")
    return row


@router.patch("/{setup_id}/status", response_model=TradeSetupRead)
def update_setup_status(setup_id: int, new_status: SetupStatus, db=Depends(get_db)) -> TradeSetup:
    row = db.get(TradeSetup, setup_id)
    if row is None:
        raise NotFoundError(f"Trade setup {setup_id} not found.")
    row.status = new_status
    db.flush()
    db.refresh(row)
    return row
