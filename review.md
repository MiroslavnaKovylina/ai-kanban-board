# Code Review: Project Management MVP

Date: 2026-06-24
Scope: Full project (backend, frontend, infra, docs, scripts). No code was changed.

## Summary

The MVP is functional and well-structured for its size. Backend persistence,
auth, board CRUD, and AI integration are all wired end-to-end with a reasonable
test suite. The architecture is simple and mostly idiomatic, matching the
"keep it simple" project standard.

The most important issues are about security (plaintext credentials stored and
re-sent on every request), a React anti-pattern (side effects inside state
updaters causing double/excessive saves), and several documentation/config
drifts (stale `AGENTS.md` files, DB path mismatch, missing cross-platform
scripts). None block the MVP demo, but the security and persistence items should
be acknowledged explicitly given the database is designed for "multiple users
for future".

Severity legend: High = fix soon / security or correctness; Medium = should
fix; Low = polish / nice to have.

---

## High severity

### H1. Passwords stored in plaintext in the database
`backend/db.py` stores `password` as-is and authenticates by direct string
compare:

```199:205:backend/db.py
def authenticate_user(username: str, password: str) -> int | None:
    row = get_user_by_username(username)
    if row is None:
        return None
    if row["password"] != password:
        return None
    return int(row["id"])
```

The schema and `register` flow support arbitrary multi-user accounts, so this is
not just the hardcoded `user`/`password` pair. Plaintext at rest is a real risk
once more than the demo user exists.

Remediation:
- Hash passwords with a vetted algorithm (e.g. `bcrypt` via `passlib`, or
  `hashlib.scrypt`/`pbkdf2_hmac` from stdlib to avoid a new dependency).
- Store the hash, compare with a constant-time check.
- Note: this is acceptable only if the project intentionally keeps the MVP
  trivial; if so, document the decision explicitly.

### H2. Credentials persisted in `localStorage` and re-sent as the auth mechanism
`frontend/src/lib/auth.ts` saves the raw username+password in `localStorage` and
attaches them to the body of every board/AI request:

```65:81:frontend/src/lib/auth.ts
const saveSession = (session: AuthSession) => {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
};
```

Consequences: the password is readable by any XSS, lives indefinitely in the
browser, and is transmitted on every `load`/`save`/`ai` call instead of a
short-lived token. There is no real session/expiry; `AuthGuard` only checks for
the presence of the localStorage key, never validating it with the server.

Remediation:
- Introduce a server-issued session token (signed cookie or bearer token) on
  login/register and stop persisting the password client-side.
- Validate the token on protected endpoints rather than re-authenticating with
  username/password each call.
- If keeping it simple for the MVP, at minimum stop storing the password (store
  only a token/username) and document the trade-off.

### H3. Side effects called inside React state updater functions
In `frontend/src/components/KanbanBoard.tsx`, `persistBoard` (an async network
call) is invoked from inside the `setBoard(prev => ...)` updater in drag, rename,
add, and delete handlers:

```74:82:frontend/src/components/KanbanBoard.tsx
    setBoard((prev) => {
      const nextBoard = {
        ...prev,
        columns: moveCard(prev.columns, active.id as string, over.id as string),
      };
      void persistBoard(nextBoard);
      return nextBoard;
    });
```

State updater functions must be pure. Under React 18/19 Strict Mode (dev),
updaters run twice, so this fires duplicate save requests; it also makes the
network behavior hard to reason about.

Remediation:
- Compute `nextBoard` outside the updater, call `setBoard(nextBoard)`, then call
  `void persistBoard(nextBoard)`; or move persistence into a `useEffect` that
  watches `board` (with care to skip the initial load).

---

## Medium severity

### M1. Column rename persists on every keystroke
`handleRenameColumn` runs on each `onChange` of the column title input
(`KanbanColumn.tsx` calls `onRename` per keystroke), and each call triggers a
full board save. Typing "Backlog" sends 7 save requests, with full
delete-and-reinsert of all columns/cards each time, plus last-write-wins race
risk.

