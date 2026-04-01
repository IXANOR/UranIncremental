"""Unit tests for balance_ai_service — pure-function coverage (no DB, no API)."""

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.services.balance_ai_service import (
    ALLOWED_UNIT_FIELDS,
    ALLOWED_UPGRADE_FIELDS,
    build_prompt,
    parse_ai_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit(
    id: str,
    tier: int = 1,
    production_resource: str = "energy_drink",
    production_rate_per_sec: str = "0.3",
    base_cost_currency: str = "energy_drink",
    base_cost_amount: str = "15",
    cost_growth_factor: str = "1.15",
) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.tier = tier
    u.production_resource = production_resource
    u.production_rate_per_sec = Decimal(production_rate_per_sec)
    u.base_cost_currency = base_cost_currency
    u.base_cost_amount = Decimal(base_cost_amount)
    u.cost_growth_factor = Decimal(cost_growth_factor)
    return u


def _make_upgrade(
    id: str,
    cost_currency: str = "energy_drink",
    cost_amount: str = "200",
    effect_type: str = "prod_mult",
    effect_value: str = "1.10",
    is_repeatable: bool = False,
) -> MagicMock:
    u = MagicMock()
    u.id = id
    u.cost_currency = cost_currency
    u.cost_amount = Decimal(cost_amount)
    u.effect_type = effect_type
    u.effect_value = Decimal(effect_value)
    u.is_repeatable = is_repeatable
    return u


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_contains_unit_ids() -> None:
    """Prompt must include all unit IDs so the AI knows what to tweak."""
    units = [_make_unit("barrel"), _make_unit("mini_reactor")]
    upgrades = [_make_upgrade("barrel_opt_mk1")]
    prompt = build_prompt(units, upgrades)
    assert "barrel" in prompt
    assert "mini_reactor" in prompt


def test_build_prompt_contains_upgrade_ids() -> None:
    """Prompt must include all upgrade IDs."""
    units = [_make_unit("barrel")]
    upgrades = [_make_upgrade("barrel_opt_mk1"), _make_upgrade("reactor_tuning_mk1")]
    prompt = build_prompt(units, upgrades)
    assert "barrel_opt_mk1" in prompt
    assert "reactor_tuning_mk1" in prompt


def test_build_prompt_contains_numeric_values() -> None:
    """Prompt must expose current production rates and costs."""
    units = [_make_unit("barrel", production_rate_per_sec="0.3", base_cost_amount="15")]
    upgrades: list[MagicMock] = []
    prompt = build_prompt(units, upgrades)
    assert "0.3" in prompt
    assert "15" in prompt


def test_build_prompt_contains_balance_constraints() -> None:
    """Prompt must mention the two key balance constraints."""
    prompt = build_prompt([], [])
    assert "120" in prompt  # mini_reactor reachable in 120s
    assert "4 min" in prompt  # centrifuge t2 gate


# ---------------------------------------------------------------------------
# parse_ai_response
# ---------------------------------------------------------------------------


def test_parse_valid_response_returns_changes_and_rationale() -> None:
    """Valid JSON with 'changes' and 'rationale' keys is parsed correctly."""
    payload = {
        "changes": [
            {
                "entity": "unit",
                "id": "barrel",
                "field": "production_rate_per_sec",
                "old_value": "0.3",
                "new_value": "0.35",
                "reason": "Small boost",
            }
        ],
        "rationale": "Barrel feels a bit slow.",
    }
    changes, rationale = parse_ai_response(json.dumps(payload))
    assert len(changes) == 1
    assert changes[0]["id"] == "barrel"
    assert changes[0]["new_value"] == "0.35"
    assert "slow" in rationale


def test_parse_response_strips_markdown_fences() -> None:
    """Response wrapped in ```json ... ``` fences is handled correctly."""
    payload = {"changes": [], "rationale": "No changes needed."}
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    changes, rationale = parse_ai_response(wrapped)
    assert changes == []
    assert "No changes" in rationale


def test_parse_response_skips_malformed_items() -> None:
    """Items missing required keys are silently skipped."""
    payload = {
        "changes": [
            {"entity": "unit", "id": "barrel"},  # missing field/old_value/new_value
            {
                "entity": "unit",
                "id": "mini_reactor",
                "field": "production_rate_per_sec",
                "old_value": "1.5",
                "new_value": "1.6",
            },
        ],
        "rationale": "Mixed.",
    }
    changes, _ = parse_ai_response(json.dumps(payload))
    assert len(changes) == 1
    assert changes[0]["id"] == "mini_reactor"


def test_parse_response_skips_unknown_entity_type() -> None:
    """Items with entity types other than 'unit'/'upgrade' are skipped."""
    payload = {
        "changes": [
            {
                "entity": "player",
                "id": "prestige",
                "field": "prestige_count",
                "old_value": "0",
                "new_value": "10",
            }
        ],
        "rationale": "Cheat attempt.",
    }
    changes, _ = parse_ai_response(json.dumps(payload))
    assert changes == []


def test_parse_invalid_json_raises_value_error() -> None:
    """Non-JSON input raises ValueError."""
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_ai_response("this is not json")


def test_parse_missing_changes_key_raises_value_error() -> None:
    """JSON without 'changes' key raises ValueError."""
    with pytest.raises(ValueError, match="missing 'changes'"):
        parse_ai_response(json.dumps({"rationale": "oops"}))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_allowed_unit_fields_covers_numeric_fields() -> None:
    """ALLOWED_UNIT_FIELDS must include the three tuneable numeric fields."""
    assert "production_rate_per_sec" in ALLOWED_UNIT_FIELDS
    assert "base_cost_amount" in ALLOWED_UNIT_FIELDS
    assert "cost_growth_factor" in ALLOWED_UNIT_FIELDS


def test_allowed_upgrade_fields_excludes_design_fields() -> None:
    """survives_prestige and is_repeatable are not AI-tuneable."""
    assert "survives_prestige" not in ALLOWED_UPGRADE_FIELDS
    assert "is_repeatable" not in ALLOWED_UPGRADE_FIELDS
