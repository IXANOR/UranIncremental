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


class GameStateResponse(BaseModel):
    """Full game state snapshot returned by GET /api/v1/game/state."""

    player: PlayerStateSchema
    wallet: WalletSchema
    server_time: datetime


class StartGameResponse(BaseModel):
    """Response for POST /api/v1/game/start."""

    player_id: uuid.UUID
    state_version: int
    started_at: datetime
