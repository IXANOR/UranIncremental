"""Unit tests for experiment_service: outcome rolling, cost deduction, effects."""

import random
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentOnCooldownError,
    InsufficientFundsError,
    _roll_outcome,
    run_experiment,
)

# ---------------------------------------------------------------------------
# _roll_outcome — deterministic with seeded RNG
# ---------------------------------------------------------------------------


_SAMPLE_OUTCOMES = [
    {
        "probability": 0.6,
        "label": "A",
        "effect_type": "nothing",
        "effect_value": 0,
        "duration_seconds": 0,
    },
    {
        "probability": 0.4,
        "label": "B",
        "effect_type": "prod_bonus",
        "effect_value": 10,
        "duration_seconds": 0,
    },
]


def test_roll_outcome_first_bucket() -> None:
    """Roll of 0.0 selects the first outcome."""
    rng = random.Random()
    rng.random = lambda: 0.0  # type: ignore[method-assign]
    result = _roll_outcome(_SAMPLE_OUTCOMES, rng)
    assert result["label"] == "A"


def test_roll_outcome_second_bucket() -> None:
    """Roll of 0.7 selects the second outcome (cumulative > 0.6)."""
    rng = random.Random()
    rng.random = lambda: 0.7  # type: ignore[method-assign]
    result = _roll_outcome(_SAMPLE_OUTCOMES, rng)
    assert result["label"] == "B"


# ---------------------------------------------------------------------------
# run_experiment — success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_experiment_deducts_ed_cost(db_session: AsyncSession) -> None:
    """Running alpha_test deducts 20 ED from the wallet."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("200")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        w = await WalletRepository.get_by_player(db_session, p.id)
        assert w is not None
        starting_ed = w.energy_drink
        # Force "nothing" outcome
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        await run_experiment(db_session, p, "alpha_test", rng=rng)
        assert w.energy_drink == starting_ed - Decimal("20")


@pytest.mark.asyncio
async def test_run_experiment_deducts_u238_cost(db_session: AsyncSession) -> None:
    """Running beta_reaction deducts 1 U-238."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("500")
        w.u238 = Decimal("5")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        await run_experiment(db_session, p, "beta_reaction", rng=rng)
        w = await WalletRepository.get_by_player(db_session, p.id)
        assert w is not None
        assert w.u238 == Decimal("4")


@pytest.mark.asyncio
async def test_run_experiment_prod_bonus_adds_ed(db_session: AsyncSession) -> None:
    """prod_bonus outcome credits ED to the wallet."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("200")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        w = await WalletRepository.get_by_player(db_session, p.id)
        assert w is not None
        before = w.energy_drink
        # Roll 0.65 → second bucket of alpha_test = prod_bonus +10
        rng = random.Random()
        rng.random = lambda: 0.65  # type: ignore[method-assign]
        result = await run_experiment(db_session, p, "alpha_test", rng=rng)

    assert result.effect_type == "prod_bonus"
    assert result.effect_value == Decimal("10")
    # wallet.energy_drink = before - 20 (cost) + 10 (bonus) = before - 10
    assert w.energy_drink == before - Decimal("10")


@pytest.mark.asyncio
async def test_run_experiment_temp_multiplier_sets_player_state(db_session: AsyncSession) -> None:
    """temp_multiplier outcome sets player.temp_prod_multiplier and expiry."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("200")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        # Roll 0.95 → third bucket of alpha_test = temp_multiplier 1.5× for 60s
        rng = random.Random()
        rng.random = lambda: 0.95  # type: ignore[method-assign]
        result = await run_experiment(db_session, p, "alpha_test", rng=rng)

    assert result.effect_type == "temp_multiplier"
    assert result.effect_value == Decimal("1.5")
    assert result.duration_seconds == 60
    assert p.temp_prod_multiplier == Decimal("1.5")
    assert p.temp_prod_multiplier_expires_at is not None


@pytest.mark.asyncio
async def test_run_experiment_updates_cooldown(db_session: AsyncSession) -> None:
    """Running an experiment stores the current timestamp in experiment_cooldowns."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("200")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        rng = random.Random()
        rng.random = lambda: 0.0  # type: ignore[method-assign]
        await run_experiment(db_session, p, "alpha_test", rng=rng)

    assert "alpha_test" in p.experiment_cooldowns


# ---------------------------------------------------------------------------
# run_experiment — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_experiment_unknown_id_raises(db_session: AsyncSession) -> None:
    """ExperimentNotFoundError raised for an unknown experiment ID."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(ExperimentNotFoundError):
            await run_experiment(db_session, p, "does_not_exist")


@pytest.mark.asyncio
async def test_run_experiment_on_cooldown_raises(db_session: AsyncSession) -> None:
    """ExperimentOnCooldownError raised when cooldown has not expired."""
    from datetime import UTC, datetime

    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("500")
        # Pre-set cooldown to just now
        player.experiment_cooldowns = {"alpha_test": datetime.now(UTC).isoformat()}

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(ExperimentOnCooldownError):
            await run_experiment(db_session, p, "alpha_test")


@pytest.mark.asyncio
async def test_run_experiment_insufficient_ed_raises(db_session: AsyncSession) -> None:
    """InsufficientFundsError raised when player cannot afford ED cost."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("5")  # alpha_test costs 20 ED

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(InsufficientFundsError):
            await run_experiment(db_session, p, "alpha_test")


@pytest.mark.asyncio
async def test_run_experiment_insufficient_u238_raises(db_session: AsyncSession) -> None:
    """InsufficientFundsError raised when player cannot afford U-238 cost."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("500")
        w.u238 = Decimal("0")  # beta_reaction costs 1 U-238

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(InsufficientFundsError):
            await run_experiment(db_session, p, "beta_reaction")
