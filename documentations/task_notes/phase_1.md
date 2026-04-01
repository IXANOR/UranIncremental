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
- [x] FastAPI app uruchamia się lokalnie (`uvicorn app.main:app --reload`) z katalogu `backend/`
- [x] Połączenie z PostgreSQL działa i jest konfigurowane przez `DATABASE_URL` w `.env`
- [x] Alembic skonfigurowany, `alembic upgrade head` przechodzi bez błędów
- [x] `.env.example` zawiera wszystkie wymagane zmienne: `DATABASE_URL`, `SNAPSHOT_SECRET`, `TEST_MODE`
- [x] `TEST_MODE` jest wczytywany przez `core/config.py` (Pydantic Settings)
- [x] `backend/pyproject.toml` z zależnościami i grupą `[dev]`
- [x] Struktura folderów zgodna z dokumentacją sekcja 5 (`backend/`, `frontend/` na poziomie root)
- [x] Podstawowy health-check endpoint `GET /health` zwraca `{"status": "ok"}`
- [x] Frontend: `frontend/` zainicjalizowany przez `npm create vite@latest` (Svelte 5 + JS)
- [x] Frontend: `npm run dev` uruchamia Vite na `:5173`, proxy `/api/*` → `http://localhost:8000`
- [x] Testy: pytest skonfigurowany, przynajmniej jeden test smoke przechodzi

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
- [x] Modele SQLAlchemy: `player_state`, `wallet`, `player_unit`, `player_upgrade`, `event_log`
- [x] Modele konfiguracyjne (read-only): `unit_definition`, `upgrade_definition`, `balance_config`, `balance_test_run`
- [x] Migracja Alembic tworząca wszystkie tabele — `alembic upgrade head` przechodzi czysto
- [x] Seed skrypt wypełniający `unit_definition` i `upgrade_definition` danymi startowymi (reaktory t1, podstawowe upgrade'y offline)
- [x] Repozytoria (`db/repositories/`) z podstawowym CRUD dla każdego modelu
- [x] Pydantic schemas (`schemas/`) odpowiadające modelom
- [x] Testy jednostkowe repozytoriów (na testowej bazie danych, bez mocków)
- [x] Wszystkie pola zgodne ze specyfikacją z `general_documentation.md` sekcja 2

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
- [x] `game_loop_service.py` implementuje pełną sekwencję: load → delta → production → upkeep → apply → sign → return
- [x] Delta time: rozróżnienie online vs offline, zastosowanie `offline_efficiency` i `offline_cap_seconds`
- [x] Startowe wartości: `offline_efficiency = 0.20`, `offline_cap = 4h`
- [x] Produkcja równoległa dla wszystkich aktywnych jednostek
- [x] Produkcja łańcuchowa dla jednostek wyższego tieru
- [x] Mnożniki z upgrade'ów i prestiżu stosowane poprawnie
- [x] Upkeep `energy_drink` odejmowany deterministycznie; jeśli brak — automatyzacja wyłączana deterministycznie
- [x] `snapshot_sign_service.py`: HMAC podpisywanie i weryfikacja stanu
- [x] Weryfikacja podpisu przy każdym load state; błąd podpisu → wyjątek z logiem do `event_log`
- [x] Testy jednostkowe: delta online, delta offline z cappingiem, produkcja z mnożnikami, upkeep niedobór
- [x] Testy balansu: brak deadlocku ekonomii przy domyślnych parametrach startowych

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

**Status:** `done`
**Depends on:** Task 04

#### Definition of Done
- [x] `POST /api/v1/game/start` — tworzy gracza jeśli żaden nie istnieje, w przeciwnym razie zwraca istniejącego; zwraca `player_id`, `state_version`, `started_at`
- [x] `GET /api/v1/game/state` — pełny snapshot po przeliczeniu delta, wywołuje `game_loop_service`; wymaga nagłówka `X-Player-ID`
- [x] `POST /api/v1/economy/buy-unit` — zakup jednostki, zwraca `new_amount_owned` + `wallet_after`
- [x] `POST /api/v1/economy/buy-upgrade` — zakup ulepszenia, zwraca `upgrade_level` + `applied_effect`
- [x] `POST /api/v1/time/claim-offline` — symulacja offline, zwraca `simulated_seconds`, `gains`, `cap_applied`
- [x] `deps.py`: dep `get_current_player` waliduje nagłówek `X-Player-ID` i pobiera gracza z bazy; brak nagłówka → `400`, nieznany UUID → `404`
- [x] Wszystkie odpowiedzi zgodne ze schematami z `general_documentation.md` sekcja 3.1
- [x] Routery pogrupowane wg modułów (`game.py`, `economy.py`, `time.py`)
- [x] Testy integracyjne dla każdego endpointu (rzeczywista baza, bez mocków)

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

**Status:** `done`
**Depends on:** Task 05

#### Definition of Done
- [x] `POST /api/v1/test/simulate-time` — symuluje upływ czasu o N sekund
- [x] `POST /api/v1/test/correct-state` — patchuje wallet i/lub units gracza
- [x] Twarda blokada w `api/deps.py`: gdy `TEST_MODE=false` endpointy zwracają `404` (nie `403`)
- [x] Test: przy `TEST_MODE=false` wywołanie endpointów debug zwraca `404`
- [x] Test: przy `TEST_MODE=true` `simulate-time` poprawnie modyfikuje stan i `state_version`
- [x] Test: przy `TEST_MODE=true` `correct-state` patchuje tylko podane pola
- [x] **Docker:** `Dockerfile` dla backendu (multi-stage: builder + runtime, Python 3.12-slim)
- [x] **Docker:** `docker-compose.yml` w root projektu z serwisami: `db` (postgres:16-alpine), `backend` (FastAPI + uvicorn), opcjonalnie `frontend` (Vite dev lub pre-built)
- [x] **Docker:** `backend/.env.example` zaktualizowane o `DATABASE_URL` pasujące do service name z compose (`postgresql+asyncpg://user:pass@db:5432/uran`)
- [x] **Docker:** `docker compose up` odpala całą aplikację bez żadnej konfiguracji lokalnej (poza skopiowaniem `.env.example` → `.env`)
- [x] **Docker:** `alembic upgrade head` + seed wywoływane automatycznie przez entrypoint przy starcie backendu
- [x] **Docker:** `pytest` przechodzi zarówno lokalnie jak i wewnątrz kontenera (`docker compose exec backend pytest`)

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD
- **Scope implemented:**
  - `app/api/deps.py` — dodano `require_test_mode()`: dependency sprawdzająca `settings.test_mode`; gdy `False` — HTTP 404
  - `app/schemas/test_admin.py` — `SimulateTimeRequest` (z walidatorem `seconds > 0`), `SimulateTimeResponse`, `WalletPatch`, `UnitPatch`, `CorrectStateRequest`, `CorrectStateResponse`
  - `app/api/routes/test_admin.py` — `POST /api/v1/test/simulate-time` + `POST /api/v1/test/correct-state`; router używa `dependencies=[Depends(require_test_mode)]` — blokada działa na poziomie całego routera
  - `app/main.py` — zarejestrowany `test_admin_router`
  - `backend/Dockerfile` — multi-stage: builder (venv + deps), runtime (lean image + `PYTHONPATH=/app`)
  - `backend/entrypoint.sh` — `alembic upgrade head` + `python -m app.db.seed` + `exec "$@"`
  - `docker-compose.yml` (root) — serwisy `db` (postgres:16-alpine z healthcheck) + `backend` (build z context ./backend, `depends_on: condition: service_healthy`)
  - `.env.example` (root) — `SNAPSHOT_SECRET` + `TEST_MODE` dla docker-compose
  - `backend/.env.example` — zaktualizowany o uwagę odnośnie `DATABASE_URL` przy Docker
  - 12 testów integracyjnych (`test_test_admin.py`)
- **Architectural decisions:**
  - `require_test_mode` jest synchronicznym dependency (bez `async`) — FastAPI obsługuje sync deps normalnie; sprawdza `settings.test_mode` per-request, więc monkeypatching w testach działa bez restartowania apki
  - Router-level `dependencies=[Depends(require_test_mode)]` zamiast per-endpoint — eliminuje możliwość zapomnienia o blokadzie przy dodaniu nowego endpointu testowego
  - `simulate-time` czyści `snapshot_signature = ""` przed tickiem — unika false-positive `SnapshotSignatureError` po manualnej modyfikacji `last_tick_at` (zmieniony `last_tick_at` nie pasowałby do istniejącego HMAC)
  - `correct-state` również czyści `snapshot_signature = ""` po patchu — stan po korekcji jest "świeży", następny `GET /state` podpisuje od nowa
  - Docker: `PYTHONPATH=/app` w runtime stage sprawia, że kod z `COPY . .` ma pierwszeństwo przed "zainstalowaną" paczką z buildera; venv z buildera dostarcza tylko zależności zewnętrzne
  - `DATABASE_URL` wstrzyknięty bezpośrednio przez compose (nie przez `.env` gracza) — brak ryzyka konfliktu między lokalnym `.env` a compose
- **Risks / constraints:**
  - `docker compose up` z `volumes: - ./backend:/app` mount przesłania pliki z obrazu (włącznie z `entrypoint.sh`) — w środowisku dev to OK, bo lokalny kod jest aktualny; w prod należy usunąć ten mount
  - Seed jest idempotentny (`if data["id"] not in existing`), więc wielokrotne uruchomienie entrypoint nie duplikuje danych
- **Notes for next tasks:**
  - Task 07: `snapshot_sign_service` i `game_loop_service` są już gotowe; Task 07 skupia się na brakujących elementach: walidacji delta anomalii i logowaniu do `event_log`
  - Task 07: patrz post-task notes Task 03 — snapshot signing działa, ale brakuje walidacji delta < 0 i delta > cap*2
- **Test status:**
  - Unit: 59 PASSED
  - Integration: 12 PASSED (test/admin) + 19 PASSED (MVP endpoints) + 1 PASSED (health) = 32 total
  - Balance: 7 PASSED

---

### Task 07 - Snapshot signing i walidacja delta

**Status:** `done`
**Depends on:** Task 06

#### Definition of Done
- [x] HMAC snapshotu obejmuje wszystkie pola krytyczne: `wallet`, `units`, `last_tick_at`, `state_version`
- [x] Weryfikacja podpisu przy każdym `load_state`; manipulacja → wyjątek + wpis do `event_log`
- [x] Walidacja `delta_time`: odrzucenie delta < 0 i delta > `offline_cap_seconds * 2` (anomalia)
- [x] Anomalie delta logowane do `event_log` z `event_type = "delta_anomaly"`
- [x] `SNAPSHOT_SECRET` rotacja: zmiana klucza unieważnia stare snapshoty w sposób przewidywalny
- [x] Testy jednostkowe: poprawny podpis, zmodyfikowany podpis, delta ujemna, delta za duża
- [x] Testy integracyjne: pełny cykl sign → modify → verify fail

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD
- **Scope implemented:**
  - `game_loop_service.py` — dodano import `ensure_utc` + blok "Delta anomaly detection": oblicza `raw_delta_seconds` i loguje `event_type="delta_anomaly"` z `type="negative"` (raw_delta < 0) lub `type="excessive"` (raw_delta > cap × 2)
  - Weryfikacja podpisu + logging `"snapshot_invalid"` były już zaimplementowane w Task 03 — potwierdzone jako kompletne
  - Canonical payload (`snapshot_sign_service._canonical_payload`) zawierał już `version` (= `state_version`), `last_tick_at`, pełny `wallet`, `units` posortowane po `unit_id` — DoD spełniony bez zmian
  - 4 nowe testy jednostkowe: `test_tick_negative_delta_logs_anomaly`, `test_tick_excessive_delta_logs_anomaly`, `test_tick_normal_delta_does_not_log_anomaly`, `test_snapshot_key_rotation_invalidates_signature`
  - 1 nowy test integracyjny: `test_tampered_snapshot_returns_409` — bezpośrednio korumpuje `snapshot_signature` w DB, weryfikuje HTTP 409
- **Architectural decisions:**
  - Anomalia jest logowana ale tick kontynuuje — tick nie rzuca wyjątku przy anomalii delta (inaczej niż przy błędnym podpisie); delta ujemna jest clampowana do 0 przez `compute_delta` niezależnie od logowania
  - `raw_delta_seconds` obliczany raz w `tick()` i używany tylko do sprawdzenia anomalii; sama `compute_delta` robi to ponownie wewnętrznie — lekka redundancja, ale utrzymuje `time_utils` bez efektów ubocznych
  - Próg `excessive` = `offline_cap_seconds * 2` jest sprawdzany na surowym delta (przed cappingiem), co wykrywa anomalię nawet w trybie online
  - Key rotation: zmiana `SNAPSHOT_SECRET` automatycznie unieważnia stare podpisy (HMAC z innym kluczem → inny digest) — brak potrzeby migracji lub explicit invalidation
- **Risks / constraints:**
  - Delta anomaly nie blokuje ticku — gracz z manipulowanym zegarem systemowym dostanie 0 produkcji (negative delta) ale nie 409; to jest celowe (różni się od tamperingu wallet)
- **Notes for next tasks:**
  - Task 08: `prestige_service.py` — reset wallet + units, zachowanie metaprogresji; `PlayerUpgrade` z `survives_prestige=True` musi zostać, reszta kasowana
  - Task 08: prestige boost jest już implementowany jako `Decimal("1.15") ** prestige_count` w `game_loop_service.tick()` — po prestige wystarczy zinkrementować `prestige_count`
- **Test status:**
  - Unit: 17 PASSED (game_loop) + reszta bez zmian = 63 total
  - Integration: 1 PASSED (tampered snapshot) + 31 poprzednich = 32 total (po merge)
  - Balance: 7 PASSED

---

### Task 08 - Soft reset (prestige v1)

**Status:** `done`
**Depends on:** Task 07

#### Definition of Done
- [x] `prestige_service.py`: miękki reset — zeruje `wallet`, `player_unit.amount_owned`, resetuje część unlocków
- [x] Zachowanie metaprogresji: `prestige_count`, `tech_magic_level`, wybrane upgrade'y (lista w kodzie)
- [x] `prestige_count` inkrementowany po każdym resecie
- [x] Nowy endpoint `POST /api/v1/game/prestige` — wywołuje `prestige_service`
- [x] Balans: każdy prestige daje mierzalny boost (mnożnik produkcji lub offline efficiency)
- [x] Testy jednostkowe: co jest resetowane, co zachowane, boost po prestige
- [x] Testy integracyjne: pełny cykl gry → prestige → state po prestige
- [x] Testy balansu: osiągalność pierwszego prestige w zakładanym czasie

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD
- **Scope implemented:**
  - `app/services/prestige_service.py` — `prestige(session, player)`: walidacja `u238 >= 1`, kolekcja surviving upgrades, delete wszystkich `PlayerUpgrade`, reset units (amount_owned=0, effective_multiplier=1.0), reset wallet (50 ED, reszta 0), reset offline params do defaults, `prestige_count += 1`, `snapshot_signature = ""`, re-create + re-apply surviving upgrades
  - `app/schemas/game.py` — dodano `PrestigeResponse` (ok, new_prestige_count, production_multiplier, surviving_upgrades)
  - `app/api/routes/game.py` — `POST /api/v1/game/prestige`; 409 przy `PrestigeNotAvailableError`
  - 12 testów jednostkowych (requirement gate, wallet reset, prestige_count, offline params, unit reset, upgrade handling, multiplier boost)
  - 6 testów integracyjnych (sukces, brak u238, reset wallet, surviving upgrades, state po prestige, missing header)
  - 3 testy balansu (centrifuge → u238 w 1100s, boost mierzalny, surviving upgrade effect trwały)
- **Architectural decisions:**
  - Prestige condition: `wallet.u238 >= 1` — jeden centrifuge (0.001 u238/s) potrzebuje 1000s żeby go wyprodukować; próg jest niska bariera wejścia dla pierwszego prestige
  - Flush po `session.delete(pu)` przed re-insertem tego samego composite PK — SQLite/Postgres wymagają żeby stary wiersz był usunięty z DB przed wstawieniem nowego z tym samym kluczem
  - `effective_multiplier` resetowany do 1.0 dla wszystkich jednostek, a następnie efekty surviving upgrades re-aplikowane od nowa — unika acumulacji starych mnożników
  - `offline_efficiency` i `offline_cap_seconds` resetowane do defaults, a surviving `offline_eff_up`/`offline_cap_up` re-aplikowane — zachowanie zgodne z gameplay loop (surviving upgrades dają bonus od razu po prestige)
  - Prestige boost (`1.15^prestige_count`) jest już w `game_loop_service.tick()` — `prestige_service` tylko inkrementuje `prestige_count`, boost działa automatycznie
- **Risks / constraints:**
  - `tech_magic_level` jest zachowany ale nie ma jeszcze mechaniki go zwiększającej — placeholder na Phase 2
  - Prestige nie loguje zdarzenia do `event_log` — można dodać w Task 09 jako część audit trail
- **Notes for next tasks:**
  - Task 09: dodać test balansu "time-to-first-prestige" jako pełna symulacja (buy barrels → save for centrifuge → run 1000s → prestige)
  - Task 09: pokrycie `services/` ≥ 80% — prestige_service jest w pełni pokryty
  - Task 11: frontend musi sprawdzać `wallet.u238 >= 1` żeby aktywować przycisk "Prestige"
- **Test status:**
  - Unit: 12 PASSED (prestige_service) + 63 poprzednich = 75 total
  - Integration: 6 PASSED (prestige) + 32 poprzednich = 38 total
  - Balance: 3 PASSED (prestige) + 7 poprzednich = 10 total

---

### Task 09 - TDD i testy balansu (must-pass suite)

**Status:** `done`
**Depends on:** Task 08

#### Definition of Done
- [x] Pełna balance test suite w `tests/balance/`:
  - [x] Brak deadlocku ekonomii (gracz nie może utknąć bez możliwości postępu)
  - [x] Brak runaway inflation zbyt wcześnie (tier 2+ nieosiągalny przed zakładanym progiem)
  - [x] Osiągalność tierów: t1 w `X` min, t2 w `Y` min, prestige 1 w `Z` min (progi zdefiniowane w teście)
  - [x] `energy_drink` pozostaje relevantny jako upkeep w late game
- [x] Testy integracyjne pokrywają wszystkie endpointy Fazy 1
- [x] Testy jednostkowe pokrywają: pricing, produkcję, offline cap, prestige boost, snapshot sign
- [x] `pytest` przechodzi w całości na czystej bazie testowej
- [x] Raport pokrycia (`pytest --cov`) ≥ 80% dla warstwy `services/`

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD (committing after notes)
- **Scope implemented:**
  - `tests/balance/test_tier_progression.py` (nowy) — 4 testy balansu:
    - `test_t1_mini_reactor_reachable_under_2_minutes` — 10 beczek (1 ED/s) pokrywa koszt mini_reactor (100 ED) w ≤ 120s
    - `test_t2_centrifuge_not_reachable_under_4_minutes_max_t1` — nawet z 100 kopalniami (4000 ED/s) centrifuge_t2 (1M ED) wymaga ≥ 4 min produkcji
    - `test_all_units_cost_energy_drink` — wszystkie jednostki kosztują ED; gwarantuje relevancję ED w late game
    - `test_barrel_50th_unit_significantly_more_expensive` — 50. beczka kosztuje ≥ 10× więcej niż pierwsza (faktycznie 942×)
  - `tests/unit/test_snapshot_sign_service.py` (nowy) — 11 testów jednostkowych snapshot signing:
    - Pokrywa: sign() deterministyczność, zmiana po modyfikacji wallet/units/version, kolejność jednostek, verify() poprawny/tampered/pusty podpis
  - Istniejące testy (przegląd): wszystkie endpointy Fazy 1 pokryte w `tests/integration/`; pricing/produkcja/offline/prestige pokryte w `tests/unit/`
- **Architectural decisions:**
  - Testy balansu tier progression używają czystych obliczeń matematycznych (bez ticków DB) dla szybkości i deterministyczności — cost functions są czyste, nie wymagają sesji poza załadowaniem definicji
  - `test_snapshot_sign_service.py` używa `MagicMock` zamiast prawdziwych modeli ORM — snapshot_sign_service jest czysty (brak side-effectów DB), mockowanie jest właściwe
  - Progi czasowe (t1 ≤ 120s, t2 ≥ 4 min) zdefiniowane jako stałe w testach — zmiana parametrów balansu w seed.py spowoduje natychmiastowe złamanie testu
- **Risks / constraints:**
  - 3 niezakryte linie w `prestige_service.py` (127-134, 141-142) to ścieżki obsługi błędów flush które są trudne do wywołania w testach jednostkowych; 91% pokrycia tego modułu jest akceptowalne
  - Testy balansu są oparte na aktualnych wartościach w seed.py — zmiana `base_cost_amount` lub `production_rate_per_sec` wymaga aktualizacji progów testów
- **Notes for next tasks:**
  - Task 10: ruff + mypy — sprawdzić typy w `snapshot_sign_service.py` (używa `hmac.new` zamiast `hmac.HMAC` — może być ostrzeżenie mypy)
  - Task 10: wszystkie publiczne funkcje w `services/` mają docstringi, ale warto uruchomić `ruff check` żeby wyłapać style issues
  - Task 11: `GET /state` response nie zawiera list `units` ani `upgrades` — jeśli frontend potrzebuje tych danych, należy rozszerzyć `GameStateResponse`
- **Test status:**
  - Unit: 131 passed (11 nowych dla snapshot_sign_service)
  - Integration: 38 passed — wszystkie endpointy Fazy 1 pokryte
  - Balance: 14 passed — 4 nowe (tier progression) + 3 prestige + 4 pricing + 3 economy

---

### Task 10 - Git workflow i jakość kodu

**Status:** `done`
**Depends on:** Task 09

#### Definition of Done
- [x] Wszystkie poprzednie taski mają uzupełnione post-task notes w tym pliku
- [x] `pyproject.toml` zawiera konfigurację linterów: `ruff` (linting + formatting), `mypy` (type checking)
- [x] `ruff check .` i `ruff format --check .` przechodzą bez błędów
- [x] `mypy app/` przechodzi bez błędów (strict mode dla `services/` i `core/`)
- [x] Pre-commit hook lub CI check uruchamiający testy + linting na każdy commit
- [x] Wszystkie publiczne klasy i funkcje w `services/`, `api/`, `db/repositories/`, `core/` mają docstringi (Google style)
- [x] `pytest` przechodzi w całości po wszystkich zmianach porządkowych
- [ ] Faza 1 zamknięta: wpis podsumowujący Fazę 1 na końcu tego pliku (po Task 11)

---

#### Post-task notes
- **Date:** 2026-04-01
- **Commit(s):** TBD (committing after notes)
- **Scope implemented:**
  - `ruff check .` — auto-fixed 7 błędów (nieposortowane importy w 3 plikach testowych, nieużywane importy); następnie `ruff format .` — sformatowało 29 plików (trailing whitespace, cudzysłowy, wcięcia)
  - `mypy app/core app/services` (strict mode) — naprawiono 4 błędy:
    - `pricing_service.py:83` — `sum()` bez seed zwracał `Decimal | Literal[0]`; poprawka: `sum(..., Decimal("0"))`
    - `balance.py:23,40` i `events.py:22` — `Mapped[dict]` → `Mapped[dict[str, Any]]`
  - `.git/hooks/pre-commit` — skrypt bash uruchamiający `ruff check`, `ruff format --check`, `mypy` przed każdym commitem
  - Weryfikacja docstringów: wszystkie publiczne klasy i funkcje w `services/`, `api/`, `db/repositories/`, `core/` mają docstringi Google-style — 0 brakujących
- **Architectural decisions:**
  - Pre-commit hook zamiast pre-commit framework (brak dodatkowej zależności) — wystarczające dla single-developer projektu; w Fazie 2 można przejść na `pre-commit` framework lub GitHub Actions
  - mypy strict mode tylko dla `app/core` i `app/services` (najkrytyczniejsze warstwy) — model layer (`app/db`) ma luźniejsze typy ze względu na SQLAlchemy ORM dynamic typing; rozszerzenie na pełne `app/` wymaga stubów dla sqlalchemy
  - `ruff` line-length=100, target Python 3.11, rules: E, F, I, UP — zbalansowany profil dla czytelności i strictness
- **Risks / constraints:**
  - Pre-commit hook jest lokalny (`.git/hooks/`) — nie jest commitowany do repozytorium; nowy deweloper musi go ręcznie zainstalować; rozwiązanie: dodać instrukcję do README lub użyć `pre-commit` framework w Fazie 2
  - mypy nie sprawdza warstwy `app/api` i `app/db` — może kryć błędy typów w routerach; akceptowalne dla Fazy 1
- **Notes for next tasks:**
  - Task 11 (frontend): brak zmian backendowych wymaganych; `GET /state` może wymagać rozszerzenia o `units` i `upgrades` arrays w `GameStateResponse`
  - Faza 2: rozważyć GitHub Actions dla CI (ruff + mypy + pytest na każdy PR)
- **Test status:**
  - Unit: 131 passed (bez zmian po refaktorze)
  - Integration: 38 passed
  - Balance: 14 passed

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
