# Phase 2 Task Notes

Chronological knowledge log for Phase 2.
Phase 2 starts after Phase 1 is fully closed (commit `06e7b90`, 149 tests green).

Phase 2 focus: **AI balance proposals, content generation, minigames, seasonal sinks.**
Architecture must remain single-user-first but structurally ready for multi-user (Phase 3).

---

## Template

### Task XX - <name>

**Status:** `not started` | `in progress` | `done`
**Depends on:** Task XX

#### Definition of Done
- [ ] ...

---

#### Post-task notes
- **Date:**
- **Commit(s):**
- **Scope implemented:**
- **Architectural decisions:**
- **Risks / constraints:**
- **Notes for next tasks:**
- **Test status:**
  - Unit:
  - Integration:
  - Balance:

---

## Tasks

### Task 12 - Nowy Content: Jednostki T3-T5, Ulepszenia, Balans

**Status:** `done`
**Depends on:** Task 11 (frontend)

#### Definition of Done
- [x] Nowe jednostki T3-T5 dodane do `seed.py` z poprawnym łańcuchem zasobów (u238→u235→u233→meta)
- [x] Jednostka pomostowa T1 (`uranium_refinery`) wypełniająca lukę między kopalnią a T2
- [x] 24 nowe ulepszenia: Mk2/Mk3 dla T1, Mk1 dla T2, offline Mk3, globalne (`global_prod_mult`, `starting_energy_up`), T3-T5
- [x] Nowe typy efektów ulepszeń zaimplementowane w `economy_service.py`
- [x] Zmiany balansu: koszt `offline_module_mk1` 500→300 ED, mnożnik prestige 1.15→1.20
- [x] UI ulepszeń przepisane: 3 zwijalne sekcje (🔧 Jednostki, 🌙 Offline, ⚡ Globalne), kupione szare na dole
- [x] `target_unit_id` dodane do `UpgradeStateSchema` i `GET /game/state`
- [x] Stara infrastruktura API balansowania (Anthropic API) usunięta
- [x] 129 testów przechodzi

---

#### Post-task notes
- **Date:** 2026-04-02
- **Commit(s):** `82e2e46`, `461c396`
- **Scope implemented:**
  - 7 nowych jednostek: `uranium_refinery` (T1 bridge), `isotope_separator`, `quantum_centrifuge` (T3), `thorium_converter`, `breeder_reactor` (T4), `particle_accelerator`, `dimension_reactor` (T5)
  - 24 nowe ulepszenia w kategoriach B/E/F/G/H
  - Nowe typy efektów: `global_prod_mult` (mnoży effective_multiplier wszystkich posiadanych jednostek), `starting_energy_up` (natychmiastowy bonus ED)
  - `UpgradeList.svelte` — 3 zwijalne sekcje z licznikami dostępnych/kupionych
  - Balans C2 (offline_module_mk1 500→300) i C3 (prestige ×1.20 zamiast ×1.15)
- **Architectural decisions:**
  - T3-T5 jednostki kosztują izotopy (u238/u235/u233), nie ED — inwariant `energy_drink nie może stać się nieistotny` zachowany przez upkeep automatyzacji i wyłączność ED dla T1/T2
  - Test balansu `test_all_units_cost_energy_drink` zastąpiony bardziej precyzyjnym `test_tier1_and_tier2_units_cost_energy_drink` + weryfikacja łańcucha T3+
  - Infrastruktura balance_ai_service / balance route / BalanceProposal usunięta — zbędna bez kluczy Anthropic API; zatwierdzanie contentu odbywa się przez rozmowę z Claude w chatsie
- **Risks / constraints:**
  - `global_prod_mult` stosowany tylko do jednostek już posiadanych w momencie zakupu — nowe jednostki kupione po upgradzie nie otrzymują retroaktywnie mnożnika. Akceptowalne dla MVP.
  - Łańcuch T3-T5 nie jest widoczny w UI (brak dedykowanego filtra tier) — do rozważenia w Phase 3
- **Notes for next tasks:**
  - Task 13 (minigame Klik Reaktora) nie zależy od contentu T3-T5
  - Migracja `c3d4e5f6a7b8_add_balance_proposal_table.py` pozostawiona w historii Alembic (tabela `balance_proposal` istnieje w DB); nie wpływa na działanie aplikacji
