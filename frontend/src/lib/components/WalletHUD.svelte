<script>
  import { wallet, player, units } from '../stores/game.js';

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  const RESOURCE_LABEL = { energy_drink: 'ED', u238: 'U-238', u235: 'U-235', u233: 'U-233', meta_isotopes: 'META' };
  const RESOURCE_ICON  = { energy_drink: '⚡', u238: '☢', u235: '⚛', u233: '🔬', meta_isotopes: '✦' };
  const RESOURCE_CLASS = { energy_drink: 'ed', u238: 'u238', u235: 'u235', u233: 'u233', meta_isotopes: 'meta' };

  $: production = $units.reduce((acc, u) => {
    const rate = parseFloat(u.amount_owned) * parseFloat(u.production_rate_per_sec) * parseFloat(u.effective_multiplier);
    acc[u.production_resource] = (acc[u.production_resource] ?? 0) + rate;
    return acc;
  }, {});

  $: productionEntries = Object.entries(production).filter(([, v]) => v > 0);
</script>

<section class="hud">
  <div class="hud-title">
    Portfel
    {#if $player}
      <span class="prestige-badge">✦ Prestige {$player.prestige_count}</span>
    {/if}
  </div>
  {#if $wallet}
    <div class="currencies">
      <span class="currency ed">⚡ {fmt($wallet.energy_drink)} ED</span>
      <span class="currency u238">☢ {fmt($wallet.u238)} U-238</span>
      <span class="currency u235">⚛ {fmt($wallet.u235)} U-235</span>
      <span class="currency u233">🔬 {fmt($wallet.u233)} U-233</span>
      <span class="currency meta">✦ {fmt($wallet.meta_isotopes)} META</span>
    </div>
    {#if productionEntries.length > 0}
      <div class="production-row">
        {#each productionEntries as [res, rate]}
          <span class="prod-item {RESOURCE_CLASS[res] ?? ''}">
            {RESOURCE_ICON[res] ?? ''} +{fmt(rate)} {RESOURCE_LABEL[res] ?? res}/s
          </span>
        {/each}
      </div>
    {/if}
  {:else}
    <p class="loading">Ładowanie stanu...</p>
  {/if}
</section>

<style>
  .hud {
    background: #111;
    border: 1px solid #2a2;
    border-radius: 6px;
    padding: 10px 16px;
    margin-bottom: 16px;
  }
  .hud-title {
    font-size: 0.75rem;
    color: #5a5;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .prestige-badge {
    color: #f90;
    font-weight: bold;
  }
  .currencies {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .currency {
    font-size: 0.95rem;
    font-weight: bold;
    white-space: nowrap;
  }
  .ed { color: #7ef; }
  .u238 { color: #7f7; }
  .u235 { color: #af5; }
  .u233 { color: #5df; }
  .meta { color: #f90; }
  .loading { color: #555; font-style: italic; }
  .production-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid #1a2a1a;
  }
  .prod-item {
    font-size: 0.8rem;
    opacity: 0.85;
    white-space: nowrap;
  }
</style>
