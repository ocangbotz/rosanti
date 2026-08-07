"""Liquidity-concept detection: stop-liquidity sweeps, order blocks, and Fair
Value Gaps (FVGs) — the "smart money" confluence factors requested alongside
plain indicators/structure.
"""

from __future__ import annotations

import pandas as pd

from app.analysis.schemas import (
    FairValueGap,
    LiquidityAnalysis,
    LiquiditySweep,
    OrderBlock,
    SwingKind,
    SwingPoint,
)
from app.core.constants import TradeDirection

ORDER_BLOCK_LOOKBACK = 10  # candles to scan backward from a BOS for the origin candle


def detect_liquidity_sweeps(
    df: pd.DataFrame, swing_points: list[SwingPoint], recent_swings: int = 6
) -> list[LiquiditySweep]:
    """A liquidity sweep: a candle wicks beyond a recent swing high/low
    (grabbing the stop-loss liquidity resting there) but *closes back on the
    other side* of it — i.e. the breakout fails and reverses intracandle.

    Only the most recent `recent_swings` swing points of each kind are
    considered "still relevant" liquidity (older ones are assumed already
    swept or too far from price to matter).
    """
    highs = [p for p in swing_points if p.kind == SwingKind.HIGH][-recent_swings:]
    lows = [p for p in swing_points if p.kind == SwingKind.LOW][-recent_swings:]

    sweeps: list[LiquiditySweep] = []
    n = len(df)

    for swing in highs:
        # Look for a later candle whose high pierces the swing high but whose
        # close falls back below it — sell-side reaction after buy-side sweep.
        for i in range(swing.index + 1, n):
            candle_high = float(df["high"].iloc[i])
            candle_close = float(df["close"].iloc[i])
            if candle_high > swing.price and candle_close < swing.price:
                sweeps.append(
                    LiquiditySweep(
                        time=df["time"].iloc[i],
                        wick_price=candle_high,
                        swept_level=swing.price,
                        direction=TradeDirection.SELL,
                    )
                )
                break
            if candle_close > swing.price:
                # A clean close-through means the level was broken, not swept.
                break

    for swing in lows:
        for i in range(swing.index + 1, n):
            candle_low = float(df["low"].iloc[i])
            candle_close = float(df["close"].iloc[i])
            if candle_low < swing.price and candle_close > swing.price:
                sweeps.append(
                    LiquiditySweep(
                        time=df["time"].iloc[i],
                        wick_price=candle_low,
                        swept_level=swing.price,
                        direction=TradeDirection.BUY,
                    )
                )
                break
            if candle_close < swing.price:
                break

    sweeps.sort(key=lambda s: s.time)
    return sweeps


def detect_order_blocks(df: pd.DataFrame, bos_events: list) -> list[OrderBlock]:
    """An order block is the last opposite-colored candle immediately before
    the impulsive move that produced a BOS — the footprint of the orders
    that fueled the breakout.

    For a bullish BOS: scan backward from the BOS candle for the most recent
    bearish (close < open) candle; its high/low become the demand zone.
    The mirror logic applies to bearish BOS (supply zone).
    """
    order_blocks: list[OrderBlock] = []
    times = df["time"]

    for event in bos_events:
        bos_index = times[times == event.time].index
        if len(bos_index) == 0:
            continue
        idx = int(bos_index[0])

        origin_idx = None
        for j in range(idx, max(idx - ORDER_BLOCK_LOOKBACK, 0) - 1, -1):
            is_bearish = df["close"].iloc[j] < df["open"].iloc[j]
            is_bullish = df["close"].iloc[j] > df["open"].iloc[j]
            if event.direction == TradeDirection.BUY and is_bearish:
                origin_idx = j
                break
            if event.direction == TradeDirection.SELL and is_bullish:
                origin_idx = j
                break

        if origin_idx is None:
            continue

        top = float(df["high"].iloc[origin_idx])
        bottom = float(df["low"].iloc[origin_idx])

        # Mitigated if price has traded back into the zone after it formed.
        mitigated = False
        subsequent_lows = df["low"].iloc[origin_idx + 1 :]
        subsequent_highs = df["high"].iloc[origin_idx + 1 :]
        if len(subsequent_lows):
            mitigated = bool(((subsequent_lows <= top) & (subsequent_highs >= bottom)).any())

        order_blocks.append(
            OrderBlock(
                time=times.iloc[origin_idx],
                top=top,
                bottom=bottom,
                direction=event.direction,
                mitigated=mitigated,
            )
        )

    return order_blocks


def detect_fair_value_gaps(df: pd.DataFrame) -> list[FairValueGap]:
    """Three-candle imbalance: candle[i-1] and candle[i+1] leave a price gap
    that candle[i]'s range never traded into — a "fair value gap" the market
    often revisits before continuing.
    """
    fvgs: list[FairValueGap] = []
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)

    for i in range(1, n - 1):
        prev_high, prev_low = highs[i - 1], lows[i - 1]
        next_high, next_low = highs[i + 1], lows[i + 1]

        if next_low > prev_high:
            top, bottom = float(next_low), float(prev_high)
            filled = bool((lows[i + 2 :] <= bottom).any()) if i + 2 < n else False
            fvgs.append(
                FairValueGap(
                    time=df["time"].iloc[i],
                    top=top,
                    bottom=bottom,
                    direction=TradeDirection.BUY,
                    filled=filled,
                )
            )
        elif next_high < prev_low:
            top, bottom = float(prev_low), float(next_high)
            filled = bool((highs[i + 2 :] >= top).any()) if i + 2 < n else False
            fvgs.append(
                FairValueGap(
                    time=df["time"].iloc[i],
                    top=top,
                    bottom=bottom,
                    direction=TradeDirection.SELL,
                    filled=filled,
                )
            )

    return fvgs


def analyze_liquidity(
    df: pd.DataFrame, swing_points: list[SwingPoint], bos_events: list
) -> LiquidityAnalysis:
    return LiquidityAnalysis(
        sweeps=detect_liquidity_sweeps(df, swing_points),
        order_blocks=detect_order_blocks(df, bos_events),
        fair_value_gaps=detect_fair_value_gaps(df),
    )
