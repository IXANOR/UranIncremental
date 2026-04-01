"""HMAC-based snapshot signing and verification for player game state.

A snapshot signature is stored in ``player_state.snapshot_signature`` and
re-computed on every tick.  Tampering with wallet or unit amounts invalidates
the signature and causes the tick to be rejected.
"""

import hashlib
import hmac
import json

from app.core.config import settings
from app.core.time_utils import ensure_utc
from app.db.models.player_state import PlayerState
from app.db.models.unit import PlayerUnit
from app.db.models.wallet import Wallet


def _canonical_payload(
    player: PlayerState,
    wallet: Wallet,
    units: list[PlayerUnit],
) -> bytes:
    """Build a deterministic, canonical JSON payload from game state.

    Args:
        player: Current player state row.
        wallet: Player's wallet row.
        units: All PlayerUnit rows for the player.

    Returns:
        UTF-8 encoded canonical JSON string for HMAC input.
    """
    payload = {
        "player_id": str(player.id),
        "version": player.version,
        "last_tick_at": ensure_utc(player.last_tick_at).isoformat(),
        "prestige_count": player.prestige_count,
        "wallet": {
            "energy_drink": str(wallet.energy_drink),
            "u238": str(wallet.u238),
            "u235": str(wallet.u235),
            "u233": str(wallet.u233),
            "meta_isotopes": str(wallet.meta_isotopes),
        },
        "units": {u.unit_id: u.amount_owned for u in sorted(units, key=lambda x: x.unit_id)},
    }
    return json.dumps(payload, sort_keys=True).encode()


def sign(
    player: PlayerState,
    wallet: Wallet,
    units: list[PlayerUnit],
) -> str:
    """Generate an HMAC-SHA256 signature for the current game state.

    Args:
        player: Current player state row.
        wallet: Player's wallet row.
        units: All PlayerUnit rows for the player.

    Returns:
        Hex-encoded HMAC digest string.
    """
    payload = _canonical_payload(player, wallet, units)
    return hmac.new(
        settings.snapshot_secret.encode(),
        payload,
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify(
    player: PlayerState,
    wallet: Wallet,
    units: list[PlayerUnit],
) -> bool:
    """Verify that the stored snapshot signature matches the current state.

    Uses ``hmac.compare_digest`` to prevent timing attacks.

    Args:
        player: Current player state row (``snapshot_signature`` is read from here).
        wallet: Player's wallet row.
        units: All PlayerUnit rows for the player.

    Returns:
        True if the signature is valid, False otherwise.
    """
    expected = sign(player, wallet, units)
    return hmac.compare_digest(player.snapshot_signature, expected)
