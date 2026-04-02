"""Unit tests for click_service: reward calculation and rate limiting."""

import time
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.click_service import (
    BASE_CLICK_REWARD,
    ClickRateLimitError,
    _click_timestamps,
    process_click,
)


@pytest.fixture(autouse=True)
def clear_rate_limiter() -> None:
    """Reset in-memory rate limiter state between tests.

    Yields:
        None
    """
    _click_timestamps.clear()
    yield
    _click_timestamps.clear()


@pytest.mark.asyncio
async def test_click_reward_no_prestige(db_session: AsyncSession) -> None:
    """Click reward with prestige_count=0 equals BASE_CLICK_REWARD."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        gained = await process_click(db_session, p)

    assert gained == BASE_CLICK_REWARD


@pytest.mark.asyncio
async def test_click_reward_scales_with_prestige(db_session: AsyncSession) -> None:
    """Click reward equals BASE_CLICK_REWARD * 1.20 ** prestige_count."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.prestige_count = 3

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        gained = await process_click(db_session, p)

    expected = BASE_CLICK_REWARD * Decimal("1.20") ** 3
    assert gained == expected


@pytest.mark.asyncio
async def test_click_adds_ed_to_wallet(db_session: AsyncSession) -> None:
    """Click reward is credited to the player's energy_drink balance."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        starting_ed = w.energy_drink

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        gained = await process_click(db_session, p)
        w = await WalletRepository.get_by_player(db_session, p.id)
        assert w is not None
        assert w.energy_drink == starting_ed + gained


@pytest.mark.asyncio
async def test_click_increments_click_count(db_session: AsyncSession) -> None:
    """Each successful click increments player.click_count by 1."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await process_click(db_session, p)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        assert p.click_count == 1


@pytest.mark.asyncio
async def test_click_accumulates_total_click_gains(db_session: AsyncSession) -> None:
    """total_click_gains accumulates the sum of all click rewards."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    total = Decimal("0")
    for _ in range(3):
        _click_timestamps.clear()  # bypass rate limit between calls
        async with db_session.begin():
            p = await PlayerStateRepository.get_by_id(db_session, player.id)
            assert p is not None
            gained = await process_click(db_session, p)
            total += gained

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        assert p.total_click_gains == total


@pytest.mark.asyncio
async def test_click_rate_limit_exceeded(db_session: AsyncSession) -> None:
    """ClickRateLimitError is raised on the 11th click within 1 second."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    # Pre-fill rate limiter with 10 timestamps within the current second
    now = time.time()
    _click_timestamps[player.id] = [now] * 10

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(ClickRateLimitError):
            await process_click(db_session, p)


@pytest.mark.asyncio
async def test_click_rate_limit_resets_after_window(db_session: AsyncSession) -> None:
    """Clicks older than 1 second do not count toward the rate limit."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    # Pre-fill with 10 timestamps from 2 seconds ago (outside the window)
    old = time.time() - 2.0
    _click_timestamps[player.id] = [old] * 10

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        # Should NOT raise — old timestamps are pruned
        gained = await process_click(db_session, p)

    assert gained == BASE_CLICK_REWARD
