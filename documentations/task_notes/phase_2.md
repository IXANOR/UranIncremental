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

**Status:** `not started`
**Depends on:** Task 11 (frontend)

#### Definition of Done
- [ ] Przycisk "Klik" w UI (widoczny zawsze) — każde kliknięcie generuje bonus ED równy `base_click_reward * prestige_multiplier`
- [ ] Endpoint `POST /api/v1/game/click` przyjmuje kliknięcie, waliduje rate-limit (max 10/s per player), zwraca `{gained: Decimal}`
- [ ] Rate-limit przechowywany w pamięci (Redis w Phase 3; na razie `dict` per process z TTL)
- [ ] `click_count` i `total_click_gains` śledzone w `PlayerState` (nowe kolumny + migracja)
- [ ] Frontend animuje przycisk przy kliknięciu (CSS transition, bez biblioteki animacji)
- [ ] Testy: unit dla logiki reward + integration dla rate-limit + balance (klik nie może zastąpić pasywnej produkcji — musi być < 1% godzinnej produkcji z 1 barrel)

---

### Task 14 - Sezonowy Sink: Eksperyment Jądrowy

**Status:** `not started`
**Depends on:** Task 13

#### Definition of Done
- [ ] Mechanizm "eksperymentu" — gracz może wydać pulę ED i U-238 na losowe wydarzenie z tabelą wyników (sukces/porażka/krytyczny sukces)
- [ ] `ExperimentDefinition` (id, name, description, ed_cost, u238_cost, outcomes: JSON)
- [ ] Endpoint `POST /api/v1/game/experiment/{experiment_id}` — odejmuje koszt, losuje wynik, aplikuje efekt (bonus do produkcji, tymczasowy mnożnik, lub nic)
- [ ] Seed: 3 eksperymenty startowe (tanie, średnie, drogie)
- [ ] Cooldown 1h per eksperyment (zapisany w `PlayerState.last_experiment_at`)
- [ ] Frontend: sekcja "Laboratoryum" w zakładce lub na dole strony; lista eksperymentów z kosztami i historią ostatnich wyników
- [ ] Testy: unit dla losowania wyników (seed RNG) + integration dla transakcji kosztów + balance (max efekt nie może przebić 30-min produkcji)

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
