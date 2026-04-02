"""Experiment endpoints: list available experiments and run one."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_player
from app.db.models.player_state import PlayerState
from app.db.repositories.experiment_definition import ExperimentDefinitionRepository
from app.db.session import get_db
from app.schemas.game import ExperimentOutcomeSchema, ExperimentRunResponse, ExperimentSchema
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentOnCooldownError,
    InsufficientFundsError,
    get_cooldown_remaining,
    run_experiment,
)

router = APIRouter(prefix="/api/v1/game", tags=["experiment"])


@router.get("/experiments", response_model=list[ExperimentSchema])
async def list_experiments(
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> list[ExperimentSchema]:
    """List all available experiments with the player's current cooldown status.

    Args:
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        List of ExperimentSchema with cooldown_remaining_seconds for each experiment.
    """
    exp_defs = await ExperimentDefinitionRepository.get_all(session)
    result = []
    for exp in exp_defs:
        remaining = await get_cooldown_remaining(player, exp.id, exp.cooldown_seconds)
        result.append(
            ExperimentSchema(
                experiment_id=exp.id,
                name=exp.name,
                description=exp.description,
                ed_cost=exp.ed_cost,
                u238_cost=exp.u238_cost,
                cooldown_seconds=exp.cooldown_seconds,
                cooldown_remaining_seconds=remaining,
                outcomes=[ExperimentOutcomeSchema(**o) for o in exp.outcomes],
            )
        )
    return result


@router.post("/experiment/{experiment_id}", response_model=ExperimentRunResponse)
async def run_experiment_endpoint(
    experiment_id: str,
    player: PlayerState = Depends(get_current_player),
    session: AsyncSession = Depends(get_db),
) -> ExperimentRunResponse:
    """Run a nuclear experiment, deduct costs, and apply the rolled effect.

    Args:
        experiment_id: ID of the experiment to run (path parameter).
        player: Authenticated player resolved from the ``X-Player-ID`` header.
        session: Async database session injected by ``get_db``.

    Returns:
        ExperimentRunResponse with the outcome label, effect details, and
        the UTC timestamp when the experiment can be run again.

    Raises:
        HTTPException(404): If the experiment_id does not exist.
        HTTPException(409): If the experiment is on cooldown.
        HTTPException(402): If the player has insufficient funds.
    """
    try:
        result = await run_experiment(session, player, experiment_id)
        await session.commit()
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExperimentOnCooldownError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=402, detail=str(exc))

    return ExperimentRunResponse(
        experiment_id=result.experiment_id,
        outcome_label=result.outcome_label,
        effect_type=result.effect_type,
        effect_value=result.effect_value,
        duration_seconds=result.duration_seconds,
        cooldown_until=result.cooldown_until,
    )
