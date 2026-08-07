"""Chart screenshot upload + AI analysis endpoint."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_app_settings, get_db, require_api_key
from app.config import Settings
from app.core.exceptions import ValidationFailedError
from app.database.models.journal import ScreenshotAnalysis
from app.journal.repository import add_screenshot, get_screenshot
from app.schemas.journal import ScreenshotAnalysisRead
from app.services.ai.factory import get_llm_provider
from app.services.ai.screenshot_analyzer import ScreenshotAnalyzer

router = APIRouter(
    prefix="/screenshot", tags=["screenshot"], dependencies=[Depends(require_api_key)]
)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/analyze", response_model=ScreenshotAnalysisRead)
async def analyze_screenshot(
    file: UploadFile = File(...),
    symbol_hint: str | None = Form(default=None),
    journal_entry_id: int | None = Form(default=None),
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> ScreenshotAnalysis:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationFailedError(
            f"Unsupported image type {file.content_type!r}. "
            f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
        )

    contents = await file.read()
    max_bytes = settings.max_screenshot_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise ValidationFailedError(
            f"Screenshot exceeds the {settings.max_screenshot_size_mb}MB upload limit."
        )

    # Constructed only after validation passes — the AI provider requiring
    # configuration (e.g. no ANTHROPIC_API_KEY) must not preempt a 4xx
    # validation error with a 502 from an unrelated dependency.
    analyzer = ScreenshotAnalyzer(get_llm_provider(settings))
    result = await analyzer.analyze(contents, file.content_type, symbol_hint=symbol_hint)

    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    filename = f"{uuid.uuid4().hex}.{extension}"
    destination: Path = settings.screenshots_dir / filename
    destination.write_bytes(contents)

    return add_screenshot(
        db,
        result,
        str(destination),
        journal_entry_id=journal_entry_id,
        symbol_hint=symbol_hint,
    )


@router.get("/{screenshot_id}", response_model=ScreenshotAnalysisRead)
def get_screenshot_analysis(screenshot_id: int, db=Depends(get_db)) -> ScreenshotAnalysis:
    return get_screenshot(db, screenshot_id)
