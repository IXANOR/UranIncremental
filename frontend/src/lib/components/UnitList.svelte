<script>
  import { units, wallet, gameState } from '../stores/game.js';
  import { buyUnit } from '../api/client.js';
  import { error } from '../stores/game.js';

  let buying = {};
  let expanded = {};
  let bulkMode = 1; // 1 | 10 | 100 | 'max'

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  function resourceLabel(res) {
    const map = {
      energy_drink: 'ED',
      u238: 'U-238',
      u235: 'U-235',
      u233: 'U-233',
      meta_isotopes: 'META',
    };
    return map[res] ?? res;
  }

  function fleetRate(unit) {
    return (
      parseFloat(unit.amount_owned) *
      parseFloat(unit.production_rate_per_sec) *
      parseFloat(unit.effective_multiplier)
    );
  }

  function bulkCost(unit) {
    if (bulkMode === 1) return parseFloat(unit.next_cost);
    if (bulkMode === 10) return parseFloat(unit.bulk_10_cost);
    if (bulkMode === 100) return parseFloat(unit.bulk_100_cost);
    // max: sum for max_affordable units — backend returns total via max_affordable
    // approximate cost: we'll just show max_affordable label; actual cost from bulk
    return parseFloat(unit.bulk_10_cost); // fallback display; canAfford handles logic
  }

  function bulkQuantity(unit) {
    if (bulkMode === 'max') return unit.max_affordable;
    return bulkMode;
  }

  function canAfford(unit) {
    if (!$wallet) return false;
    const bal = parseFloat($wallet[unit.base_cost_currency] ?? 0);
    if (bulkMode === 1) return bal >= parseFloat(unit.next_cost);
    if (bulkMode === 10) return bal >= parseFloat(unit.bulk_10_cost);
    if (bulkMode === 100) return bal >= parseFloat(unit.bulk_100_cost);
    if (bulkMode === 'max') return unit.max_affordable >= 1;
    return false;
  }

  function costLabel(unit) {
    if (bulkMode === 1) return `${fmt(unit.next_cost)} ${resourceLabel(unit.base_cost_currency)}`;
    if (bulkMode === 10)
      return `${fmt(unit.bulk_10_cost)} ${resourceLabel(unit.base_cost_currency)}`;
    if (bulkMode === 100)
      return `${fmt(unit.bulk_100_cost)} ${resourceLabel(unit.base_cost_currency)}`;
    if (bulkMode === 'max') {
      if (unit.max_affordable < 1) return 'za mało';
      return `×${unit.max_affordable}`;
    }
    return '';
  }

  function buyLabel(unit) {
    if (bulkMode === 'max') {
      if (unit.max_affordable < 1) return 'MAX';
      return `Kup ×${unit.max_affordable}`;
    }
    return `Kup ${bulkMode}×`;
  }

  async function handleBuy(unit_id) {
    const unit = $units.find((u) => u.unit_id === unit_id);
    if (!unit) return;
    const qty = bulkMode === 'max' ? unit.max_affordable : bulkMode;
    if (qty < 1) return;
    buying = { ...buying, [unit_id]: true };
    try {
      await buyUnit(unit_id, qty);
      const { fetchState } = await import('../api/client.js');
      gameState.set(await fetchState());
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      buying = { ...buying, [unit_id]: false };
    }
  }

  function toggleExpand(unit_id) {
    expanded = { ...expanded, [unit_id]: !expanded[unit_id] };
  }
</script>

