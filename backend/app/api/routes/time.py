"""Offline time-simulation endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.db.models.player_state import PlayerState
from app.db.session import get_db
from app.schemas.economy import ClaimOfflineResponse
from app.services.game_loop_service import SnapshotSignatureError, tick

router = APIRouter(prefix="/api/v1/time", tags=["time"])


@router.post("/claim-offline", response_model=ClaimOfflineResponse)
async def claim_offline(
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> ClaimOfflineResponse:
    """Simulate offline production gains and claim them.

    Always applies offline efficiency and the offline cap regardless of when
    the player last called the API.  Useful for claiming rewards after a long
    absence without waiting for the next regular ``GET /state`` tick.

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        ClaimOfflineResponse with ``simulated_seconds``, ``efficiency_used``,
        ``gains``, and ``cap_applied``.

    Raises:
        HTTPException(409): If the snapshot signature does not match the
            stored state (possible tampering detected).
    """
    try:
        result = await tick(session, player, force_offline=True)
        await session.commit()
    except SnapshotSignatureError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return ClaimOfflineResponse(
        simulated_seconds=int(result.effective_delta_seconds),
        efficiency_used=result.player.offline_efficiency,
        gains={k: v for k, v in result.gains.items()},
        cap_applied=result.cap_applied,
    )
