<script>
  import { wallet, player } from '../stores/game.js';

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }
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
</style>
