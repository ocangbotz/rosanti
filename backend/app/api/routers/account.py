"""Broker account endpoints: saved account records, live snapshot, and
historical balance/equity curve."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db, get_market_data_service, require_api_key
from app.core.exceptions import NotFoundError
from app.core.security import CredentialCipher
from app.database.models.account import AccountSnapshot, BrokerAccount
from app.schemas.account import (
    AccountSnapshotRead,
    BrokerAccountCreate,
    BrokerAccountRead,
    LiveAccountInfo,
)
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=BrokerAccountRead)
def create_account(data: BrokerAccountCreate, db=Depends(get_db)) -> BrokerAccount:
    cipher = CredentialCipher()
    account = BrokerAccount(
        login=data.login,
        server=data.server,
        broker_name=data.broker_name,
        currency=data.currency,
        leverage=data.leverage,
        encrypted_password=cipher.encrypt(data.password),
    )
    db.add(account)
    db.flush()
    db.refresh(account)
    return account


@router.get("", response_model=list[BrokerAccountRead])
def list_accounts(db=Depends(get_db)) -> list[BrokerAccount]:
    return list(db.query(BrokerAccount).order_by(BrokerAccount.created_at.desc()).all())


@router.get("/live", response_model=LiveAccountInfo)
def get_live_account_info(
    market_data: MarketDataService = Depends(get_market_data_service),
) -> LiveAccountInfo:
    """The account info read directly from the active broker gateway —
    always reflects the current connection, independent of any saved
    `BrokerAccount` row."""
    return market_data.get_account_info()


@router.get("/{account_id}", response_model=BrokerAccountRead)
def get_account(account_id: int, db=Depends(get_db)) -> BrokerAccount:
    account = db.get(BrokerAccount, account_id)
    if account is None:
        raise NotFoundError(f"Account {account_id} not found.")
    return account


@router.get("/{account_id}/snapshots", response_model=list[AccountSnapshotRead])
def get_account_snapshots(
    account_id: int, limit: int = 200, db=Depends(get_db)
) -> list[AccountSnapshot]:
    return list(
        db.query(AccountSnapshot)
        .filter(AccountSnapshot.account_id == account_id)
        .order_by(AccountSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
