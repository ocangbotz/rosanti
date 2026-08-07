"""Market structure analysis: swing points, trend, Break of Structure (BOS),
and Change of Character (CHOCH).

Methodology (a simplified, deterministic version of Smart Money Concepts
structure reading):

1. Swing points are found with a fractal filter — a swing high at index i
   requires `high[i]` to be the strictest local maximum across
   `[i-left, i+right]`; swing lows are the mirror image.
2. Starting from the first two swing points, the trend is tracked as a
   state machine: while bullish, a close above the last swing high is a
   **BOS** (continuation); a close below the last swing low is a **CHOCH**
   (the structure has broken character — trend flips to bearish). The
   bearish case is the mirror image.
3. Before the first BOS is found, the market is considered `NEUTRAL`
   (ranging / not yet trending) — this is the case for the initial history
   and is intentionally conservative rather than guessing a bias.
"""

from __future__ import annotations

import pandas as pd

from app.analysis.schemas import StructureAnalysis, StructureEvent, SwingKind, SwingPoint
from app.core.constants import TradeDirection


def detect_swing_points(df: pd.DataFrame, left: int = 2, right: int = 2) -> list[SwingPoint]:
    """Fractal swing high/low detection.

    `left`/`right` are the number of candles on each side that must be
    strictly lower (for a high) or strictly higher (for a low) than the
    candidate candle. left=right=2 is the classic 5-bar fractal.
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    times = df["time"]
    n = len(df)

    points: list[SwingPoint] = []
    for i in range(left, n - right):
        window_high = highs[i - left : i + right + 1]
        if highs[i] == window_high.max() and (window_high == highs[i]).sum() == 1:
            points.append(
                SwingPoint(index=i, time=times.iloc[i], price=float(highs[i]), kind=SwingKind.HIGH)
            )

        window_low = lows[i - left : i + right + 1]
        if lows[i] == window_low.min() and (window_low == lows[i]).sum() == 1:
            points.append(
                SwingPoint(index=i, time=times.iloc[i], price=float(lows[i]), kind=SwingKind.LOW)
            )

    points.sort(key=lambda p: p.index)
    return points


def analyze_market_structure(
    df: pd.DataFrame, swing_left: int = 2, swing_right: int = 2
) -> StructureAnalysis:
    """Run the full structure analysis: swings + trend + BOS/CHOCH events."""
    swing_points = detect_swing_points(df, left=swing_left, right=swing_right)

    trend = TradeDirection.NEUTRAL
    bos_events: list[StructureEvent] = []
    choch_events: list[StructureEvent] = []

    last_swing_high: SwingPoint | None = None
    last_swing_low: SwingPoint | None = None

    closes = df["close"]
    times = df["time"]

    swing_iter = iter(swing_points)
    next_swing = next(swing_iter, None)
    swing_cursor_idx = 0

    for i in range(len(df)):
        # Register any swing points confirmed as of this candle.
        while next_swing is not None and next_swing.index <= i:
            if next_swing.kind == SwingKind.HIGH:
                last_swing_high = next_swing
            else:
                last_swing_low = next_swing
            swing_cursor_idx += 1
            next_swing = (
                swing_points[swing_cursor_idx] if swing_cursor_idx < len(swing_points) else None
            )

        close_price = float(closes.iloc[i])
        candle_time = times.iloc[i]

        if trend == TradeDirection.NEUTRAL:
            # Establish the initial trend on the first confirmed break of a swing level.
            if last_swing_high is not None and close_price > last_swing_high.price:
                trend = TradeDirection.BUY
                bos_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.BUY,
                        reference_swing=last_swing_high,
                    )
                )
            elif last_swing_low is not None and close_price < last_swing_low.price:
                trend = TradeDirection.SELL
                bos_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.SELL,
                        reference_swing=last_swing_low,
                    )
                )

        elif trend == TradeDirection.BUY:
            if last_swing_low is not None and close_price < last_swing_low.price:
                trend = TradeDirection.SELL
                choch_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.SELL,
                        reference_swing=last_swing_low,
                    )
                )
            elif last_swing_high is not None and close_price > last_swing_high.price:
                bos_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.BUY,
                        reference_swing=last_swing_high,
                    )
                )

        elif trend == TradeDirection.SELL:
            if last_swing_high is not None and close_price > last_swing_high.price:
                trend = TradeDirection.BUY
                choch_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.BUY,
                        reference_swing=last_swing_high,
                    )
                )
            elif last_swing_low is not None and close_price < last_swing_low.price:
                bos_events.append(
                    StructureEvent(
                        time=candle_time,
                        price=close_price,
                        direction=TradeDirection.SELL,
                        reference_swing=last_swing_low,
                    )
                )

    return StructureAnalysis(
        swing_points=swing_points,
        trend=trend,
        bos_events=bos_events,
        choch_events=choch_events,
        last_bos=bos_events[-1] if bos_events else None,
        last_choch=choch_events[-1] if choch_events else None,
    )
