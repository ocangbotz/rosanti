"""Risk management endpoints: settings, lot size / breakeven calculators,
daily limit checks, and drawdown tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db, require_api_key
from app.risk.breakeven import calculate_breakeven
from app.risk.limits import check_daily_limits, get_drawdown_for_account, get_risk_settings
from app.risk.position_sizing import calculate_lot_size
from app.schemas.risk import (
    BreakevenRequest,
    BreakevenResponse,
    DailyLimitCheckResponse,
    DrawdownInfo,
    LotSizeRequest,
    LotSizeResponse,
    RiskSettingsRead,
    RiskSettingsUpdate,
)

router = APIRouter(prefix="/risk", tags=["risk"], dependencies=[Depends(require_api_key)])


@router.get("/settings", response_model=RiskSettingsRead)
def get_settings_for_account(account_id: int | None = None, db=Depends(get_db)) -> RiskSettingsRead:
    settings_row = get_risk_settings(db, account_id)
    return RiskSettingsRead.model_validate(settings_row)


@router.put("/settings", response_model=RiskSettingsRead)
def update_settings_for_account(
    update: RiskSettingsUpdate, account_id: int | None = None, db=Depends(get_db)
) -> RiskSettingsRead:
    settings_row = get_risk_settings(db, account_id)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(settings_row, field, value)
    db.flush()
    db.refresh(settings_row)
    return RiskSettingsRead.model_validate(settings_row)


@router.post("/lot-size", response_model=LotSizeResponse)
def post_lot_size(request: LotSizeRequest) -> LotSizeResponse:
    return calculate_lot_size(request)


@router.post("/breakeven", response_model=BreakevenResponse)
def post_breakeven(request: BreakevenRequest) -> BreakevenResponse:
    return calculate_breakeven(request)


@router.get("/daily-limits", response_model=DailyLimitCheckResponse)
def get_daily_limits(account_id: int, db=Depends(get_db)) -> DailyLimitCheckResponse:
    return check_daily_limits(db, account_id)


@router.get("/drawdown", response_model=DrawdownInfo)
def get_drawdown(account_id: int, db=Depends(get_db)) -> DrawdownInfo:
    return get_drawdown_for_account(db, account_id)
