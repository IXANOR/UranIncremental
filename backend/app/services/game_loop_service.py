"""Core idle game loop.

Implements the full tick sequence:
    load → verify snapshot → compute delta → production pass
    → automation upkeep → apply gains → update state → sign → return

The caller is responsible for wrapping the call in a database transaction.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import compute_delta, ensure_utc
from app.db.models.player_state import PlayerState
from app.db.models.unit import PlayerUnit
from app.db.models.upgrade import PlayerUpgrade
from app.db.models.wallet import Wallet
from app.db.repositories.event_log import EventLogRepository
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.wallet import WalletRepository
from app.services import snapshot_sign_service

# A player is considered online if the last API call was within this threshold.
# Ticks within the threshold receive 100 % efficiency; larger gaps apply
# offline_efficiency.
_ONLINE_THRESHOLD_SECONDS = 300.0  # 5 minutes

_WALLET_CURRENCIES = ("energy_drink", "u238", "u235", "u233", "meta_isotopes")


class SnapshotSignatureError(Exception):
    """Raised when the stored snapshot signature does not match the game state."""


@dataclass
class TickResult:
    """Full result of a game loop tick, ready to be serialised as an API response.

    Attributes:
        player: Updated PlayerState row.
        wallet: Updated Wallet row.
        units: All PlayerUnit rows for the player after the tick.
        upgrades: All PlayerUpgrade rows for the player.
        server_time: UTC timestamp at which the tick was processed.
        effective_delta_seconds: Actual seconds of production simulated (after
            efficiency and cap are applied).
        cap_applied: Whether the offline cap was hit during this tick.
        gains: Currency amounts added to the wallet this tick.
    """

    player: PlayerState
    wallet: Wallet
    units: list[PlayerUnit]
    upgrades: list[PlayerUpgrade]
    server_time: datetime
    effective_delta_seconds: float
    cap_applied: bool
    gains: dict[str, Decimal] = field(default_factory=dict)


async def tick(
    session: AsyncSession,
    player: PlayerState,
    *,
    force_offline: bool = False,
) -> TickResult:
    """Run one game loop tick for the given player.

    Loads wallet, units, and upgrades; verifies the snapshot signature;
    computes the production delta; applies production gains; deducts automation
    upkeep; updates ``last_tick_at``, ``last_online_at``, and ``version``;
    writes a fresh snapshot signature.

    The caller must wrap this in ``async with session.begin():``.

    Args:
        session: Active async database session inside an open transaction.
        player: The player whose state is being ticked.
        force_offline: When True, always apply offline efficiency and cap
            regardless of when the player last called the API.  Used by the
            ``claim-offline`` endpoint.

    Returns:
        TickResult containing the updated state.

    Raises:
        SnapshotSignatureError: If the stored signature does not match the
            current state (possible tampering).
    """
    now = datetime.now(UTC)

    wallet = await WalletRepository.get_by_player(session, player.id)
    units = await PlayerUnitRepository.get_by_player(session, player.id)
    upgrades = await PlayerUpgradeRepository.get_by_player(session, player.id)

    assert wallet is not None, "Wallet missing for player — database integrity error"

    # --- Snapshot verification -------------------------------------------
    if player.snapshot_signature:
        if not snapshot_sign_service.verify(player, wallet, units):
            await EventLogRepository.create(
                session,
                player.id,
                "snapshot_invalid",
                {"version": player.version, "player_id": str(player.id)},
            )
            raise SnapshotSignatureError(f"Snapshot signature mismatch for player {player.id}")

    # --- Delta anomaly detection --------------------------------------------
    raw_delta_seconds = (ensure_utc(now) - ensure_utc(player.last_tick_at)).total_seconds()

    if raw_delta_seconds < 0:
        await EventLogRepository.create(
            session,
            player.id,
            "delta_anomaly",
            {
                "type": "negative",
                "raw_delta": raw_delta_seconds,
                "version": player.version,
            },
        )
    elif raw_delta_seconds > player.offline_cap_seconds * 2:
        await EventLogRepository.create(
            session,
            player.id,
            "delta_anomaly",
            {
                "type": "excessive",
                "raw_delta": raw_delta_seconds,
                "cap_seconds": player.offline_cap_seconds,
                "version": player.version,
            },
        )

    # --- Delta time ---------------------------------------------------------
    is_offline = force_offline or (
        (
            now - player.last_online_at.replace(tzinfo=UTC)
            if player.last_online_at.tzinfo is None
            else now - player.last_online_at
        ).total_seconds()
        > _ONLINE_THRESHOLD_SECONDS
    )
    effective_delta, cap_applied = compute_delta(
        player.last_tick_at,
        now,
        player.offline_cap_seconds,
        player.offline_efficiency,
        is_offline=is_offline,
    )

    # --- Production pass ----------------------------------------------------
    gains: dict[str, Decimal] = defaultdict(Decimal)

    if effective_delta > 0 and units:
        prestige_mult = Decimal("1.20") ** player.prestige_count
        delta_dec = Decimal(str(effective_delta))

        unit_defs = {ud.id: ud for ud in await UnitDefinitionRepository.get_all(session)}

        for unit in units:
            if unit.amount_owned <= 0:
                continue
            unit_def = unit_defs.get(unit.unit_id)
            if unit_def is None:
                continue
            production = (
                Decimal(str(unit.amount_owned))
                * unit_def.production_rate_per_sec
                * delta_dec
                * unit.effective_multiplier
                * prestige_mult
            )
            gains[unit_def.production_resource] += production

        for currency, amount in gains.items():
            if currency in _WALLET_CURRENCIES:
                setattr(wallet, currency, getattr(wallet, currency) + amount)

    # --- Automation upkeep --------------------------------------------------
    if effective_delta > 0:
        delta_dec = Decimal(str(effective_delta))
        auto_units = [u for u in units if u.automation_enabled]

        if auto_units:
            total_upkeep = sum(u.upkeep_energy_per_sec for u in auto_units) * delta_dec

            if wallet.energy_drink >= total_upkeep:
                wallet.energy_drink -= total_upkeep
            else:
                # Insufficient energy_drink: disable automation deterministically
                # (reverse alphabetical order — worst-named units first).
                for unit in sorted(auto_units, key=lambda u: u.unit_id, reverse=True):
                    unit_cost = unit.upkeep_energy_per_sec * delta_dec
                    remaining = (
                        sum(u.upkeep_energy_per_sec for u in units if u.automation_enabled)
                        * delta_dec
                    )
                    if wallet.energy_drink >= remaining - unit_cost:
                        break
                    unit.automation_enabled = False

                affordable = (
                    sum(u.upkeep_energy_per_sec for u in units if u.automation_enabled) * delta_dec
                )
                wallet.energy_drink = max(Decimal("0"), wallet.energy_drink - affordable)

    # --- Persist changes ----------------------------------------------------
    await session.flush()

    # Reload wallet so sign() uses the DB-rounded Numeric(28,10) values, not the
    # full-precision in-memory Decimals.  Without this, str(wallet.energy_drink)
    # in _canonical_payload would differ between the signing tick and the next
    # tick's verify, causing a permanent signature mismatch.
    await session.refresh(wallet)

    await PlayerStateRepository.update(
        session,
        player,
        last_tick_at=now,
        last_online_at=now,
        version=player.version + 1,
    )

    new_sig = snapshot_sign_service.sign(player, wallet, units)
    await PlayerStateRepository.update(session, player, snapshot_signature=new_sig)

    return TickResult(
        player=player,
        wallet=wallet,
        units=units,
        upgrades=upgrades,
        server_time=now,
        effective_delta_seconds=effective_delta,
        cap_applied=cap_applied,
        gains=dict(gains),
    )
