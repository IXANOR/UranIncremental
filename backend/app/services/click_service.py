"""Click minigame service: reward calculation and in-process rate limiting."""

from collections import defaultdict
from decimal import Decimal
from time import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.player_state import PlayerState
from app.db.repositories.wallet import WalletRepository

BASE_CLICK_REWARD = Decimal("1.0")
_PRESTIGE_BASE = Decimal("1.20")
MAX_CLICKS_PER_SECOND = 10
_RATE_WINDOW = 1.0  # seconds

# In-process store: player_id -> list of recent click timestamps.
# Intentionally not persisted; resets on process restart (Redis in Phase 3).
_click_timestamps: dict[UUID, list[float]] = defaultdict(list)


class ClickRateLimitError(Exception):
    """Raised when a player exceeds the server-side click rate limit."""


def _check_rate_limit(player_id: UUID) -> None:
    """Enforce max-clicks-per-second for a player.

    Args:
        player_id: UUID of the player making the click.

    Raises:
        ClickRateLimitError: If the player has already reached
            ``MAX_CLICKS_PER_SECOND`` clicks within the last second.
    """
    now = time()
    cutoff = now - _RATE_WINDOW
    recent = [t for t in _click_timestamps[player_id] if t > cutoff]
    if len(recent) >= MAX_CLICKS_PER_SECOND:
        _click_timestamps[player_id] = recent
        raise ClickRateLimitError(
            f"Rate limit exceeded: max {MAX_CLICKS_PER_SECOND} clicks per second"
        )
    recent.append(now)
    _click_timestamps[player_id] = recent


async def process_click(session: AsyncSession, player: PlayerState) -> Decimal:
    """Process a single reactor click, apply ED reward, and update stats.

    The reward is ``BASE_CLICK_REWARD * 1.20 ** prestige_count``.  Rate limiting
    is enforced in-process (max 10 clicks/s per player).

    Args:
        session: Async database session.
        player: Authenticated player whose state will be updated.

    Returns:
        Amount of ``energy_drink`` gained by this click.

    Raises:
        ClickRateLimitError: If the player has exceeded the click rate limit.
    """
    _check_rate_limit(player.id)
    prestige_mult = _PRESTIGE_BASE**player.prestige_count
    gained = BASE_CLICK_REWARD * prestige_mult
    wallet = await WalletRepository.get_by_player(session, player.id)
    if wallet is not None:
        wallet.energy_drink += gained
    player.click_count += 1
    player.total_click_gains += gained
    player.snapshot_signature = ""
    return gained
