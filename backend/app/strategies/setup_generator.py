"""Trade setup generation: turns a scored confluence result into concrete
entry/stop-loss/take-profit levels, or explains why no valid setup exists.

Design intent (see docs/ARCHITECTURE.md §1): this module never invents a
trade. If neither direction clears `MIN_CONFIDENCE_THRESHOLD`, it returns
`has_valid_setup=False` with the scored reasons attached, so the caller can
show the trader *why* the market doesn't currently qualify.
"""

from __future__ import annotations

from app.analysis.schemas import MarketAnalysis, SwingKind, SwingPoint
from app.core.constants import TradeDirection, VolatilityRegime
from app.schemas.setup import Reason
from app.strategies.confluence import ConfluenceScorer
from app.strategies.schemas import ConfluenceResult, SetupGenerationResult, TradeSetupProposal

MIN_CONFIDENCE_THRESHOLD = 40.0
MIN_RISK_REWARD = 1.5
DEFAULT_TARGET_RR = 2.5
SL_BUFFER_ATR_MULT = 0.25
ZONE_ENTRY_PROXIMITY_ATR_MULT = 1.5
EXTREME_VOLATILITY_CONFIDENCE_MULT = 0.85


def _most_recent_swing(swing_points: list[SwingPoint], kind: SwingKind) -> SwingPoint | None:
    matching = [p for p in swing_points if p.kind == kind]
    return matching[-1] if matching else None


