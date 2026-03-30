# Dokumentacja techniczna backendu gry idle (FastAPI)
Wersja: `v0.1` (na podstawie ustaleń projektowych)

## 1. System Overview

### 1.1. Koncepcja gry
- Gatunek: `idle/incremental` inspirowany Swarm Simulator.
- Motyw: `uran + energetyk z uranu` (memiczny sci-fi).
- Styl: `humorystyczny techno-magic`.
- Filozofia progresji: `technologia + magia` z absurdalnymi akcentami.

### 1.2. Założenia architektury backendu
- Stack: `Python 3.12+`, `FastAPI`, `PostgreSQL`, `SQLAlchemy`, `Alembic`, `Pydantic`.
- Tryb uruchomienia: `single-user lokalnie` (ale architektura gotowa pod rozszerzenie).
- Model czasu:
  - online: czas rzeczywisty serwerowy,
  - offline: symulacja po `delta_time` od ostatniego snapshotu.
- Bezpieczeństwo czasu/progresji: `signed snapshots + walidacja delta_time`.
- Konfiguracja środowiskowa:
  - `TEST_MODE=false` (prod-like lokalnie): brak endpointów debug write.
  - `TEST_MODE=true`: debug endpointy dostępne (`simulate`, `correction`).

### 1.3. Ekonomia wysokiego poziomu
- Główna waluta bazowa: `energy_drink` (energetyk z uranu).
- Waluty wyższych tierów:
  - `u238`
  - `u235`
  - `u233`
  - `meta_isotopes`
- Zasada: waluta bazowa nigdy nie traci znaczenia.
  - Utrzymanie automatyzacji (fuel/upkeep).
  - Sinki sezonowe/rotacyjne (kontrakty, mutacje, aukcje).

## 2. Modele danych (z polami)

