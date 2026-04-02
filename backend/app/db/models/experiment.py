"""Experiment definition model for the nuclear experiment seasonal sink."""

from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_DECIMAL = Numeric(precision=28, scale=10)


class ExperimentDefinition(Base):
    """Static definition of a nuclear experiment that players can run.

    Each experiment has fixed ED and U-238 costs, a cooldown duration, and
    a weighted table of possible outcomes stored as JSON.

    Outcome JSON structure (list of dicts):
        probability (float): Cumulative weight; rows must sum to 1.0.
        label (str): Player-facing outcome description.
        effect_type (str): "nothing" | "prod_bonus" | "temp_multiplier".
        effect_value (float): ED bonus (prod_bonus) or multiplier value.
        duration_seconds (int): Active duration for temp_multiplier effects.
    """

    __tablename__ = "experiment_definition"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512))
    ed_cost: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    u238_cost: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    cooldown_seconds: Mapped[int] = mapped_column(default=3600)
    outcomes: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
