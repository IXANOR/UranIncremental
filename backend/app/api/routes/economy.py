"""Economy endpoints: buying units and upgrades."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.db.models.player_state import PlayerState
from app.db.session import get_db
from app.schemas.economy import (
    BuyUnitRequest,
    BuyUnitResponse,
    BuyUpgradeRequest,
    BuyUpgradeResponse,
)
from app.services.economy_service import (
    AlreadyPurchasedError,
    InsufficientFundsError,
    InvalidQuantityError,
    UnknownUnitError,
    UnknownUpgradeError,
    buy_unit,
    buy_upgrade,
)

router = APIRouter(prefix="/api/v1/economy", tags=["economy"])


@router.post("/buy-unit", response_model=BuyUnitResponse)
async def buy_unit_endpoint(
    body: BuyUnitRequest,
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> BuyUnitResponse:
    """Purchase one or more units for the authenticated player.

    Deducts the total cost from the player's wallet using the hybrid pricing
    curve.  The purchased units are added to the player's inventory atomically.

    Args:
        body: Request body containing ``unit_id`` and ``quantity``.
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        BuyUnitResponse with ``new_amount_owned`` and ``wallet_after`` balances.

    Raises:
        HTTPException(404): If ``unit_id`` does not exist.
        HTTPException(409): If the player cannot afford the purchase.
        HTTPException(422): If ``quantity`` is less than 1.
    """
    try:
        result = await buy_unit(session, player, body.unit_id, body.quantity)
        await session.commit()
    except UnknownUnitError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidQuantityError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    w = result.wallet
    return BuyUnitResponse(
        ok=True,
        new_amount_owned=result.player_unit.amount_owned,
        wallet_after={
            "energy_drink": w.energy_drink,
            "u238": w.u238,
            "u235": w.u235,
            "u233": w.u233,
            "meta_isotopes": w.meta_isotopes,
        },
    )


@router.post("/buy-upgrade", response_model=BuyUpgradeResponse)
async def buy_upgrade_endpoint(
    body: BuyUpgradeRequest,
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> BuyUpgradeResponse:
    """Purchase an upgrade for the authenticated player and apply its effect.

    Non-repeatable upgrades may only be bought once.  The upgrade's effect
    (production multiplier, offline efficiency, or offline cap) is applied
    immediately after purchase.

    Args:
        body: Request body containing ``upgrade_id``.
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        BuyUpgradeResponse with ``upgrade_level`` and ``applied_effect`` details.

    Raises:
        HTTPException(404): If ``upgrade_id`` does not exist.
        HTTPException(409): If the player cannot afford it, or has already
            purchased a non-repeatable upgrade.
    """
    try:
        result = await buy_upgrade(session, player, body.upgrade_id)
        await session.commit()
    except UnknownUpgradeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (InsufficientFundsError, AlreadyPurchasedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return BuyUpgradeResponse(
        ok=True,
        upgrade_level=result.player_upgrade.level,
        applied_effect={
            "effect_type": result.upgrade_def.effect_type,
            "effect_value": float(result.upgrade_def.effect_value),
        },
    )
