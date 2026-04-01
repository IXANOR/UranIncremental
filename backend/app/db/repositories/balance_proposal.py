"""Repository for BalanceProposal CRUD operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.balance import BalanceProposal


class BalanceProposalRepository:
    """Data-access layer for BalanceProposal records."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[BalanceProposal]:
        """Return all proposals ordered newest-first.

        Args:
            session: Active async database session.

        Returns:
            List of BalanceProposal rows, newest first.
        """
        result = await session.execute(
            select(BalanceProposal).order_by(BalanceProposal.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, proposal_id: uuid.UUID) -> BalanceProposal | None:
        """Fetch a single proposal by primary key.

        Args:
            session: Active async database session.
            proposal_id: UUID of the proposal.

        Returns:
            BalanceProposal if found, else None.
        """
        return await session.get(BalanceProposal, proposal_id)

    @staticmethod
    async def set_status(
        session: AsyncSession,
        proposal: BalanceProposal,
        status: str,
    ) -> BalanceProposal:
        """Update a proposal's status and set resolved_at if terminal.

        Args:
            session: Active async database session.
            proposal: The proposal to update.
            status: New status string (``approved``, ``rejected``, ``applied``).

        Returns:
            The updated BalanceProposal.
        """
        proposal.status = status
        if status in {"approved", "rejected", "applied"}:
            proposal.resolved_at = datetime.now(UTC)
        await session.flush()
        return proposal
