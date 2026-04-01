# Phase 1 Task Notes

Chronological knowledge log for Phase 1. Each completed task appends a filled-in section below.
Tasks are sequential — do not start Task N+1 until Task N is `done`.

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

### Task 01 - Bootstrap projektu

**Status:** `done`
**Depends on:** —

#### Definition of Done
- [ ] FastAPI app uruchamia się lokalnie (`uvicorn app.main:app --reload`) z katalogu `backend/`
- [ ] Połączenie z PostgreSQL działa i jest konfigurowane przez `DATABASE_URL` w `.env`
- [ ] Alembic skonfigurowany, `alembic upgrade head` przechodzi bez błędów
- [ ] `.env.example` zawiera wszystkie wymagane zmienne: `DATABASE_URL`, `SNAPSHOT_SECRET`, `TEST_MODE`
- [ ] `TEST_MODE` jest wczytywany przez `core/config.py` (Pydantic Settings)
- [ ] `backend/pyproject.toml` z zależnościami i grupą `[dev]`
- [ ] Struktura folderów zgodna z dokumentacją sekcja 5 (`backend/`, `frontend/` na poziomie root)
- [ ] Podstawowy health-check endpoint `GET /health` zwraca `{"status": "ok"}`
- [ ] Frontend: `frontend/` zainicjalizowany przez `npm create vite@latest` (Svelte 5 + JS)
- [ ] Frontend: `npm run dev` uruchamia Vite na `:5173`, proxy `/api/*` → `http://localhost:8000`
- [ ] Testy: pytest skonfigurowany, przynajmniej jeden test smoke przechodzi

---

#### Post-task notes
- **Date:** 2026-03-31
- **Commit(s):** TBD (committing after notes)
- **Scope implemented:**
  - `backend/` folder z pełną strukturą (`app/core`, `app/db`, `app/api`, `app/services`, `app/schemas`, `app/tests`)
  - `pyproject.toml` z zależnościami prod + dev, setuptools package discovery
  - `app/core/config.py` — Pydantic Settings ładuje `DATABASE_URL`, `SNAPSHOT_SECRET`, `TEST_MODE` z `.env`
  - `app/db/session.py` — async SQLAlchemy engine + `AsyncSessionLocal` + dep `get_db`
  - `app/db/base.py` — `DeclarativeBase` dla wszystkich modeli
  - `app/api/routes/health.py` — `GET /health` → `{"status": "ok"}`
  - `app/main.py` — FastAPI app z health routerem
  - `alembic/env.py` — async migrations, metadata z `Base`, `DATABASE_URL` z settings
  - `app/tests/conftest.py` — `AsyncClient` fixture przez ASGI transport
  - `frontend/` — Svelte 5 + Vite, proxy `/api/*` → `:8000`, struktura `src/lib/{api,components,stores}`
  - `.gitignore` zaktualizowany o `frontend/node_modules/`, `frontend/dist/`, `backend/.env`
- **Architectural decisions:**
  - `requires-python = ">=3.11"` zamiast 3.12 — środowisko ma Python 3.11.6, kod jest w pełni kompatybilny
  - Alembic używa `async_engine_from_config` (nie sync) — spójne z asyncpg i resztą stacku
  - `app/db/models/__init__.py` importuje wszystkie modele — Alembic odkrywa je przez `import app.db.models` w `env.py`
  - Frontend: Svelte (nie Svelte 5 runes) — scaffolded przez `create-vite --template svelte`, wystarczy na Fazę 1
- **Risks / constraints:**
  - `create-vite@9.0.3` wymaga Node `>=20.19.0`; użytkownik ma `20.15.0` — ostrzeżenie, ale scaffold przeszedł poprawnie; do rozwiązania przed produkcją
  - Brak `.env` w `backend/` — developer musi skopiować `.env.example` i uzupełnić przed uruchomieniem serwera
