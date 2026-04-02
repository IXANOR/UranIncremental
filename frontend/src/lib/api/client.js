/**
 * API client — all calls inject X-Player-ID from localStorage.
 */

const BASE = '/api/v1';

function playerId() {
  return localStorage.getItem('player_id') ?? '';
}

function headers() {
  return {
    'Content-Type': 'application/json',
    'X-Player-ID': playerId(),
  };
}

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = body.detail ?? `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return res.json();
}

export async function startGame() {
  const res = await fetch(`${BASE}/game/start`, { method: 'POST' });
  return handle(res);
}

export async function fetchState() {
  const res = await fetch(`${BASE}/game/state`, { headers: headers() });
  return handle(res);
}

export async function buyUnit(unit_id, quantity = 1) {
  const res = await fetch(`${BASE}/economy/buy-unit`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ unit_id, quantity }),
  });
  return handle(res);
}

export async function buyUpgrade(upgrade_id) {
  const res = await fetch(`${BASE}/economy/buy-upgrade`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ upgrade_id }),
  });
  return handle(res);
}

export async function claimOffline() {
  const res = await fetch(`${BASE}/time/claim-offline`, {
    method: 'POST',
    headers: headers(),
  });
  return handle(res);
}

export async function simulateTime(seconds) {
  const res = await fetch(`${BASE}/test/simulate-time`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ seconds }),
  });
  return handle(res);
}

export async function doPrestige() {
  const res = await fetch(`${BASE}/game/prestige`, {
    method: 'POST',
    headers: headers(),
  });
  return handle(res);
}

export async function clickReactor() {
  const res = await fetch(`${BASE}/game/click`, {
    method: 'POST',
    headers: headers(),
  });
  return handle(res);
}
