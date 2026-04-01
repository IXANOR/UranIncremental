"""Unit tests for snapshot_sign_service."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.services import snapshot_sign_service


def _make_player(
    player_id: str = "00000000-0000-0000-0000-000000000001",
    version: int = 1,
    prestige_count: int = 0,
    last_tick_at: datetime | None = None,
    snapshot_signature: str = "",
) -> MagicMock:
    """Build a minimal mock PlayerState for signature tests."""
    p = MagicMock()
    p.id = player_id
    p.version = version
    p.prestige_count = prestige_count
    p.last_tick_at = last_tick_at or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    p.snapshot_signature = snapshot_signature
    return p


def _make_wallet(
    energy_drink: str = "50",
    u238: str = "0",
    u235: str = "0",
    u233: str = "0",
    meta_isotopes: str = "0",
) -> MagicMock:
    """Build a minimal mock Wallet for signature tests."""
    w = MagicMock()
    w.energy_drink = Decimal(energy_drink)
    w.u238 = Decimal(u238)
    w.u235 = Decimal(u235)
    w.u233 = Decimal(u233)
    w.meta_isotopes = Decimal(meta_isotopes)
    return w


def _make_unit(unit_id: str, amount_owned: int = 0) -> MagicMock:
    """Build a minimal mock PlayerUnit for signature tests."""
    u = MagicMock()
    u.unit_id = unit_id
    u.amount_owned = amount_owned
    return u


# ---------------------------------------------------------------------------
# sign()
# ---------------------------------------------------------------------------


def test_sign_returns_non_empty_hex_string() -> None:
    """sign() must return a non-empty hex digest."""
    player = _make_player()
    wallet = _make_wallet()
    sig = snapshot_sign_service.sign(player, wallet, [])
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex = 64 chars
    assert all(c in "0123456789abcdef" for c in sig)


def test_sign_is_deterministic() -> None:
    """The same inputs always produce the same signature."""
    player = _make_player()
    wallet = _make_wallet()
    sig1 = snapshot_sign_service.sign(player, wallet, [])
    sig2 = snapshot_sign_service.sign(player, wallet, [])
    assert sig1 == sig2


def test_sign_changes_when_wallet_changes() -> None:
    """Changing wallet.energy_drink produces a different signature."""
    player = _make_player()
    wallet_a = _make_wallet(energy_drink="50")
    wallet_b = _make_wallet(energy_drink="9999")
    assert snapshot_sign_service.sign(player, wallet_a, []) != snapshot_sign_service.sign(
        player, wallet_b, []
    )


def test_sign_changes_when_version_changes() -> None:
    """Bumping player.version invalidates any previously computed signature."""
    wallet = _make_wallet()
    player_v1 = _make_player(version=1)
    player_v2 = _make_player(version=2)
    assert snapshot_sign_service.sign(player_v1, wallet, []) != snapshot_sign_service.sign(
        player_v2, wallet, []
    )


def test_sign_changes_when_units_change() -> None:
    """Adding a unit to the list changes the signature."""
    player = _make_player()
    wallet = _make_wallet()
    sig_empty = snapshot_sign_service.sign(player, wallet, [])
    sig_with_unit = snapshot_sign_service.sign(
        player, wallet, [_make_unit("barrel", amount_owned=5)]
    )
    assert sig_empty != sig_with_unit


def test_sign_unit_order_independent() -> None:
    """Units are sorted by unit_id, so order in the list does not matter."""
    player = _make_player()
    wallet = _make_wallet()
    units_ab = [_make_unit("barrel", 3), _make_unit("mini_reactor", 1)]
    units_ba = [_make_unit("mini_reactor", 1), _make_unit("barrel", 3)]
    assert snapshot_sign_service.sign(player, wallet, units_ab) == snapshot_sign_service.sign(
        player, wallet, units_ba
    )


# ---------------------------------------------------------------------------
# verify()
# ---------------------------------------------------------------------------


def test_verify_valid_signature_returns_true() -> None:
    """verify() returns True when the stored signature matches the current state."""
    player = _make_player()
    wallet = _make_wallet()
    units: list = []
    sig = snapshot_sign_service.sign(player, wallet, units)
    player.snapshot_signature = sig
    assert snapshot_sign_service.verify(player, wallet, units) is True


def test_verify_tampered_wallet_returns_false() -> None:
    """verify() returns False after wallet is modified post-signing."""
    player = _make_player()
    wallet = _make_wallet(energy_drink="50")
    units: list = []
    sig = snapshot_sign_service.sign(player, wallet, units)
    player.snapshot_signature = sig

    wallet.energy_drink = Decimal("99999")  # tamper
    assert snapshot_sign_service.verify(player, wallet, units) is False


def test_verify_tampered_unit_returns_false() -> None:
    """verify() returns False after a unit amount_owned is modified post-signing."""
    player = _make_player()
    wallet = _make_wallet()
    unit = _make_unit("barrel", amount_owned=5)
    sig = snapshot_sign_service.sign(player, wallet, [unit])
    player.snapshot_signature = sig

    unit.amount_owned = 1000  # tamper
    assert snapshot_sign_service.verify(player, wallet, [unit]) is False


def test_verify_empty_signature_returns_false() -> None:
    """verify() returns False when snapshot_signature is the empty string."""
    player = _make_player(snapshot_signature="")
    wallet = _make_wallet()
    assert snapshot_sign_service.verify(player, wallet, []) is False


def test_verify_wrong_signature_string_returns_false() -> None:
    """verify() returns False for an arbitrary wrong signature string."""
    player = _make_player(snapshot_signature="deadbeef" * 8)
    wallet = _make_wallet()
    assert snapshot_sign_service.verify(player, wallet, []) is False