- **Test status:**
  - Unit: ✅ 129 testów
  - Integration: ✅
  - Balance: ✅ (tier progression, prestige, economy)

---

### Task 13 - Minigame: Klik Reaktora

**Status:** `done`
**Depends on:** Task 11 (frontend)

#### Definition of Done
- [x] Przycisk "Klik" w UI (widoczny zawsze) — każde kliknięcie generuje bonus ED równy `base_click_reward * prestige_multiplier`
- [x] Endpoint `POST /api/v1/game/click` przyjmuje kliknięcie, waliduje rate-limit (max 10/s per player), zwraca `{gained: Decimal}`
- [x] Rate-limit przechowywany w pamięci (Redis w Phase 3; na razie `dict` per process z TTL)
- [x] `click_count` i `total_click_gains` śledzone w `PlayerState` (nowe kolumny + migracja)
- [x] Frontend animuje przycisk przy kliknięciu (CSS transition, bez biblioteki animacji)
- [x] Testy: unit dla logiki reward + integration dla rate-limit + balance (klik nie może zastąpić pasywnej produkcji — musi być < 1% godzinnej produkcji z 1 barrel)

---

#### Post-task notes
- **Date:** 2026-04-02
- **Commit(s):** `2d81d36`
- **Scope implemented:**
  - `click_service.py`: `process_click()` + `ClickRateLimitError` + in-process rate limiter (`_click_timestamps: dict[UUID, list[float]]`, okno 1s, max 10 kliknięć)
  - `BASE_CLICK_REWARD = 1.0 ED × 1.20^prestige_count`
  - `PlayerState`: nowe kolumny `click_count: int` i `total_click_gains: Decimal(28,10)`
  - Migracja Alembic `d4e5f6a7b8c9` z `server_default="0"`
  - `POST /api/v1/game/click` w `game.py` router, zwraca `ClickResponse(gained: Decimal)`, 429 przy rate limit
  - `PlayerStateSchema` rozszerzone o `click_count` + `total_click_gains`
  - `App.svelte` przywrócone (było puste) + przycisk ⚡ Klik! z CSS scale transform + fade dla `+X ED`
  - Footer gry pokazuje licznik kliknięć i poprawiony mnożnik 1.20×
- **Architectural decisions:**
  - Rate limiter in-process (dict) — wystarczający dla single-user MVP; Redis/shared store gdy multi-user (Phase 3)
  - `process_click` invaliduje `snapshot_signature = ""` — spójność z pozostałymi mutacjami stanu
  - `ClickRateLimitError` → HTTP 429; błędy rate-limit ignorowane cicho po stronie frontendu (brak spamu bannerów)
- **Risks / constraints:**
  - Rate limiter resetuje się przy restarcie procesu — akceptowalne dla Phase 2
  - `total_click_gains` nie jest retroaktywnie agregowane — zaczyna od 0 dla istniejących graczy po migracji
- **Notes for next tasks:**
  - Task 14 (Eksperyment Jądrowy) zależy od Task 13 wg planu, ale nie technicznie — można implementować niezależnie
- **Test status:**
  - Unit: ✅ 7 testów (reward, prestige scaling, wallet, click_count, total_gains, rate limit, window reset)
  - Integration: ✅ 5 testów (200 gained, wallet balance, 429 rate limit, 400 brak nagłówka, 404 nieznany gracz)
  - Balance: ✅ 1 test (BASE_CLICK_REWARD < 1% hourly barrel = 10.8 ED)
  - Total: 142 testów

---

### Task 14 - Sezonowy Sink: Eksperyment Jądrowy

**Status:** `done`
**Depends on:** Task 13

#### Definition of Done
- [x] Mechanizm "eksperymentu" — gracz może wydać pulę ED i U-238 na losowe wydarzenie z tabelą wyników (sukces/porażka/krytyczny sukces)
- [x] `ExperimentDefinition` (id, name, description, ed_cost, u238_cost, outcomes: JSON)
- [x] Endpoint `POST /api/v1/game/experiment/{experiment_id}` — odejmuje koszt, losuje wynik, aplikuje efekt (bonus do produkcji, tymczasowy mnożnik, lub nic)
- [x] Seed: 3 eksperymenty startowe (tanie, średnie, drogie)
- [x] Cooldown 1h per eksperyment (zapisany w `PlayerState.experiment_cooldowns` jako JSON dict)
- [x] Frontend: sekcja "Laboratorium" na dole strony; lista eksperymentów z kosztami i historią ostatnich wyników
- [x] Testy: unit dla losowania wyników (seed RNG) + integration dla transakcji kosztów + balance (max efekt nie może przebić 30-min produkcji)

