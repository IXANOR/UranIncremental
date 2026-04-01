"""Test/admin endpoints — only active when TEST_MODE=true."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player, require_test_mode
from app.db.models.player_state import PlayerState
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.wallet import WalletRepository
from app.db.session import get_db
from app.schemas.test_admin import (
    CorrectStateRequest,
    CorrectStateResponse,
    SimulateTimeRequest,
    SimulateTimeResponse,
)
from app.services.game_loop_service import SnapshotSignatureError, tick

router = APIRouter(
    prefix="/api/v1/test",
    tags=["test"],
    dependencies=[Depends(require_test_mode)],
)


@router.post("/simulate-time", response_model=SimulateTimeResponse)
async def simulate_time(
    body: SimulateTimeRequest,
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> SimulateTimeResponse:
    """Simulate the passage of ``body.seconds`` seconds for the player.

    Sets ``last_tick_at`` to ``now - seconds`` and ``last_online_at`` to ``now``
    (full production efficiency), clears the snapshot signature so verification
    is skipped, then runs a regular tick to apply the simulated production.

    Args:
        body: Request containing the number of seconds to simulate.
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        SimulateTimeResponse with ``simulated_seconds`` and ``new_state_version``.

    Raises:
        HTTPException(409): If the tick raises an unexpected snapshot error.
    """
    now = datetime.now(UTC)
    player.last_tick_at = now - timedelta(seconds=body.seconds)
    player.last_online_at = now  # full efficiency, no offline penalty
    player.snapshot_signature = ""  # skip verification for the forced tick

    try:
        result = await tick(session, player)
        await session.commit()
    except SnapshotSignatureError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return SimulateTimeResponse(
        ok=True,
        simulated_seconds=int(result.effective_delta_seconds),
        new_state_version=result.player.version,
    )


@router.post("/correct-state", response_model=CorrectStateResponse)
async def correct_state(
    body: CorrectStateRequest,
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> CorrectStateResponse:
    """Directly patch the player's wallet and/or unit amounts.

    Only the fields explicitly provided in the request body are modified.
    After patching, the snapshot signature is cleared so the next regular
    tick re-signs from the corrected state.

    Args:
        body: Request with optional ``wallet`` and ``units`` patches.
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        CorrectStateResponse with ``wallet_after`` showing the final balances.
    """
    wallet = await WalletRepository.get_by_player(session, player.id)
    assert wallet is not None, "Wallet missing — database integrity error"

    if body.wallet:
        for field, value in body.wallet.model_dump(exclude_none=True).items():
            setattr(wallet, field, value)

    if body.units:
        for unit_id, patch in body.units.items():
            fields = patch.model_dump(exclude_none=True)
            if fields:
                await PlayerUnitRepository.upsert(session, player.id, unit_id, **fields)

    # Invalidate snapshot so next tick re-signs from the patched state
    player.snapshot_signature = ""
    await session.flush()
    await session.commit()

    return CorrectStateResponse(
        ok=True,
        wallet_after={
            "energy_drink": wallet.energy_drink,
            "u238": wallet.u238,
            "u235": wallet.u235,
            "u233": wallet.u233,
            "meta_isotopes": wallet.meta_isotopes,
        },
    )
