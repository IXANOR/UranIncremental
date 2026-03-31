import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import EventLog


class EventLogRepository:
    """Data access layer for the append-only event log."""

    @staticmethod
    async def create(
        session: AsyncSession,
        player_id: uuid.UUID,
        event_type: str,
        payload: dict,  # type: ignore[type-arg]
    ) -> EventLog:
        """Append a new event to the log.

        Args:
            session: Active async database session.
            player_id: UUID of the player associated with this event.
            event_type: Short identifier for the event (e.g. ``"delta_anomaly"``).
            payload: Arbitrary JSON-serialisable data for the event.

        Returns:
            Newly created EventLog instance after flush.
        """
        row = EventLog(player_id=player_id, event_type=event_type, payload=payload)
        session.add(row)
        await session.flush()
        return row