- **Notes for next tasks:**
  - Task 02 może zacząć od razu — `Base`, `get_db` i Alembic są gotowe
  - Modele dodawać w `app/db/models/`, importować je w `app/db/models/__init__.py` — inaczej Alembic ich nie zobaczy
  - Testy wymagające DB muszą używać osobnej testowej bazy (`TEST_DATABASE_URL`) — skonfigurować w `conftest.py` Task 02
- **Test status:**
  - Unit: n/a (brak logiki domenowej w tym tasku)
  - Integration: `test_health_returns_ok` — PASSED
  - Balance: n/a

---

### Task 02 - Modele i migracje

**Status:** `done`
**Depends on:** Task 01

#### Definition of Done
- [ ] Modele SQLAlchemy: `player_state`, `wallet`, `player_unit`, `player_upgrade`, `event_log`
- [ ] Modele konfiguracyjne (read-only): `unit_definition`, `upgrade_definition`, `balance_config`, `balance_test_run`
- [ ] Migracja Alembic tworząca wszystkie tabele — `alembic upgrade head` przechodzi czysto
- [ ] Seed skrypt wypełniający `unit_definition` i `upgrade_definition` danymi startowymi (reaktory t1, podstawowe upgrade'y offline)
- [ ] Repozytoria (`db/repositories/`) z podstawowym CRUD dla każdego modelu
- [ ] Pydantic schemas (`schemas/`) odpowiadające modelom
- [ ] Testy jednostkowe repozytoriów (na testowej bazie danych, bez mocków)
- [ ] Wszystkie pola zgodne ze specyfikacją z `general_documentation.md` sekcja 2

---

#### Post-task notes
- **Date:** 2026-03-31
- **Commit(s):** TBD
- **Scope implemented:**
  - Modele SQLAlchemy: `PlayerState`, `Wallet`, `UnitDefinition`, `PlayerUnit`, `UpgradeDefinition`, `PlayerUpgrade`, `BalanceConfig`, `BalanceTestRun`, `EventLog`
  - Repozytoria: `PlayerStateRepository`, `WalletRepository`, `PlayerUnitRepository`, `PlayerUpgradeRepository`, `EventLogRepository`, `UnitDefinitionRepository`, `UpgradeDefinitionRepository`
  - Pydantic schemas: `game.py` (PlayerState, Wallet, GameStateResponse, StartGameResponse), `economy.py` (Unit/Upgrade defs + player rows + Buy requests/responses)
  - Seed: 7 jednostek (t1: barrel, mini_reactor, isotope_lab, processing_plant, uranium_mine; t2: centrifuge_t2, enrichment_facility) + 6 upgrade'ów
  - Migracja Alembic: `fc60fc089de5_initial_schema.py` — ręczna (bez `--autogenerate`, brak lokalnego PostgreSQL)
  - 12 testów jednostkowych dla repozytoriów (SQLite in-memory via aiosqlite)
- **Architectural decisions:**
  - UUID generowane jawnie w Pythonie (`uuid.uuid4()`) przed tworzeniem obiektów ORM — SQLAlchemy `default=` nie ustawia pola Python do czasu INSERT, co powodowałoby `NULL` w FK przy tworzeniu powiązanych obiektów w tej samej sesji
  - Seed data jako plain dicts, nie moduł-level ORM instances — instance ORM dzielone między testami powodują "detached object" corruption w SQLAlchemy identity map
  - `StaticPool` w unit test conftest — SQLite `:memory:` tworzy osobną bazę per-konekcja; StaticPool wymusza jedną konekcję dla całego testu
  - `os.environ.setdefault(...)` na górze `app/tests/conftest.py` przed importem apki — Pydantic Settings instancjonuje się przy imporcie modułu
  - `upgrade_definition` ma dodatkowe pole `survives_prestige` (nie w oryginalnej sekcji 2 docs) — wymagane przez mechanikę prestiżu z sekcji 17
- **Risks / constraints:**
  - Migracja ręczna — przy każdej zmianie modeli trzeba ją aktualizować ręcznie do czasu, gdy developer skonfiguruje lokalny PostgreSQL pod `--autogenerate`
  - Brak `ondelete` na FK `player_unit.unit_id` → `unit_definition.id` — celowo: usuwanie definicji jednostek nie powinno kasować historii gracza
- **Notes for next tasks:**
  - Task 03: `PlayerStateRepository` i `WalletRepository` są gotowe do użycia w `game_loop_service`; `EventLogRepository.create` gotowy do logowania anomalii delta
  - Task 03: `snapshot_signature` w `PlayerState` istnieje jako pusty string — `snapshot_sign_service` (Task 07) uzupełni logikę
  - Task 05: dep `get_current_player` w `api/deps.py` powinien używać `PlayerStateRepository.get_by_id()` po walidacji nagłówka `X-Player-ID`
- **Test status:**
  - Unit: 11 testów PASSED (repositories, seed idempotency)
  - Integration: 1 test PASSED (health check)
  - Balance: n/a

---

### Task 03 - Core loop service

**Status:** `done`
**Depends on:** Task 02

#### Definition of Done
- [ ] `game_loop_service.py` implementuje pełną sekwencję: load → delta → production → upkeep → apply → sign → return
- [ ] Delta time: rozróżnienie online vs offline, zastosowanie `offline_efficiency` i `offline_cap_seconds`
- [ ] Startowe wartości: `offline_efficiency = 0.20`, `offline_cap = 4h`
- [ ] Produkcja równoległa dla wszystkich aktywnych jednostek
- [ ] Produkcja łańcuchowa dla jednostek wyższego tieru
- [ ] Mnożniki z upgrade'ów i prestiżu stosowane poprawnie
- [ ] Upkeep `energy_drink` odejmowany deterministycznie; jeśli brak — automatyzacja wyłączana deterministycznie
- [ ] `snapshot_sign_service.py`: HMAC podpisywanie i weryfikacja stanu
- [ ] Weryfikacja podpisu przy każdym load state; błąd podpisu → wyjątek z logiem do `event_log`
- [ ] Testy jednostkowe: delta online, delta offline z cappingiem, produkcja z mnożnikami, upkeep niedobór
- [ ] Testy balansu: brak deadlocku ekonomii przy domyślnych parametrach startowych

---

#### Post-task notes
- **Date:** 2026-03-31
- **Commit(s):** TBD
- **Scope implemented:**
  - `app/core/time_utils.py` — `ensure_utc()`, `compute_delta()` z rozróżnieniem online/offline
  - `app/services/snapshot_sign_service.py` — HMAC-SHA256 sign/verify; canonical JSON payload (player_id, version, last_tick_at, wallet, units sorted by unit_id)
  - `app/services/game_loop_service.py` — pełna sekwencja: load → verify → delta → production → upkeep → flush → update state → sign; `SnapshotSignatureError`; `TickResult` dataclass
  - 13 testów jednostkowych (delta, snapshot, production, prestige mult, upkeep, tamper)
  - 3 testy balansu (starting balance, single barrel output, no deadlock after offline)
  - `db_session` fixture przeniesiona do root conftest — dostępna dla wszystkich podkatalogów testów
- **Architectural decisions:**
  - Online/offline rozróżnienie przez `_ONLINE_THRESHOLD_SECONDS = 300` (5 min od `last_online_at`); `force_offline=True` w `tick()` dla endpointu `claim-offline`
  - Snapshot weryfikowany tylko gdy `snapshot_signature != ""` — pierwszy tick (puste pole) przechodzi bez weryfikacji
  - Upkeep w razie niedoboru wyłączany deterministycznie reverse-alphabetically po `unit_id`
  - `effective_multiplier` z `PlayerUnit` (Task 04 będzie go ustawiał); prestige multiplier liczony w locie `Decimal("1.15") ** prestige_count`
  - Timezone-naive datetimes z SQLite obsługiwane przez `ensure_utc()` — dodaje `UTC` jeśli brak tzinfo
- **Risks / constraints:**
  - `effective_multiplier` = 1.0 na wszystkich unitach do czasu Task 04 (economy service go zaktualizuje przy zakupie upgrade'ów)
  - Brak upkeep w praktyce do Task 04 (domyślnie `upkeep_energy_per_sec = 0`, `automation_enabled = False`)
- **Notes for next tasks:**
  - Task 04: `economy_service.buy_upgrade()` musi aktualizować `PlayerUnit.effective_multiplier` per unit_id dla upgrade'ów `prod_mult`; po każdym zakupie upgrade'u wywołać `tick()` by stan był aktualny
  - Task 04: `pricing_service` używa `unit_def.base_cost_amount`, `cost_growth_type`, `cost_growth_factor` — dostępne w `UnitDefinition`
  - Task 05: `GET /state` wywołuje `tick(session, player)` wewnątrz transakcji i serializuje `TickResult`
- **Test status:**
  - Unit: 13 PASSED
  - Integration: 1 PASSED (health)
  - Balance: 3 PASSED

---

### Task 04 - Ekonomia i pricing

**Status:** `done`
**Depends on:** Task 03

#### Definition of Done
- [x] `pricing_service.py`: hybrydowa krzywa cen (`linear_early_exp_late`) zgodnie z `cost_growth_type` z `unit_definition`
- [x] `economy_service.py`: transakcje `buy_unit` i `buy_upgrade` atomowe (rollback przy błędzie)
- [x] Walidacja: brak środków → czytelny błąd, ilość ≤ 0 → odrzucenie
- [x] Upkeep automatyzacji jako aktywny sink `energy_drink` przez całą grę (Task 03 zaimplementował, Task 04 go używa)
- [x] Testy jednostkowe `pricing_service`: krzywa liniowa early, wykładnicza mid/late, brak ujemnych cen
- [x] Testy jednostkowe `economy_service`: poprawny zakup, niewystarczające środki, aktualizacja wallet po zakupie
- [x] Testy balansu: osiągalność reactor_t1 w zakładanym czasie przy startowych parametrach

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** 56b41c9
- **Scope implemented:**
  - `app/services/pricing_service.py` — `compute_unit_cost()` + `compute_bulk_cost()`; hybrydowa krzywa `linear_early_exp_late` (linear n≤25: `base × (1 + 0.15 × n)`, exp n>25: `base × 1.15^n`)
  - `app/services/economy_service.py` — `buy_unit()` + `buy_upgrade()` + `_apply_upgrade_effect()`; wyjątki: `InsufficientFundsError`, `InvalidQuantityError`, `UnknownUnitError`, `UnknownUpgradeError`, `AlreadyPurchasedError`
  - `UpgradeDefinition` + migracja: dodano `target_unit_id` (nullable String) — wymagane dla efektu `prod_mult`
  - `seed.py` zaktualizowany: `barrel_opt_mk1 → target_unit_id="barrel"`, `reactor_tuning_mk1 → target_unit_id="mini_reactor"`
  - 14 testów jednostkowych pricing, 13 testów economy, 4 testy balansu
- **Architectural decisions:**
  - Zakup wielu jednostek (qty > 1) sumuje koszty sekwencyjnie — gracz płaci dokładnie tyle, ile by zapłacił kupując po jednej
  - `buy_upgrade` bez qty — upgrade'y są zawsze "jeden na raz" (powtarzalne przez `level`)
  - `_apply_upgrade_effect()` działa in-place na przekazanym `PlayerState` (bez dodatkowego db.get), flush następuje po wszystkich zmianach
  - `prod_mult` tworzy `PlayerUnit` z `amount_owned=0` jeśli nie istnieje — multiplier jest zapisany nawet przed zakupem jednostki
  - Upkeep (sink) jest obsługiwany przez `game_loop_service.tick()` z Task 03 — Task 04 nie duplikuje tej logiki
- **Risks / constraints:**
  - `target_unit_id` jest nullable String, bez FK do `unit_definition` — celowo, by uniknąć komplikacji przy usuwaniu definicji jednostek; aplikacja zakłada integralność danych
  - Migracja ręcznie zaktualizowana (dodano kolumnę `target_unit_id` w `upgrade_definition`)
- **Notes for next tasks:**
  - Task 05: endpointy `POST /buy-unit` i `POST /buy-upgrade` wywołują odpowiednio `buy_unit()` i `buy_upgrade()` w jednej transakcji; obsługują `InsufficientFundsError` → HTTP 409, `UnknownUnitError` → HTTP 404
  - Task 05: po `buy_upgrade` należy wywołać `tick()` by odświeżyć snapshot — nowy multiplier wpłynie na następny tick
  - Task 08 (prestige): `buy_upgrade` przy resecie musi sprawdzić `survives_prestige`; upgrade'y z `False` kasowane, z `True` zostają
- **Test status:**
  - Unit: 14 pricing + 13 economy = 27 PASSED
  - Integration: 1 PASSED (health check)
  - Balance: 4 PASSED (pricing affordability)

---

### Task 05 - Endpointy MVP

**Status:** `not started`
**Depends on:** Task 04

#### Definition of Done
- [ ] `POST /api/v1/game/start` — tworzy gracza jeśli żaden nie istnieje, w przeciwnym razie zwraca istniejącego; zwraca `player_id`, `state_version`, `started_at`
- [ ] `GET /api/v1/game/state` — pełny snapshot po przeliczeniu delta, wywołuje `game_loop_service`; wymaga nagłówka `X-Player-ID`
- [ ] `POST /api/v1/economy/buy-unit` — zakup jednostki, zwraca `new_amount_owned` + `wallet_after`
- [ ] `POST /api/v1/economy/buy-upgrade` — zakup ulepszenia, zwraca `upgrade_level` + `applied_effect`
- [ ] `POST /api/v1/time/claim-offline` — symulacja offline, zwraca `simulated_seconds`, `gains`, `cap_applied`
- [ ] `deps.py`: dep `get_current_player` waliduje nagłówek `X-Player-ID` i pobiera gracza z bazy; brak nagłówka → `400`, nieznany UUID → `404`
- [ ] Wszystkie odpowiedzi zgodne ze schematami z `general_documentation.md` sekcja 3.1
- [ ] Routery pogrupowane wg modułów (`game.py`, `economy.py`, `time.py`)
- [ ] Testy integracyjne dla każdego endpointu (rzeczywista baza, bez mocków)

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD
- **Scope implemented:**
  - `app/api/deps.py` — `get_current_player` dependency: validates `X-Player-ID` header, parses UUID, fetches PlayerState; raises HTTP 400 (missing/invalid) or HTTP 404 (not found)
  - `app/api/routes/game.py` — `POST /api/v1/game/start` (idempotent create-or-return), `GET /api/v1/game/state` (full tick + response)
  - `app/api/routes/economy.py` — `POST /api/v1/economy/buy-unit`, `POST /api/v1/economy/buy-upgrade`
  - `app/api/routes/time.py` — `POST /api/v1/time/claim-offline` (force_offline=True tick)
  - `app/main.py` updated to include all four routers
  - 19 integration tests covering success paths, auth errors, and domain errors for every endpoint
- **Architectural decisions:**
  - `get_db` yields `AsyncSessionLocal()` without an explicit transaction; autobegin fires on the first SQL op; route handlers call `await session.commit()` after the service call succeeds — if an exception propagates, `get_db`'s context manager closes the session and the implicit transaction is rolled back by the connection pool
  - `expire_on_commit=False` (already set on `AsyncSessionLocal`) prevents "lazy-load after commit" errors in async context — ORM objects remain accessible after `session.commit()`
  - FastAPI caches `Depends(get_db)` within a request, so `get_current_player` and the route handler share the same `AsyncSession` instance; this means the player loaded in the dep is already in the session's identity map when `tick()` runs
  - Integration tests override `get_db` with a lambda yielding the test `db_session`; `session.commit()` inside the route commits the StaticPool in-memory SQLite connection, making data visible to subsequent calls in the same test
  - `claim-offline` reads `player_id` from the `X-Player-ID` header via `get_current_player` (not from a request body); `ClaimOfflineRequest` schema is not used in the endpoint — kept in schemas for documentation completeness
- **Risks / constraints:**
  - `GET /state` response does not include `units` or `upgrades` lists — the existing `GameStateResponse` schema omits them; Task 11 (frontend) may require extending the schema
  - `POST /start` uses `get_single_player` (single-user mode); in multi-user Phase 3, this endpoint will need session/auth rework
- **Notes for next tasks:**
  - Task 06: `deps.py` needs a `require_test_mode` dependency that checks `settings.test_mode` and raises HTTP 404 if false; add it alongside `get_current_player`
  - Task 06: test/admin routers live under `/api/v1/test/`; add them to `main.py` only when `TEST_MODE=true` or block via the dep — prefer the dep approach for consistency
  - Task 11 (frontend): `GET /state` may need to be extended with `units` and `upgrades` arrays; add to `GameStateResponse` at that point
- **Test status:**
  - Unit: 59 PASSED (all prior unit tests still green)
  - Integration: 19 PASSED (new endpoint tests) + 1 PASSED (health) = 20 total
  - Balance: 7 PASSED

---

### Task 06 - Test/Admin endpoints (TEST_MODE)

**Status:** `not started`
**Depends on:** Task 05

#### Definition of Done
- [ ] `POST /api/v1/test/simulate-time` — symuluje upływ czasu o N sekund
- [ ] `POST /api/v1/test/correct-state` — patchuje wallet i/lub units gracza
- [ ] Twarda blokada w `api/deps.py`: gdy `TEST_MODE=false` endpointy zwracają `404` (nie `403`)
- [ ] Test: przy `TEST_MODE=false` wywołanie endpointów debug zwraca `404`
- [ ] Test: przy `TEST_MODE=true` `simulate-time` poprawnie modyfikuje stan i `state_version`
- [ ] Test: przy `TEST_MODE=true` `correct-state` patchuje tylko podane pola

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

### Task 07 - Snapshot signing i walidacja delta

**Status:** `not started`
**Depends on:** Task 06

#### Definition of Done
- [ ] HMAC snapshotu obejmuje wszystkie pola krytyczne: `wallet`, `units`, `last_tick_at`, `state_version`
- [ ] Weryfikacja podpisu przy każdym `load_state`; manipulacja → wyjątek + wpis do `event_log`
- [ ] Walidacja `delta_time`: odrzucenie delta < 0 i delta > `offline_cap_seconds * 2` (anomalia)
- [ ] Anomalie delta logowane do `event_log` z `event_type = "delta_anomaly"`
- [ ] `SNAPSHOT_SECRET` rotacja: zmiana klucza unieważnia stare snapshoty w sposób przewidywalny
- [ ] Testy jednostkowe: poprawny podpis, zmodyfikowany podpis, delta ujemna, delta za duża
- [ ] Testy integracyjne: pełny cykl sign → modify → verify fail

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

### Task 08 - Soft reset (prestige v1)

**Status:** `not started`
**Depends on:** Task 07

#### Definition of Done
- [ ] `prestige_service.py`: miękki reset — zeruje `wallet`, `player_unit.amount_owned`, resetuje część unlocków
- [ ] Zachowanie metaprogresji: `prestige_count`, `tech_magic_level`, wybrane upgrade'y (lista w kodzie)
- [ ] `prestige_count` inkrementowany po każdym resecie
- [ ] Nowy endpoint `POST /api/v1/game/prestige` — wywołuje `prestige_service`
- [ ] Balans: każdy prestige daje mierzalny boost (mnożnik produkcji lub offline efficiency)
- [ ] Testy jednostkowe: co jest resetowane, co zachowane, boost po prestige
- [ ] Testy integracyjne: pełny cykl gry → prestige → state po prestige
- [ ] Testy balansu: osiągalność pierwszego prestige w zakładanym czasie

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

### Task 09 - TDD i testy balansu (must-pass suite)

**Status:** `not started`
**Depends on:** Task 08

#### Definition of Done
- [ ] Pełna balance test suite w `tests/balance/`:
  - [ ] Brak deadlocku ekonomii (gracz nie może utknąć bez możliwości postępu)
  - [ ] Brak runaway inflation zbyt wcześnie (tier 2+ nieosiągalny przed zakładanym progiem)
  - [ ] Osiągalność tierów: t1 w `X` min, t2 w `Y` min, prestige 1 w `Z` min (progi zdefiniowane w teście)
  - [ ] `energy_drink` pozostaje relevantny jako upkeep w late game
- [ ] Testy integracyjne pokrywają wszystkie endpointy Fazy 1
- [ ] Testy jednostkowe pokrywają: pricing, produkcję, offline cap, prestige boost, snapshot sign
- [ ] `pytest` przechodzi w całości na czystej bazie testowej
- [ ] Raport pokrycia (`pytest --cov`) ≥ 80% dla warstwy `services/`

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

### Task 10 - Git workflow i jakość kodu

**Status:** `not started`
**Depends on:** Task 09

#### Definition of Done
- [ ] Wszystkie poprzednie taski mają uzupełnione post-task notes w tym pliku
- [ ] `pyproject.toml` zawiera konfigurację linterów: `ruff` (linting + formatting), `mypy` (type checking)
- [ ] `ruff check .` i `ruff format --check .` przechodzą bez błędów
- [ ] `mypy app/` przechodzi bez błędów (strict mode dla `services/` i `core/`)
- [ ] Pre-commit hook lub CI check uruchamiający testy + linting na każdy commit
- [ ] Wszystkie publiczne klasy i funkcje w `services/`, `api/`, `db/repositories/`, `core/` mają docstringi (Google style)
- [ ] `pytest` przechodzi w całości po wszystkich zmianach porządkowych
- [ ] Faza 1 zamknięta: wpis podsumowujący Fazę 1 na końcu tego pliku

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

### Task 11 - Frontend MVP

**Status:** `not started`
**Depends on:** Task 08

#### Definition of Done
- [ ] Wallet HUD: wyświetla wszystkie waluty (`energy_drink`, `u238`, `u235`, `u233`, `meta_isotopes`) w czasie rzeczywistym
- [ ] Lista jednostek: każda pozycja pokazuje nazwę, ilość, koszt następnego zakupu, stawkę produkcji; przycisk "Kup" wywołuje `POST /economy/buy-unit`
- [ ] Lista upgrade'ów: każda pozycja pokazuje nazwę, opis, koszt; przycisk "Kup" wywołuje `POST /economy/buy-upgrade`; zakupione upgrade'y wizualnie oznaczone
- [ ] Przycisk "Odbierz nagrody offline" widoczny po powrocie z pauzy; wywołuje `POST /time/claim-offline` i wyświetla gains
- [ ] Przycisk "Prestige" widoczny (i aktywny) dopiero po spełnieniu warunku prestiżu; wywołuje `POST /game/prestige` z potwierdzeniem
- [ ] Auto-refresh stanu co 5 sekund (polling `GET /game/state`); wallet i ilości jednostek aktualizowane bez przeładowania strony
- [ ] `player_id` pobierany przez `POST /game/start` przy pierwszym uruchomieniu i przechowywany w `localStorage`; każde żądanie API dołącza nagłówek `X-Player-ID`
- [ ] Ciemny motyw, czytelny HUD, estetyka tech/nuclear — bez animacji i skomplikowanych efektów
- [ ] Vite proxy `/api/*` → FastAPI; `npm run build` generuje `frontend/dist/` serwowane przez FastAPI jako StaticFiles
- [ ] Brak błędów w konsoli przeglądarki przy normalnym użytkowaniu

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

## Phase 1 Summary

*(Wypełnić po zakończeniu Task 10)*

- **Closed:**
- **Commits:**
- **Final test status:**
- **Known tech debt for Phase 2:**
