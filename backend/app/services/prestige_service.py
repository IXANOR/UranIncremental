"""Prestige (soft reset) service.

A prestige resets the player's wallet and unit inventory while preserving
metaprogression (prestige_count, tech_magic_level, upgrades marked
survives_prestige=True).  Each prestige permanently increases the production
multiplier by ×1.20 (applied in game_loop_service via 1.20^prestige_count).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.player_state import PlayerState
from app.db.models.upgrade import PlayerUpgrade
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository
from app.db.repositories.wallet import WalletRepository

# Base u238 required for the very first prestige (prestige_count == 0).
# Each subsequent prestige doubles the requirement: base * 2^prestige_count.
PRESTIGE_U238_REQUIREMENT = Decimal("1")  # kept for backwards-compat imports

# Valid (count, currency) combinations for multi-prestige.
_VALID_PRESTIGE_OPTIONS: dict[int, tuple[str, int]] = {
    1: ("u238", 0),  # cost = 2^p
    5: ("u235", 1),  # cost = max(1, 2^(p-1))
    10: ("u233", 2),  # cost = max(1, 2^(p-2))
    25: ("meta_isotopes", 3),  # cost = max(1, 2^(p-3))
}


def multi_prestige_requirement(
    prestige_count: int,
    count: int,
    currency: str,
) -> tuple[Decimal, str]:
    """Return the (cost, currency) required to perform a multi-prestige.

    Args:
        prestige_count: Player's current prestige count (before the reset).
        count: Number of prestiges to purchase at once. Must be one of: 1, 5, 10, 25.
        currency: Currency to spend. Must match the expected currency for the given
            count (u238 for 1×, u235 for 5×, u233 for 10×, meta_isotopes for 25×).

    Returns:
        Tuple of (Decimal cost, currency name).

    Raises:
        ValueError: If count is not one of 1/5/10/25, or currency doesn't match count.
    """
    if count not in _VALID_PRESTIGE_OPTIONS:
        raise ValueError(f"count must be one of {sorted(_VALID_PRESTIGE_OPTIONS)}, got {count}")
    expected_currency, exponent_offset = _VALID_PRESTIGE_OPTIONS[count]
    if currency != expected_currency:
        raise ValueError(
            f"currency for {count}× prestige must be '{expected_currency}', got '{currency}'"
        )
    exponent = prestige_count - exponent_offset
    cost = max(Decimal("1"), Decimal(2) ** exponent)
    return cost, currency


def prestige_requirement(prestige_count: int) -> Decimal:
    """Return the u238 required for the next prestige.

    The requirement doubles with each completed prestige so the player must
    accumulate progressively more u238 to keep resetting.

    Args:
        prestige_count: The player's *current* prestige count (before the reset).

    Returns:
        Decimal u238 threshold: ``1 * 2^prestige_count``.
    """
    return PRESTIGE_U238_REQUIREMENT * Decimal(2) ** prestige_count


_DEFAULT_STARTING_ENERGY = Decimal("50")
_DEFAULT_OFFLINE_EFFICIENCY = 0.20
_DEFAULT_OFFLINE_CAP_SECONDS = 14400


class PrestigeNotAvailableError(Exception):
    """Raised when the player has not met the prestige requirement."""


@dataclass
class PrestigeResult:
    """Outcome of a successful prestige reset.

    Attributes:
        new_prestige_count: ``prestige_count`` value after the reset.
        surviving_upgrade_ids: IDs of upgrades that were preserved across the reset.
    """

    new_prestige_count: int
    surviving_upgrade_ids: list[str] = field(default_factory=list)


async def _execute_reset(
    session: AsyncSession,
    player: PlayerState,
    count: int,
) -> PrestigeResult:
    """Execute the common soft-reset logic and increment prestige_count by count.

    Does NOT validate requirements — callers must check cost/currency first.

    Args:
        session: Active async database session (within a transaction).
        player: The player to reset.
        count: Number to add to prestige_count.

    Returns:
        PrestigeResult with the new prestige_count and surviving upgrade IDs.
    """
    wallet = await WalletRepository.get_by_player(session, player.id)
    assert wallet is not None, "Wallet missing — database integrity error"

    # --- Collect surviving upgrades before deletion -------------------------
    all_player_upgrades = await PlayerUpgradeRepository.get_by_player(session, player.id)
    all_defs = {d.id: d for d in await UpgradeDefinitionRepository.get_all(session)}

    surviving_pairs = [
        (pu, all_defs[pu.upgrade_id])
        for pu in all_player_upgrades
        if pu.upgrade_id in all_defs and all_defs[pu.upgrade_id].survives_prestige
    ]

    # --- Delete all upgrade rows (flush so PKs are free to re-insert) -------
    for pu in all_player_upgrades:
        await session.delete(pu)
    await session.flush()

    # --- Reset units --------------------------------------------------------
    units = await PlayerUnitRepository.get_by_player(session, player.id)
    for unit in units:
        unit.amount_owned = 0
        unit.effective_multiplier = Decimal("1.0")

    # --- Reset wallet -------------------------------------------------------
    wallet.energy_drink = _DEFAULT_STARTING_ENERGY
    wallet.u238 = Decimal("0")
    wallet.u235 = Decimal("0")
    wallet.u233 = Decimal("0")
    wallet.meta_isotopes = Decimal("0")

    # --- Reset player state -------------------------------------------------
    player.offline_efficiency = _DEFAULT_OFFLINE_EFFICIENCY
    player.offline_cap_seconds = _DEFAULT_OFFLINE_CAP_SECONDS
    player.prestige_count += count
    player.snapshot_signature = ""
    now = datetime.now(UTC)
    player.last_tick_at = now
    player.last_online_at = now

    # --- Re-create surviving upgrades and re-apply their effects ------------
    surviving_ids: list[str] = []
    for pu, udef in surviving_pairs:
        new_pu = PlayerUpgrade(player_id=player.id, upgrade_id=pu.upgrade_id)
        new_pu.level = pu.level
        session.add(new_pu)

        for _ in range(pu.level):
            if udef.effect_type == "prod_mult" and udef.target_unit_id:
                unit_row = await PlayerUnitRepository.get_by_player_and_unit(
                    session, player.id, udef.target_unit_id
                )
                if unit_row is None:
                    unit_row = await PlayerUnitRepository.upsert(
                        session, player.id, udef.target_unit_id, amount_owned=0
                    )
                unit_row.effective_multiplier *= udef.effect_value

            elif udef.effect_type == "offline_eff_up":
                player.offline_efficiency = float(
                    Decimal(str(player.offline_efficiency)) + udef.effect_value
                )

            elif udef.effect_type == "offline_cap_up":
                player.offline_cap_seconds += int(udef.effect_value)

        surviving_ids.append(pu.upgrade_id)

    await session.flush()

    return PrestigeResult(
        new_prestige_count=player.prestige_count,
        surviving_upgrade_ids=surviving_ids,
    )


async def prestige(session: AsyncSession, player: PlayerState) -> PrestigeResult:
    """Perform a 1× soft reset spending U-238.

    Delegates to ``prestige_bulk`` with count=1, currency="u238".

    Args:
        session: Active async database session (within a transaction).
        player: The player to reset.

    Returns:
        PrestigeResult with the new prestige_count and surviving upgrade IDs.

    Raises:
        PrestigeNotAvailableError: If wallet.u238 < required threshold.
    """
    return await prestige_bulk(session, player, 1, "u238")


async def prestige_bulk(
    session: AsyncSession,
    player: PlayerState,
    count: int,
    currency: str,
) -> PrestigeResult:
    """Perform a multi-prestige soft reset.

    Validates that the player holds the required amount of the appropriate
    higher-tier currency, then executes a full soft reset and increments
    prestige_count by ``count``.

    Cost formulas (``p`` = current prestige_count):
        1× U-238:      ``2^p``
        5× U-235:      ``max(1, 2^(p-1))``
        10× U-233:     ``max(1, 2^(p-2))``
        25× META:      ``max(1, 2^(p-3))``

    Args:
        session: Active async database session (within a transaction).
        player: The player to reset.
        count: Number of prestiges to purchase. Must be 1, 5, 10, or 25.
        currency: Currency to spend. Must match the expected currency for count.

    Returns:
        PrestigeResult with the new prestige_count and surviving upgrade IDs.

    Raises:
        PrestigeNotAvailableError: If the player cannot afford the prestige.
        ValueError: If count/currency combination is invalid.
    """
    required, _ = multi_prestige_requirement(player.prestige_count, count, currency)

    wallet = await WalletRepository.get_by_player(session, player.id)
    assert wallet is not None, "Wallet missing — database integrity error"

    wallet_amount = getattr(wallet, currency)
    if wallet_amount < required:
        raise PrestigeNotAvailableError(
            f"Need {required} {currency} to prestige {count}× "
            f"(prestige #{player.prestige_count + 1}–{player.prestige_count + count}), "
            f"have {wallet_amount}"
        )

    return await _execute_reset(session, player, count)
