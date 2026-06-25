# Code and Test Report

Generated: 2026-06-25

---

## Project

AI Kanban Board — single-container MVP. FastAPI backend serves both the REST API and a statically-exported Next.js frontend. One board per authenticated user. AI chat sidebar powered by OpenRouter.

---

## Test suites

### Backend unit tests (pytest)

| File | Tests | Result |
|---|---|---|
| test_db.py | 7 | Passed |
| test_api.py | 12 | Passed |
| test_ai.py | 4 | Passed |
| test_ai_board.py | 7 | Passed |
| **Total** | **29** | **All passed** |

### Frontend unit tests (Vitest)

| File | Tests | Result |
|---|---|---|
| src/lib/kanban.test.ts | 3 | Passed |
| src/lib/auth.test.ts | 5 | Passed |
| src/components/KanbanBoard.test.tsx | 3 | Passed |
| src/components/LoginPage.test.tsx | 3 | Passed |
| src/components/AiChatSidebar.test.tsx | 3 | Passed |
| **Total** | **17** | **All passed** |

### Integration and E2E tests

| Suite | Transport | Result |
|---|---|---|
| scripts/integration_test.py | HTTP vs Docker container | Passed |
| scripts/validate_part11_e2e.py | HTTP vs Docker container | 4/4 suites passed |
| Playwright E2E (tests/kanban.spec.ts) | Browser vs Docker container | 3/3 passed |

Playwright tests require `docker compose up --build -d` before running.

---

## Coverage

### Backend (source files only)

| File | Stmts | Covered | Coverage | Notes |
|---|---|---|---|---|
| db.py | 261 | 241 | **92%** | |
| main.py | 300 | 248 | **83%** | |
| ai.py | 78 | 21 | **27%** | See below |
| **Total (source)** | **639** | **510** | **80%** | |

`ai.py` coverage is low by design: 57 uncovered lines are the live HTTP client that calls OpenRouter. All tests mock the HTTP layer; the live path is validated separately by `GET /api/ai/sanity` against the running container. Treating production-HTTP code as mock-only dead weight is the right call here.

`main.py` uncovered lines are mostly error branches (malformed request bodies, provider-down paths) and the static file fallback handler — all exercised by the E2E suite rather than unit tests.

`db.py` uncovered lines are edge-case error branches (duplicate position conflicts during reorder, connection teardown paths).

### Frontend (src/ files only)

| Area | Stmts | Branch | Funcs | Lines |
|---|---|---|---|---|
| src/components | 83% | 85% | 78% | 83% |
| src/lib/kanban.ts | 86% | 74% | 100% | 86% |
| src/lib/auth.ts | 47% | 67% | 56% | 47% |

`auth.ts` unit coverage (47%) is expected: the file is an API client with 10 exported functions. Unit tests mock `fetch` and cover `login`, `register`, `isAuthenticated`, and `getCurrentUser`. The remaining functions (`loadBoard`, `saveBoard`, `sendAiBoardPrompt`, `logout`) are exercised end-to-end via the Playwright and container validation tests.

`KanbanCardPreview.tsx` shows near-zero unit coverage — it renders only during an active dnd-kit drag overlay and is covered by Playwright test 3.

`AuthGuard.tsx` shows 0% unit coverage — it relies on `useRouter` from Next.js which is awkward to unit-test; it is covered by the Playwright suite (every test navigates through it).

---

## What each test suite covers

| Concern | Unit | Integration | E2E |
|---|---|---|---|
| Password hashing and session token storage | db.py | | |
| Schema migrations (idempotency, legacy upgrade) | db.py | | |
| Auth endpoints (register, login, logout, /me) | test_api.py | validate_part11 | Playwright |
| Board load/save (user-scoped) | test_api.py | validate_part11 | Playwright |
| AI endpoint (mocked provider) | test_ai_board.py | | |
| AI rate limiting (429) | test_ai_board.py | validate_part11 | |
| Origin validation (403) | test_ai_board.py | validate_part11 | |
| Oversized input (422) | test_ai_board.py | validate_part11 | |
| AI endpoint (live provider) | | validate_part11 | |
| Board persistence across restarts | | validate_part11 | |
| Drag-and-drop between columns | | | Playwright |
| Add/delete cards | Vitest | | Playwright |
| Login/register UI | Vitest | | |
| AI chat sidebar UI | Vitest | | |

---

## Notes on test infrastructure

- **Backend venv**: must be built with Python 3.12 (`uv venv --python .../Python312/python.exe`); the Docker-built venv (Linux symlinks) is not usable on Windows.
- **uv sync on Windows**: requires `--system-certs` flag due to corporate TLS inspection.
- **Playwright**: requires `docker compose up --build -d` before `npm run test:e2e`. Login runs once via `tests/global-setup.ts` and the session cookie is stored in `tests/auth-state.json` (gitignored) to avoid hitting the auth rate limiter (10 req / 5 min per IP).
- **Playwright drag test**: dnd-kit's `PointerSensor` requires an explicit 10px activation move before the full drag — `page.mouse.down()` → `mouse.move(+10px)` → `mouse.move(target)` → `mouse.up()`.
