"""Pydantic schemas for balance proposal endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BalanceChange(BaseModel):
    """A single field-level change within a balance proposal."""

    entity: str  # "unit" | "upgrade"
    id: str
    field: str
    old_value: str
    new_value: str
    reason: str = ""


class BalanceProposalSchema(BaseModel):
    """Public representation of a BalanceProposal record."""

    id: uuid.UUID
    status: str
    changes: list[BalanceChange]
    rationale: str
    created_at: datetime
    resolved_at: datetime | None


class ProposeResponse(BaseModel):
    """Response for POST /balance/propose."""

    ok: bool
    proposal: BalanceProposalSchema


class ApplyResponse(BaseModel):
    """Response for POST /balance/proposals/{id}/apply."""

    ok: bool
    applied_changes: int
    message: str
