"""Trading journal endpoints: CRUD over journal entries + reports."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_db, require_api_key
from app.core.constants import TradeOutcome
from app.core.exceptions import FathirError
from app.database.models.journal import JournalEntry
from app.journal import reports as journal_reports
from app.journal.repository import create_entry, delete_entry, get_entry, list_entries, update_entry
from app.risk.limits import record_closed_trade
from app.schemas.common import Page
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryUpdate,
    PeriodReport,
    WinRateReport,
)
from app.services.broker.factory import get_broker_gateway
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/journal", tags=["journal"], dependencies=[Depends(require_api_key)])


@router.post("/entries", response_model=JournalEntryRead)
def post_entry(data: JournalEntryCreate, db=Depends(get_db)) -> JournalEntry:
    return create_entry(db, data)


@router.get("/entries", response_model=Page[JournalEntryRead])
def get_entries(
    account_id: int | None = None,
    symbol: str | None = None,
    outcome: TradeOutcome | None = None,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
) -> Page[JournalEntryRead]:
    items, total = list_entries(
        db, account_id=account_id, symbol=symbol, outcome=outcome, page=page, page_size=page_size
    )
    return Page[JournalEntryRead](
        items=[JournalEntryRead.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/entries/{entry_id}", response_model=JournalEntryRead)
def get_single_entry(entry_id: int, db=Depends(get_db)) -> JournalEntry:
    return get_entry(db, entry_id)


@router.patch("/entries/{entry_id}", response_model=JournalEntryRead)
def patch_entry(entry_id: int, data: JournalEntryUpdate, db=Depends(get_db)) -> JournalEntry:
    entry = update_entry(db, entry_id, data)

    # A trade that just closed (has both an exit price and a P&L figure)
    # feeds the daily risk ledger so limits.check_daily_limits stays accurate.
    if (
        entry.account_id is not None
        and entry.exit_price is not None
        and entry.profit_loss is not None
    ):
        try:
            market_data = MarketDataService(get_broker_gateway())
            equity = market_data.get_account_info().equity
            record_closed_trade(
                db,
                account_id=entry.account_id,
                pnl=entry.profit_loss,
                ending_equity=equity,
                closed_at=entry.closed_at or datetime.now(UTC),
            )
        except FathirError:
            # Broker unavailable shouldn't block the journal update itself —
            # the daily ledger will simply catch up on the next successful poll.
            pass

    return entry


@router.delete("/entries/{entry_id}", status_code=204, response_model=None)
def remove_entry(entry_id: int, db=Depends(get_db)) -> None:
    delete_entry(db, entry_id)


@router.get("/reports/win-rate", response_model=WinRateReport)
def get_win_rate(account_id: int | None = None, db=Depends(get_db)) -> WinRateReport:
    entries, _ = list_entries(db, account_id=account_id, page=1, page_size=10_000)
    return journal_reports.calculate_win_rate(entries)


@router.get("/reports/weekly", response_model=PeriodReport)
def get_weekly(account_id: int | None = None, db=Depends(get_db)) -> PeriodReport:
    return journal_reports.get_weekly_report(db, account_id=account_id)


@router.get("/reports/monthly", response_model=PeriodReport)
def get_monthly(account_id: int | None = None, db=Depends(get_db)) -> PeriodReport:
    return journal_reports.get_monthly_report(db, account_id=account_id)
