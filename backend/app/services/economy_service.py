"""Economy transactions: buying units and upgrades.

All public functions are atomic — they call ``session.flush()`` at the end so
the caller's transaction can be committed (or rolled back) as a unit.

Supported upgrade effect types:
- ``prod_mult``:      multiply ``PlayerUnit.effective_multiplier`` for ``target_unit_id``
- ``offline_eff_up``: increase ``PlayerState.offline_efficiency``
- ``offline_cap_up``: increase ``PlayerState.offline_cap_seconds``
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.player_state import PlayerState
from app.db.models.unit import PlayerUnit
from app.db.models.upgrade import PlayerUpgrade, UpgradeDefinition
from app.db.models.wallet import Wallet
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository
from app.db.repositories.wallet import WalletRepository
from app.services.pricing_service import compute_bulk_cost


class InsufficientFundsError(Exception):
    """Raised when the player cannot afford the requested purchase."""


class AlreadyPurchasedError(Exception):
    """Raised when a non-repeatable upgrade has already been bought."""


class InvalidQuantityError(Exception):
    """Raised when the requested quantity is ≤ 0."""


class UnknownUnitError(Exception):
    """Raised when the requested unit_id does not exist in unit_definition."""


class UnknownUpgradeError(Exception):
    """Raised when the requested upgrade_id does not exist in upgrade_definition."""


@dataclass
class BuyUnitResult:
    """Result of a successful unit purchase.

    Attributes:
        wallet: Updated wallet after deduction.
        player_unit: Updated PlayerUnit row.
        total_cost: Total energy_drink (or other currency) spent.
    """

    wallet: Wallet
    player_unit: PlayerUnit
    total_cost: Decimal


@dataclass
class BuyUpgradeResult:
    """Result of a successful upgrade purchase.

    Attributes:
        wallet: Updated wallet after deduction.
        player_upgrade: Newly created PlayerUpgrade row.
        upgrade_def: The upgrade definition that was purchased.
    """

    wallet: Wallet
    player_upgrade: PlayerUpgrade
    upgrade_def: UpgradeDefinition


async def buy_unit(
    session: AsyncSession,
    player: PlayerState,
    unit_id: str,
    quantity: int = 1,
) -> BuyUnitResult:
    """Purchase ``quantity`` units of type ``unit_id`` for the given player.

    Deducts the total cost from the wallet using the hybrid pricing curve.
    The transaction is not committed here — caller owns the session boundary.

    Args:
        session: Active async database session (within a transaction).
        player: PlayerState row for the purchasing player.
        unit_id: Identifier of the unit to buy.
        quantity: Number of units to purchase (must be ≥ 1).

    Returns:
        BuyUnitResult with updated wallet and player_unit rows.

    Raises:
        InvalidQuantityError: If ``quantity`` < 1.
        UnknownUnitError: If ``unit_id`` is not in ``unit_definition``.
        InsufficientFundsError: If wallet balance is below the total cost.
    """
    if quantity < 1:
        raise InvalidQuantityError(f"quantity must be >= 1, got {quantity}")

    unit_def = await UnitDefinitionRepository.get_by_id(session, unit_id)
    if unit_def is None:
        raise UnknownUnitError(f"Unit '{unit_id}' not found")

    player_unit = await PlayerUnitRepository.get_by_player_and_unit(session, player.id, unit_id)
    amount_owned = player_unit.amount_owned if player_unit is not None else 0

    total_cost = compute_bulk_cost(
        unit_def.base_cost_amount,
        unit_def.cost_growth_factor,
        unit_def.cost_growth_type,
        amount_owned,
        quantity,
    )

    wallet = await WalletRepository.get_by_player(session, player.id)
    if wallet is None:
        raise RuntimeError(f"Wallet not found for player {player.id}")

    currency_balance: Decimal = getattr(wallet, unit_def.base_cost_currency)
    if currency_balance < total_cost:
        raise InsufficientFundsError(
            f"Need {total_cost} {unit_def.base_cost_currency}, have {currency_balance}"
        )

    setattr(wallet, unit_def.base_cost_currency, currency_balance - total_cost)

    new_player_unit = await PlayerUnitRepository.upsert(
        session,
        player.id,
        unit_id,
        amount_owned=amount_owned + quantity,
    )

    await session.flush()
    return BuyUnitResult(wallet=wallet, player_unit=new_player_unit, total_cost=total_cost)


async def buy_upgrade(
    session: AsyncSession,
    player: PlayerState,
    upgrade_id: str,
) -> BuyUpgradeResult:
    """Purchase upgrade ``upgrade_id`` for the given player and apply its effect.

    Non-repeatable upgrades may only be purchased once. After deducting the cost,
    the upgrade's effect is applied immediately to the relevant player data.

    Args:
        session: Active async database session (within a transaction).
        player: PlayerState row for the purchasing player.
        upgrade_id: Identifier of the upgrade to buy.

    Returns:
        BuyUpgradeResult with updated wallet, new PlayerUpgrade row, and upgrade def.

    Raises:
        UnknownUpgradeError: If ``upgrade_id`` is not in ``upgrade_definition``.
        AlreadyPurchasedError: If the upgrade is non-repeatable and already owned.
        InsufficientFundsError: If wallet balance is below the upgrade cost.
    """
    upgrade_def = await UpgradeDefinitionRepository.get_by_id(session, upgrade_id)
    if upgrade_def is None:
        raise UnknownUpgradeError(f"Upgrade '{upgrade_id}' not found")

    existing = await PlayerUpgradeRepository.get_by_player_and_upgrade(
        session, player.id, upgrade_id
    )
    if existing is not None and not upgrade_def.is_repeatable:
        raise AlreadyPurchasedError(
            f"Upgrade '{upgrade_id}' already purchased and is not repeatable"
        )

    wallet = await WalletRepository.get_by_player(session, player.id)
    if wallet is None:
        raise RuntimeError(f"Wallet not found for player {player.id}")

    currency_balance: Decimal = getattr(wallet, upgrade_def.cost_currency)
    if currency_balance < upgrade_def.cost_amount:
        raise InsufficientFundsError(
            f"Need {upgrade_def.cost_amount} {upgrade_def.cost_currency}, have {currency_balance}"
        )

    setattr(wallet, upgrade_def.cost_currency, currency_balance - upgrade_def.cost_amount)

    if existing is not None:
        player_upgrade = await PlayerUpgradeRepository.increment_level(session, existing)
    else:
        player_upgrade = await PlayerUpgradeRepository.create(session, player.id, upgrade_id)

    await _apply_upgrade_effect(session, player, upgrade_def)

    await session.flush()
    return BuyUpgradeResult(wallet=wallet, player_upgrade=player_upgrade, upgrade_def=upgrade_def)


async def _apply_upgrade_effect(
    session: AsyncSession,
    player: PlayerState,
    upgrade_def: UpgradeDefinition,
) -> None:
    """Apply the upgrade's effect to player state or unit multipliers.

    Args:
        session: Active async database session.
        player: PlayerState row to modify in-place if needed.
        upgrade_def: The upgrade definition describing the effect.
    """
    effect = upgrade_def.effect_type
    value = upgrade_def.effect_value

    if effect == "prod_mult" and upgrade_def.target_unit_id is not None:
        unit_row = await PlayerUnitRepository.get_by_player_and_unit(
            session, player.id, upgrade_def.target_unit_id
        )
        if unit_row is None:
            unit_row = await PlayerUnitRepository.upsert(
                session, player.id, upgrade_def.target_unit_id, amount_owned=0
            )
        unit_row.effective_multiplier = unit_row.effective_multiplier * value

    elif effect == "offline_eff_up":
        player.offline_efficiency = float(Decimal(str(player.offline_efficiency)) + value)

    elif effect == "offline_cap_up":
        player.offline_cap_seconds = int(player.offline_cap_seconds + int(value))
