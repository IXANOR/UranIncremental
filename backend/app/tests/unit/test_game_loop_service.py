"""Unit tests for game_loop_service and time_utils."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time_utils import compute_delta
from app.db.models.events import EventLog
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services import snapshot_sign_service
from app.services.game_loop_service import SnapshotSignatureError, tick

# ---------------------------------------------------------------------------
# time_utils.compute_delta
# ---------------------------------------------------------------------------


def test_online_delta_full_efficiency() -> None:
    """Online delta should return raw seconds with no efficiency scaling."""
    last_tick = datetime.now(UTC) - timedelta(seconds=10)
    now = datetime.now(UTC)
    delta, cap = compute_delta(last_tick, now, 14400, 0.2, is_offline=False)
    assert 9 < delta < 11
    assert not cap


def test_offline_delta_within_cap() -> None:
    """Offline delta within cap should apply efficiency only."""
    last_tick = datetime.now(UTC) - timedelta(hours=1)
    now = datetime.now(UTC)
    delta, cap = compute_delta(last_tick, now, 14400, 0.5, is_offline=True)
    assert pytest.approx(delta, rel=0.01) == 3600 * 0.5
    assert not cap


def test_offline_delta_exceeds_cap() -> None:
    """Offline delta beyond cap should be truncated and scaled."""
    last_tick = datetime.now(UTC) - timedelta(hours=8)
    now = datetime.now(UTC)
    # cap = 4h = 14400s, efficiency = 0.2
    delta, cap = compute_delta(last_tick, now, 14400, 0.2, is_offline=True)
    assert pytest.approx(delta, rel=0.01) == 14400 * 0.2
    assert cap


def test_zero_or_negative_delta_returns_zero() -> None:
    """Delta should never be negative."""
    now = datetime.now(UTC)
    delta, cap = compute_delta(now, now - timedelta(seconds=5), 14400, 0.2, is_offline=False)
    assert delta == 0.0
    assert not cap


# ---------------------------------------------------------------------------
# snapshot_sign_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_sign_and_verify(db_session: AsyncSession) -> None:
    """Signing then verifying unchanged state should return True."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)
        wallet = await WalletRepository.get_by_player(db_session, player.id)
        assert wallet is not None
        sig = snapshot_sign_service.sign(player, wallet, [])
        player.snapshot_signature = sig

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert p is not None and w is not None
        assert snapshot_sign_service.verify(p, w, [])


@pytest.mark.asyncio
async def test_snapshot_verify_fails_after_wallet_tamper(db_session: AsyncSession) -> None:
    """Modifying the wallet after signing should invalidate the signature."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)
        wallet = await WalletRepository.get_by_player(db_session, player.id)
        assert wallet is not None
        sig = snapshot_sign_service.sign(player, wallet, [])
        player.snapshot_signature = sig

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert p is not None and w is not None
        w.energy_drink = Decimal("999999")  # tamper
        assert not snapshot_sign_service.verify(p, w, [])


# ---------------------------------------------------------------------------
# game_loop_service.tick — production
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tick_production_adds_currency(db_session: AsyncSession) -> None:
    """A tick with a barrel unit should increase energy_drink."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        # Backdate last_tick_at by 100 seconds
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=100)
        player.last_online_at = datetime.now(UTC)  # online → no efficiency penalty
        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=10)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    # barrel: 10 units × 0.1 ED/s × ~100s × 1.0 multiplier × 1.0 prestige = ~100 ED gained
    # starting balance: 50 ED
    assert result.wallet.energy_drink > Decimal("100")
    assert result.effective_delta_seconds > 0


@pytest.mark.asyncio
async def test_tick_production_with_prestige_multiplier(db_session: AsyncSession) -> None:
    """Production should scale by 1.20^prestige_count."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=100)
        player.last_online_at = datetime.now(UTC)
        player.prestige_count = 2  # multiplier = 1.20^2 = 1.44
        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=1)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    # 1 barrel × 0.3 ED/s × 100s × 1.20^2 = 43.2 ED gained
    gains = result.gains.get("energy_drink", Decimal("0"))
    assert gains > Decimal("42") and gains < Decimal("45")


@pytest.mark.asyncio
async def test_tick_version_increments(db_session: AsyncSession) -> None:
    """Each tick should increment player.version by 1."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_online_at = datetime.now(UTC)
        initial_version = player.version

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    assert result.player.version == initial_version + 1


