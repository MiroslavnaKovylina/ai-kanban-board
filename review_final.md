# Final Review: Project Management MVP (post security + medium fixes)

Date: 2026-06-24
Scope: Final review after the auth hardening and medium/low-severity fixes.
No code was modified during this review.

## Regressions introduced

No functional regressions were found. The risky refactors landed cleanly, but
three things are worth flagging:

- **State handlers now close over `board` instead of using the functional
  `setBoard(prev => ...)` updater** (`KanbanBoard.tsx`, handlers for drag,
  rename-commit, add, delete). This correctly fixes the "side effects inside
  updater" anti-pattern, but trades one subtle risk for another: if two
  state-changing events fire within the same render tick, the second computes
  from a stale `board` and the first update is lost. For this UI these are
  discrete user actions, so it is safe in practice — just no longer batch-safe
  by construction.
- **`uv sync --frozen` in the Dockerfile** now hard-requires `backend/uv.lock`
  to be in sync with `pyproject.toml`. `uv.lock` exists, but if it is stale the
  Docker build will now fail instead of silently resolving. Correct behavior,
  but it converts latent drift into a build-time blocker — verify `uv lock` is
  current before shipping.
- **CORS now derives from `_allowed_ai_origins()`** with
  `allow_credentials=True`. Fine because those are explicit origins, but if
  anyone sets `AI_ALLOWED_ORIGINS="*"`, browsers reject credentialed `*` and
  auth silently breaks. Worth a guard or doc note.

Validation in this session: lint passed, 17 frontend tests passed, 7 DB tests
passed. The FastAPI-backed tests still could not run in this shell (no
`fastapi`/`uv`), so the new auth/rate-limit/AI tests are unverified here.

## Remaining production blockers

Only one true blocker, and it is configuration, not code:

- **Must run behind HTTPS with `SESSION_COOKIE_SECURE=true`** (or
  `ENVIRONMENT=production`). Out of the box the default is insecure for local
  Docker.

Strongly recommended before ship (not hard blockers):

- Run the full backend suite in the `uv` env
  (`uv run python -m unittest test_api.py test_ai.py test_ai_board.py test_db.py`)
  — the cookie, rate-limit, and AI-auth tests have never executed.
- Confirm `uv.lock` is current so the `--frozen` build succeeds.

## Docker / cloud readiness

Good. Multi-stage build, frozen deps, `KANBAN_DB_DIR=/data`, named volume
`kanban_data:/data`, lifespan startup, and same-origin static serving are all
correct. Caveats:

- **Single shared SQLite connection** (`check_same_thread=False`) means run
  **one uvicorn worker**. Multiple workers/replicas would corrupt under
  concurrent writes and split the in-memory rate-limit/session-guard state.
  SQLite + single container is the supported topology only.
- The in-memory auth/AI limiters are per-process and reset on restart —
  acceptable for one container, not for horizontal scale.

## Auth / session security

Solid. Passwords are `scrypt`-hashed with constant-time compare; session tokens
are 256-bit opaque, stored only as `sha256` at rest, hashed before
lookup/delete, with server-side expiry and real logout revocation.
Login/register are rate-limited per IP+username with `429` + `Retry-After`.
`/api/ai/sanity` now requires auth. Residual items (all previously noted, none
new):

- Username-based limiting enables targeted lockout DoS.
- Per-IP limiting degrades behind a proxy unless `X-Forwarded-For` is honored.
- The **AI-board 429** still sets `Retry-After` on `response.headers` before
  raising `HTTPException`, so that one header is dropped — pre-existing,
  cosmetic.

## SQLite persistence

Correct and durable for the MVP. Path resolution order is right, migrations are
idempotent and versioned (now through v4), and legacy password/token upgrades
run on startup. Known, documented trade-off: `replace_board` is full
delete-and-reinsert, so card/column `created_at` is not authoritative across
saves; `archived` now round-trips because the frontend `Card` type carries it.
Sessions accumulate until looked up (no sweeper) — negligible at MVP scale.

## React state / persistence logic

Improved. Persistence is out of the updaters, rename persists on blur/Enter (no
more per-keystroke save storm), a loading state removes the demo-data flash, and
load failures surface an error. The only nuance is the closure-vs-updater point
above.

---

## Final readiness score: 8 / 10

Up from the earlier 7. The security and medium fixes materially improved
correctness, persistence behavior, and ops hygiene. It is a clean, deployable
small-scale single-container app once the HTTPS/secure-cookie config is set and
the full test suite is run.

## Prioritized remaining risks

1. **Config blocker:** deploy over HTTPS with `SESSION_COOKIE_SECURE=true`
   (else session cookies leak in cleartext).
2. **Verify build/tests:** run full backend suite in `uv` and confirm
   `uv.lock` matches `pyproject.toml` (the `--frozen` build will fail if stale).
3. **Single-worker constraint:** document/enforce one uvicorn worker; SQLite +
   in-memory limiters do not support multi-worker/replica.
4. **Auth limiter edge:** username-based limiting allows targeted login lockout,
   and per-IP limiting is weak behind a proxy (honor `X-Forwarded-For` if you
   add one).
5. **Minor:** AI-board `429` drops its `Retry-After` header (move it onto the
   `HTTPException`), and guard against `AI_ALLOWED_ORIGINS="*"` with credentialed
   CORS.
