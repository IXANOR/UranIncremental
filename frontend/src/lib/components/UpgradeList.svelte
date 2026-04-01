<script>
  import { upgrades, wallet, units } from '../stores/game.js';
  import { buyUpgrade } from '../api/client.js';
  import { error, gameState } from '../stores/game.js';

  let buying = {};
  // open/closed state for each section
  let open = { units: true, offline: true, global: true };

  const OFFLINE_EFFECTS = new Set(['offline_eff_up', 'offline_cap_up']);

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  function canAfford(upg) {
    if (!$wallet) return false;
    return parseFloat($wallet[upg.cost_currency] ?? 0) >= parseFloat(upg.cost_amount);
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

  // Split upgrades into three buckets
  $: unitUpgrades = $upgrades.filter(u => u.target_unit_id != null);
  $: offlineUpgrades = $upgrades.filter(u => u.target_unit_id == null && OFFLINE_EFFECTS.has(u.effect_type));
  $: globalUpgrades = $upgrades.filter(u => u.target_unit_id == null && !OFFLINE_EFFECTS.has(u.effect_type));

  // Group unit upgrades by target_unit_id
  $: unitGroups = (() => {
    const unitNameMap = Object.fromEntries(($units ?? []).map(u => [u.unit_id, u.name]));
    const groups = {};
    for (const upg of unitUpgrades) {
      const key = upg.target_unit_id;
      if (!groups[key]) groups[key] = { name: unitNameMap[key] ?? key, items: [] };
      groups[key].items.push(upg);
    }
    return Object.values(groups);
  })();

  function sectionCounts(list) {
    const available = list.filter(u => !isMaxed(u)).length;
    const bought = list.filter(u => isMaxed(u)).length;
    return { available, bought };
  }

  $: unitCounts = sectionCounts(unitUpgrades);
  $: offlineCounts = sectionCounts(offlineUpgrades);
  $: globalCounts = sectionCounts(globalUpgrades);

  function toggle(key) {
    open = { ...open, [key]: !open[key] };
  }
</script>

<section class="panel">
  <h2>Ulepszenia</h2>

  <!-- === JEDNOSTKI === -->
  <div class="section">
    <button class="section-header" on:click={() => toggle('units')}>
      <span class="section-icon">{open.units ? '▾' : '▸'}</span>
      🔧 Jednostki
      <span class="counts">
        {#if unitCounts.available > 0}<span class="cnt-avail">{unitCounts.available} dostępnych</span>{/if}
        {#if unitCounts.bought > 0}<span class="cnt-bought">{unitCounts.bought} kupionych</span>{/if}
        {#if unitCounts.available === 0 && unitCounts.bought === 0}<span class="cnt-empty">brak</span>{/if}
      </span>
    </button>

    {#if open.units}
      {#each unitGroups as group (group.name)}
        <div class="subgroup">
          <div class="subgroup-header">{group.name}</div>
          {#each group.items.filter(u => !isMaxed(u)) as upg (upg.upgrade_id)}
            <div class="row">
              <div class="info">
                <span class="name">{upg.name}</span>
                <span class="desc">{upg.description}</span>
                {#if upg.survives_prestige}
                  <span class="badge-prestige" title="To ulepszenie przeżywa reset prestige">↺ trwałe</span>
                {/if}
              </div>
              <div class="buy-col">
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
              </div>
            </div>
          {/each}
          {#each group.items.filter(u => isMaxed(u)) as upg (upg.upgrade_id)}
            <div class="row purchased">
              <div class="info">
                <span class="name">{upg.name}</span>
                <span class="desc">{upg.description}</span>
              </div>
              <div class="buy-col">
                <span class="maxed">✓ Kupione</span>
              </div>
            </div>
          {/each}
        </div>
      {/each}
      {#if unitGroups.length === 0}
        <div class="empty-section">Brak ulepszeń jednostek.</div>
      {/if}
    {/if}
  </div>

  <!-- === OFFLINE === -->
  <div class="section">
    <button class="section-header" on:click={() => toggle('offline')}>
      <span class="section-icon">{open.offline ? '▾' : '▸'}</span>
      🌙 Offline
      <span class="counts">
        {#if offlineCounts.available > 0}<span class="cnt-avail">{offlineCounts.available} dostępnych</span>{/if}
        {#if offlineCounts.bought > 0}<span class="cnt-bought">{offlineCounts.bought} kupionych</span>{/if}
        {#if offlineCounts.available === 0 && offlineCounts.bought === 0}<span class="cnt-empty">brak</span>{/if}
      </span>
    </button>

    {#if open.offline}
      {#each offlineUpgrades.filter(u => !isMaxed(u)) as upg (upg.upgrade_id)}
        <div class="row">
          <div class="info">
            <span class="name">{upg.name}</span>
            <span class="desc">{upg.description}</span>
            {#if upg.survives_prestige}
              <span class="badge-prestige" title="To ulepszenie przeżywa reset prestige">↺ trwałe</span>
            {/if}
          </div>
          <div class="buy-col">
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
          </div>
        </div>
      {/each}
      {#each offlineUpgrades.filter(u => isMaxed(u)) as upg (upg.upgrade_id)}
        <div class="row purchased">
          <div class="info">
            <span class="name">{upg.name}</span>
            <span class="desc">{upg.description}</span>
          </div>
          <div class="buy-col">
            <span class="maxed">✓ Kupione</span>
          </div>
        </div>
      {/each}
      {#if offlineUpgrades.length === 0}
        <div class="empty-section">Brak ulepszeń offline.</div>
      {/if}
    {/if}
  </div>

  <!-- === GLOBALNE === -->
  <div class="section">
    <button class="section-header" on:click={() => toggle('global')}>
      <span class="section-icon">{open.global ? '▾' : '▸'}</span>
      ⚡ Globalne
      <span class="counts">
        {#if globalCounts.available > 0}<span class="cnt-avail">{globalCounts.available} dostępnych</span>{/if}
        {#if globalCounts.bought > 0}<span class="cnt-bought">{globalCounts.bought} kupionych</span>{/if}
        {#if globalCounts.available === 0 && globalCounts.bought === 0}<span class="cnt-empty">brak</span>{/if}
      </span>
    </button>

    {#if open.global}
      {#each globalUpgrades.filter(u => !isMaxed(u)) as upg (upg.upgrade_id)}
        <div class="row">
          <div class="info">
            <span class="name">{upg.name}</span>
            <span class="desc">{upg.description}</span>
            {#if upg.survives_prestige}
              <span class="badge-prestige" title="To ulepszenie przeżywa reset prestige">↺ trwałe</span>
            {/if}
          </div>
          <div class="buy-col">
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
          </div>
        </div>
      {/each}
      {#each globalUpgrades.filter(u => isMaxed(u)) as upg (upg.upgrade_id)}
        <div class="row purchased">
          <div class="info">
            <span class="name">{upg.name}</span>
            <span class="desc">{upg.description}</span>
          </div>
          <div class="buy-col">
            <span class="maxed">✓ Kupione</span>
          </div>
        </div>
      {/each}
      {#if globalUpgrades.length === 0}
        <div class="empty-section">Brak ulepszeń globalnych.</div>
      {/if}
    {/if}
  </div>
</section>

<style>
  .panel { margin-bottom: 20px; }
  h2 { color: #5a5; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 8px; }

  .section { margin-bottom: 6px; }

  .section-header {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 7px 12px;
    cursor: pointer;
    color: #ccc;
    font-size: 0.85rem;
    font-weight: bold;
    text-align: left;
    transition: background 0.1s;
  }
  .section-header:hover { background: #1e1e1e; }
  .section-icon { color: #555; font-size: 0.7rem; }

  .counts { margin-left: auto; display: flex; gap: 8px; font-weight: normal; }
  .cnt-avail { color: #5af; font-size: 0.78rem; }
  .cnt-bought { color: #5a5; font-size: 0.78rem; }
  .cnt-empty { color: #444; font-size: 0.78rem; }

  .subgroup { margin: 4px 0 4px 0; }
  .subgroup-header {
    color: #666;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 4px 12px 2px;
  }

  .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 4px;
    padding: 7px 12px;
    margin-bottom: 3px;
    gap: 8px;
  }
  .row.purchased { opacity: 0.45; }

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

  .empty-section { color: #444; font-size: 0.8rem; padding: 6px 12px; }
</style>
