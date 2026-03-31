# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

UranIncremental is an idle/incremental game backend inspired by Swarm Simulator. Theme: uranium + energy drinks (memetic sci-fi), humorous techno-magic style. Single-user locally, but architecture must be ready to extend to multi-user.

Tech stack: `Python 3.12+`, `FastAPI`, `PostgreSQL`, `SQLAlchemy`, `Alembic`, `Pydantic`.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run server (local)
uvicorn app.main:app --reload

# Run all tests
pytest

# Run tests for a single module
pytest backend/tests/unit/test_pricing_service.py

# Run only balance tests
pytest backend/tests/balance/

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

Environment variables (see `.env.example`):
- `DATABASE_URL` — PostgreSQL connection string
- `SNAPSHOT_SECRET` — HMAC key for snapshot signing
- `TEST_MODE` — `true` enables debug endpoints (`/api/v1/test/*`), `false` blocks them hard

## Architecture

### Core game loop (`services/game_loop_service.py`)
On every `GET /api/v1/game/state` call:
1. Load state + verify `snapshot_signature` (HMAC)
2. Compute `delta = now_utc - last_tick_at`; apply `offline_efficiency` + `offline_cap_seconds` if offline
3. Production pass: parallel production for all active units, chain production for higher-tier units, apply upgrade/prestige multipliers
4. Automation upkeep: deduct `energy_drink` as fuel; deterministically disable automation if insufficient
5. Apply gains to `wallet`, update `last_tick_at` / `state_version`
6. Re-sign snapshot, return state

### Key invariant
`energy_drink` (base currency) must never become irrelevant — it serves as automation upkeep throughout the entire game.

### Service layer responsibilities
- `game_loop_service` — delta time, production, upkeep, snapshot signing
- `economy_service` — buy-unit / buy-upgrade transactions
- `pricing_service` — hybrid cost curve (linear early → exponential mid/late), `cost_growth_type: linear_early_exp_late`
- `offline_service` — offline simulation, cap, efficiency
- `prestige_service` — soft reset, metaprogression retention
- `balance_service` — balance config read/write, proposal/approval flow
- `snapshot_sign_service` — HMAC sign/verify of player state

### Balance config flow
Balance changes follow a strict approval pipeline: AI proposal → `pending` → `tests=passed` → `admin_approved` → `active`. Config is read-only in prod (`TEST_MODE=false`). No config is ever published without passing the full balance test suite.

### Test/Admin endpoints
All routes under `/api/v1/test/` (`simulate-time`, `correct-state`) must be hard-blocked when `TEST_MODE=false`. This check lives in `api/deps.py`.

## Implementation phases

- **Phase 1 (current):** MVP+ Core — full idle loop, economy, prestige v1, TDD, test-mode. Tasks are sequential: finish Task N before starting Task N+1.
- **Phase 2:** AI balance proposals + approval flow, AI content generator, minigames, seasonal sinks.
- **Phase 3:** Liveops, multi-user prep, performance, security hardening.

Phase 2 and 3 tasks are not planned until the previous phase is complete.

## Task workflow (mandatory)

After completing each task, append a section to `documentations/task_notes/phase_1.md` with:
- Task ID and name
- Date and commit hash(es)
- Scope implemented
- Architectural decisions and rationale
- Risks / constraints
- Notes for subsequent tasks
- Test status: Unit / Integration / Balance

This note is part of the Definition of Done and must be written before the task is considered complete.

## TDD policy (mandatory)

1. Every functional change starts with a failing test (red → green → refactor).
2. A task is not done without green tests covering its scope.
3. Every bugfix requires a reproducing test written before the fix.
4. Balance tests are treated as release-blocking.
5. Per task minimum: unit tests for domain logic + integration tests for changed endpoints + balance regression if the task touches the economy.

## Language rules (mandatory)

All technical code must be fully in English:
- File and folder names, class/function/variable/constant names
- API endpoints, schemas, model fields
- Technical comments, test names, log messages

Polish is allowed **only** in player-facing strings: HUD elements, unit/upgrade descriptions, flavor text, UI messages.

## Docstrings (mandatory)

Every public class and function in `services/`, `api/`, `db/repositories/`, and `core/` must have a Google-style docstring with at minimum: short description, `Args`, `Returns`, `Raises` (when relevant). Test helpers follow the same style; test functions themselves may use shorter docstrings.

## Commit discipline

- Small, clean, frequent commits.
- Commit message is written **after** implementation and must describe what was actually done.
- Each commit must pass local tests for the modified module before being committed.
