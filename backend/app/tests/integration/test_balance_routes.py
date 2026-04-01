"""Integration tests for balance proposal endpoints.

Each test uses a real in-memory SQLite database with ``get_db`` overridden
so the app and the test setup code share the same session — same pattern as
``test_endpoints.py``.
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.seed import seed
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_AI_RESPONSE = json.dumps(
    {
        "changes": [
            {
                "entity": "unit",
                "id": "barrel",
                "field": "production_rate_per_sec",
                "old_value": "0.3",
                "new_value": "0.33",
                "reason": "Tiny boost to early game feel.",
            }
        ],
        "rationale": "Barrel feels slightly slow in the first 2 minutes.",
    }
)


@pytest.fixture
async def seeded(db_session):
    """Seed unit/upgrade definitions into the test database."""
    await seed(db_session)
    return db_session


@pytest.fixture
async def api_client(seeded):
    """AsyncClient with get_db overridden to use the seeded test session."""

    async def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TEST_MODE guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_propose_blocked_in_prod_mode(seeded) -> None:
    """Balance endpoints return 404 when TEST_MODE=false."""

    async def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    original = settings.test_mode
    settings.test_mode = False
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            res = await c.post("/api/v1/balance/propose")
        assert res.status_code == 404
    finally:
        settings.test_mode = original
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/balance/propose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_propose_creates_pending_proposal(api_client: AsyncClient) -> None:
    """POST /propose triggers AI and returns a pending proposal."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        res = await api_client.post("/api/v1/balance/propose")

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["proposal"]["status"] == "pending"
    assert len(data["proposal"]["changes"]) == 1
    assert data["proposal"]["changes"][0]["id"] == "barrel"
    assert data["proposal"]["rationale"] != ""


# ---------------------------------------------------------------------------
# GET /api/v1/balance/proposals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_proposals_empty(api_client: AsyncClient) -> None:
    """GET /proposals returns an empty list when no proposals exist."""
    res = await api_client.get("/api/v1/balance/proposals")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_proposals_returns_created(api_client: AsyncClient) -> None:
    """GET /proposals lists proposals after one is created."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        await api_client.post("/api/v1/balance/propose")

    res = await api_client.get("/api/v1/balance/proposals")
    assert res.status_code == 200
    assert len(res.json()) == 1


# ---------------------------------------------------------------------------
# POST /api/v1/balance/proposals/{id}/approve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_proposal_sets_status(api_client: AsyncClient) -> None:
    """Approving a pending proposal changes its status to 'approved'."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        propose_res = await api_client.post("/api/v1/balance/propose")
    proposal_id = propose_res.json()["proposal"]["id"]

    res = await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_nonexistent_proposal_returns_404(api_client: AsyncClient) -> None:
    """Approving a non-existent proposal ID returns 404."""
    import uuid

    res = await api_client.post(f"/api/v1/balance/proposals/{uuid.uuid4()}/approve")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_approve_already_approved_returns_409(api_client: AsyncClient) -> None:
    """Attempting to approve an already-approved proposal returns 409."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        propose_res = await api_client.post("/api/v1/balance/propose")
    proposal_id = propose_res.json()["proposal"]["id"]

    await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/approve")
    res = await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/approve")
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/v1/balance/proposals/{id}/apply
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_approved_proposal_updates_unit_definition(
    api_client: AsyncClient,
    seeded,
) -> None:
    """Applying an approved proposal updates the unit definition in the DB."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        propose_res = await api_client.post("/api/v1/balance/propose")
    proposal_id = propose_res.json()["proposal"]["id"]

    await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/approve")
    apply_res = await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/apply")

    assert apply_res.status_code == 200
    data = apply_res.json()
    assert data["ok"] is True
    assert data["applied_changes"] == 1

    barrel = await UnitDefinitionRepository.get_by_id(seeded, "barrel")
    assert barrel is not None
    assert barrel.production_rate_per_sec == Decimal("0.33")


@pytest.mark.asyncio
async def test_apply_pending_proposal_returns_409(api_client: AsyncClient) -> None:
    """Applying a proposal that is still pending returns 409."""
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=_VALID_AI_RESPONSE),
    ):
        propose_res = await api_client.post("/api/v1/balance/propose")
    proposal_id = propose_res.json()["proposal"]["id"]

    res = await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/apply")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_apply_ignores_disallowed_fields(
    api_client: AsyncClient,
    seeded,
) -> None:
    """Changes targeting disallowed fields are silently skipped (applied_changes=0)."""
    bad_response = json.dumps(
        {
            "changes": [
                {
                    "entity": "unit",
                    "id": "barrel",
                    "field": "name",  # NOT in ALLOWED_UNIT_FIELDS
                    "old_value": "Beczka Energetyka",
                    "new_value": "Hacked Name",
                }
            ],
            "rationale": "Attempting to rename a unit.",
        }
    )
    with patch(
        "app.services.balance_ai_service._call_ai",
        new=AsyncMock(return_value=bad_response),
    ):
        propose_res = await api_client.post("/api/v1/balance/propose")
    proposal_id = propose_res.json()["proposal"]["id"]

    await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/approve")
    apply_res = await api_client.post(f"/api/v1/balance/proposals/{proposal_id}/apply")

    assert apply_res.json()["applied_changes"] == 0
    barrel = await UnitDefinitionRepository.get_by_id(seeded, "barrel")
    assert barrel is not None
    assert barrel.name == "Beczka Energetyka"  # unchanged