class TradeSetupGenerator:
    """Combines `ConfluenceScorer` with structure-aware entry/SL/TP placement."""

    def __init__(self, scorer: ConfluenceScorer | None = None):
        self.scorer = scorer or ConfluenceScorer()

    def generate(self, analysis: MarketAnalysis) -> SetupGenerationResult:
        buy_result, sell_result = self.scorer.score(analysis)
        winner = buy_result if buy_result.confidence >= sell_result.confidence else sell_result

        if (
            winner.confidence < MIN_CONFIDENCE_THRESHOLD
            or winner.direction == TradeDirection.NEUTRAL
        ):
            return SetupGenerationResult(
                symbol=analysis.symbol,
                timeframe=analysis.timeframe,
                has_valid_setup=False,
                setup=None,
                dominant_direction=winner.direction,
                confidence=round(winner.confidence, 1),
                reasons=winner.reasons,
                rejection_reason=(
                    f"Confidence ({winner.confidence:.0f}%) is below the "
                    f"{MIN_CONFIDENCE_THRESHOLD:.0f}% threshold required to propose a trade — "
                    "confluence is too weak or conflicting right now."
                ),
            )

        proposal = self._build_proposal(analysis, winner)
        if proposal is None:
            return SetupGenerationResult(
                symbol=analysis.symbol,
                timeframe=analysis.timeframe,
                has_valid_setup=False,
                setup=None,
                dominant_direction=winner.direction,
                confidence=round(winner.confidence, 1),
                reasons=winner.reasons,
                rejection_reason=(
                    "Confluence supports a "
                    f"{winner.direction.value} bias, but no stop-loss reference structure "
                    "(swing high/low) was found to safely place a setup."
                ),
            )

        return SetupGenerationResult(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            has_valid_setup=True,
            setup=proposal,
            dominant_direction=winner.direction,
            confidence=proposal.confidence_score,
            reasons=proposal.reasons,
        )

    def _build_proposal(
        self, analysis: MarketAnalysis, winner: ConfluenceResult
    ) -> TradeSetupProposal | None:
        direction = winner.direction
        atr = max(analysis.volatility.atr, 1e-9)
        price = analysis.indicators.price

        entry = self._determine_entry(analysis, direction, price, atr)
        stop_loss = self._determine_stop_loss(analysis, direction, entry, atr)
        if stop_loss is None:
            return None

        risk = abs(entry - stop_loss)
        take_profit = self._determine_take_profit(analysis, direction, entry, risk)

        risk_reward = abs(take_profit - entry) / risk if risk > 0 else 0.0

        confidence = winner.confidence
        reasons = list(winner.reasons)
        if analysis.volatility.regime == VolatilityRegime.EXTREME:
            confidence = round(confidence * EXTREME_VOLATILITY_CONFIDENCE_MULT, 1)
            reasons = [
                *reasons,
                _volatility_warning_reason(direction),
            ]

        return TradeSetupProposal(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            direction=direction,
            entry_price=round(entry, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            risk_reward=round(risk_reward, 2),
            confidence_score=round(min(confidence, 100.0), 1),
            reasons=reasons,
            structure_snapshot=analysis.model_dump(mode="json"),
        )

    def _determine_entry(
        self, analysis: MarketAnalysis, direction: TradeDirection, price: float, atr: float
    ) -> float:
        """Prefer entering at the edge of a nearby unmitigated order block/zone
        (a disciplined pullback entry) over chasing the current market price."""
        is_buy = direction == TradeDirection.BUY

        for ob in reversed(analysis.liquidity.order_blocks):
            if ob.direction != direction or ob.mitigated:
                continue
            edge = ob.top if is_buy else ob.bottom
            if abs(price - edge) <= atr * ZONE_ENTRY_PROXIMITY_ATR_MULT:
                return edge

        zone_kind = "DEMAND" if is_buy else "SUPPLY"
        for zone in reversed(analysis.levels.supply_demand_zones):
            if zone.kind != zone_kind:
                continue
            edge = zone.top if is_buy else zone.bottom
            if abs(price - edge) <= atr * ZONE_ENTRY_PROXIMITY_ATR_MULT:
                return edge

        return price

    def _determine_stop_loss(
        self, analysis: MarketAnalysis, direction: TradeDirection, entry: float, atr: float
    ) -> float | None:
        is_buy = direction == TradeDirection.BUY
        buffer = atr * SL_BUFFER_ATR_MULT

        reference_prices = []
        swing = _most_recent_swing(
            analysis.structure.swing_points, SwingKind.LOW if is_buy else SwingKind.HIGH
        )
        if swing is not None:
            reference_prices.append(swing.price)

        for ob in reversed(analysis.liquidity.order_blocks):
            if ob.direction == direction and not ob.mitigated:
                reference_prices.append(ob.bottom if is_buy else ob.top)
                break

        if not reference_prices:
            return None

        if is_buy:
            reference = min(reference_prices)
            stop_loss = reference - buffer
            if stop_loss >= entry:
                return None
        else:
            reference = max(reference_prices)
            stop_loss = reference + buffer
            if stop_loss <= entry:
                return None

        return stop_loss

    def _determine_take_profit(
        self, analysis: MarketAnalysis, direction: TradeDirection, entry: float, risk: float
    ) -> float:
        is_buy = direction == TradeDirection.BUY
        candidates: list[float] = []

        opposing_sr_kind = "RESISTANCE" if is_buy else "SUPPORT"
        for level in analysis.levels.support_resistance:
            beyond_entry = (is_buy and level.price > entry) or (not is_buy and level.price < entry)
            if level.kind == opposing_sr_kind and beyond_entry:
                candidates.append(level.price)

        opposing_direction = TradeDirection.SELL if is_buy else TradeDirection.BUY
        for ob in analysis.liquidity.order_blocks:
            if ob.direction == opposing_direction and not ob.mitigated:
                edge = ob.bottom if is_buy else ob.top
                if (is_buy and edge > entry) or (not is_buy and edge < entry):
                    candidates.append(edge)

        opposing_zone_kind = "SUPPLY" if is_buy else "DEMAND"
        for zone in analysis.levels.supply_demand_zones:
            if zone.kind == opposing_zone_kind:
                edge = zone.bottom if is_buy else zone.top
                if (is_buy and edge > entry) or (not is_buy and edge < entry):
                    candidates.append(edge)

        candidates.sort(key=lambda p: abs(p - entry))

        default_target = (
            entry + risk * DEFAULT_TARGET_RR if is_buy else entry - risk * DEFAULT_TARGET_RR
        )

        for candidate in candidates:
            candidate_rr = abs(candidate - entry) / risk if risk > 0 else 0.0
            if candidate_rr >= MIN_RISK_REWARD:
                return candidate

        return default_target


def _volatility_warning_reason(direction: TradeDirection) -> Reason:
    return Reason(
        factor="volatility_warning",
        description="Volatility is in the EXTREME regime — confidence has been reduced and "
        "position size should be trimmed accordingly.",
        direction=direction,
        weight=0.0,
    )
