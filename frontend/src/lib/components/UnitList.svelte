<script>
  import { units, wallet } from '../stores/game.js';
  import { buyUnit } from '../api/client.js';
  import { error, gameState } from '../stores/game.js';

  let buying = {};

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  function canAfford(unit) {
    if (!$wallet) return false;
    const bal = parseFloat($wallet[unit.base_cost_currency] ?? 0);
    return bal >= parseFloat(unit.next_cost);
  }

  async function handleBuy(unit_id) {
    buying = { ...buying, [unit_id]: true };
    try {
      await buyUnit(unit_id, 1);
      // state will be refreshed by the polling interval; force immediate refresh
      const { fetchState } = await import('../api/client.js');
      gameState.set(await fetchState());
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      buying = { ...buying, [unit_id]: false };
    }
  }

  function resourceLabel(res) {
    const map = { energy_drink: 'ED', u238: 'U-238', u235: 'U-235', u233: 'U-233', meta_isotopes: 'META' };
    return map[res] ?? res;
  }
</script>

<section class="panel">
  <h2>Jednostki</h2>
  {#each $units as unit (unit.unit_id)}
    <div class="row" class:tier2={unit.tier === 2}>
      <div class="info">
        <span class="name">{unit.name}</span>
        <span class="owned">× {unit.amount_owned}</span>
        <span class="rate">+{fmt(unit.production_rate_per_sec)} {resourceLabel(unit.production_resource)}/s</span>
      </div>
      <div class="buy-col">
        <span class="cost" class:cant={!canAfford(unit)}>
          {fmt(unit.next_cost)} {resourceLabel(unit.base_cost_currency)}
        </span>
        <button
          class="btn-buy"
          disabled={!canAfford(unit) || buying[unit.unit_id]}
          on:click={() => handleBuy(unit.unit_id)}
        >
          {buying[unit.unit_id] ? '...' : 'Kup'}
        </button>
      </div>
    </div>
  {/each}
</section>

<style>
  .panel { margin-bottom: 20px; }
  h2 { color: #5a5; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 8px; }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #111;
    border: 1px solid #222;
    border-radius: 4px;
    padding: 8px 12px;
    margin-bottom: 4px;
  }
  .row.tier2 { border-color: #354; }
  .info { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
  .name { font-weight: bold; color: #eee; }
  .owned { color: #7ef; font-size: 0.85rem; }
  .rate { color: #7f7; font-size: 0.8rem; }
  .buy-col { display: flex; align-items: center; gap: 8px; }
  .cost { color: #aaa; font-size: 0.85rem; white-space: nowrap; }
  .cost.cant { color: #633; }
  .btn-buy {
    background: #1a3a1a;
    color: #7ef;
    border: 1px solid #2a6;
    border-radius: 4px;
    padding: 4px 12px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: background 0.15s;
  }
  .btn-buy:disabled { opacity: 0.35; cursor: not-allowed; }
  .btn-buy:not(:disabled):hover { background: #254; }
</style>
