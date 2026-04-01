"""Balance AI service — generates and applies balance proposals via Anthropic API.

Flow:
1. ``generate_proposal`` reads current unit/upgrade config from DB.
2. Builds a prompt and calls ``_call_ai`` (Anthropic claude-haiku).
3. ``parse_ai_response`` validates the JSON and extracts changes.
4. A ``BalanceProposal`` row is saved with status ``pending``.
5. Admin reviews the proposal and approves it (sets status ``approved``).
6. ``apply_proposal`` writes approved changes to unit/upgrade definition rows.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.balance import BalanceProposal
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository

logger = logging.getLogger(__name__)

# Fields the AI is allowed to tweak — design fields are intentionally excluded.
ALLOWED_UNIT_FIELDS: frozenset[str] = frozenset(
    {"production_rate_per_sec", "base_cost_amount", "cost_growth_factor"}
)
ALLOWED_UPGRADE_FIELDS: frozenset[str] = frozenset({"cost_amount", "effect_value"})

_SYSTEM_PROMPT = (
    "You are a game balance AI for UranIncremental, an idle incremental game.\n"
    "Theme: uranium + energy drinks, humorous techno-magic sci-fi.\n"
    "Core invariant: energy_drink must never become irrelevant — it is automation upkeep "
    "throughout the game.\n\n"
    "Propose SMALL, targeted balance changes to improve game feel. Maximum 5 changes.\n"
    "Changes must be modest: ±30% max per numeric field.\n"
    "Do not invent new entities — only tweak existing numeric values.\n\n"
    "Allowed unit fields: production_rate_per_sec, base_cost_amount, cost_growth_factor\n"
    "Allowed upgrade fields: cost_amount, effect_value\n\n"
    "Respond ONLY with valid JSON in this exact schema (no markdown fences):\n"
    '{"changes": [{"entity": "unit", "id": "<id>", "field": "<field>", '
    '"old_value": "<current>", "new_value": "<proposed>", "reason": "<one sentence>"}], '
    '"rationale": "<one paragraph>"}'
)


def build_prompt(
    unit_defs: list[Any],
    upgrade_defs: list[Any],
) -> str:
    """Build the user-turn prompt string for the balance AI.

    Args:
        unit_defs: List of UnitDefinition ORM objects (or compatible mocks).
        upgrade_defs: List of UpgradeDefinition ORM objects (or compatible mocks).

    Returns:
        Formatted prompt string ready to send as the user message.
    """
    lines: list[str] = ["Current game configuration:\n\nUNITS:"]
    for u in unit_defs:
        lines.append(
            f"  {u.id} (tier {u.tier}): prod={u.production_rate_per_sec} "
            f"{u.production_resource}/s, cost={u.base_cost_amount} "
            f"{u.base_cost_currency}, growth_factor={u.cost_growth_factor}"
        )
    lines.append("\nUPGRADES:")
    for upg in upgrade_defs:
        lines.append(
            f"  {upg.id}: cost={upg.cost_amount} {upg.cost_currency}, "
            f"effect={upg.effect_type} {upg.effect_value}, repeatable={upg.is_repeatable}"
        )
    lines.append(
        "\nBalance constraints:"
        "\n  - 10 barrels must afford mini_reactor in ≤ 120 s"
        "\n  - 100 uranium_mines need ≥ 4 min to afford centrifuge_t2"
        "\n  - prestige_requirement(n) = 1 × 2^n U-238; centrifuge produces 0.003 u238/s"
        "\n\nPropose changes to improve game pacing and player satisfaction."
    )
    return "\n".join(lines)


def parse_ai_response(response_text: str) -> tuple[list[dict[str, Any]], str]:
    """Parse the AI response into a validated list of changes and a rationale string.

    Args:
        response_text: Raw text from the AI (expected to be JSON, optionally fenced).

    Returns:
        Tuple of (validated_changes, rationale).

    Raises:
        ValueError: If the text is not valid JSON or lacks the ``changes`` key.
    """
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "changes" not in data:
        raise ValueError("AI response missing 'changes' key")

    required_keys = {"entity", "id", "field", "old_value", "new_value"}
    changes: list[dict[str, Any]] = []
    for item in data.get("changes", []):
        if not required_keys.issubset(item.keys()):
            logger.warning("Skipping malformed change item: %s", item)
            continue
        if item["entity"] not in {"unit", "upgrade"}:
            logger.warning("Skipping unknown entity type: %s", item["entity"])
            continue
        changes.append(dict(item))

    rationale: str = str(data.get("rationale", ""))
    return changes, rationale


async def _call_ai(prompt: str) -> str:
    """Call the Anthropic API and return the raw text response.

    This function is intentionally thin so tests can mock it in isolation.

    Args:
        prompt: The user-turn message to send to the model.

    Returns:
        Raw text of the first content block in the model response.

    Raises:
        RuntimeError: If ``ANTHROPIC_API_KEY`` is not configured.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured. "
            "Add ANTHROPIC_API_KEY=<key> to backend/.env to enable AI proposals."
        )
    import anthropic  # imported here to keep startup fast when key is absent

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    block = message.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        raise ValueError(f"Unexpected AI response block type: {type(block).__name__}")
    return block.text