# ---------------------------------------------------------------------------
# game_loop_service.tick — upkeep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tick_upkeep_deducted_when_sufficient(db_session: AsyncSession) -> None:
    """Upkeep should be deducted from energy_drink when balance is sufficient."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=100)
        player.last_online_at = datetime.now(UTC)
        # Give player lots of energy_drink
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("10000")
        # Unit with automation enabled: 1 ED/s upkeep
        unit = await PlayerUnitRepository.upsert(
            db_session,
            player.id,
            "barrel",
            amount_owned=1,
            automation_enabled=True,
            upkeep_energy_per_sec=Decimal("1"),
        )
        assert unit is not None

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    # 100s × 1 ED/s upkeep deducted, plus production added
    # energy_drink should be < 10000 + production - 100 (upkeep)
    assert result.wallet.energy_drink < Decimal("10000")


@pytest.mark.asyncio
async def test_tick_upkeep_disables_automation_when_broke(db_session: AsyncSession) -> None:
    """When energy_drink cannot cover upkeep, automation is disabled deterministically."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=100)
        player.last_online_at = datetime.now(UTC)
        # Zero out energy_drink
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("0")
        # Two units with automation: heavy upkeep each
        await PlayerUnitRepository.upsert(
            db_session,
            player.id,
            "barrel",
            amount_owned=1,
            automation_enabled=True,
            upkeep_energy_per_sec=Decimal("10"),
        )
        await PlayerUnitRepository.upsert(
            db_session,
            player.id,
            "mini_reactor",
            amount_owned=1,
            automation_enabled=True,
            upkeep_energy_per_sec=Decimal("10"),
        )

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    auto_still_on = [u for u in result.units if u.automation_enabled]
    all_units = result.units
    # At least some automation should have been disabled
    assert len(auto_still_on) < len(all_units)
    assert result.wallet.energy_drink >= Decimal("0")


# ---------------------------------------------------------------------------
# game_loop_service.tick — snapshot verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tick_rejects_tampered_snapshot(db_session: AsyncSession) -> None:
    """tick() should raise SnapshotSignatureError when signature is invalid."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_online_at = datetime.now(UTC)
        player.snapshot_signature = "invalid-signature"

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(SnapshotSignatureError):
            await tick(db_session, p)


@pytest.mark.asyncio
async def test_tick_skips_verify_on_empty_signature(db_session: AsyncSession) -> None:
    """First tick (empty signature) should pass without raising."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_online_at = datetime.now(UTC)
        # snapshot_signature defaults to ""

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    assert result.player.snapshot_signature != ""


# ---------------------------------------------------------------------------
# game_loop_service.tick — delta anomaly detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tick_negative_delta_logs_anomaly(db_session: AsyncSession) -> None:
    """A negative raw delta (last_tick_at in the future) is logged as delta_anomaly."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        # Push last_tick_at 60 s into the future → raw delta will be negative
        player.last_tick_at = datetime.now(UTC) + timedelta(seconds=60)
        player.last_online_at = datetime.now(UTC)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    # Production should be zero (negative delta clamped to 0)
    assert result.effective_delta_seconds == 0.0

    # event_log must contain a delta_anomaly entry
    rows = (
        (
            await db_session.execute(
                select(EventLog)
                .where(EventLog.player_id == player.id)
                .where(EventLog.event_type == "delta_anomaly")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].payload["type"] == "negative"


@pytest.mark.asyncio
async def test_tick_excessive_delta_logs_anomaly(db_session: AsyncSession) -> None:
    """A raw delta exceeding offline_cap * 2 is logged as delta_anomaly."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        # default cap = 14400 s (4h); set last_tick_at > cap * 2 = 8h ago
        player.last_tick_at = datetime.now(UTC) - timedelta(hours=9)
        player.last_online_at = datetime.now(UTC)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await tick(db_session, p)

    rows = (
        (
            await db_session.execute(
                select(EventLog)
                .where(EventLog.player_id == player.id)
                .where(EventLog.event_type == "delta_anomaly")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].payload["type"] == "excessive"
    assert rows[0].payload["cap_seconds"] == 14400


@pytest.mark.asyncio
async def test_tick_normal_delta_does_not_log_anomaly(db_session: AsyncSession) -> None:
    """A normal delta (within cap) produces no delta_anomaly event."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=30)
        player.last_online_at = datetime.now(UTC)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await tick(db_session, p)

    rows = (
        (
            await db_session.execute(
                select(EventLog)
                .where(EventLog.player_id == player.id)
                .where(EventLog.event_type == "delta_anomaly")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# snapshot_sign_service — key rotation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_key_rotation_invalidates_signature(
    db_session: AsyncSession, monkeypatch
) -> None:
    """Changing SNAPSHOT_SECRET makes existing signatures fail verification."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)
        wallet = await WalletRepository.get_by_player(db_session, player.id)
        assert wallet is not None
        # Sign with current key
        sig = snapshot_sign_service.sign(player, wallet, [])
        player.snapshot_signature = sig

    # Rotate the secret
    monkeypatch.setattr(settings, "snapshot_secret", "rotated-secret-different-key")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert p is not None and w is not None
        # Verification must fail with the new key
        assert not snapshot_sign_service.verify(p, w, [])
