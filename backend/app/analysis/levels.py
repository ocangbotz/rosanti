"""Support/Resistance level clustering and Supply/Demand zone detection."""

from __future__ import annotations

import pandas as pd

from app.analysis.indicators import atr
from app.analysis.schemas import LevelsAnalysis, SRLevel, SupplyDemandZone, SwingKind, SwingPoint

# % of price — swing points within this range of each other are "the same level"
DEFAULT_CLUSTER_TOLERANCE_PCT = 0.15
DEFAULT_ZONE_WIDTH_ATR_MULT = 0.5


def _flush_cluster(cluster: list[SwingPoint], sr_kind: str) -> SRLevel | None:
    if not cluster:
        return None
    avg_price = sum(p.price for p in cluster) / len(cluster)
    latest = max(cluster, key=lambda p: p.index)
    return SRLevel(price=avg_price, kind=sr_kind, touches=len(cluster), last_touch_time=latest.time)


def detect_support_resistance(
    swing_points: list[SwingPoint], tolerance_pct: float = DEFAULT_CLUSTER_TOLERANCE_PCT
) -> list[SRLevel]:
    """Cluster swing highs/lows that sit within `tolerance_pct` of each other
    into a single level; the more distinct swings touch a cluster, the more
    significant that level is treated as.
    """
    levels: list[SRLevel] = []

    for kind, sr_kind in ((SwingKind.HIGH, "RESISTANCE"), (SwingKind.LOW, "SUPPORT")):
        points = sorted((p for p in swing_points if p.kind == kind), key=lambda p: p.price)
        cluster: list[SwingPoint] = []

        for point in points:
            if not cluster:
                cluster.append(point)
                continue
            cluster_mid = sum(p.price for p in cluster) / len(cluster)
            if abs(point.price - cluster_mid) / cluster_mid * 100 <= tolerance_pct:
                cluster.append(point)
            else:
                if (level := _flush_cluster(cluster, sr_kind)) is not None:
                    levels.append(level)
                cluster = [point]
        if (level := _flush_cluster(cluster, sr_kind)) is not None:
            levels.append(level)

    levels.sort(key=lambda lvl: lvl.price)
    return levels


def detect_supply_demand_zones(
    df: pd.DataFrame,
    swing_points: list[SwingPoint],
    zone_width_atr_mult: float = DEFAULT_ZONE_WIDTH_ATR_MULT,
) -> list[SupplyDemandZone]:
    """Build a zone (not just a point) around each significant swing, sized
    by ATR so it scales with the instrument's volatility. A swing high forms
    a supply zone (sellers previously overwhelmed buyers there); a swing low
    forms a demand zone.
    """
    atr_series = atr(df, 14)
    zones: list[SupplyDemandZone] = []

    for point in swing_points:
        candle_atr = atr_series.iloc[point.index]
        if pd.isna(candle_atr) or candle_atr <= 0:
            continue
        width = float(candle_atr) * zone_width_atr_mult

        if point.kind == SwingKind.HIGH:
            top, bottom = point.price, point.price - width
            kind = "SUPPLY"
        else:
            top, bottom = point.price + width, point.price
            kind = "DEMAND"

        tested = False
        subsequent = df.iloc[point.index + 1 :]
        if len(subsequent):
            tested = bool(((subsequent["low"] <= top) & (subsequent["high"] >= bottom)).any())

        zones.append(
            SupplyDemandZone(top=top, bottom=bottom, kind=kind, formed_at=point.time, tested=tested)
        )

    return zones


def analyze_levels(df: pd.DataFrame, swing_points: list[SwingPoint]) -> LevelsAnalysis:
    return LevelsAnalysis(
        support_resistance=detect_support_resistance(swing_points),
        supply_demand_zones=detect_supply_demand_zones(df, swing_points),
    )
