"""Game management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.db.models.player_state import PlayerState
from app.db.repositories.player_state import PlayerStateRepository
from app.db.session import get_db
from app.schemas.game import (
    GameStateResponse,
    PlayerStateSchema,
    StartGameResponse,
    WalletSchema,
)
from app.services.game_loop_service import SnapshotSignatureError, tick

router = APIRouter(prefix="/api/v1/game", tags=["game"])


@router.post("/start", response_model=StartGameResponse)
async def start_game(session: AsyncSession = Depends(get_db)) -> StartGameResponse:
    """Create a new player or return the existing one.

    In single-player mode there is at most one PlayerState row.  Calling this
    endpoint a second time is idempotent — it returns the existing player.

    Args:
        session: Async database session injected by ``get_db``.

    Returns:
        StartGameResponse with ``player_id``, ``state_version``, and ``started_at``.
    """
    player = await PlayerStateRepository.get_single_player(session)
    if player is None:
        player = await PlayerStateRepository.create(session)
    await session.commit()
    return StartGameResponse(
        player_id=player.id,
        state_version=player.version,
        started_at=player.created_at,
    )


@router.get("/state", response_model=GameStateResponse)
async def get_state(
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> GameStateResponse:
    """Run one game-loop tick and return the full player state.

    Computes production since the last tick, applies automation upkeep,
    updates the snapshot signature, and persists the result.

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        GameStateResponse with the updated player, wallet, and server timestamp.

    Raises:
        HTTPException(409): If the stored snapshot signature does not match the
            current state, indicating possible tampering.
    """
    try:
        result = await tick(session, player)
        await session.commit()
    except SnapshotSignatureError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return GameStateResponse(
        player=PlayerStateSchema.model_validate(result.player),
        wallet=WalletSchema.model_validate(result.wallet),
        server_time=result.server_time,
    )
