def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss_price: float,
) -> float:
    """
    Calculate position size from account balance, risk percent, and stop-loss distance.

    Returns 0.0 if the stop-loss distance is zero.
    """
    if entry_price == stop_loss_price:
        return 0.0

    risk_amount_per_trade = account_balance * risk_percentage
    risk_per_unit = abs(entry_price - stop_loss_price)

    position_size = risk_amount_per_trade / risk_per_unit
    return float(max(position_size, 0.0))
