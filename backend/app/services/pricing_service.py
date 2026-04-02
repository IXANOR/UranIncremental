"""Unit cost calculation using the hybrid linear_early_exp_late curve.

Pricing formula for ``linear_early_exp_late`` (growth_factor = 1.15):
  - n ≤ 25  (early game): ``base × (1 + 0.15 × n)``
  - n > 25  (late game):  ``base × 1.15^n``

where ``n`` is the number of units already owned *before* the purchase.

The crossover at n = 25 keeps prices accessible in early game while ensuring
exponential scaling in late game. Both formulas yield the same value at n = 25.
"""

from decimal import Decimal

_EARLY_GAME_THRESHOLD = 25


def compute_unit_cost(
    base_cost: Decimal,
    growth_factor: Decimal,
    growth_type: str,
    amount_owned: int,
) -> Decimal:
    """Return the cost of the next unit given current ownership count.

    Args:
        base_cost: Base price of the first unit (n = 0).
        growth_factor: Multiplicative growth factor (e.g. Decimal("1.15")).
        growth_type: One of the supported curve types. Currently only
            ``"linear_early_exp_late"`` is implemented; any other value
            falls back to pure exponential.
        amount_owned: Number of units already owned before this purchase.

    Returns:
        Decimal cost for purchasing one unit at position ``amount_owned``.

    Raises:
        ValueError: If ``amount_owned`` is negative.
    """
    if amount_owned < 0:
        raise ValueError(f"amount_owned must be >= 0, got {amount_owned}")

    n = amount_owned

    if growth_type == "linear_early_exp_late":
        if n <= _EARLY_GAME_THRESHOLD:
            return base_cost * (Decimal("1") + (growth_factor - Decimal("1")) * n)
        return base_cost * (growth_factor**n)

    # Generic fallback: pure exponential
    return base_cost * (growth_factor**n)


def compute_bulk_cost(
    base_cost: Decimal,
    growth_factor: Decimal,
    growth_type: str,
    amount_owned: int,
    quantity: int,
) -> Decimal:
    """Return the total cost to purchase ``quantity`` units sequentially.

    Sums individual costs from ``amount_owned`` to ``amount_owned + quantity - 1``.

    Args:
        base_cost: Base price of the first unit.
        growth_factor: Multiplicative growth factor.
        growth_type: Curve type identifier.
        amount_owned: Units already owned before this purchase.
        quantity: How many units to buy.

    Returns:
        Total Decimal cost for all ``quantity`` units.

    Raises:
        ValueError: If ``quantity`` is less than 1 or ``amount_owned`` is negative.
    """
    if quantity < 1:
        raise ValueError(f"quantity must be >= 1, got {quantity}")
    if amount_owned < 0:
        raise ValueError(f"amount_owned must be >= 0, got {amount_owned}")

    return sum(
        (
            compute_unit_cost(base_cost, growth_factor, growth_type, amount_owned + i)
            for i in range(quantity)
        ),
        Decimal("0"),
    )


def compute_max_affordable(
    base_cost: Decimal,
    growth_factor: Decimal,
    growth_type: str,
    amount_owned: int,
    wallet_balance: Decimal,
) -> int:
    """Return the maximum number of units purchasable with ``wallet_balance``.

    Uses a binary search over ``compute_bulk_cost`` to find the largest quantity
    whose total cost does not exceed the wallet balance.

    Args:
        base_cost: Base price of the first unit.
        growth_factor: Multiplicative growth factor.
        growth_type: Curve type identifier (e.g. ``"linear_early_exp_late"``).
        amount_owned: Number of units already owned before this purchase.
        wallet_balance: Available currency.

    Returns:
        Maximum integer quantity the player can afford (0 if none).
    """
    if wallet_balance <= Decimal("0"):
        return 0

    # Quick check: can they afford even one?
    if compute_unit_cost(base_cost, growth_factor, growth_type, amount_owned) > wallet_balance:
        return 0

    lo, hi = 1, 1
    # Double hi until we overshoot or hit a reasonable cap
    while True:
        cost = compute_bulk_cost(base_cost, growth_factor, growth_type, amount_owned, hi)
        if cost > wallet_balance:
            break
        hi *= 2
        if hi > 100_000:
            break

    # Binary search between lo and hi
    while lo < hi:
        mid = (lo + hi + 1) // 2
        cost = compute_bulk_cost(base_cost, growth_factor, growth_type, amount_owned, mid)
        if cost <= wallet_balance:
            lo = mid
        else:
            hi = mid - 1

    return lo
