<script>
  import { wallet } from '../stores/game.js';
  import { listExperiments, runExperiment } from '../api/client.js';

  let experiments = [];
  let results = [];   // last N run results (most recent first)
  let busy = {};
  let loadError = null;

  async function load() {
    try {
      experiments = await listExperiments();
      loadError = null;
    } catch (e) {
      loadError = e.message;
    }
  }

  async function handleRun(experiment_id) {
    busy = { ...busy, [experiment_id]: true };
    try {
      const res = await runExperiment(experiment_id);
      results = [{ ...res, experiment_id }, ...results].slice(0, 5);
      await load(); // refresh cooldowns
    } catch (e) {
      results = [{ outcome_label: `Błąd: ${e.message}`, effect_type: 'error', experiment_id }, ...results].slice(0, 5);
    } finally {
      busy = { ...busy, [experiment_id]: false };
    }
  }

  function canAfford(exp) {
    if (!$wallet) return false;
    return (
      parseFloat($wallet.energy_drink ?? 0) >= parseFloat(exp.ed_cost) &&
      parseFloat($wallet.u238 ?? 0) >= parseFloat(exp.u238_cost)
    );
  }

  function fmt(val) {
    const n = parseFloat(val ?? 0);
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(2) + 'k';
    return n.toFixed(2);
  }

  function fmtCooldown(secs) {
    if (secs <= 0) return 'gotowy';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }

  function effectLabel(res) {
    if (res.effect_type === 'prod_bonus') return `+${fmt(res.effect_value)} ED`;
    if (res.effect_type === 'temp_multiplier') return `×${parseFloat(res.effect_value).toFixed(1)} przez ${res.duration_seconds}s`;
    if (res.effect_type === 'error') return '';
    return 'brak efektu';
  }

  load();
</script>

<section class="lab">
  <div class="lab-title">⚗ Laboratorium Jądrowe</div>

  {#if loadError}
    <div class="lab-error">{loadError}</div>
  {/if}

  <div class="exp-list">
    {#each experiments as exp (exp.experiment_id)}
      <div class="exp-card">
        <div class="exp-header">
          <span class="exp-name">{exp.name}</span>
          <span class="exp-costs">
            <span class="cost-ed">⚡ {fmt(exp.ed_cost)} ED</span>
            {#if parseFloat(exp.u238_cost) > 0}
              <span class="cost-u238">☢ {fmt(exp.u238_cost)} U-238</span>
            {/if}
          </span>
        </div>
        <div class="exp-desc">{exp.description}</div>
        <div class="exp-footer">
          <span class="exp-cooldown" class:ready={exp.cooldown_remaining_seconds === 0}>
            {#if exp.cooldown_remaining_seconds > 0}
              ⏳ {fmtCooldown(exp.cooldown_remaining_seconds)}
            {:else}
              ✓ Gotowy
            {/if}
          </span>
          <button
            class="btn-run"
            disabled={busy[exp.experiment_id] || exp.cooldown_remaining_seconds > 0 || !canAfford(exp)}
            on:click={() => handleRun(exp.experiment_id)}
          >
            {busy[exp.experiment_id] ? '...' : 'Przeprowadź'}
          </button>
        </div>
      </div>
    {/each}
  </div>

  {#if results.length > 0}
    <div class="results-section">
      <div class="results-title">Ostatnie wyniki</div>
      <ul class="results-list">
        {#each results as r}
          <li class="result-item" class:result-error={r.effect_type === 'error'}>
            <span class="result-label">{r.outcome_label}</span>
            {#if r.effect_type !== 'error' && r.effect_type !== 'nothing'}
              <span class="result-effect">{effectLabel(r)}</span>
            {/if}
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</section>

<style>
  .lab {
    background: #080d14;
    border: 1px solid #1a3a5a;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 16px;
  }
  .lab-title {
    font-size: 0.75rem;
    color: #4af;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
  }
  .lab-error {
    color: #f88;
    font-size: 0.8rem;
    margin-bottom: 8px;
  }

  .exp-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .exp-card {
    background: #0c1520;
    border: 1px solid #1a3a5a;
    border-radius: 4px;
    padding: 10px 12px;
  }
  .exp-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 4px;
    flex-wrap: wrap;
    gap: 6px;
  }
  .exp-name {
    font-weight: bold;
    color: #7ef;
    font-size: 0.9rem;
  }
  .exp-costs {
    display: flex;
    gap: 8px;
    font-size: 0.8rem;
  }
  .cost-ed { color: #7ef; }
  .cost-u238 { color: #7f7; }
  .exp-desc {
    color: #778;
    font-size: 0.78rem;
    margin-bottom: 8px;
    line-height: 1.4;
  }
  .exp-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .exp-cooldown {
    font-size: 0.78rem;
    color: #f90;
  }
  .exp-cooldown.ready { color: #5c5; }

  .btn-run {
    background: #0e2236;
    color: #4af;
    border: 1px solid #1a5a8a;
    border-radius: 4px;
    padding: 4px 14px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.82rem;
    transition: background 0.1s;
  }
  .btn-run:not(:disabled):hover { background: #163652; }
  .btn-run:disabled { opacity: 0.35; cursor: not-allowed; }

  .results-section {
    margin-top: 12px;
    border-top: 1px solid #1a3a5a;
    padding-top: 10px;
  }
  .results-title {
    font-size: 0.7rem;
    color: #4af;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }
  .results-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .result-item {
    font-size: 0.8rem;
    color: #99b;
    display: flex;
    gap: 10px;
    align-items: baseline;
  }
  .result-effect {
    color: #4af;
    font-weight: bold;
  }
  .result-error { color: #f88; }
</style>
