"""Dashboard-editable key/value app settings (not the `.env`-backed
`Settings` object — see app/database/models/settings.py for the rationale)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db, require_api_key
from app.core.exceptions import NotFoundError
from app.database.models.settings import AppSetting
from app.schemas.settings import AppSettingRead, AppSettingUpsert

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[AppSettingRead])
def list_settings(db=Depends(get_db)) -> list[AppSetting]:
    return list(db.query(AppSetting).order_by(AppSetting.key.asc()).all())


@router.get("/{key}", response_model=AppSettingRead)
def get_setting(key: str, db=Depends(get_db)) -> AppSetting:
    setting = db.query(AppSetting).filter(AppSetting.key == key).one_or_none()
    if setting is None:
        raise NotFoundError(f"Setting {key!r} not found.")
    return setting


@router.put("/{key}", response_model=AppSettingRead)
def upsert_setting(key: str, data: AppSettingUpsert, db=Depends(get_db)) -> AppSetting:
    setting = db.query(AppSetting).filter(AppSetting.key == key).one_or_none()
    if setting is None:
        setting = AppSetting(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    db.flush()
    db.refresh(setting)
    return setting
