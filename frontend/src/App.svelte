<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { startGame, fetchState, claimOffline, doPrestige, clickReactor } from './lib/api/client.js';
  import { gameState, error, offlineGains, canPrestige, player, testMode, prestigeOptions } from './lib/stores/game.js';
  import WalletHUD from './lib/components/WalletHUD.svelte';
  import UnitList from './lib/components/UnitList.svelte';
  import UpgradeList from './lib/components/UpgradeList.svelte';
  import CheatPanel from './lib/components/CheatPanel.svelte';
  import Laboratorium from './lib/components/Laboratorium.svelte';

  const POLL_MS = 500;
  let interval;
  let offlinePending = false;
  let prestigeConfirm = null; // null | { count, currency } — pending confirmation
  let actionBusy = false;

  // Click minigame state
  let clickAnimating = false;
  let lastClickGained = null;
  let clickAnimTimer;
  let clickKey = 0; // incremented each click to restart float animation

  async function init() {
    let pid = localStorage.getItem('player_id');
    if (!pid) {
      try {
        const res = await startGame();
        pid = res.player_id;
        localStorage.setItem('player_id', pid);
      } catch (e) {
        error.set('Nie można uruchomić gry: ' + e.message);
        return;
      }
    }
    await refresh();
    interval = setInterval(refresh, POLL_MS);
  }

  async function refresh() {
    try {
      const state = await fetchState();
      gameState.set(state);
      error.set(null);
      const lastTick = new Date(state.player.last_tick_at).getTime();
      offlinePending = (Date.now() - lastTick) > 60_000;
    } catch (e) {
      error.set(e.message);
    }
  }

  async function handleClaimOffline() {
    actionBusy = true;
    try {
      const gains = await claimOffline();
      offlineGains.set(gains);
      gameState.set(await fetchState());
      offlinePending = false;
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      actionBusy = false;
    }
  }

  function requestPrestige(count, currency) {
    prestigeConfirm = { count, currency };
  }

  async function handlePrestige() {
    if (!prestigeConfirm) return;
    const { count, currency } = prestigeConfirm;
    prestigeConfirm = null;
    actionBusy = true;
    try {
      await doPrestige(count, currency);
      gameState.set(await fetchState());
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      actionBusy = false;
    }
  }

  async function handleClick() {
    try {
      const res = await clickReactor();
      lastClickGained = parseFloat(res.gained).toFixed(2);
      // Reset animation so it re-triggers on every click
      clickAnimating = false;
      await tick();
      clickAnimating = true;
      clickKey += 1;
      clearTimeout(clickAnimTimer);
      clickAnimTimer = setTimeout(() => { clickAnimating = false; }, 400);
    } catch (e) {
      // rate limit silently ignored
    }
  }

  function dismissOfflineGains() { offlineGains.set(null); }

  onMount(init);
  onDestroy(() => { clearInterval(interval); clearTimeout(clickAnimTimer); });
</script>

