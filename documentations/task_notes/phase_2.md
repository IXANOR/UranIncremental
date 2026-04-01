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

### Task 12 - AI Balance Proposals

**Status:** `not started`
**Depends on:** Task 09 (balance suite), Task 11 (frontend)

#### Definition of Done
- [ ] Endpoint `POST /api/v1/balance/propose` przyjmuje payload z propozycją zmiany (unit rates, costs, upgrade values) i zapisuje ją jako rekord `BalanceProposal` ze statusem `pending`
- [ ] Serwis AI (`balance_ai_service.py`) generuje propozycję przez wywołanie modelu LLM (Anthropic API) — prompt zawiera obecną konfigurację, wyniki testów balansu i prośbę o uzasadnienie
- [ ] Pipeline zatwierdzania: `pending` → `tests_passed` (po uruchomieniu balance suite) → `admin_approved` → `active`
- [ ] Endpoint `POST /api/v1/balance/approve/{proposal_id}` (wymaga `TEST_MODE=true` lub admin tokenu) przesuwa propozycję do `admin_approved`
- [ ] Endpoint `POST /api/v1/balance/activate/{proposal_id}` aktywuje propozycję — nadpisuje wartości w `seed()` i wywołuje upsert
- [ ] Balance suite uruchamiana automatycznie po przejściu do `tests_passed`; propozycja blokowana jeśli któryś test nie przejdzie
- [ ] Konfiguracja balance readonly gdy `TEST_MODE=false`
- [ ] Testy: unit dla logiki AI promptu + integration dla pipeline'u zatwierdzeń + balance regression

---

### Task 13 - AI Content Generator (unit/upgrade flavor text)

**Status:** `not started`
**Depends on:** Task 12

#### Definition of Done
- [ ] Endpoint `POST /api/v1/content/generate` przyjmuje `entity_type` (`unit`|`upgrade`) i `entity_id`; zwraca wygenerowany opis w stylu humoru techno-magic (PL)
- [ ] `content_service.py` buduje prompt z kontekstem gry (nazwa, tier, mechanika) i wywołuje Anthropic API
- [ ] Wygenerowany tekst zapisywany jako pole `flavor_text` w `UnitDefinition` / `UpgradeDefinition` (nowa kolumna, nullable)
- [ ] Frontend wyświetla `flavor_text` jako dodatkowy opis pod nazwą jednostki/ulepszenia (gdy istnieje)
- [ ] Alembic migracja dodająca `flavor_text TEXT NULL` do obu tabel
- [ ] Testy: unit dla promptu + integration dla endpointu + sprawdzenie że pole trafia do `GET /state`

---

### Task 14 - Minigame: Klik Reaktora

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

### Task 15 - Sezonowy Sink: Eksperyment Jądrowy

**Status:** `not started`
**Depends on:** Task 13, Task 14

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

### AI Integration

- Anthropic API klucz w `backend/.env` jako `ANTHROPIC_API_KEY`
- Wywołania AI tylko w endpointach oznaczonych `TEST_MODE=true` lub przez pipeline zatwierdzania
- Prompty wersjonowane w `app/services/ai_prompts/` jako osobne pliki `.txt` — ułatwia A/B testing
- Timeout 30s na wywołanie LLM; fallback: zwróć błąd 503 bez crashowania gracza

### Balance Pipeline

Zgodnie z CLAUDE.md — rygorystyczny pipeline zatwierdzania:
```
AI proposal → pending → tests_passed → admin_approved → active
```
- Żadna propozycja nie trafia do `active` bez przejścia pełnej balance suite
- Config balance readonly w produkcji (`TEST_MODE=false`)
- `BalanceProposal` przechowuje diff (before/after) dla audytu

### Minigame Design Constraints

- Kliknięcie nie może zastąpić pasywnej produkcji (max ~1% godzinnej produkcji)
- Rate-limit po stronie serwera — klient nie jest zaufany
- Eksperymenty muszą kosztować zarówno ED jak i U-238 — utrzymuje relevance obu walut

### Tech Debt z Phase 1 do rozwiązania w Phase 2

- Uruchomić Vitest dla testów jednostkowych frontendu
- Rozważyć GitHub Actions dla CI (pre-commit + pytest)
- `tech_magic_level` — zaprojektować mechanikę zanim pojawi się w UI
