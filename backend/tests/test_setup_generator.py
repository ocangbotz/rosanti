from app.core.constants import TradeDirection
from app.strategies.setup_generator import MIN_RISK_REWARD, TradeSetupGenerator
from tests.analysis_factories import make_bullish_market_analysis, make_flat_market_analysis


def test_bullish_analysis_produces_a_valid_buy_setup():
    analysis = make_bullish_market_analysis()
    result = TradeSetupGenerator().generate(analysis)

    assert result.has_valid_setup is True
    assert result.setup is not None
    setup = result.setup

    assert setup.direction == TradeDirection.BUY
    assert setup.stop_loss < setup.entry_price < setup.take_profit
    assert setup.risk_reward >= MIN_RISK_REWARD - 1e-6
    assert setup.confidence_score == result.confidence
    assert len(setup.reasons) > 0


def test_flat_analysis_is_rejected_with_a_reason():
    analysis = make_flat_market_analysis()
    result = TradeSetupGenerator().generate(analysis)

    assert result.has_valid_setup is False
    assert result.setup is None
    assert result.rejection_reason is not None
    assert "%" in result.rejection_reason


def test_setup_structure_snapshot_matches_source_analysis():
    analysis = make_bullish_market_analysis()
    result = TradeSetupGenerator().generate(analysis)
    assert result.setup.structure_snapshot["symbol"] == analysis.symbol
    assert result.setup.structure_snapshot["candles_analyzed"] == analysis.candles_analyzed


def test_risk_reward_is_consistent_with_price_levels():
    analysis = make_bullish_market_analysis()
    result = TradeSetupGenerator().generate(analysis)
    setup = result.setup
    risk = setup.entry_price - setup.stop_loss
    reward = setup.take_profit - setup.entry_price
    assert risk > 0
    assert reward > 0
    assert abs(setup.risk_reward - reward / risk) < 1e-2
