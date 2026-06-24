# Backend AGENTS

## Current backend state

The backend is a FastAPI app served from `backend/main.py`. In Docker, the backend also serves the static Next.js export at `/`.

### Primary responsibilities

- Serve `/api/ping` for health checks.
- Register, login, logout, and validate users with cookie-based sessions.
- Store password hashes using stdlib `scrypt`; never store plaintext passwords.
- Store only hashed session tokens in SQLite. The raw opaque token exists only in the browser cookie.
- Load and save one Kanban board per user through SQLite.
- Call OpenRouter for AI sanity checks and board updates.
- Apply basic abuse protection for auth and AI endpoints.

### Key files

- `main.py` - FastAPI routes, cookie/session auth, rate limiting, static file serving
- `db.py` - SQLite path resolution, migrations, auth/session persistence, board persistence
- `ai.py` - OpenRouter API calls and structured response parsing
- `test_*.py` - backend unit/API tests

### Operational notes

- DB path resolution order: `KANBAN_DB_PATH`, then `KANBAN_DB_DIR/kanban.db`, then `/data/kanban.db`.
- Production must set `SESSION_COOKIE_SECURE=true` and run behind HTTPS.
- Docker Compose mounts `kanban_data:/data` so users, sessions, and boards survive rebuilds.
- Keep auth simple and same-origin; do not introduce JWT, Supabase, or Auth0 unless the project direction changes.