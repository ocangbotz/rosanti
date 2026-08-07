"""Pydantic schemas for broker accounts and balance/equity snapshots."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedSchema


class BrokerAccountCreate(BaseModel):
    login: int
    password: str = Field(..., min_length=1, description="Plaintext in transit, encrypted at rest.")
    server: str
    broker_name: str = ""
    currency: str = "USD"
    leverage: int = 100


class BrokerAccountRead(TimestampedSchema):
    login: int
    server: str
    broker_name: str
    currency: str
    leverage: int
    is_active: bool


class AccountSnapshotRead(TimestampedSchema):
    account_id: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float | None = None


class LiveAccountInfo(BaseModel):
    """Live snapshot pulled directly from the broker gateway (not persisted
    unless the scheduler records it into `account_snapshots`)."""

    login: int
    server: str
    currency: str
    leverage: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float | None = None
    profit: float = 0.0
    connected: bool = True
