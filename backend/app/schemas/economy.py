import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class UnitDefinitionSchema(BaseModel):
    """Public representation of a unit type definition."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tier: int
    base_cost_currency: str
    base_cost_amount: Decimal
    production_resource: str
    production_rate_per_sec: Decimal


class PlayerUnitSchema(BaseModel):
    """Public representation of a player's unit ownership."""

    model_config = ConfigDict(from_attributes=True)

    unit_id: str
    amount_owned: int
    effective_multiplier: Decimal
    automation_enabled: bool
    upkeep_energy_per_sec: Decimal


class UpgradeDefinitionSchema(BaseModel):
    """Public representation of an upgrade type definition."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    tier: int
    cost_currency: str
    cost_amount: Decimal
    effect_type: str
    effect_value: Decimal
    is_repeatable: bool
    survives_prestige: bool


class PlayerUpgradeSchema(BaseModel):
    """Public representation of a purchased upgrade."""

    model_config = ConfigDict(from_attributes=True)

    upgrade_id: str
    level: int


class BuyUnitRequest(BaseModel):
    """Request body for POST /api/v1/economy/buy-unit."""

    unit_id: str
    quantity: int = 1


class BuyUnitResponse(BaseModel):
    """Response for POST /api/v1/economy/buy-unit."""

    ok: bool
    new_amount_owned: int
    wallet_after: dict[str, Decimal]


class BuyUpgradeRequest(BaseModel):
    """Request body for POST /api/v1/economy/buy-upgrade."""

    upgrade_id: str


class BuyUpgradeResponse(BaseModel):
    """Response for POST /api/v1/economy/buy-upgrade."""

    ok: bool
    upgrade_level: int
    applied_effect: dict[str, object]


class ClaimOfflineRequest(BaseModel):
    """Request body for POST /api/v1/time/claim-offline."""

    player_id: uuid.UUID


class ClaimOfflineResponse(BaseModel):
    """Response for POST /api/v1/time/claim-offline."""

    simulated_seconds: int
    efficiency_used: float
    gains: dict[str, Decimal]
    cap_applied: bool