### 2.1. `player_state`
- `id: UUID`
- `created_at: datetime`
- `updated_at: datetime`
- `version: int` (optimistic locking)
- `last_tick_at: datetime` (UTC)
- `last_online_at: datetime` (UTC)
- `prestige_count: int`
- `tech_magic_level: int`
- `offline_efficiency: float` (0.2 start, max 1.0)
- `offline_cap_seconds: int` (skalowane upgrade'ami)
- `snapshot_signature: str` (HMAC)

### 2.2. `wallet`
- `player_id: UUID`
- `energy_drink: Decimal`
- `u238: Decimal`
- `u235: Decimal`
- `u233: Decimal`
- `meta_isotopes: Decimal`

### 2.3. `unit_definition` (konfig)
- `id: str` (np. `reactor_t1`)
- `tier: int`
- `base_cost_currency: str`
- `base_cost_amount: Decimal`
- `cost_growth_type: str` (`linear_early_exp_late`)
- `cost_growth_factor: Decimal`
- `production_resource: str`
- `production_rate_per_sec: Decimal`
- `unlocked_by: str | null`

### 2.4. `player_unit`
- `player_id: UUID`
- `unit_id: str`
- `amount_owned: int`
- `effective_multiplier: Decimal`
- `automation_enabled: bool`
- `upkeep_energy_per_sec: Decimal`

### 2.5. `upgrade_definition` (konfig)
- `id: str`
- `name: str`
- `description: str`
- `tier: int`
- `cost_currency: str`
- `cost_amount: Decimal`
- `effect_type: str` (np. `prod_mult`, `offline_eff_up`, `offline_cap_up`)
- `effect_value: Decimal`
- `is_repeatable: bool`

### 2.6. `player_upgrade`
- `player_id: UUID`
- `upgrade_id: str`
- `level: int`
- `purchased_at: datetime`

### 2.7. `balance_config` (read-only in prod)
- `id: UUID`
- `version_tag: str`
- `is_active: bool`
- `json_blob: JSONB`
- `created_at: datetime`

### 2.8. `balance_test_run`
- `id: UUID`
- `config_version: str`
- `test_suite_version: str`
- `status: str` (`passed`/`failed`)
- `summary: JSONB`
- `created_at: datetime`

### 2.9. `event_log`
- `id: UUID`
- `player_id: UUID`
- `event_type: str`
- `payload: JSONB`
- `created_at: datetime`

## 3. API Endpoints (request/response)

### 3.1. Public Core
1. `POST /api/v1/game/start`
- Cel: inicjalizacja nowej gry/sesji.
- Response:
```json
{
  "player_id": "uuid",
  "state_version": 1,
  "started_at": "2026-03-30T10:00:00Z"
}
```

2. `GET /api/v1/game/state`
- Cel: pełny snapshot stanu po przeliczeniu delta czasu.
- Response:
```json
{
  "player": { "offline_efficiency": 0.2, "offline_cap_seconds": 14400 },
  "wallet": { "energy_drink": "120.5", "u238": "0" },
  "units": [{ "unit_id": "reactor_t1", "amount_owned": 12 }],
  "upgrades": [{ "upgrade_id": "offline_module_mk1", "level": 1 }],
  "server_time": "2026-03-30T10:05:00Z"
}
```

3. `POST /api/v1/economy/buy-unit`
- Request:
```json
{ "unit_id": "reactor_t1", "quantity": 1 }
```
- Response:
```json
{
  "ok": true,
  "new_amount_owned": 13,
  "wallet_after": { "energy_drink": "110.2" }
}
```

4. `POST /api/v1/economy/buy-upgrade`
- Request:
```json
{ "upgrade_id": "offline_eff_mk1" }
```
- Response:
```json
{
  "ok": true,
  "upgrade_level": 1,
  "applied_effect": { "offline_efficiency": 0.25 }
}
```

5. `POST /api/v1/time/claim-offline`
- Request:
```json
{ "client_last_seen_at": "2026-03-30T08:00:00Z" }
```
- Response:
```json
{
  "simulated_seconds": 7200,
  "efficiency_used": 0.2,
  "gains": { "energy_drink": "540.0" },
  "cap_applied": false
}
```

### 3.2. Test/Admin (`TEST_MODE=true`)
1. `POST /api/v1/test/simulate-time`
- Request:
```json
{ "seconds": 3600 }
```
- Response:
```json
{ "ok": true, "simulated_seconds": 3600, "state_version": 42 }
```

2. `POST /api/v1/test/correct-state`
- Request:
```json
{
  "wallet_patch": { "energy_drink": "999999" },
  "units_patch": [{ "unit_id": "reactor_t1", "amount_owned": 1000 }]
}
```
- Response:
```json
{ "ok": true, "applied": ["wallet_patch", "units_patch"] }
```

### 3.3. Balans / AI
1. `GET /api/v1/balance/config` (prod + test)
2. `POST /api/v1/balance/proposal` (AI propozycja, status `pending`)
3. `POST /api/v1/balance/proposal/{id}/approve` (admin)
4. `GET /api/v1/ai/content/proposals` (lista nazw/opisów do zatwierdzenia)
5. `POST /api/v1/ai/content/proposals/{id}/approve`
6. `POST /api/v1/ai/content/proposals/{id}/reject`

## 4. Core Game Loop (dokładny)

1. `Load State`
- Pobierz `player_state + wallet + units + upgrades`.
- Zweryfikuj `snapshot_signature`.

2. `Compute Delta Time`
- `delta = now_utc - last_tick_at`.
- Jeśli gracz offline: zastosuj `offline_efficiency` i `offline_cap_seconds`.

3. `Production Pass`
- Produkcja równoległa dla wszystkich aktywnych jednostek.
- Dodatkowa produkcja łańcuchowa dla jednostek wyższego tieru.
- Zastosuj mnożniki z upgrade'ów i prestiżu.

4. `Automation Upkeep`
- Odejmij `energy_drink` jako paliwo automatyzacji.
- Jeśli brak paliwa: wyłącz część automatyzacji (deterministycznie).

5. `Apply Gains`
- Zapisz zasoby do `wallet`.
- Aktualizuj `last_tick_at`, `last_online_at`, `state_version`.

6. `Sign Snapshot`
- Wygeneruj nowy podpis HMAC stanu.
- Zapisz podpis do `player_state.snapshot_signature`.

7. `Return State`
- Zwróć snapshot API wraz z `server_time`.

## 5. Struktura projektu (foldery)

```txt
backend/
  app/
    main.py
    core/
      config.py
      security.py
      time_utils.py
    db/
      session.py
      base.py
      models/
        player_state.py
        wallet.py
        unit.py
        upgrade.py
        balance.py
        events.py
      repositories/
    schemas/
      game.py
      economy.py
      time.py
      balance.py
      ai.py
    services/
      game_loop_service.py
      economy_service.py
      pricing_service.py
      offline_service.py
      prestige_service.py
      balance_service.py
      ai_content_service.py
      snapshot_sign_service.py
    api/
      deps.py
      routes/
        game.py
        economy.py
        time.py
        balance.py
        ai.py
        test_tools.py
    tests/
      unit/
      integration/
      balance/
      api/
  alembic/
  .env.example
  pyproject.toml
  README.md
```

## 6. Implementation Phases (bardzo ważne)

### Faza 1: MVP+ Core (z taskami)
Cel: działająca gra single-user lokalnie, pełna pętla idle, podstawowy balans i test-mode.

1. Task 1: Bootstrap projektu
- FastAPI app, config, DB connection (PostgreSQL), Alembic.
- `.env` z `TEST_MODE`, `DATABASE_URL`, `SNAPSHOT_SECRET`.

2. Task 2: Modele i migracje
- Utworzyć tabele: `player_state`, `wallet`, `player_unit`, `player_upgrade`, `event_log`.
- Seed definicji jednostek/upgrade'ów.

3. Task 3: Core loop service
- Delta time online/offline.
- Offline efficiency od 20% (upgrade'owalne).
- Offline cap skalowany.

4. Task 4: Ekonomia i pricing
- Hybrydowa krzywa cen (liniowa early, wykładnicza mid/late).
- Silny wzrost wykładniczy progresji.
- Utrzymanie automatyzacji za `energy_drink`.

5. Task 5: Endpointy MVP
- `start_game`, `get_state`, `buy_unit`, `buy_upgrade`, `claim_offline`.
- Grupowanie endpointów wg modułów.

6. Task 6: Test/Admin w `TEST_MODE=true`
- `simulate-time`, `correct-state`.
- Twarda blokada endpointów debug przy `TEST_MODE=false`.

7. Task 7: Snapshot signing + walidacja
- HMAC snapshotu.
- Walidacja delta i event log błędów.

8. Task 8: Soft reset (prestige v1)
- Miękki reset części progresji.
- Zachowanie metaprogresji i części unlocków.

9. Task 9: TDD i testy balansu (must-pass)
- Unit testy pricingu, produkcji, offline cap.
- Integration testy endpointów.
- Balance test suite z progami akceptacji:
  - brak deadlocku ekonomii,
  - brak runaway zbyt wcześnie,
  - osiągalność tierów w zakładanym czasie.

10. Task 10: Git workflow i jakość
- Częste, małe, czyste commity.
- Nazwy commitów są ustalane dopiero po implementacji i muszą opisywać faktycznie wykonane zmiany.
- Każdy commit: przechodzi testy lokalne dla zmienionego modułu.

### Faza 2: Po zamknięciu Fazy 1
- Taski zostaną rozpisane dopiero po ukończeniu Fazy 1 (zgodnie z wymaganiem).
- Planowany zakres:
  - AI propozycje balansu z approval flow,
  - AI generator contentu (lista nazw/opisów do akceptacji),
  - minigierki,
  - seasonal sinks i eventy.

### Faza 3: Po zamknięciu Fazy 2
- Taski zostaną rozpisane dopiero po ukończeniu Fazy 2 (zgodnie z wymaganiem).
- Planowany zakres:
  - rozszerzenie liveops i eventów sezonowych,
  - przygotowanie pod tryb multi-user,
  - optymalizacje wydajności i observability,
  - hardening bezpieczeństwa i deployment produkcyjny.

### Zasada realizacji tasków (obowiązkowa)
- Taski w Fazie 1 są wykonywane sekwencyjnie: `Task N -> Task N+1` bez równoległego wdrażania.
- Kolejny task można rozpocząć dopiero po spełnieniu Definition of Done bieżącego taska.
- Każdy task musi zostawić trwałą notatkę wiedzy technicznej, aby kolejne taski mogły się do niej odwołać.

### Baza wiedzy taskowej (obowiązkowa)
- Lokalizacja:
  - `documentations/task_notes/phase_1.md` (chronologiczny dziennik)
  - opcjonalnie: `documentations/task_notes/task_XX.md` dla większych tematów
- Po zakończeniu każdego taska AI dopisuje sekcję w notatkach:
  - `Task ID i nazwa`
  - `Data i commit hash(e)`
  - `Zakres zmian (co zaimplementowano)`
  - `Decyzje architektoniczne i uzasadnienie`
  - `Pułapki / ryzyka / ograniczenia`
  - `Co trzeba mieć na uwadze w kolejnych taskach`
  - `Status testów (unit/integration/balance)`
- Notatki są częścią Definition of Done każdego taska.

## 7. Zasady AI (content/balans) i TDD

### Globalna polityka TDD (obowiązkowa)
1. Każda zmiana funkcjonalna zaczyna się od testu (`red -> green -> refactor`).
2. Brak merge/uznania taska za zakończony bez zielonych testów dla zmienionego zakresu.
3. Każdy bugfix wymaga testu reprodukującego błąd przed poprawką.
4. Testy balansu są traktowane jak testy blokujące publikację konfiguracji.
5. Minimalny zestaw per task:
- testy jednostkowe logiki domenowej,
- testy integracyjne endpointów zmienionych w tasku,
- aktualizacja/regresja testów balansu, jeśli task dotyka ekonomii.

1. AI nigdy nie publikuje balansu bez akceptacji admina.
2. AI content trafia najpierw na listę propozycji (`pending`).
3. Każda propozycja balansu przechodzi test suite:
- economy stability,
- progression pacing,
- currency relevance (`energy_drink` w late game),
- brak regresji względem poprzedniej konfiguracji.
4. Dopiero po `tests=passed` i `admin_approved` config może być `active`.

## 8. Ustalone parametry startowe (rekomendowane)

- `offline_efficiency_start = 0.20`
- `offline_efficiency_max = 1.00`
- `offline_cap_start = 4h`
- `offline_cap_max = 24h+` (przez upgrade'y)
- `tick_resolution = 1s` logicznie, liczone analitycznie po `delta`
- `energy_drink` jako upkeep dla automatyzacji: aktywny sink przez całą grę

## 9. Zasada językowa (obowiązkowa)

- Cały kod techniczny musi być w pełni po angielsku:
  - nazwy plików i folderów,
  - nazwy klas, funkcji, zmiennych, stałych,
  - endpointy API, schematy, pola modeli,
  - komentarze techniczne, nazwy testów i komunikaty logów.
- Język polski jest dozwolony wyłącznie w stringach wyświetlanych graczowi, np.:
  - elementy HUD,
  - opisy jednostek i ulepszeń,
  - flavor texty i komunikaty UI.

## 10. Docstringi (obowiązkowe)

- Każda publiczna klasa i każda funkcja (co najmniej w warstwach `services`, `api`, `db/repositories`, `core`) musi mieć docstring.
- Format docstringów: standard Google.
- Minimalny zakres:
  - krótki opis celu,
  - `Args` dla parametrów wejściowych,
  - `Returns` dla wartości zwracanej,
  - `Raises` dla istotnych wyjątków.
- W testach dopuszczalne są krótsze docstringi, ale dla test utilities i helperów również obowiązuje styl Google.
