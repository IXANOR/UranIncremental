"""Balance tests for nuclear experiments.

All experiment outcomes must stay below 30 minutes of passive production
from a single barrel unit (0.3 ED/s × 1800s = 540 ED equivalent).

For prod_bonus outcomes: effect_value < 540.
For temp_multiplier outcomes: (effect_value - 1) × barrel_rate × duration_seconds < 540.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.experiment_definition import ExperimentDefinitionRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.seed import seed


@pytest.mark.asyncio
async def test_all_experiment_outcomes_below_30min_barrel(db_session: AsyncSession) -> None:
    """Every outcome of every experiment must not exceed 30-min barrel production.

    Threshold: 0.3 ED/s × 1800s = 540 ED equivalent.
    prod_bonus: effect_value < 540.
    temp_multiplier: (mult - 1) × 0.3 × duration_seconds < 540.
    """
    async with db_session.begin():
        await seed(db_session)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert barrel is not None
        experiments = await ExperimentDefinitionRepository.get_all(db_session)

    barrel_rate = barrel.production_rate_per_sec  # 0.3 ED/s
    threshold = barrel_rate * Decimal("1800")  # 540 ED / 30 min

    violations = []
    for exp in experiments:
        for outcome in exp.outcomes:
            etype = outcome["effect_type"]
            evalue = Decimal(str(outcome["effect_value"]))
            duration = int(outcome.get("duration_seconds", 0))

            if etype == "prod_bonus":
                equiv = evalue
            elif etype == "temp_multiplier":
                equiv = (evalue - Decimal("1")) * barrel_rate * Decimal(str(duration))
            else:
                equiv = Decimal("0")

            if equiv >= threshold:
                violations.append(
                    f"{exp.id}/{etype}/{outcome['label']}: "
                    f"{equiv:.2f} ED equiv >= {threshold} threshold"
                )

    assert not violations, "Experiment outcomes exceed 30-min balance cap:\n" + "\n".join(
        violations
    )


@pytest.mark.asyncio
async def test_experiment_outcome_probabilities_sum_to_one(db_session: AsyncSession) -> None:
    """Each experiment's outcome probabilities must sum to 1.0 (±0.001 tolerance)."""
    async with db_session.begin():
        await seed(db_session)
        experiments = await ExperimentDefinitionRepository.get_all(db_session)

    for exp in experiments:
        total = sum(o["probability"] for o in exp.outcomes)
        assert abs(total - 1.0) < 0.001, (
            f"Experiment '{exp.id}' probabilities sum to {total:.4f}, expected 1.0"
        )
