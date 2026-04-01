<script>
  import { upgrades, wallet } from '../stores/game.js';
  import { buyUpgrade } from '../api/client.js';
  import { error, gameState } from '../stores/game.js';

  let buying = {};

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  function canAfford(upg) {
    if (!$wallet) return false;
    const bal = parseFloat($wallet[upg.cost_currency] ?? 0);
    return bal >= parseFloat(upg.cost_amount);
  }

  function isMaxed(upg) {
    return !upg.is_repeatable && upg.purchased_level >= 1;
  }

  async function handleBuy(upgrade_id) {
    buying = { ...buying, [upgrade_id]: true };
    try {
      await buyUpgrade(upgrade_id);
      const { fetchState } = await import('../api/client.js');
      gameState.set(await fetchState());
      error.set(null);
    } catch (e) {
      error.set(e.message);
    } finally {
      buying = { ...buying, [upgrade_id]: false };
    }
  }

  function currencyLabel(c) {
    const map = { energy_drink: 'ED', u238: 'U-238', u235: 'U-235', u233: 'U-233', meta_isotopes: 'META' };
    return map[c] ?? c;
  }
</script>

<section class="panel">
  <h2>Ulepszenia</h2>
  {#each $upgrades as upg (upg.upgrade_id)}
    <div class="row" class:purchased={upg.purchased_level > 0}>
      <div class="info">
        <span class="name">{upg.name}</span>
        <span class="desc">{upg.description}</span>
        {#if upg.survives_prestige}
          <span class="badge-prestige" title="To ulepszenie przeżywa reset prestige">↺ trwałe</span>
        {/if}
      </div>
      <div class="buy-col">
        {#if isMaxed(upg)}
          <span class="maxed">✓ Kupione</span>
        {:else}
          <span class="cost" class:cant={!canAfford(upg)}>
            {fmt(upg.cost_amount)} {currencyLabel(upg.cost_currency)}
          </span>
          <button
            class="btn-buy"
            disabled={!canAfford(upg) || buying[upg.upgrade_id]}
            on:click={() => handleBuy(upg.upgrade_id)}
          >
            {buying[upg.upgrade_id] ? '...' : 'Kup'}
          </button>
        {/if}
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
    gap: 8px;
  }
  .row.purchased { opacity: 0.55; }
  .info { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; flex: 1; }
  .name { font-weight: bold; color: #eee; }
  .desc { color: #888; font-size: 0.8rem; }
  .badge-prestige { color: #f90; font-size: 0.75rem; }
  .buy-col { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .cost { color: #aaa; font-size: 0.85rem; white-space: nowrap; }
  .cost.cant { color: #633; }
  .maxed { color: #5a5; font-size: 0.85rem; }
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
