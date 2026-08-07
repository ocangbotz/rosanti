"""Result shape produced by the screenshot analyzer — what the vision model
is instructed to return, validated before it ever reaches the database."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScreenshotAnalysisResult(BaseModel):
    detected_trend: str = Field(..., description="e.g. 'bullish', 'bearish', 'ranging'.")
    detected_support: list[float] = Field(default_factory=list)
    detected_resistance: list[float] = Field(default_factory=list)
    suggested_entry: float | None = None
    suggested_stop_loss: float | None = None
    suggested_take_profit: float | None = None
    mistakes: list[str] = Field(default_factory=list)
    risk_notes: str = ""
    full_report: str

    raw_model_response: dict = Field(default_factory=dict, exclude=False)
