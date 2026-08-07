from app.analysis.levels import detect_supply_demand_zones, detect_support_resistance
from app.analysis.structure import detect_swing_points
from tests.factories import make_trend_then_reversal_ohlcv


def test_support_resistance_levels_are_sorted_by_price():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    levels = detect_support_resistance(points)
    prices = [lvl.price for lvl in levels]
    assert prices == sorted(prices)


def test_support_resistance_touch_counts_are_positive():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    levels = detect_support_resistance(points)
    assert all(lvl.touches >= 1 for lvl in levels)
    assert sum(lvl.touches for lvl in levels) == len(points)


def test_supply_demand_zones_have_valid_ranges():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    zones = detect_supply_demand_zones(df, points)
    assert all(zone.top >= zone.bottom for zone in zones)
    assert all(zone.kind in {"SUPPLY", "DEMAND"} for zone in zones)
