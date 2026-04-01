"""Prestige (soft reset) service.

A prestige resets the player's wallet and unit inventory while preserving
metaprogression (prestige_count, tech_magic_level, upgrades marked
survives_prestige=True).  Each prestige permanently increases the production
multiplier by ×1.15 (applied in game_loop_service via 1.15^prestige_count).
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

# Minimum u238 balance required to trigger prestige.
PRESTIGE_U238_REQUIREMENT = Decimal("1")

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


async def prestige(session: AsyncSession, player: PlayerState) -> PrestigeResult:
    """Perform a soft reset for the given player.

    Flow:
    1. Validate prestige requirement (u238 threshold).
    2. Identify upgrades that survive the reset.
    3. Delete all PlayerUpgrade rows, flush.
    4. Zero unit amounts and multipliers.
    5. Reset wallet to starting values.
    6. Reset offline parameters to defaults.
    7. Increment prestige_count; clear snapshot signature.
    8. Re-create surviving upgrades and re-apply their effects.

    The caller must commit the session after this call.

    Args:
        session: Active async database session (within a transaction).
        player: The player to reset.

    Returns:
        PrestigeResult with the new prestige_count and surviving upgrade IDs.

    Raises:
        PrestigeNotAvailableError: If wallet.u238 < PRESTIGE_U238_REQUIREMENT.
    """
    wallet = await WalletRepository.get_by_player(session, player.id)
    assert wallet is not None, "Wallet missing — database integrity error"

    if wallet.u238 < PRESTIGE_U238_REQUIREMENT:
        raise PrestigeNotAvailableError(
            f"Need {PRESTIGE_U238_REQUIREMENT} u238 to prestige, have {wallet.u238}"
        )

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
    player.prestige_count += 1
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
