"""Unit tests for economy_service: buy_unit and buy_upgrade transactions."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.economy_service import (
    AlreadyPurchasedError,
    InsufficientFundsError,
    InvalidQuantityError,
    UnknownUnitError,
    UnknownUpgradeError,
    buy_unit,
    buy_upgrade,
)

# ---------------------------------------------------------------------------
# buy_unit — success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_unit_deducts_wallet(db_session: AsyncSession) -> None:
    """Purchasing a barrel should deduct its cost from energy_drink."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        # Give player plenty of funds
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("500")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await buy_unit(db_session, p, "barrel")

    # barrel base cost = 15, n=0 → cost = 15; 500 - 15 = 485
    assert result.wallet.energy_drink == Decimal("485")
    assert result.player_unit.amount_owned == 1
    assert result.total_cost == Decimal("15")


@pytest.mark.asyncio
async def test_buy_unit_increments_amount_owned(db_session: AsyncSession) -> None:
    """Buying a unit when already owning some should increment the count."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("10000")
        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=5)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await buy_unit(db_session, p, "barrel", quantity=3)

    assert result.player_unit.amount_owned == 8
    assert result.total_cost > Decimal("0")


@pytest.mark.asyncio
async def test_buy_unit_bulk_cost_is_sequential_sum(db_session: AsyncSession) -> None:
    """Bulk purchase cost must equal the sum of individual unit costs."""
    from app.services.pricing_service import compute_unit_cost

    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("50000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await buy_unit(db_session, p, "barrel", quantity=5)

    from app.db.repositories.unit_definition import UnitDefinitionRepository
    async with db_session.begin():
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert barrel is not None

    expected = sum(
        compute_unit_cost(barrel.base_cost_amount, barrel.cost_growth_factor,
                          barrel.cost_growth_type, i)
        for i in range(5)
    )
    assert result.total_cost == expected


# ---------------------------------------------------------------------------
# buy_unit — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_unit_insufficient_funds(db_session: AsyncSession) -> None:
    """Buying with insufficient energy_drink should raise InsufficientFundsError."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("0")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(InsufficientFundsError):
            await buy_unit(db_session, p, "barrel")


@pytest.mark.asyncio
async def test_buy_unit_zero_quantity_rejected(db_session: AsyncSession) -> None:
    """Quantity of 0 must be rejected before any DB access."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(InvalidQuantityError):
            await buy_unit(db_session, p, "barrel", quantity=0)


@pytest.mark.asyncio
async def test_buy_unit_unknown_unit_id(db_session: AsyncSession) -> None:
    """Buying a non-existent unit_id should raise UnknownUnitError."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(UnknownUnitError):
            await buy_unit(db_session, p, "nonexistent_unit")


# ---------------------------------------------------------------------------
# buy_upgrade — success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_upgrade_deducts_wallet(db_session: AsyncSession) -> None:
    """Buying barrel_opt_mk1 should deduct 200 energy_drink from wallet."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("1000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await buy_upgrade(db_session, p, "barrel_opt_mk1")

    assert result.wallet.energy_drink == Decimal("800")
    assert result.player_upgrade.upgrade_id == "barrel_opt_mk1"
    assert result.player_upgrade.level == 1


@pytest.mark.asyncio
async def test_buy_upgrade_prod_mult_updates_effective_multiplier(
    db_session: AsyncSession,
) -> None:
    """barrel_opt_mk1 (×1.10) should update barrel's effective_multiplier."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("1000")
        # Ensure barrel unit row exists
        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=1)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await buy_upgrade(db_session, p, "barrel_opt_mk1")

    async with db_session.begin():
        barrel_unit = await PlayerUnitRepository.get_by_player_and_unit(
            db_session, player.id, "barrel"
        )
        assert barrel_unit is not None
        assert barrel_unit.effective_multiplier == pytest.approx(
            Decimal("1.10"), rel=Decimal("0.001")
        )


@pytest.mark.asyncio
async def test_buy_upgrade_offline_eff_up_updates_player(
    db_session: AsyncSession,
) -> None:
    """offline_module_mk1 (+0.05) should increase player offline_efficiency."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("1000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        initial_eff = p.offline_efficiency
        await buy_upgrade(db_session, p, "offline_module_mk1")
        assert p.offline_efficiency == pytest.approx(initial_eff + 0.05, rel=0.001)


@pytest.mark.asyncio
async def test_buy_upgrade_offline_cap_up_updates_player(
    db_session: AsyncSession,
) -> None:
    """offline_cap_mk1 (+7200s) should increase player offline_cap_seconds."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("5000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        initial_cap = p.offline_cap_seconds
        await buy_upgrade(db_session, p, "offline_cap_mk1")
        assert p.offline_cap_seconds == initial_cap + 7200


# ---------------------------------------------------------------------------
# buy_upgrade — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_upgrade_already_purchased_raises(db_session: AsyncSession) -> None:
    """Buying a non-repeatable upgrade twice should raise AlreadyPurchasedError."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("5000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await buy_upgrade(db_session, p, "barrel_opt_mk1")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("5000")
        with pytest.raises(AlreadyPurchasedError):
            await buy_upgrade(db_session, p, "barrel_opt_mk1")


@pytest.mark.asyncio
async def test_buy_upgrade_insufficient_funds_raises(db_session: AsyncSession) -> None:
    """Buying with insufficient balance should raise InsufficientFundsError."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("0")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(InsufficientFundsError):
            await buy_upgrade(db_session, p, "barrel_opt_mk1")


@pytest.mark.asyncio
async def test_buy_upgrade_unknown_id_raises(db_session: AsyncSession) -> None:
    """Buying a non-existent upgrade_id should raise UnknownUpgradeError."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(UnknownUpgradeError):
            await buy_upgrade(db_session, p, "nonexistent_upgrade")
