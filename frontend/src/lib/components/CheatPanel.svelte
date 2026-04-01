<script>
  import { simulateTime } from '../api/client.js';
  import { error, gameState } from '../stores/game.js';
  import { fetchState } from '../api/client.js';

  let seconds = 60;
  let busy = false;
  let lastResult = null;

  async function handleSimulate() {
    if (!seconds || seconds <= 0) return;
    busy = true;
    lastResult = null;
    try {
      const res = await simulateTime(seconds);
      lastResult = res;
      gameState.set(await fetchState());
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      busy = false;
    }
  }
</script>

<section class="cheat-panel">
  <div class="cheat-title">⚙ CHEAT MENU <span class="test-badge">TEST_MODE</span></div>

  <div class="row">
    <label for="sim-seconds">Simulate time:</label>
    <input
      id="sim-seconds"
      type="number"
      min="1"
      max="999999"
      bind:value={seconds}
      on:keydown={(e) => e.key === 'Enter' && handleSimulate()}
    />
    <span class="unit">s</span>
    <button class="btn-cheat" disabled={busy} on:click={handleSimulate}>
      {busy ? '...' : '▶ Run'}
    </button>
    {#if lastResult}
      <span class="result">
        ✓ {lastResult.simulated_seconds}s symulowane, wersja stanu: {lastResult.new_state_version}
      </span>
    {/if}
  </div>

  <div class="shortcuts">
    <button class="btn-preset" on:click={() => { seconds = 60; handleSimulate(); }}>1 min</button>
    <button class="btn-preset" on:click={() => { seconds = 600; handleSimulate(); }}>10 min</button>
    <button class="btn-preset" on:click={() => { seconds = 3600; handleSimulate(); }}>1 h</button>
    <button class="btn-preset" on:click={() => { seconds = 86400; handleSimulate(); }}>1 d</button>
  </div>
</section>

<style>
  .cheat-panel {
    background: #110a00;
    border: 1px solid #543;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 14px;
  }
  .cheat-title {
    font-size: 0.75rem;
    color: #a63;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .test-badge {
    background: #a63;
    color: #000;
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: bold;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 6px;
  }
  label { color: #888; font-size: 0.85rem; }
  input[type="number"] {
    width: 80px;
    background: #1a1000;
    border: 1px solid #543;
    color: #fa8;
    border-radius: 3px;
    padding: 3px 6px;
    font-family: inherit;
    font-size: 0.9rem;
  }
  .unit { color: #666; font-size: 0.85rem; }
  .btn-cheat {
    background: #2a1500;
    color: #fa8;
    border: 1px solid #a63;
    border-radius: 4px;
    padding: 4px 14px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85rem;
  }
  .btn-cheat:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-cheat:not(:disabled):hover { background: #3a2000; }
  .result { color: #6a4; font-size: 0.8rem; }
  .shortcuts { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn-preset {
    background: #1a0d00;
    color: #a63;
    border: 1px solid #543;
    border-radius: 3px;
    padding: 3px 10px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.8rem;
  }
  .btn-preset:hover { background: #2a1500; }
</style>