<section class="panel">
  <div class="header-row">
    <h2>Jednostki</h2>
    <div class="bulk-controls">
      {#each [1, 10, 100, 'max'] as mode}
        <button
          class="btn-bulk"
          class:active={bulkMode === mode}
          on:click={() => (bulkMode = mode)}
        >
          {mode === 'max' ? 'MAX' : `${mode}×`}
        </button>
      {/each}
    </div>
  </div>

  {#each $units as unit (unit.unit_id)}
    <div class="card" class:tier2={unit.tier === 2} class:tier3plus={unit.tier >= 3}>
      <div
        class="card-row"
        role="button"
        tabindex="0"
        on:click={() => toggleExpand(unit.unit_id)}
        on:keydown={(e) => e.key === 'Enter' && toggleExpand(unit.unit_id)}
        title="Kliknij aby rozwinąć szczegóły"
      >
        <div class="info">
          <span class="name">{unit.name}</span>
          <span class="owned">×{unit.amount_owned}</span>
          <span class="rate">
            +{fmt(fleetRate(unit))} {resourceLabel(unit.production_resource)}/s
          </span>
        </div>
        <div class="buy-col">
          <span class="cost" class:cant={!canAfford(unit)}>{costLabel(unit)}</span>
          <button
            class="btn-buy"
            disabled={!canAfford(unit) || buying[unit.unit_id]}
            on:click|stopPropagation={() => handleBuy(unit.unit_id)}
          >
            {buying[unit.unit_id] ? '...' : buyLabel(unit)}
          </button>
          <span class="chevron">{expanded[unit.unit_id] ? '▲' : '▼'}</span>
        </div>
      </div>

      {#if expanded[unit.unit_id]}
        <div class="details">
          <div class="detail-row">
            <span class="dl">Posiadane:</span>
            <span class="dv owned">{unit.amount_owned} szt.</span>
          </div>
          <div class="detail-row">
            <span class="dl">Produkcja floty:</span>
            <span class="dv rate">
              {fmt(fleetRate(unit))} {resourceLabel(unit.production_resource)}/s
            </span>
          </div>
          <div class="detail-row">
            <span class="dl">Produkcja 1 szt.:</span>
            <span class="dv">
              {fmt(unit.production_rate_per_sec)} {resourceLabel(unit.production_resource)}/s
            </span>
          </div>
          <div class="detail-row">
            <span class="dl">Mnożnik:</span>
            <span class="dv">{parseFloat(unit.effective_multiplier).toFixed(3)}×</span>
          </div>
          <div class="detail-row">
            <span class="dl">Koszt następnej:</span>
            <span class="dv">{fmt(unit.next_cost)} {resourceLabel(unit.base_cost_currency)}</span>
          </div>
        </div>
      {/if}
    </div>
  {/each}
</section>

<style>
  .panel { margin-bottom: 20px; }
  .header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  h2 {
    color: #5a5;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 0;
  }
  .bulk-controls { display: flex; gap: 4px; }
  .btn-bulk {
    background: #111;
    color: #888;
    border: 1px solid #333;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 0.75rem;
    cursor: pointer;
    font-family: inherit;
  }
  .btn-bulk.active {
    background: #1a3a1a;
    color: #7ef;
    border-color: #2a6;
  }
  .btn-bulk:hover:not(.active) { border-color: #555; color: #aaa; }

  .card {
    background: #111;
    border: 1px solid #222;
    border-radius: 4px;
    margin-bottom: 4px;
    overflow: hidden;
  }
  .card.tier2 { border-color: #354; }
  .card.tier3plus { border-color: #445; }

  .card-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    cursor: pointer;
    user-select: none;
  }
  .card-row:hover { background: #161616; }

  .info { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
  .name { font-weight: bold; color: #eee; }
  .owned { color: #7ef; font-size: 0.85rem; }
  .rate { color: #7f7; font-size: 0.8rem; }

  .buy-col { display: flex; align-items: center; gap: 8px; }
  .cost { color: #aaa; font-size: 0.85rem; white-space: nowrap; }
  .cost.cant { color: #633; }
  .chevron { color: #555; font-size: 0.7rem; min-width: 10px; }

  .btn-buy {
    background: #1a3a1a;
    color: #7ef;
    border: 1px solid #2a6;
    border-radius: 4px;
    padding: 4px 10px;
    cursor: pointer;
    font-size: 0.8rem;
    font-family: inherit;
    white-space: nowrap;
    transition: background 0.15s;
  }
  .btn-buy:disabled { opacity: 0.35; cursor: not-allowed; }
  .btn-buy:not(:disabled):hover { background: #254; }

  .details {
    border-top: 1px solid #1a1a1a;
    padding: 8px 12px 10px;
    background: #0d0d0d;
  }
  .detail-row {
    display: flex;
    gap: 8px;
    font-size: 0.8rem;
    padding: 2px 0;
  }
  .dl { color: #666; min-width: 120px; }
  .dv { color: #aaa; }
  .dv.owned { color: #7ef; }
  .dv.rate { color: #7f7; }
</style>
