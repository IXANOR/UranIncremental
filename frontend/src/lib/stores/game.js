import { writable, derived } from 'svelte/store';

export const gameState = writable(null);   // full GET /state response
export const error = writable(null);        // last API error string
export const offlineGains = writable(null); // result of claim-offline

export const wallet = derived(gameState, ($s) => $s?.wallet ?? null);
export const units = derived(gameState, ($s) => $s?.units ?? []);
export const upgrades = derived(gameState, ($s) => $s?.upgrades ?? []);
export const player = derived(gameState, ($s) => $s?.player ?? null);

export const prestigeNextRequirement = derived(gameState, ($s) =>
  $s?.prestige_next_requirement != null ? parseFloat($s.prestige_next_requirement) : 1
);

/** true when u238 >= prestige_next_requirement */
export const canPrestige = derived([wallet, prestigeNextRequirement], ([$w, $req]) => {
  if (!$w) return false;
  return parseFloat($w.u238) >= $req;
});

export const testMode = derived(gameState, ($s) => $s?.test_mode === true);
