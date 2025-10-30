from typing import Tuple


def compute_stop_take(entry_price: float, stop_pct: float, take_pct: float, long: bool = True) -> Tuple[float, float]:
    """
    Compute absolute stop-loss and take-profit levels given percentages.

    Args:
        entry_price: Entry execution price.
        stop_pct: Stop distance as fraction (e.g., 0.01 for 1%).
        take_pct: Take profit distance as fraction.
        long: True for long, False for short.

    Returns:
        (stop_price, take_price)
    """
    if long:
        stop = entry_price * (1 - stop_pct)
        take = entry_price * (1 + take_pct)
    else:
        stop = entry_price * (1 + stop_pct)
        take = entry_price * (1 - take_pct)
    return float(stop), float(take)
