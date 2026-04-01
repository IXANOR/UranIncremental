"""Schemas for test/admin endpoints (TEST_MODE only)."""

from decimal import Decimal

from pydantic import BaseModel, field_validator


class SimulateTimeRequest(BaseModel):
    """Request body for POST /api/v1/test/simulate-time."""

    seconds: int

    @field_validator("seconds")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        """Validate that seconds is a positive integer.

        Args:
            v: The seconds value to validate.

        Returns:
            The validated seconds value.

        Raises:
            ValueError: If seconds is not positive.
        """
        if v <= 0:
            raise ValueError("seconds must be a positive integer")
        return v


class SimulateTimeResponse(BaseModel):
    """Response for POST /api/v1/test/simulate-time."""

    ok: bool
    simulated_seconds: int
    new_state_version: int


class WalletPatch(BaseModel):
    """Optional currency overrides for POST /api/v1/test/correct-state."""

    energy_drink: Decimal | None = None
    u238: Decimal | None = None
    u235: Decimal | None = None
    u233: Decimal | None = None
    meta_isotopes: Decimal | None = None


class UnitPatch(BaseModel):
    """Optional unit overrides for POST /api/v1/test/correct-state."""

    amount_owned: int | None = None


class CorrectStateRequest(BaseModel):
    """Request body for POST /api/v1/test/correct-state.

    All fields are optional — only provided values are patched.
    """

    wallet: WalletPatch | None = None
    units: dict[str, UnitPatch] | None = None


class CorrectStateResponse(BaseModel):
    """Response for POST /api/v1/test/correct-state."""

    ok: bool
    wallet_after: dict[str, Decimal]
