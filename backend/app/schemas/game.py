import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PlayerStateSchema(BaseModel):
    """Public representation of player progression state."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    prestige_count: int
    tech_magic_level: int
    offline_efficiency: float
    offline_cap_seconds: int
    last_tick_at: datetime
    last_online_at: datetime


class WalletSchema(BaseModel):
    """Public representation of a player's currency balances."""

    model_config = ConfigDict(from_attributes=True)

    energy_drink: Decimal
    u238: Decimal
    u235: Decimal
    u233: Decimal
    meta_isotopes: Decimal


class UnitStateSchema(BaseModel):
    """Combined unit definition + player ownership data for the state response."""

    unit_id: str
    name: str
    tier: int
    production_resource: str
    production_rate_per_sec: Decimal
    base_cost_currency: str
    amount_owned: int
    effective_multiplier: Decimal
    next_cost: Decimal


class UpgradeStateSchema(BaseModel):
    """Combined upgrade definition + purchase status for the state response."""

    upgrade_id: str
    name: str
    description: str
    tier: int
    cost_currency: str
    cost_amount: Decimal
    effect_type: str
    effect_value: Decimal
    is_repeatable: bool
    survives_prestige: bool
    purchased_level: int  # 0 = not purchased


class GameStateResponse(BaseModel):
    """Full game state snapshot returned by GET /api/v1/game/state."""

    player: PlayerStateSchema
    wallet: WalletSchema
    server_time: datetime
    units: list[UnitStateSchema]
    upgrades: list[UpgradeStateSchema]


class StartGameResponse(BaseModel):
    """Response for POST /api/v1/game/start."""

    player_id: uuid.UUID
    state_version: int
    started_at: datetime


class PrestigeResponse(BaseModel):
    """Response for POST /api/v1/game/prestige."""

    ok: bool
    new_prestige_count: int
    production_multiplier: float
    surviving_upgrades: list[str]
