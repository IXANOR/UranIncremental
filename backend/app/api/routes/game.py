"""Game management endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.core.config import settings
from app.db.models.player_state import PlayerState
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository
from app.db.session import get_db
from app.schemas.game import (
    ClickResponse,
    GameStateResponse,
    PlayerStateSchema,
    PrestigeOptionSchema,
    PrestigeRequest,
    PrestigeResponse,
    StartGameResponse,
    UnitStateSchema,
    UpgradeStateSchema,
    WalletSchema,
)
from app.services.click_service import ClickRateLimitError, process_click
from app.services.game_loop_service import SnapshotSignatureError, tick
from app.services.prestige_service import (
    _VALID_PRESTIGE_OPTIONS,
    PrestigeNotAvailableError,
    multi_prestige_requirement,
    prestige_bulk,
    prestige_requirement,
)
from app.services.pricing_service import (
    compute_bulk_cost,
    compute_max_affordable,
    compute_unit_cost,
)

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

    wallet = result.wallet

    units: list[UnitStateSchema] = []
    for ud in unit_defs:
        pu = owned_map.get(ud.id)
        amount = pu.amount_owned if pu is not None else 0
        mult = pu.effective_multiplier if pu is not None else Decimal("1")
        next_cost = compute_unit_cost(
            ud.base_cost_amount, ud.cost_growth_factor, ud.cost_growth_type, amount
        )
        bulk_10 = compute_bulk_cost(
            ud.base_cost_amount, ud.cost_growth_factor, ud.cost_growth_type, amount, 10
        )
        bulk_100 = compute_bulk_cost(
            ud.base_cost_amount, ud.cost_growth_factor, ud.cost_growth_type, amount, 100
        )
        wallet_balance = getattr(wallet, ud.base_cost_currency, Decimal("0"))
        max_buy = compute_max_affordable(
            ud.base_cost_amount,
            ud.cost_growth_factor,
            ud.cost_growth_type,
            amount,
            wallet_balance,
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
                bulk_10_cost=bulk_10,
                bulk_100_cost=bulk_100,
                max_affordable=max_buy,
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
            target_unit_id=ud.target_unit_id,
            is_repeatable=ud.is_repeatable,
            survives_prestige=ud.survives_prestige,
            purchased_level=purchased_map.get(ud.id, 0),
        )
        for ud in upgrade_defs
    ]

    p = result.player.prestige_count
    prestige_options: list[PrestigeOptionSchema] = []
    for count, (currency, _) in sorted(_VALID_PRESTIGE_OPTIONS.items()):
        cost, _ = multi_prestige_requirement(p, count, currency)
        wallet_amount = getattr(wallet, currency, Decimal("0"))
        prestige_options.append(
            PrestigeOptionSchema(
                count=count,
                currency=currency,
                cost=cost,
                can_afford=wallet_amount >= cost,
            )
        )

    return GameStateResponse(
        player=PlayerStateSchema.model_validate(result.player),
        wallet=WalletSchema.model_validate(result.wallet),
        server_time=result.server_time,
        units=units,
        upgrades=upgrades,
        test_mode=settings.test_mode,
        prestige_next_requirement=prestige_requirement(result.player.prestige_count),
        prestige_options=prestige_options,
    )


@router.post("/prestige", response_model=PrestigeResponse)
async def prestige_endpoint(
    req: PrestigeRequest = PrestigeRequest(),
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> PrestigeResponse:
    """Perform a soft reset and advance prestige_count by req.count.

    Resets the wallet and unit inventory back to starting values.  Upgrades
    marked ``survives_prestige=True`` are retained and their effects
    re-applied.  The production multiplier permanently increases by ×1.20
    per prestige level (applied in the game loop as 1.20^prestige_count).

    Supported prestige options (count, currency):
        1×  U-238  — cost 2^p
        5×  U-235  — cost max(1, 2^(p-1))
        10× U-233  — cost max(1, 2^(p-2))
        25× META   — cost max(1, 2^(p-3))

    Args:
        req: Optional prestige parameters (count and currency).  Defaults to
            1× U-238 when the body is omitted.
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        PrestigeResponse with the new prestige_count, production_multiplier,
        and the list of upgrade IDs that survived the reset.

    Raises:
        HTTPException(409): If the player cannot afford the chosen prestige.
        HTTPException(422): If count/currency combination is invalid.
    """
    try:
        result = await prestige_bulk(session, player, req.count, req.currency)
        await session.commit()
    except PrestigeNotAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return PrestigeResponse(
        ok=True,
        new_prestige_count=result.new_prestige_count,
        production_multiplier=float(Decimal("1.20") ** result.new_prestige_count),
        surviving_upgrades=result.surviving_upgrade_ids,
    )


@router.post("/click", response_model=ClickResponse)
async def click_reactor(
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> ClickResponse:
    """Process a single reactor click and award ED to the player.

    Awards ``BASE_CLICK_REWARD * 1.20 ** prestige_count`` energy_drink per click.
    Enforces a server-side rate limit of 10 clicks per second.

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        ClickResponse with the ``gained`` amount of energy_drink.

    Raises:
        HTTPException(429): If the player exceeds the click rate limit.
    """
    try:
        gained = await process_click(session, player)
        await session.commit()
    except ClickRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    return ClickResponse(gained=gained)
