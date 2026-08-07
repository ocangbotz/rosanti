from app.core.constants import TradeDirection
from app.strategies.confluence import WEIGHT_BOS, WEIGHT_EMA_TREND, ConfluenceScorer
from tests.analysis_factories import make_bullish_market_analysis, make_flat_market_analysis


def test_bullish_analysis_scores_buy_higher_than_sell():
    analysis = make_bullish_market_analysis()
    buy_result, sell_result = ConfluenceScorer().score(analysis)

    assert buy_result.confidence > sell_result.confidence
    assert buy_result.direction == TradeDirection.BUY
    factor_names = {r.factor for r in buy_result.reasons}
    assert "structure_bos" in factor_names
    assert "ema_trend_alignment" in factor_names


def test_every_reason_direction_matches_the_scored_direction():
    analysis = make_bullish_market_analysis()
    buy_result, sell_result = ConfluenceScorer().score(analysis)
    assert all(r.direction == TradeDirection.BUY for r in buy_result.reasons)
    assert all(r.direction == TradeDirection.SELL for r in sell_result.reasons)


def test_confidence_is_sum_of_reason_weights_capped_at_100():
    analysis = make_bullish_market_analysis()
    buy_result, _ = ConfluenceScorer().score(analysis)
    expected = min(sum(r.weight for r in buy_result.reasons), 100.0)
    assert buy_result.confidence == expected


def test_flat_analysis_scores_low_on_both_sides():
    analysis = make_flat_market_analysis()
    buy_result, sell_result = ConfluenceScorer().score(analysis)
    assert buy_result.confidence < 40
    assert sell_result.confidence < 40


def test_bos_and_ema_alone_would_not_reach_full_confidence():
    # Sanity check on the weight table: no single pair of factors should be
    # able to fake a 100% "everything agrees" score.
    assert WEIGHT_BOS + WEIGHT_EMA_TREND < 100
