"""Unit tests for compute_max_affordable in pricing_service."""

from decimal import Decimal

from app.services.pricing_service import compute_bulk_cost, compute_max_affordable


class TestComputeMaxAffordable:
    """Tests for compute_max_affordable(base_cost, growth_factor, growth_type,
    amount_owned, wallet_balance)."""

    _GF = Decimal("1.15")
    _GT = "linear_early_exp_late"

    def test_cannot_afford_even_one(self) -> None:
        result = compute_max_affordable(Decimal("100"), self._GF, self._GT, 0, Decimal("50"))
        assert result == 0

    def test_afford_exactly_one(self) -> None:
        # base_cost for 0 owned = 100; wallet = 100
        result = compute_max_affordable(Decimal("100"), self._GF, self._GT, 0, Decimal("100"))
        assert result == 1

    def test_afford_several_in_early_linear_zone(self) -> None:
        # With large wallet and small base_cost, can buy multiple
        result = compute_max_affordable(Decimal("10"), self._GF, self._GT, 0, Decimal("1000"))
        assert result > 10
        # Verify: total cost for result units should fit, result+1 should not
        total = compute_bulk_cost(Decimal("10"), self._GF, self._GT, 0, result)
        assert total <= Decimal("1000")
        if result > 0:
            total_plus_one = compute_bulk_cost(Decimal("10"), self._GF, self._GT, 0, result + 1)
            assert total_plus_one > Decimal("1000")

    def test_respects_amount_owned(self) -> None:
        # If already own 50 units (late game, exponential), costs are higher
        result_from_0 = compute_max_affordable(Decimal("10"), self._GF, self._GT, 0, Decimal("500"))
        result_from_50 = compute_max_affordable(
            Decimal("10"), self._GF, self._GT, 50, Decimal("500")
        )
        assert result_from_50 < result_from_0

    def test_zero_wallet_returns_zero(self) -> None:
        result = compute_max_affordable(Decimal("100"), self._GF, self._GT, 0, Decimal("0"))
        assert result == 0

    def test_returns_int(self) -> None:
        result = compute_max_affordable(Decimal("10"), self._GF, self._GT, 0, Decimal("100"))
        assert isinstance(result, int)

    def test_negative_wallet_returns_zero(self) -> None:
        result = compute_max_affordable(Decimal("10"), self._GF, self._GT, 0, Decimal("-5"))
        assert result == 0
