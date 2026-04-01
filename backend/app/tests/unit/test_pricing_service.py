"""Unit tests for pricing_service: hybrid linear_early_exp_late cost curve."""

from decimal import Decimal

import pytest

from app.services.pricing_service import compute_bulk_cost, compute_unit_cost

_BASE = Decimal("100")
_FACTOR = Decimal("1.15")
_TYPE = "linear_early_exp_late"


# ---------------------------------------------------------------------------
# compute_unit_cost — linear phase (n <= 25)
# ---------------------------------------------------------------------------


def test_first_unit_costs_base() -> None:
    """n = 0 should return base cost unchanged."""
    assert compute_unit_cost(_BASE, _FACTOR, _TYPE, 0) == _BASE


def test_linear_phase_n1() -> None:
    """n = 1: base × (1 + 0.15 × 1) = 115."""
    assert compute_unit_cost(_BASE, _FACTOR, _TYPE, 1) == Decimal("115")


def test_linear_phase_n10() -> None:
    """n = 10: base × (1 + 0.15 × 10) = 250."""
    assert compute_unit_cost(_BASE, _FACTOR, _TYPE, 10) == Decimal("250")


def test_linear_phase_n25() -> None:
    """n = 25: base × (1 + 0.15 × 25) = base × 4.75 = 475."""
    assert compute_unit_cost(_BASE, _FACTOR, _TYPE, 25) == Decimal("475")


# ---------------------------------------------------------------------------
# compute_unit_cost — exponential phase (n > 25)
# ---------------------------------------------------------------------------


def test_exponential_phase_n26() -> None:
    """n = 26: base × 1.15^26; must exceed linear value at n=25."""
    linear_n25 = compute_unit_cost(_BASE, _FACTOR, _TYPE, 25)
    exp_n26 = compute_unit_cost(_BASE, _FACTOR, _TYPE, 26)
    assert exp_n26 > linear_n25


def test_exponential_phase_grows() -> None:
    """Cost at n=50 should be strictly greater than at n=26."""
    cost_26 = compute_unit_cost(_BASE, _FACTOR, _TYPE, 26)
    cost_50 = compute_unit_cost(_BASE, _FACTOR, _TYPE, 50)
    assert cost_50 > cost_26


def test_exponential_phase_n30_formula() -> None:
    """n = 30: base × 1.15^30 — verify against direct formula."""
    expected = _BASE * (Decimal("1.15") ** 30)
    result = compute_unit_cost(_BASE, _FACTOR, _TYPE, 30)
    assert result == pytest.approx(expected, rel=Decimal("0.0001"))


# ---------------------------------------------------------------------------
# compute_unit_cost — invariants
# ---------------------------------------------------------------------------


def test_cost_never_negative_any_n() -> None:
    """Cost must be positive for any realistic n."""
    for n in range(0, 101):
        cost = compute_unit_cost(_BASE, _FACTOR, _TYPE, n)
        assert cost > Decimal("0"), f"Negative cost at n={n}"


def test_cost_is_monotonically_increasing() -> None:
    """Each successive unit should cost at least as much as the previous."""
    prev = compute_unit_cost(_BASE, _FACTOR, _TYPE, 0)
    for n in range(1, 60):
        curr = compute_unit_cost(_BASE, _FACTOR, _TYPE, n)
        assert curr >= prev, f"Cost decreased from n={n - 1} to n={n}"
        prev = curr


def test_negative_amount_owned_raises() -> None:
    """Negative amount_owned is a programming error."""
    with pytest.raises(ValueError):
        compute_unit_cost(_BASE, _FACTOR, _TYPE, -1)


# ---------------------------------------------------------------------------
# compute_bulk_cost
# ---------------------------------------------------------------------------


def test_bulk_cost_quantity_1_equals_unit_cost() -> None:
    """bulk cost for qty=1 must equal compute_unit_cost."""
    assert compute_bulk_cost(_BASE, _FACTOR, _TYPE, 5, 1) == compute_unit_cost(
        _BASE, _FACTOR, _TYPE, 5
    )


def test_bulk_cost_quantity_3() -> None:
    """bulk cost for qty=3 = sum of costs at n, n+1, n+2."""
    n = 3
    expected = sum(compute_unit_cost(_BASE, _FACTOR, _TYPE, n + i) for i in range(3))
    assert compute_bulk_cost(_BASE, _FACTOR, _TYPE, n, 3) == expected


def test_bulk_cost_zero_quantity_raises() -> None:
    """Quantity of 0 must be rejected."""
    with pytest.raises(ValueError):
        compute_bulk_cost(_BASE, _FACTOR, _TYPE, 0, 0)


def test_bulk_cost_negative_quantity_raises() -> None:
    """Negative quantity must be rejected."""
    with pytest.raises(ValueError):
        compute_bulk_cost(_BASE, _FACTOR, _TYPE, 0, -5)
