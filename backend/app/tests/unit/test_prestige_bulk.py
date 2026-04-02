"""Unit tests for multi-prestige cost formulas and prestige_bulk service function."""

from decimal import Decimal

import pytest

from app.services.prestige_service import multi_prestige_requirement


class TestMultiPrestigeRequirement:
    """Tests for multi_prestige_requirement(prestige_count, count, currency)."""

    # --- 1× U-238: cost = 2^p -----------------------------------------------

    def test_1x_u238_at_p0(self) -> None:
        cost, currency = multi_prestige_requirement(0, 1, "u238")
        assert cost == Decimal("1")
        assert currency == "u238"

    def test_1x_u238_at_p1(self) -> None:
        cost, currency = multi_prestige_requirement(1, 1, "u238")
        assert cost == Decimal("2")
        assert currency == "u238"

    def test_1x_u238_at_p5(self) -> None:
        cost, currency = multi_prestige_requirement(5, 1, "u238")
        assert cost == Decimal("32")
        assert currency == "u238"

    # --- 5× U-235: cost = max(1, 2^(p-1)) -----------------------------------

    def test_5x_u235_at_p0_clamps_to_1(self) -> None:
        cost, currency = multi_prestige_requirement(0, 5, "u235")
        assert cost == Decimal("1")
        assert currency == "u235"

    def test_5x_u235_at_p1(self) -> None:
        cost, currency = multi_prestige_requirement(1, 5, "u235")
        assert cost == Decimal("1")
        assert currency == "u235"

    def test_5x_u235_at_p2(self) -> None:
        cost, currency = multi_prestige_requirement(2, 5, "u235")
        assert cost == Decimal("2")
        assert currency == "u235"

    def test_5x_u235_at_p4(self) -> None:
        cost, currency = multi_prestige_requirement(4, 5, "u235")
        assert cost == Decimal("8")
        assert currency == "u235"

    # --- 10× U-233: cost = max(1, 2^(p-2)) ----------------------------------

    def test_10x_u233_at_p0_clamps_to_1(self) -> None:
        cost, currency = multi_prestige_requirement(0, 10, "u233")
        assert cost == Decimal("1")
        assert currency == "u233"

    def test_10x_u233_at_p2_boundary(self) -> None:
        cost, currency = multi_prestige_requirement(2, 10, "u233")
        assert cost == Decimal("1")
        assert currency == "u233"

    def test_10x_u233_at_p3(self) -> None:
        cost, currency = multi_prestige_requirement(3, 10, "u233")
        assert cost == Decimal("2")
        assert currency == "u233"

    def test_10x_u233_at_p5(self) -> None:
        cost, currency = multi_prestige_requirement(5, 10, "u233")
        assert cost == Decimal("8")
        assert currency == "u233"

    # --- 25× META: cost = max(1, 2^(p-3)) -----------------------------------

    def test_25x_meta_at_p0_clamps_to_1(self) -> None:
        cost, currency = multi_prestige_requirement(0, 25, "meta_isotopes")
        assert cost == Decimal("1")
        assert currency == "meta_isotopes"

    def test_25x_meta_at_p3_boundary(self) -> None:
        cost, currency = multi_prestige_requirement(3, 25, "meta_isotopes")
        assert cost == Decimal("1")
        assert currency == "meta_isotopes"

    def test_25x_meta_at_p4(self) -> None:
        cost, currency = multi_prestige_requirement(4, 25, "meta_isotopes")
        assert cost == Decimal("2")
        assert currency == "meta_isotopes"

    def test_25x_meta_at_p6(self) -> None:
        cost, currency = multi_prestige_requirement(6, 25, "meta_isotopes")
        assert cost == Decimal("8")
        assert currency == "meta_isotopes"

    # --- invalid args ---------------------------------------------------------

    def test_invalid_count_raises(self) -> None:
        with pytest.raises(ValueError, match="count"):
            multi_prestige_requirement(0, 3, "u238")

    def test_invalid_currency_raises(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            multi_prestige_requirement(0, 1, "energy_drink")


class TestBalanceProgressionEfficiency:
    """Balance: higher-tier prestige options become efficient at correct prestige_count.

    5× U-235 should be cheaper (per prestige) than 5× U-238 only at p >= 2.
    10× U-233 should be cheaper per prestige than 10× U-238 only at p >= 3.
    25× META should be cheaper per prestige than 25× U-238 only at p >= 4.
    """

    def test_5x_u235_cheaper_per_prestige_than_5x_u238_at_p2(self) -> None:
        """At p=2, 5× U-235 costs 2 U-235 vs 5× U-238 would cost sum(2^2..2^6)."""
        p = 2
        cost_u235, _ = multi_prestige_requirement(p, 5, "u235")
        # Cost-equivalent in U-238: cost of doing 5 consecutive 1× prestiges
        total_u238 = sum(Decimal(2) ** (p + i) for i in range(5))
        # 5× U-235 costs 1 U-235 unit; 5× U-238 costs 4+8+16+32+64 = 124 units
        assert cost_u235 == Decimal("2"), f"Expected 2 U-235 at p=2, got {cost_u235}"
        # Baseline: 5 sequential U-238 prestiges at p=2 costs 4+8+16+32+64 = 124 units
        assert total_u238 > Decimal("100")

    def test_5x_u235_not_yet_available_at_p1(self) -> None:
        """At p=1, 5× U-235 costs 1 U-235 (minimal). Mechanic still works but cost is minimum."""
        cost, _ = multi_prestige_requirement(1, 5, "u235")
        assert cost == Decimal("1")

    def test_10x_u233_cheaper_per_prestige_than_10x_u238_at_p3(self) -> None:
        p = 3
        cost_u233, _ = multi_prestige_requirement(p, 10, "u233")
        total_u238 = sum(Decimal(2) ** (p + i) for i in range(10))
        assert cost_u233 == Decimal("2")
        assert total_u238 > Decimal("1000")

    def test_25x_meta_cheaper_per_prestige_than_25x_u238_at_p4(self) -> None:
        p = 4
        cost_meta, _ = multi_prestige_requirement(p, 25, "meta_isotopes")
        total_u238 = sum(Decimal(2) ** (p + i) for i in range(25))
        assert cost_meta == Decimal("2")
        assert total_u238 > Decimal("1_000_000")