---

#### Post-task notes
- **Date:** 2026-04-02
- **Commit(s):** `aaa022e`
- **Scope implemented:**
  - `ExperimentDefinition` model: `id`, `name`, `description`, `ed_cost`, `u238_cost`, `cooldown_seconds`, `outcomes: JSON`
  - 3 eksperymenty w seed: `alpha_test` (20 ED), `beta_reaction` (100 ED + 1 U238), `gamma_fusion` (300 ED + 5 U238)
  - Typy wyników: `nothing`, `prod_bonus` (natychmiastowy ED), `temp_multiplier` (mnożnik × duration_seconds)
  - `PlayerState` rozszerzone: `experiment_cooldowns: JSON dict[str, str]`, `temp_prod_multiplier: Decimal`, `temp_prod_multiplier_expires_at: DateTime?`
  - `game_loop_service`: `temp_mult` aplikowany do produkcji gdy aktywny i nie wygasł
  - `GET /api/v1/game/experiments`: lista z `cooldown_remaining_seconds` per gracz
  - `POST /api/v1/game/experiment/{id}`: 404 (brak)/409 (cooldown)/402 (brak kasy)/200 (sukces)
  - Migracja `e5f6a7b8c9d0`: tabela `experiment_definition` + 3 kolumny w `player_state`
  - `Laboratorium.svelte`: karty eksperymentów, licznik cooldownu, historia 5 ostatnich wyników
- **Architectural decisions:**
  - `experiment_cooldowns` jako JSON dict zamiast kolumny per-eksperyment — skalowalny bez kolejnych migracji dla nowych eksperymentów
  - `_roll_outcome(rng)` — wstrzykiwalne RNG dla deterministycznych testów; prod używa `random.Random()` bez seeda
  - `temp_prod_multiplier` w PlayerState + check w game_loop_service — spójne z resztą mnożników produkcji; brak osobnej tabeli efektów
  - Stacking: gdy mnożnik już aktywny i nowy jest słabszy, wydłuża expiry zamiast nadpisywać; silniejszy nadpisuje
- **Risks / constraints:**
  - `temp_prod_multiplier` nie jest uwzględniony w podpisie snapshot (celowo — signing pokrywa wallet+units, nie buffs)
  - Cooldown timer w Laboratorium.svelte nie tyka automatycznie — wymaga kliknięcia "Przeprowadź" żeby odświeżyć; można poprawić w Phase 3 (polling)
- **Test status:**
  - Unit: ✅ 11 testów (roll_outcome deterministyczne, koszty ED/U238, efekty prod_bonus/temp_mult, cooldown, error paths)
  - Integration: ✅ 7 testów (list 3 exp, cooldown_remaining=0, run 200, 404, 409, 402, 400)
  - Balance: ✅ 2 testy (wszystkie wyniki < 30-min barrel, sumy probabilistyczne = 1.0)
  - Total: 162 testów

---

## Phase 2 Architecture Notes

### Content i balans — workflow

Zamiast Anthropic API, nowe jednostki/ulepszenia/zmiany balansu są proponowane przez Claude Code w rozmowie z developerem.
Pipeline zatwierdzania:
1. Claude prezentuje propozycje (lista z opisami i wartościami)
2. Developer odpowiada: ✅ zatwierdzone / ❌ odrzucone / modyfikacja
3. Claude implementuje zatwierdzone zmiany bezpośrednio w `seed.py` i serwisach
4. Testy (`pytest`) muszą przechodzić — balans traktowany jako release-blocking

### Minigame Design Constraints

- Kliknięcie nie może zastąpić pasywnej produkcji (max ~1% godzinnej produkcji)
- Rate-limit po stronie serwera — klient nie jest zaufany
- Eksperymenty muszą kosztować zarówno ED jak i U-238 — utrzymuje relevance obu walut

### Tech Debt z Phase 1 do rozwiązania w Phase 2

- Uruchomić Vitest dla testów jednostkowych frontendu
- Rozważyć GitHub Actions dla CI (pre-commit + pytest)
- `tech_magic_level` — zaprojektować mechanikę zanim pojawi się w UI
