"""FastAPI shared dependencies."""

import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.player_state import PlayerState
from app.db.repositories.player_state import PlayerStateRepository
from app.db.session import get_db


async def get_current_player(
    x_player_id: str | None = Header(None),
    session: AsyncSession = Depends(get_db),
) -> PlayerState:
    """Resolve the X-Player-ID header into a PlayerState row.

    Args:
        x_player_id: Value of the ``X-Player-ID`` HTTP header.
        session: Async database session injected by ``get_db``.

    Returns:
        PlayerState for the authenticated player.

    Raises:
        HTTPException(400): If the header is missing or not a valid UUID.
        HTTPException(404): If no player with that UUID exists in the database.
    """
    if x_player_id is None:
        raise HTTPException(status_code=400, detail="X-Player-ID header is required")
    try:
        player_id = uuid.UUID(x_player_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="X-Player-ID must be a valid UUID"
        )
    player = await PlayerStateRepository.get_by_id(session, player_id)
    if player is None:
        raise HTTPException(
            status_code=404, detail=f"Player '{x_player_id}' not found"
        )
    return player


def require_test_mode() -> None:
    """Block access when TEST_MODE is disabled.

    Returns:
        None if TEST_MODE is enabled.

    Raises:
        HTTPException(404): When ``settings.test_mode`` is False, mimicking a
            non-existent route so the endpoint is invisible to non-admin callers.
    """
    if not settings.test_mode:
        raise HTTPException(status_code=404, detail="Not found")
