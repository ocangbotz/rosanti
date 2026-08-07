"""Position sizing: converts an account's risk % into a concrete lot size
for a given stop-loss distance — the calculation that turns a trade idea's
entry/SL into "how much do I actually put on".
"""

from __future__ import annotations

import math

from app.core.exceptions import ValidationFailedError
from app.schemas.risk import LotSizeRequest, LotSizeResponse

LOT_STEP = 0.01
MIN_LOT = 0.01
MAX_LOT = 100.0


def calculate_lot_size(request: LotSizeRequest) -> LotSizeResponse:
    """Standard fixed-fractional position sizing:

        risk_amount   = account_balance * risk_percent / 100
        sl_pips       = |entry - stop_loss| / pip_size
        lot_size      = risk_amount / (sl_pips * pip_value_per_lot)

    The result is floored to the broker's lot step so the *realized* risk
    never exceeds the requested risk_percent (rounding up could silently
    over-risk the account).
    """
    stop_loss_distance = abs(request.entry_price - request.stop_loss)
    if stop_loss_distance <= 0:
        raise ValidationFailedError("Stop loss must be different from the entry price.")

    risk_amount = request.account_balance * (request.risk_percent / 100)
    stop_loss_pips = stop_loss_distance / request.pip_size

    raw_lot_size = risk_amount / (stop_loss_pips * request.pip_value_per_lot)
    # Floor to the lot step, but nudge by a tiny epsilon first so a value
    # that's mathematically exact (e.g. 0.2) doesn't get floored down one
    # step due to binary floating-point representation error (e.g. 0.2 /
    # 0.01 evaluating to 19.999999999998 instead of 20).
    steps = raw_lot_size / LOT_STEP
    lot_size = math.floor(steps + 1e-9) * LOT_STEP
    lot_size = max(MIN_LOT, min(lot_size, MAX_LOT))
    lot_size = round(lot_size, 2)

    return LotSizeResponse(
        lot_size=lot_size,
        risk_amount=round(risk_amount, 2),
        stop_loss_pips=round(stop_loss_pips, 1),
        pip_value_per_lot=request.pip_value_per_lot,
    )
