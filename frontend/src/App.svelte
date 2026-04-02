<script>
  import { onMount, onDestroy } from 'svelte';
  import { startGame, fetchState, claimOffline, doPrestige, clickReactor } from './lib/api/client.js';
  import { gameState, error, offlineGains, canPrestige, player, testMode } from './lib/stores/game.js';
  import WalletHUD from './lib/components/WalletHUD.svelte';
  import UnitList from './lib/components/UnitList.svelte';
  import UpgradeList from './lib/components/UpgradeList.svelte';
  import CheatPanel from './lib/components/CheatPanel.svelte';

  const POLL_MS = 500;
  let interval;
  let offlinePending = false;
  let prestigeConfirm = false;
  let actionBusy = false;

  // Click minigame state
  let clickAnimating = false;
  let lastClickGained = null;
  let clickAnimTimer;

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

  async function handlePrestige() {
    if (!prestigeConfirm) { prestigeConfirm = true; return; }
    prestigeConfirm = false;
    actionBusy = true;
    try {
      await doPrestige();
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
      clickAnimating = true;
      clearTimeout(clickAnimTimer);
      clickAnimTimer = setTimeout(() => { clickAnimating = false; }, 300);
    } catch (e) {
      // rate limit or other error — silently ignore to avoid spamming error banner
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

  <div class="prestige-info">
    <span class="pi-label">✦ Prestige</span>
    <span class="pi-sep">—</span>
    <span class="pi-item">reset: waluta, jednostki i nieutrwalone ulepszenia</span>
    <span class="pi-sep">·</span>
    <span class="pi-item">nagroda: <strong>+20% produkcji na stałe</strong> (kumuluje się)</span>
    <span class="pi-sep">·</span>
    <span class="pi-item">zostają: ulepszenia oznaczone <em>↺ trwałe</em></span>
  </div>

  <div class="actions">
    <div class="click-section">
      <button
        class="btn-click"
        class:animating={clickAnimating}
        on:click={handleClick}
      >
        ⚡ Klik!
      </button>
      {#if lastClickGained !== null}
        <span class="click-gain" class:pop={clickAnimating}>+{lastClickGained} ED</span>
      {/if}
    </div>

    {#if offlinePending}
      <button class="btn-action offline" disabled={actionBusy} on:click={handleClaimOffline}>
        📦 Odbierz nagrody offline
      </button>
    {/if}

    {#if $canPrestige}
      {#if prestigeConfirm}
        <span class="confirm-msg">Na pewno? Reset postępu!</span>
        <button class="btn-action prestige" disabled={actionBusy} on:click={handlePrestige}>
          ✦ POTWIERDŹ PRESTIGE
        </button>
        <button class="btn-cancel" on:click={() => (prestigeConfirm = false)}>Anuluj</button>
      {:else}
        <button class="btn-action prestige" disabled={actionBusy} on:click={handlePrestige}>
          ✦ Prestige
        </button>
      {/if}
    {/if}
  </div>

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
  .pi-item em { color: #f90; font-style: normal; }

  .actions {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .click-section {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn-click {
    background: #0a1a2a;
    color: #7ef;
    border: 1px solid #37a;
    border-radius: 6px;
    padding: 8px 20px;
    cursor: pointer;
    font-family: inherit;
    font-size: 1rem;
    font-weight: bold;
    transition: transform 0.1s ease, background 0.1s ease;
  }
  .btn-click:hover { background: #0e2236; }
  .btn-click.animating {
    transform: scale(0.92);
    background: #1a3a5a;
  }

  .click-gain {
    color: #7ef;
    font-size: 0.85rem;
    font-weight: bold;
    opacity: 0;
    transition: opacity 0.15s ease;
  }
  .click-gain.pop {
    opacity: 1;
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