Remediation:
- Save on blur or debounce (e.g. 500ms). Optionally update local state on every
  keystroke but persist only after the user stops typing.

### M2. Full-board replace resets timestamps and drops `archived` state
`replace_board` (`backend/db.py`) deletes all columns/cards and reinserts them on
every save, so `created_at` is reset on every edit and IDs change. Also the
frontend `Card` type has no `archived` field, so any archived card round-trips
back as `archived = false`.

```405:419:backend/db.py
def replace_board(board_id: int, board: dict[str, Any]) -> None:
    ...
    with conn:
        conn.execute("DELETE FROM cards WHERE column_id IN (SELECT id FROM \"columns\" WHERE board_id = ?)", (board_id,))
        conn.execute("DELETE FROM \"columns\" WHERE board_id = ?", (board_id,))
```

Remediation:
- For the MVP this is acceptable (simple and correct for state), but document
  that timestamps/`archived` are not authoritative, or preserve them by keying on
  existing IDs. At minimum, surface `archived` in the frontend `Card` type so it
  is not silently dropped.

### M3. In-memory AI rate-limit maps grow unbounded
`main.py` keeps `_ai_minute_windows` and `_ai_daily_usage` keyed by client IP and
never evicts stale IPs. Over a long-running container this is a slow memory leak,
and it resets on restart (so limits are not durable).

Remediation:
- Periodically prune empty/expired entries, or accept the leak and document it as
  acceptable for a single-container local MVP.

### M4. Deprecated FastAPI startup hook
`@app.on_event("startup")` is deprecated in current FastAPI/Starlette in favor of
lifespan handlers.

```147:150:backend/main.py
@app.on_event("startup")
def startup() -> None:
    _load_project_env()
    get_db_connection()
```

Remediation:
- Migrate to the `lifespan=` context manager on `FastAPI(...)`.

### M5. Broad exception + string sniffing in `register`
`register` catches `Exception` and inspects the message for `"unique"` to decide
409 vs 500:

```191:195:backend/main.py
    except Exception as exc:
        message = str(exc).lower()
        if "unique" in message:
            raise HTTPException(status_code=409, detail="Username already exists") from exc
        raise HTTPException(status_code=500, detail="Failed to register user") from exc
```

Remediation:
- Catch `sqlite3.IntegrityError` specifically for the duplicate case; let other
  errors propagate to a generic 500.

### M6. Dockerfile does not use `uv.lock` (non-reproducible installs)
The image copies only `pyproject.toml` before `uv sync`, so the committed
`backend/uv.lock` is ignored and dependency resolution can drift between builds.
`pip install uv` is also unpinned.

```17:18:Dockerfile
COPY backend/pyproject.toml ./
RUN uv sync
```

Remediation:
- `COPY backend/pyproject.toml backend/uv.lock ./` and use `uv sync --frozen`
  (or `--locked`) for reproducible builds. Pin the `uv` version.

### M7. Missing cross-platform start/stop scripts
`AGENTS.md` and `scripts/AGENTS.md` require start/stop scripts for Mac, PC, and
Linux, but only `scripts/start.ps1` and `scripts/stop.ps1` exist. No `.sh`
equivalents are present.

Remediation:
- Add `start.sh` / `stop.sh` (or a single cross-platform script) for Mac/Linux.

### M8. `start.ps1` issues
```1:4:scripts/start.ps1
$env:OPENROUTER_API_KEY = $env:OPENROUTER_API_KEY
cd ..
docker-compose up --build
```
- Line 1 is a no-op self-assignment.
- Uses `docker-compose` (v1) while `AGENTS.md`'s official run sequence uses
  `docker compose` (v2). Inconsistent and may fail where only the v2 plugin is
  installed.

Remediation:
- Remove the no-op, standardize on `docker compose`, and rely on `.env` /
  compose for the API key rather than re-exporting it.

---

## Low severity / polish

