"""Nuclear experiment minigame service.

Handles cost deduction, weighted outcome rolling, and effect application
for the seasonal sink experiment mechanic.
"""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import ensure_utc
from app.db.models.player_state import PlayerState
from app.db.repositories.experiment_definition import ExperimentDefinitionRepository
from app.db.repositories.wallet import WalletRepository


class ExperimentNotFoundError(Exception):
    """Raised when the requested experiment_id does not exist."""


class ExperimentOnCooldownError(Exception):
    """Raised when the experiment was run too recently."""


class InsufficientFundsError(Exception):
    """Raised when the player cannot afford the experiment."""


@dataclass
class ExperimentResult:
    """Result of running a single experiment.

    Attributes:
        experiment_id: Identifier of the experiment that was run.
        outcome_label: Player-facing description of the rolled outcome.
        effect_type: One of "nothing", "prod_bonus", "temp_multiplier".
        effect_value: Amount of ED (prod_bonus) or multiplier value.
        duration_seconds: Active seconds for temp_multiplier effects (0 for others).
        cooldown_until: UTC timestamp when the experiment can be run again.
    """

    experiment_id: str
    outcome_label: str
    effect_type: str
    effect_value: Decimal
    duration_seconds: int
    cooldown_until: datetime


def _roll_outcome(outcomes: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    """Select one outcome from a weighted probability table.

    Args:
        outcomes: List of outcome dicts, each with a ``probability`` key.
            Probabilities must sum to 1.0.
        rng: Random instance (injectable for deterministic testing).

    Returns:
        The selected outcome dict.
    """
    roll = rng.random()
    cumulative = 0.0
    for outcome in outcomes:
        cumulative += outcome["probability"]
        if roll < cumulative:
            return outcome
    return outcomes[-1]  # fallback for floating-point edge cases


async def run_experiment(
    session: AsyncSession,
    player: PlayerState,
    experiment_id: str,
    *,
    rng: random.Random | None = None,
) -> ExperimentResult:
    """Run a nuclear experiment: deduct cost, roll outcome, apply effect.

    Args:
        session: Async database session.
        player: Authenticated player whose state will be updated.
        experiment_id: ID of the experiment to run.
        rng: Optional Random instance for deterministic testing. Defaults to
            a fresh ``random.Random()`` (unseeded, non-deterministic).

    Returns:
        ExperimentResult describing the outcome and its effect.

    Raises:
        ExperimentNotFoundError: If experiment_id is not in the database.
        ExperimentOnCooldownError: If the experiment was run within its cooldown window.
        InsufficientFundsError: If the player cannot cover ed_cost or u238_cost.
    """
    if rng is None:
        rng = random.Random()

    exp = await ExperimentDefinitionRepository.get_by_id(session, experiment_id)
    if exp is None:
        raise ExperimentNotFoundError(f"Experiment '{experiment_id}' not found")

    now = datetime.now(UTC)

    # --- Cooldown check -------------------------------------------------------
    cooldowns: dict[str, Any] = player.experiment_cooldowns or {}
    last_run_str = cooldowns.get(experiment_id)
    if last_run_str is not None:
        last_run = datetime.fromisoformat(last_run_str)
        elapsed = (ensure_utc(now) - ensure_utc(last_run)).total_seconds()
        if elapsed < exp.cooldown_seconds:
            remaining = int(exp.cooldown_seconds - elapsed)
            raise ExperimentOnCooldownError(
                f"Experiment '{experiment_id}' on cooldown: {remaining}s remaining"
            )

    # --- Funds check ----------------------------------------------------------
    wallet = await WalletRepository.get_by_player(session, player.id)
    assert wallet is not None, "Wallet missing — database integrity error"

    if wallet.energy_drink < exp.ed_cost:
        raise InsufficientFundsError(f"Need {exp.ed_cost} ED, have {wallet.energy_drink:.2f}")
    if wallet.u238 < exp.u238_cost:
        raise InsufficientFundsError(f"Need {exp.u238_cost} U-238, have {wallet.u238:.2f}")

    # --- Deduct costs ---------------------------------------------------------
    wallet.energy_drink -= exp.ed_cost
    wallet.u238 -= exp.u238_cost

    # --- Roll outcome ---------------------------------------------------------
    outcome = _roll_outcome(exp.outcomes, rng)
    effect_type = outcome["effect_type"]
    effect_value = Decimal(str(outcome["effect_value"]))
    duration_seconds = int(outcome.get("duration_seconds", 0))

    # --- Apply effect ---------------------------------------------------------
    if effect_type == "prod_bonus":
        wallet.energy_drink += effect_value
    elif effect_type == "temp_multiplier":
        expires_at = now + timedelta(seconds=duration_seconds)
        # Stack by taking the max expiry if a multiplier is already active
        if (
            player.temp_prod_multiplier_expires_at is not None
            and ensure_utc(player.temp_prod_multiplier_expires_at) > ensure_utc(now)
            and effect_value <= player.temp_prod_multiplier
        ):
            # Active multiplier is already equal or better — just extend expiry
            player.temp_prod_multiplier_expires_at = max(
                ensure_utc(player.temp_prod_multiplier_expires_at), ensure_utc(expires_at)
            )
        else:
            player.temp_prod_multiplier = effect_value
            player.temp_prod_multiplier_expires_at = expires_at
    # "nothing" — no action

    # --- Update cooldown ------------------------------------------------------
    player.experiment_cooldowns = {**cooldowns, experiment_id: now.isoformat()}
    player.snapshot_signature = ""

    cooldown_until = now + timedelta(seconds=exp.cooldown_seconds)
    return ExperimentResult(
        experiment_id=experiment_id,
        outcome_label=outcome["label"],
        effect_type=effect_type,
        effect_value=effect_value,
        duration_seconds=duration_seconds,
        cooldown_until=cooldown_until,
    )


async def get_cooldown_remaining(
    player: PlayerState, experiment_id: str, cooldown_seconds: int
) -> int:
    """Return remaining cooldown seconds for an experiment (0 if ready).

    Args:
        player: Player state containing cooldown timestamps.
        experiment_id: Experiment to check.
        cooldown_seconds: Total cooldown duration from the experiment definition.

    Returns:
        Seconds remaining until the experiment can be run again (0 = ready).
    """
    cooldowns: dict[str, Any] = player.experiment_cooldowns or {}
    last_run_str = cooldowns.get(experiment_id)
    if last_run_str is None:
        return 0
    now = datetime.now(UTC)
    last_run = datetime.fromisoformat(last_run_str)
    elapsed = (ensure_utc(now) - ensure_utc(last_run)).total_seconds()
    return max(0, int(cooldown_seconds - elapsed))