async def generate_proposal(session: AsyncSession) -> BalanceProposal:
    """Generate a balance proposal using the AI and persist it with status ``pending``.

    Reads current unit and upgrade definitions from the database, builds a prompt,
    calls the Anthropic API, parses the response, and saves a new BalanceProposal.
    The caller must commit the session.

    Args:
        session: Active async database session (within a transaction).

    Returns:
        Newly created BalanceProposal with status ``pending``.

    Raises:
        RuntimeError: If ``ANTHROPIC_API_KEY`` is not set.
        ValueError: If the AI returns an unparseable response.
    """
    unit_defs = await UnitDefinitionRepository.get_all(session)
    upgrade_defs = await UpgradeDefinitionRepository.get_all(session)

    prompt = build_prompt(unit_defs, upgrade_defs)
    response_text = await _call_ai(prompt)
    changes, rationale = parse_ai_response(response_text)

    proposal = BalanceProposal(changes_json=changes, rationale=rationale)
    session.add(proposal)
    await session.flush()
    return proposal


async def apply_proposal(session: AsyncSession, proposal: BalanceProposal) -> int:
    """Apply an approved balance proposal directly to unit/upgrade definition rows.

    Each change in ``proposal.changes_json`` is validated against the allow-list
    of fields before being written to the database.  The proposal status is set
    to ``applied`` on success.  The caller must commit the session.

    Args:
        session: Active async database session (within a transaction).
        proposal: The BalanceProposal to apply; must have status ``approved``.

    Returns:
        Number of changes successfully applied to the database.

    Raises:
        ValueError: If the proposal status is not ``approved``.
    """
    if proposal.status != "approved":
        raise ValueError(
            f"Proposal {proposal.id} cannot be applied (status: {proposal.status}). "
            "Approve it first."
        )

    applied = 0
    for change in proposal.changes_json:
        entity = change.get("entity", "")
        entity_id = str(change.get("id", ""))
        field = str(change.get("field", ""))
        raw_value = change.get("new_value", "")

        try:
            decimal_value = Decimal(str(raw_value))
        except InvalidOperation:
            logger.warning("Skipping change — invalid decimal for field '%s': %s", field, raw_value)
            continue

        if entity == "unit" and field in ALLOWED_UNIT_FIELDS:
            unit = await UnitDefinitionRepository.get_by_id(session, entity_id)
            if unit is not None:
                setattr(unit, field, decimal_value)
                applied += 1
            else:
                logger.warning("Unit '%s' not found, skipping change", entity_id)

        elif entity == "upgrade" and field in ALLOWED_UPGRADE_FIELDS:
            upgrade = await UpgradeDefinitionRepository.get_by_id(session, entity_id)
            if upgrade is not None:
                setattr(upgrade, field, decimal_value)
                applied += 1
            else:
                logger.warning("Upgrade '%s' not found, skipping change", entity_id)

        else:
            logger.warning("Disallowed field '%s' for entity '%s', skipping", field, entity)

    proposal.status = "applied"
    proposal.resolved_at = datetime.now(UTC)
    await session.flush()
    return applied