### L1. Stale `AGENTS.md` files
- `frontend/AGENTS.md` still says "No backend integration yet", "No
  authentication or login flow", "No AI or OpenRouter connectivity" - all now
  false. It should describe the current login page, `auth.ts` API client,
  `AiChatSidebar`, and backend-driven board state.
- `backend/AGENTS.md` is a single placeholder line ("This file should be updated
  with a description of the Backend"). The workspace rule explicitly asks for it
  to be filled in.

Remediation: update both to reflect the implemented system.

### L2. Documentation drift in `docs/database.md`
- States the default DB file is `backend/data/kanban.db`, but `db.py` defaults to
  `/data/kanban.db`.
- Says only migration `v1` exists; code has a `v2` migration (`Todo` -> `To Do`).

Remediation: align the doc with `get_db_path()` and list `v2`.

### L3. Dead code: `get_or_create_user_board`
`backend/db.py` defines `get_or_create_user_board` but no endpoint or test uses
it (confirmed by search). Remove it to reduce surface area.

### L4. Duplicate dependency manifests
`backend/requirements.txt` and `backend/pyproject.toml` list the same deps. The
Docker build uses `uv` (pyproject), so `requirements.txt` is unused and can
drift. Remove it or generate it from the lockfile.

### L5. Redundant `useMemo`
```60:60:frontend/src/components/KanbanBoard.tsx
  const cardsById = useMemo(() => board.cards, [board.cards]);
```
This just returns the same reference; the `useMemo` adds no value. Use
`board.cards` directly.

### L6. Two sources of truth for allowed origins
`main.py` hardcodes CORS origins (`add_middleware`) separately from
`_allowed_ai_origins()` (env-driven). They can drift.

Remediation: derive both from one config source.

### L7. Demo data flashes before remote load
`KanbanBoard` initializes state with `initialData` (demo cards) and only replaces
it after `loadBoard()` resolves. On a slow network the user briefly sees demo
content; if `loadBoard()` returns `null` (auth/transient error) the demo board
stays visible with no error shown.

Remediation: render a loading state until the first load completes, and surface
load failures.

### L8. Drag listeners on the entire card include the Remove button
`KanbanCard.tsx` spreads `{...listeners}` on the outer `article`, so the Remove
button is also a drag handle. The 6px activation distance mitigates accidental
drags, but a dedicated drag handle would be cleaner.

### L9. AI structured output relies on heuristic JSON extraction
`ai.py` strips markdown fences and slices between the first `{` and last `}`.
This is brittle if the model wraps JSON in prose.

Remediation: request `response_format` JSON schema from OpenRouter (supported by
the model) for more reliable structured output.

### L10. No input normalization on username
Usernames are not trimmed, so `"user"` and `"user "` are distinct accounts.
Consider trimming/normalizing on register/login.

---

## What looks good

- Clean separation: `db.py` (persistence), `ai.py` (provider), `main.py`
  (HTTP) on the backend; `lib/` vs `components/` on the frontend.
- Idempotent, versioned SQLite migrations with a `schema_migrations` table.
- Sensible reorder strategy using temporary offset positions to avoid transient
  `UNIQUE(position)` conflicts.
- DB path resolution order (`KANBAN_DB_PATH` -> `KANBAN_DB_DIR` -> `/data`)
  matches the project requirement, and persistence is mounted via a named volume.
- Server-side validation in `replace_board` with clear `ValueError` -> 422
  mapping.
- AI abuse protections (origin check, per-minute rate limit, prompt/history size
  caps) with matching unit tests in `test_ai_board.py`.
- Tests use isolated temp SQLite DBs and reset AI guard state between cases.

---

## Suggested priority order

1. H2 / H1 - stop persisting/transmitting plaintext passwords; hash at rest
   (or explicitly document the MVP trade-off).
2. H3 / M1 - fix the state-updater side effects and per-keystroke saves.
3. M6 - make Docker builds reproducible with `uv.lock`.
4. M4, M5 - lifespan migration and precise exception handling.
5. M7, M8, L1, L2 - scripts and documentation parity (low effort, high clarity).
6. Remaining Low items as polish.
