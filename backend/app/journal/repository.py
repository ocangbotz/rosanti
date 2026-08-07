"""Trading journal persistence — CRUD over `JournalEntry` and
`ScreenshotAnalysis`, plus the small amount of derived-field math that only
makes sense at write time (R-multiple, outcome) so every caller doesn't
have to reimplement it.

Deliberately DB-only: this module knows nothing about the broker or risk
limits (see docs/ARCHITECTURE.md's layering table) — the API layer (M11)
is what wires a closed trade's realized P&L into `risk/limits.py`'s daily
ledger, using whatever equity figure it read from the broker gateway.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import TradeDirection, TradeOutcome
from app.core.exceptions import NotFoundError
from app.database.models.journal import JournalEntry, ScreenshotAnalysis
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.services.ai.schemas import ScreenshotAnalysisResult


def create_entry(db: Session, data: JournalEntryCreate) -> JournalEntry:
    entry = JournalEntry(
        setup_id=data.setup_id,
        account_id=data.account_id,
        mt5_ticket=data.mt5_ticket,
        symbol=data.symbol.upper(),
        direction=data.direction,
        entry_price=data.entry_price,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        lot_size=data.lot_size,
        risk_percent=data.risk_percent,
        opened_at=data.opened_at,
        trader_notes=data.trader_notes,
        outcome=TradeOutcome.PENDING,
    )
    db.add(entry)
    db.flush()
    return entry


def get_entry(db: Session, entry_id: int) -> JournalEntry:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise NotFoundError(f"Journal entry {entry_id} not found.")
    return entry


def list_entries(
    db: Session,
    *,
    account_id: int | None = None,
    symbol: str | None = None,
    outcome: TradeOutcome | None = None,
    opened_after: datetime | None = None,
    opened_before: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[JournalEntry], int]:
    query = select(JournalEntry)
    if account_id is not None:
        query = query.where(JournalEntry.account_id == account_id)
    if symbol is not None:
        query = query.where(JournalEntry.symbol == symbol.upper())
    if outcome is not None:
        query = query.where(JournalEntry.outcome == outcome)
    if opened_after is not None:
        query = query.where(JournalEntry.opened_at >= opened_after)
    if opened_before is not None:
        query = query.where(JournalEntry.opened_at < opened_before)

    total = len(db.execute(query).scalars().all())

    query = (
        query.order_by(JournalEntry.opened_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.execute(query).scalars().all())
    return items, total


def _compute_r_multiple(entry: JournalEntry, exit_price: float) -> float | None:
    risk_distance = (
        entry.entry_price - entry.stop_loss
        if entry.direction == TradeDirection.BUY
        else entry.stop_loss - entry.entry_price
    )
    if risk_distance <= 0:
        return None
    favorable_move = (
        exit_price - entry.entry_price
        if entry.direction == TradeDirection.BUY
        else entry.entry_price - exit_price
    )
    return round(favorable_move / risk_distance, 2)


def _infer_outcome(profit_loss: float | None) -> TradeOutcome | None:
    if profit_loss is None:
        return None
    if profit_loss > 0:
        return TradeOutcome.WIN
    if profit_loss < 0:
        return TradeOutcome.LOSS
    return TradeOutcome.BREAKEVEN


def update_entry(db: Session, entry_id: int, data: JournalEntryUpdate) -> JournalEntry:
    entry = get_entry(db, entry_id)
    payload = data.model_dump(exclude_unset=True)

    for field in (
        "exit_price",
        "closed_at",
        "profit_loss",
        "profit_loss_percent",
        "ai_summary",
        "trader_notes",
    ):
        if field in payload:
            setattr(entry, field, payload[field])

    if "outcome" in payload:
        entry.outcome = payload["outcome"]
    elif entry.exit_price is not None:
        inferred = _infer_outcome(entry.profit_loss)
        if inferred is not None:
            entry.outcome = inferred

    if "r_multiple" in payload:
        entry.r_multiple = payload["r_multiple"]
    elif entry.exit_price is not None:
        entry.r_multiple = _compute_r_multiple(entry, entry.exit_price)

    db.flush()
    return entry


def delete_entry(db: Session, entry_id: int) -> None:
    entry = get_entry(db, entry_id)
    db.delete(entry)
    db.flush()


def add_screenshot(
    db: Session,
    result: ScreenshotAnalysisResult,
    file_path: str,
    *,
    journal_entry_id: int | None = None,
    symbol_hint: str | None = None,
) -> ScreenshotAnalysis:
    if journal_entry_id is not None:
        get_entry(db, journal_entry_id)  # raises NotFoundError if missing

    screenshot = ScreenshotAnalysis(
        journal_entry_id=journal_entry_id,
        file_path=file_path,
        symbol_hint=symbol_hint,
        detected_trend=result.detected_trend,
        detected_support=result.detected_support,
        detected_resistance=result.detected_resistance,
        suggested_entry=result.suggested_entry,
        suggested_stop_loss=result.suggested_stop_loss,
        suggested_take_profit=result.suggested_take_profit,
        mistakes=result.mistakes,
        risk_notes=result.risk_notes,
        full_report=result.full_report,
        raw_model_response=result.raw_model_response,
    )
    db.add(screenshot)
    db.flush()
    return screenshot


def get_screenshot(db: Session, screenshot_id: int) -> ScreenshotAnalysis:
    screenshot = db.get(ScreenshotAnalysis, screenshot_id)
    if screenshot is None:
        raise NotFoundError(f"Screenshot analysis {screenshot_id} not found.")
    return screenshot