<main>
  <header>
    <h1>☢ UranIncremental</h1>
    <div class="tagline">Energetyk + Pluton = Postęp</div>
  </header>

  {#if $error}
    <div class="banner error">{$error}</div>
  {/if}

  {#if $offlineGains}
    <div class="banner offline-gains">
      <strong>Nagrody offline odebrane!</strong>
      Czas: {$offlineGains.simulated_seconds}s
      {#if $offlineGains.cap_applied}<span class="cap">(limit zastosowany)</span>{/if}
      <button class="btn-dismiss" on:click={dismissOfflineGains}>✕</button>
    </div>
  {/if}

  {#if $testMode}
    <CheatPanel />
  {/if}

  <WalletHUD />

  <div class="click-hero">
    <div class="click-float-wrap">
      {#key clickKey}
        {#if lastClickGained !== null}
          <span class="click-float">+{lastClickGained} ED</span>
        {/if}
      {/key}
    </div>
    <button
      class="btn-reactor"
      class:animating={clickAnimating}
      on:click={handleClick}
    >
      <span class="reactor-icon">☢</span>
      <span class="reactor-label">KLIK!</span>
      {#if $player}
        <span class="reactor-sub">×{$player.click_count}</span>
      {/if}
    </button>
  </div>

  <div class="prestige-info">
    <span class="pi-label">✦ Prestige</span>
    <span class="pi-sep">—</span>
    <span class="pi-item">reset: waluta, jednostki i nieutrwalone ulepszenia</span>
    <span class="pi-sep">·</span>
    <span class="pi-item">nagroda: <strong>+20% produkcji na stałe</strong> (kumuluje się)</span>
    {#if $prestigeOptions.length > 0}
      <span class="pi-sep">·</span>
      <span class="pi-item pi-costs">
        {#each $prestigeOptions as opt}
          <span class="pi-opt" class:pi-affordable={opt.can_afford}>
            {opt.count}×:
            {parseFloat(opt.cost).toFixed(0)}
            {opt.currency === 'meta_isotopes' ? 'META' : opt.currency.toUpperCase()}
          </span>
        {/each}
      </span>
    {/if}
  </div>

  <div class="actions">
    {#if offlinePending}
      <button class="btn-action offline" disabled={actionBusy} on:click={handleClaimOffline}>
        📦 Odbierz nagrody offline
      </button>
    {/if}

    {#if $prestigeOptions.some((o) => o.can_afford)}
      {#if prestigeConfirm}
        <div class="prestige-confirm">
          <span class="confirm-msg">
            Na pewno? Reset postępu! ({prestigeConfirm.count}× za {prestigeConfirm.currency.replace('_', ' ')})
          </span>
          <button class="btn-action prestige" disabled={actionBusy} on:click={handlePrestige}>
            ✦ POTWIERDŹ
          </button>
          <button class="btn-cancel" on:click={() => (prestigeConfirm = null)}>Anuluj</button>
        </div>
      {:else}
        <div class="prestige-options">
          {#each $prestigeOptions as opt}
            {#if opt.can_afford}
              <button
                class="btn-prestige-opt"
                disabled={actionBusy}
                on:click={() => requestPrestige(opt.count, opt.currency)}
                title="{opt.count}× za {parseFloat(opt.cost).toFixed(0)} {opt.currency.replace('_', ' ')}"
              >
                ✦ {opt.count}×
                <span class="opt-cost">
                  {parseFloat(opt.cost).toFixed(0)}
                  {opt.currency === 'meta_isotopes' ? 'META' : opt.currency.toUpperCase()}
                </span>
              </button>
            {/if}
          {/each}
        </div>
      {/if}
    {/if}
  </div>

  <Laboratorium />

  <div class="columns">
    <div class="col">
      <UnitList />
    </div>
    <div class="col">
      <UpgradeList />
    </div>
  </div>

  {#if $player}
    <footer>
      kliknięcia: {$player.click_count} &nbsp;|&nbsp;
      wersja stanu: {$player.version} &nbsp;|&nbsp;
      eff. offline: {($player.offline_efficiency * 100).toFixed(0)}% &nbsp;|&nbsp;
      cap: {($player.offline_cap_seconds / 3600).toFixed(1)}h &nbsp;|&nbsp;
      mnożnik prestige: {(1.20 ** $player.prestige_count).toFixed(3)}×
    </footer>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    background: #0a0a0a;
    color: #ccc;
    font-family: 'Courier New', monospace;
    font-size: 14px;
  }
  :global(*, *::before, *::after) { box-sizing: border-box; }

  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 16px;
  }

  header {
    border-bottom: 1px solid #2a2;
    margin-bottom: 14px;
    padding-bottom: 8px;
  }
  h1 {
    margin: 0;
    color: #7ef;
    font-size: 1.4rem;
    letter-spacing: 0.05em;
  }
  .tagline { color: #454; font-size: 0.75rem; }

  .banner {
    border-radius: 4px;
    padding: 8px 12px;
    margin-bottom: 12px;
    font-size: 0.85rem;
  }
  .error { background: #2a0000; border: 1px solid #700; color: #f88; }
  .offline-gains {
    background: #0a200a;
    border: 1px solid #2a6;
    color: #7ef;
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .cap { color: #f90; }
  .btn-dismiss {
    margin-left: auto;
    background: transparent;
    border: none;
    color: #888;
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
  }

  .prestige-info {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: baseline;
    background: #0d0a00;
    border: 1px solid #432;
    border-radius: 4px;
    padding: 6px 12px;
    margin-bottom: 10px;
    font-size: 0.78rem;
    color: #876;
  }
  .pi-label { color: #a73; font-weight: bold; letter-spacing: 0.05em; }
  .pi-sep { color: #432; }
  .pi-item strong { color: #fa8; }

  .click-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 10px 0 14px;
    position: relative;
  }

  .click-float-wrap {
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: visible;
    pointer-events: none;
  }

  @keyframes float-up {
    0%   { transform: translateY(0);    opacity: 1; }
    60%  { transform: translateY(-18px); opacity: 0.9; }
    100% { transform: translateY(-32px); opacity: 0; }
  }

  .click-float {
    color: #7ef;
    font-size: 1rem;
    font-weight: bold;
    animation: float-up 0.55s ease-out forwards;
  }

  @keyframes reactor-glow {
    0%   { box-shadow: 0 0 0 0 rgba(50, 220, 120, 0.55); }
    60%  { box-shadow: 0 0 0 18px rgba(50, 220, 120, 0.1); }
    100% { box-shadow: 0 0 0 26px rgba(50, 220, 120, 0); }
  }

  .btn-reactor {
    background: radial-gradient(ellipse at center, #0d2a18 0%, #060e0a 70%);
    color: #5dde90;
    border: 2px solid #1a6035;
    border-radius: 50%;
    width: 108px;
    height: 108px;
    cursor: pointer;
    font-family: inherit;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    transition: transform 0.1s ease, border-color 0.1s ease;
    position: relative;
    outline: none;
  }
  .btn-reactor:hover {
    border-color: #2a9050;
    background: radial-gradient(ellipse at center, #112e1e 0%, #080f0b 70%);
  }
  .btn-reactor.animating {
    transform: scale(0.91);
    border-color: #4dde80;
    animation: reactor-glow 0.4s ease-out;
  }
  .reactor-icon {
    font-size: 1.8rem;
    line-height: 1;
  }
  .reactor-label {
    font-size: 0.7rem;
    font-weight: bold;
    letter-spacing: 0.12em;
    color: #7ef;
  }
  .reactor-sub {
    font-size: 0.62rem;
    color: #3a7;
    letter-spacing: 0.05em;
  }

  .actions {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .btn-action {
    padding: 7px 18px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    transition: opacity 0.15s;
  }
  .btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
  .offline { background: #1a2a3a; color: #7ef; border: 1px solid #37a; }
  .offline:not(:disabled):hover { background: #1e3348; }
  .prestige { background: #2a1a00; color: #f90; border: 1px solid #860; }
  .prestige:not(:disabled):hover { background: #3a2500; }
  .confirm-msg { color: #f55; font-size: 0.85rem; }
  .btn-cancel {
    background: transparent;
    border: 1px solid #555;
    color: #888;
    border-radius: 4px;
    padding: 6px 12px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85rem;
  }

  .prestige-options { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn-prestige-opt {
    background: #2a1a00;
    color: #f90;
    border: 1px solid #860;
    border-radius: 4px;
    padding: 5px 12px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: bold;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    transition: background 0.15s;
  }
  .btn-prestige-opt:not(:disabled):hover { background: #3a2500; }
  .btn-prestige-opt:disabled { opacity: 0.4; cursor: not-allowed; }
  .opt-cost { font-size: 0.7rem; color: #c73; font-weight: normal; }
  .prestige-confirm { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  .pi-costs { display: flex; gap: 8px; }
  .pi-opt { color: #554; }
  .pi-opt.pi-affordable { color: #fa8; font-weight: bold; }

  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  @media (max-width: 640px) {
    .columns { grid-template-columns: 1fr; }
  }

  footer {
    margin-top: 20px;
    color: #3a3;
    font-size: 0.75rem;
    border-top: 1px solid #1a1a1a;
    padding-top: 8px;
  }
</style>
