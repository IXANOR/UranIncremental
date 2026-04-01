"""Balance proposal endpoints (TEST_MODE only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_test_mode
from app.db.repositories.balance_proposal import BalanceProposalRepository
from app.db.session import get_db
from app.schemas.balance import ApplyResponse, BalanceChange, BalanceProposalSchema, ProposeResponse
from app.services import balance_ai_service

router = APIRouter(
    prefix="/api/v1/balance",
    tags=["balance"],
    dependencies=[Depends(require_test_mode)],
)


def _schema(proposal: object) -> BalanceProposalSchema:
    """Convert a BalanceProposal ORM object to its Pydantic schema.

    Args:
        proposal: BalanceProposal ORM instance.

    Returns:
        BalanceProposalSchema with changes mapped to BalanceChange objects.
    """
    from app.db.models.balance import BalanceProposal as _BP

    p: _BP = proposal  # type: ignore[assignment]
    return BalanceProposalSchema(
        id=p.id,
        status=p.status,
        changes=[BalanceChange(**c) for c in p.changes_json],
        rationale=p.rationale,
        created_at=p.created_at,
        resolved_at=p.resolved_at,
    )


@router.post("/propose", response_model=ProposeResponse)
async def propose(session: AsyncSession = Depends(get_db)) -> ProposeResponse:
    """Generate an AI balance proposal and save it with status ``pending``.

    Calls the Anthropic API with the current game configuration and returns
    the structured proposal for admin review.

    Args:
        session: Async database session injected by ``get_db``.

    Returns:
        ProposeResponse containing the newly created proposal.

    Raises:
        HTTPException(503): If the Anthropic API key is not configured.
        HTTPException(422): If the AI response cannot be parsed.
    """
    try:
        proposal = await balance_ai_service.generate_proposal(session)
        await session.commit()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ProposeResponse(ok=True, proposal=_schema(proposal))


@router.get("/proposals", response_model=list[BalanceProposalSchema])
async def list_proposals(
    session: AsyncSession = Depends(get_db),
) -> list[BalanceProposalSchema]:
    """Return all balance proposals, newest first.

    Args:
        session: Async database session injected by ``get_db``.

    Returns:
        List of BalanceProposalSchema objects.
    """
    proposals = await BalanceProposalRepository.get_all(session)
    return [_schema(p) for p in proposals]


@router.post("/proposals/{proposal_id}/approve", response_model=BalanceProposalSchema)
async def approve_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> BalanceProposalSchema:
    """Mark a pending proposal as approved.

    The proposal must then be applied via the ``/apply`` endpoint to take effect.

    Args:
        proposal_id: UUID of the proposal to approve.
        session: Async database session injected by ``get_db``.

    Returns:
        Updated BalanceProposalSchema with status ``approved``.

    Raises:
        HTTPException(404): If the proposal does not exist.
        HTTPException(409): If the proposal is not in ``pending`` status.
    """
    proposal = await BalanceProposalRepository.get_by_id(session, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Proposal is '{proposal.status}', only 'pending' proposals can be approved",
        )
    await BalanceProposalRepository.set_status(session, proposal, "approved")
    await session.commit()
    return _schema(proposal)


@router.post("/proposals/{proposal_id}/apply", response_model=ApplyResponse)
async def apply_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ApplyResponse:
    """Apply an approved balance proposal to the live game configuration.

    Updates unit and upgrade definition rows in the database immediately.
    Run ``pytest app/tests/balance/`` afterwards to verify the game still passes
    all balance constraints.

    Args:
        proposal_id: UUID of the proposal to apply.
        session: Async database session injected by ``get_db``.

    Returns:
        ApplyResponse with the count of applied changes.

    Raises:
        HTTPException(404): If the proposal does not exist.
        HTTPException(409): If the proposal is not in ``approved`` status.
    """
    proposal = await BalanceProposalRepository.get_by_id(session, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    try:
        count = await balance_ai_service.apply_proposal(session, proposal)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await session.commit()

    return ApplyResponse(
        ok=True,
        applied_changes=count,
        message=(
            f"Applied {count} change(s). "
            "Run 'pytest app/tests/balance/' to verify balance constraints."
        ),
    )
