"""Breakeven calculator: tracks how many R (initial-risk multiples) a trade
has moved in the trader's favor, and whether it has earned a stop-loss move
to breakeven per the account's configured trigger.
"""

from __future__ import annotations

from app.core.exceptions import ValidationFailedError
from app.schemas.risk import BreakevenRequest, BreakevenResponse


def calculate_breakeven(request: BreakevenRequest) -> BreakevenResponse:
    is_buy = request.direction == "BUY"

    risk_distance = (
        request.entry_price - request.stop_loss
        if is_buy
        else request.stop_loss - request.entry_price
    )
    if risk_distance <= 0:
        raise ValidationFailedError(
            "Stop loss must be on the risk side of entry "
            "(below entry for BUY, above entry for SELL)."
        )

    favorable_move = (
        request.current_price - request.entry_price
        if is_buy
        else request.entry_price - request.current_price
    )
    # Round before comparing against the trigger so binary floating-point
    # representation error (e.g. 0.005/0.005 evaluating to
    # 0.9999999999999998) doesn't produce a false negative on an exact hit.
    current_r_multiple = round(favorable_move / risk_distance, 6)

    breakeven_reached = current_r_multiple >= request.trigger_r
    suggested_new_stop_loss = request.entry_price if breakeven_reached else None

    return BreakevenResponse(
        current_r_multiple=round(current_r_multiple, 2),
        breakeven_reached=breakeven_reached,
        suggested_new_stop_loss=suggested_new_stop_loss,
    )
