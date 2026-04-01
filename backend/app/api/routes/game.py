"""Game management endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.db.models.player_state import PlayerState
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository
from app.db.session import get_db
from app.schemas.game import (
    GameStateResponse,
    PlayerStateSchema,
    PrestigeResponse,
    StartGameResponse,
    UnitStateSchema,
    UpgradeStateSchema,
    WalletSchema,
)
from app.services.game_loop_service import SnapshotSignatureError, tick
from app.services.prestige_service import PrestigeNotAvailableError
from app.services.prestige_service import prestige as run_prestige
from app.services.pricing_service import compute_unit_cost

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
    updates the snapshot signature, and persists the result.  Also returns
    the full unit and upgrade catalogs enriched with per-player ownership
    data and next purchase costs.

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        GameStateResponse with updated player, wallet, server timestamp,
        all units with ownership/cost, and all upgrades with purchase level.

    Raises:
        HTTPException(409): If the stored snapshot signature does not match the
            current state, indicating possible tampering.
    """
    try:
        result = await tick(session, player)
        await session.commit()
    except SnapshotSignatureError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    unit_defs = await UnitDefinitionRepository.get_all(session)
    player_units = await PlayerUnitRepository.get_by_player(session, player.id)
    owned_map = {pu.unit_id: pu for pu in player_units}

    units: list[UnitStateSchema] = []
    for ud in unit_defs:
        pu = owned_map.get(ud.id)
        amount = pu.amount_owned if pu is not None else 0
        mult = pu.effective_multiplier if pu is not None else Decimal("1")
        next_cost = compute_unit_cost(
            ud.base_cost_amount, ud.cost_growth_factor, ud.cost_growth_type, amount
        )
        units.append(
            UnitStateSchema(
                unit_id=ud.id,
                name=ud.name,
                tier=ud.tier,
                production_resource=ud.production_resource,
                production_rate_per_sec=ud.production_rate_per_sec,
                base_cost_currency=ud.base_cost_currency,
                amount_owned=amount,
                effective_multiplier=mult,
                next_cost=next_cost,
            )
        )

    upgrade_defs = await UpgradeDefinitionRepository.get_all(session)
    player_upgrades = await PlayerUpgradeRepository.get_by_player(session, player.id)
    purchased_map = {pu.upgrade_id: pu.level for pu in player_upgrades}

    upgrades: list[UpgradeStateSchema] = [
        UpgradeStateSchema(
            upgrade_id=ud.id,
            name=ud.name,
            description=ud.description,
            tier=ud.tier,
            cost_currency=ud.cost_currency,
            cost_amount=ud.cost_amount,
            effect_type=ud.effect_type,
            effect_value=ud.effect_value,
            is_repeatable=ud.is_repeatable,
            survives_prestige=ud.survives_prestige,
            purchased_level=purchased_map.get(ud.id, 0),
        )
        for ud in upgrade_defs
    ]

    return GameStateResponse(
        player=PlayerStateSchema.model_validate(result.player),
        wallet=WalletSchema.model_validate(result.wallet),
        server_time=result.server_time,
        units=units,
        upgrades=upgrades,
    )


@router.post("/prestige", response_model=PrestigeResponse)
async def prestige_endpoint(
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> PrestigeResponse:
    """Perform a soft reset and advance prestige_count by 1.

    Resets the wallet and unit inventory back to starting values.  Upgrades
    marked ``survives_prestige=True`` are retained and their effects
    re-applied.  The production multiplier permanently increases by ×1.15
    per prestige (applied in the game loop as 1.15^prestige_count).

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        PrestigeResponse with the new prestige_count, production_multiplier,
        and the list of upgrade IDs that survived the reset.

    Raises:
        HTTPException(409): If the player has not met the u238 threshold.
    """
    try:
        result = await run_prestige(session, player)
        await session.commit()
    except PrestigeNotAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return PrestigeResponse(
        ok=True,
        new_prestige_count=result.new_prestige_count,
        production_multiplier=float(Decimal("1.15") ** result.new_prestige_count),
        surviving_upgrades=result.surviving_upgrade_ids,
    )
