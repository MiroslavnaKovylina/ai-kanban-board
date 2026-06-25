# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Kanban Board — a full-stack project management app with an AI chat assistant. FastAPI backend serves both the REST API and the statically-exported Next.js frontend as a single container. One board per user (MVP).
      use Python 3.12 for environment

      
**Stack:** FastAPI + SQLite (backend), Next.js 16 + TypeScript + Tailwind CSS 4 + dnd-kit (frontend), OpenRouter API for AI, Docker for deployment.

## Commands

### Backend (run from `backend/`)
```bash
uv sync                                          # Install dependencies
uv run uvicorn main:app --reload --port 8000     # Dev server
pytest                                           # All tests
pytest test_api.py -k "test_login"               # Single test
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev          # Dev server (port 3000)
npm run build        # Production static export → out/
npm run lint         # ESLint
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E
```

### Docker (run from project root)
```bash
docker compose up --build        # Build and start
docker compose up -d             # Detached
docker compose logs --tail=200   # Logs
./scripts/start.sh / stop.sh     # Convenience wrappers
```

### Integration tests
```bash
python scripts/integration_test.py        # Smoke tests against running app
python scripts/validate_part11_e2e.py     # Full E2E validation suite
```

## Architecture

### Data flow
```
Browser → Next.js (static) → FastAPI → SQLite
                                ↓
                          OpenRouter API
```

The frontend is a statically-exported Next.js app. In production, FastAPI serves it via `StaticFiles` mounted at `/`; in dev, Next.js runs separately on port 3000 and proxies `/api/*` to FastAPI on port 8000.

### Backend (`backend/`)

- **`main.py`** — FastAPI app, all route handlers, session dependency injection (`require_session_user()`), rate limiting middleware, CORS, lifespan startup (loads `.env`, initializes DB).
- **`db.py`** — All SQLite operations. Schema migrations run idempotently at startup (4 versions). One board per user.
- **`ai.py`** — OpenRouter integration. Sends current board state + user prompt as JSON; expects `{message, board}` back. Board can be `null` if no changes needed.

### Frontend (`frontend/src/`)

- **`app/page.tsx`** — Entry point; mounts `KanbanBoard`.
- **`components/KanbanBoard.tsx`** — Main board with dnd-kit drag-and-drop. Loads on mount, saves on every card/column change.
- **`components/AiChatSidebar.tsx`** — AI assistant. Sends chat history + prompt; if the response includes a board diff, replaces board state.
- **`lib/kanban.ts`** and **`lib/auth.ts`** — Typed API clients for the FastAPI backend.
- **`components/AuthGuard.tsx`** — Redirects unauthenticated users to `/login`.

### Database schema
`users`, `boards` (one per user), `columns`, `cards`, `sessions`, `schema_migrations`. SQLite file at `/data/kanban.db` inside Docker, persisted via a named volume (`kanban_data`).

### Authentication
Session tokens stored as SHA256 hashes in the DB. Set as `httpOnly`/`SameSite=Lax` cookies (`kanban_session`). Scrypt password hashing. Rate-limited auth: 10 attempts per 5 min per IP.

### AI endpoint security
- Origin validation for browser requests
- Rate limit: 20 req/min per IP (configurable via `AI_RATE_LIMIT_PER_MINUTE`)
- Request body size cap
- Response parsed as strict JSON

## Configuration

Requires a `.env` file at project root (excluded from git):
```
OPENROUTER_API_KEY=sk-or-...
```

Optional overrides: `KANBAN_DB_PATH`, `KANBAN_DB_DIR`, `SESSION_TTL_DAYS` (default 7), `SESSION_COOKIE_SECURE` (auto-true in prod).

## Coding standards

- No over-engineering. No unnecessary defensive programming. No extra features — focus on simplicity.
- No emojis anywhere in code or output.
- Keep READMEs minimal.
- When hitting issues: identify root cause before fixing. Prove with evidence, then fix.

## Color scheme

| Token | Hex | Usage |
|-------|-----|-------|
| Accent Yellow | `#ecad0a` | accent lines, highlights |
| Blue Primary | `#209dd7` | links, key sections |
| Purple Secondary | `#753991` | submit buttons, important actions |
| Dark Navy | `#032147` | main headings |
| Gray Text | `#888888` | supporting text, labels |

## Key constraints

- Board save is a full replacement (`POST /api/board/save`) — there are no partial update endpoints.
- The AI model is `openai/gpt-oss-120b` via OpenRouter; changing it requires updating `ai.py`.
- Next.js is configured for static export (`output: 'export'` in `next.config.ts`) — no server-side rendering or Next.js middleware.
- Docker multi-stage: stage 1 builds Next.js static files; stage 2 runs Python + copies the static output.
- All API calls must be same-origin (no hardcoded hostnames); the Docker container serves both UI and API on port 8000.
- Do not store credentials (username/password) in localStorage — auth is cookie-session only.
- Scope board persistence calls to actual completed edits; avoid excessive full-board saves on every keystroke.
