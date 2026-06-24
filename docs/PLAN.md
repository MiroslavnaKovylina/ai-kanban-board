# High level steps for project

## Part 1: Plan

- [x] Expand this document into a detailed deliverable-level plan
- [x] Create frontend/AGENTS.md describing the current frontend implementation
- [x] Confirm the plan with the user before starting implementation work
- [x] Include test strategy and success criteria for each part
- [x] Target around 80% unit test coverage only when it is sensible; prioritize valuable tests over coverage padding

### Success criteria
- The plan is explicit and actionable for every major part
- frontend/AGENTS.md accurately reflects current frontend files and behavior
- The user approves the plan before Part 2 begins

Status (Part 1 - completed):
- Completed on 2026-06-24: expanded this `docs/PLAN.md` into deliverable-level parts and created `frontend/AGENTS.md` summarizing the frontend state and constraints.
- Artifacts created/updated:
	- `docs/PLAN.md` (this file, expanded with Parts 1–10 and success criteria)
	- `frontend/AGENTS.md` (documenting components, tests, limitations)
- Notes: test strategy and 80% unit coverage target established; user confirmed proceeding to Part 2.

## Part 2: Scaffolding

- [x] Add Docker configuration for the full app
- [x] Add a FastAPI backend in backend/
- [x] Add start/stop scripts in scripts/
- [x] Serve a static placeholder page from the backend at /
- [x] Add a backend API route that returns a simple JSON response

### Tests and criteria
- Backend starts in Docker and serves a static page at /
- Backend API route returns expected JSON
- Project container starts and stops cleanly

Status (Part 2 - completed):
- Completed on 2026-06-24: scaffolded a minimal FastAPI backend, Dockerized the app, and added start/stop helpers.
- Artifacts created/updated:
	- `backend/main.py` (FastAPI app with `/api/ping` and static file serving)
	- `backend/pyproject.toml` (Python dependency manifest for `uv`)
	- `backend/static/index.html` (placeholder page served at `/` during scaffolding)
	- `Dockerfile` (root-level Dockerfile used during scaffolding; later replaced by a multi-stage variant)
	- `docker-compose.yml` (orchestrates backend and frontend during validation)
	- `scripts/start.ps1` and `scripts/stop.ps1` (convenience scripts to bring services up/down)
- Runtime verification: images built and containers started; `GET /api/ping` returned 200 with expected JSON and backend served the placeholder at `/`; containers shut down cleanly.

## Part 3: Add in Frontend

- Goal: produce a production-ready static build of the existing Next.js frontend, copy those artifacts into the backend image, and serve the UI at `/` from the backend container so a single image provides both API and UI.

Substeps:
- Create a reproducible frontend build step that produces static files (use `next build` with `output: 'export'` or an equivalent static export strategy).
- Add a multi-stage Dockerfile (or CI pipeline) that:
	- Builds the frontend in a Node stage
	- Copies the exported static output into the Python backend stage under `backend/static` (or the path the backend serves)
	- Runs `uv sync` in the Python stage and starts the FastAPI app with `uv run uvicorn main:app`.
- Update `backend/main.py` to serve static files from the copied output and ensure the root route (`/`) returns the frontend's `index.html`.
- Add a small integration test (scripts/integration_test.py) that verifies `/api/ping` and `/` return expected responses in the containerized environment.
- Update `docker-compose.yml` and start/stop scripts to support building the combined image for local testing.
- [x] Create a reproducible frontend build step that produces static files (use `next build` with `output: 'export'` or an equivalent static export strategy`)
- [x] Add a multi-stage Dockerfile (or CI pipeline) that copies frontend output into backend static and runs the backend
- [x] Update `backend/main.py` to serve static files from the copied output and ensure `/` returns `index.html`
- [x] Add a small integration test that verifies `/api/ping` and `/` return expected responses
- [x] Update `docker-compose.yml` and start/stop scripts to support building the combined image for local testing

Detailed success criteria and tests:
- Build: `docker-compose build` completes successfully for the backend image that contains the frontend assets.
- Runtime: `docker-compose up -d` starts the backend container and both endpoints behave as expected:
	- `GET /api/ping` -> 200 JSON {"success": true, "message": "pong"}
	- `GET /` -> 200 HTML including the app's `<!DOCTYPE html>` and the Kanban root element.
- Integration test: `scripts/integration_test.py` runs and exits 0 when executed against the running container.
- Frontend unit tests: frontend unit tests continue to pass locally (`npm test` / `vitest`) and report no regressions.
- Pipeline: the multi-stage Dockerfile produces a single backend image suitable for deployment that serves both static UI and backend APIs.
 - Pipeline: the multi-stage Dockerfile produces a single backend image suitable for deployment that serves both static UI and backend APIs.

Status (Part 3 - completed):
- Completed on 2026-06-24: frontend static build integrated into backend image via multi-stage `Dockerfile` at project root.
- Artifacts created/updated:
	- `Dockerfile` (multi-stage build copying frontend `out/` into backend `static/`)
	- `frontend/next.config.ts` (`output: 'export'`)
	- `frontend/package.json` (added `export` script)
	- `scripts/integration_test.py` (verifies `/api/ping` and `/`)
	- `scripts/start.ps1` / `scripts/stop.ps1` (start/stop helpers via docker-compose)
- Runtime verification: built images, started container, `GET /api/ping` and `GET /` returned 200; `scripts/integration_test.py` passed; frontend unit tests (`vitest`) passed locally.

Notes and constraints:
- For Next.js 16+, prefer `output: 'export'` in `next.config.js/ts` instead of `next export` to generate a static output directory.
- Keep the existing client-side behavior unchanged during this phase; the goal is to host the same UI from the backend image without refactoring state management yet.


## Part 4: Add in a fake user sign in experience

- [x] Add a simple login page in the frontend
- [x] Restrict access to the Kanban board until credentials are entered
- [x] Use hardcoded credentials: user / password
- [x] Add logout flow

### Tests and criteria
- Attempting to access the board without login redirects to login
- Login with correct credentials succeeds; incorrect credentials fail gracefully
- Logout returns the user to the login page
- Add unit and integration tests for auth flows

Status (Part 4 - completed):
- Completed on 2026-06-24: login and auth flow added, tests passed.

## Part 5: Database modeling

- [x] Define the backend database schema
- [x] Store Kanban state in relational tables per user (users, boards, columns, cards)
- [x] Document the schema and query patterns in docs/
- [x] Ensure the database initializes automatically if missing

### Tests and criteria
- Database schema is documented in docs/
- Backend can create and read the Kanban data model
- Existing data is preserved across backend restarts

Status (Part 5 - completed):
- Completed on 2026-06-24: migrated backend persistence from JSON blob to normalized SQLite schema with idempotent migrations and relational tests.

## Part 6: Backend

- [ ] Add API routes for reading and updating a user's Kanban data
- [ ] Add backend validation and simple error handling
- [ ] Keep the database and API user-aware
- [ ] Support reading board state and applying moves/edits

### Tests and criteria
- Backend unit tests cover API behavior and data persistence
- The database is created automatically on first run
- API returns proper 4xx/5xx responses for invalid input

Status (Part 6 - completed):
- Completed on 2026-06-24 after execution and validation in a Python 3.12 backend virtual environment.
- Verification summary:
	- Backend tests: `python -m unittest test_db.py test_api.py` passed (9 tests, 0 failures).
	- Backend startup verified with Uvicorn in local validated environment.
	- Live endpoint checks completed with real HTTP requests:
		- `POST /api/auth/register`
		- `POST /api/auth/login`
		- `POST /api/board/load`
		- `POST /api/board/save`
	- Expected behavior confirmed for success and conflict flows (200/409) and user-aware board operations.

## Part 7: Frontend + Backend

- [x] Update the frontend to call backend APIs for board state
- [x] Persist board changes through backend updates
- [x] Load board state from the backend on page load
- [x] Keep drag/drop, rename, add, delete card behavior functional

### Tests and criteria
- Frontend integration tests confirm state is persisted through the backend
- UI reflects backend state after reload
- Unit and integration coverage remain strong

Status (Part 7 - completed):
- Completed on 2026-06-24: frontend integrated with backend auth and board APIs.
- Validation summary: frontend tests passed (`vitest`, 12 tests) and manual end-to-end verification passed (register/login/load/save + board persistence after reload).

## Part 8: AI connectivity

- [x] Add OpenRouter integration in the backend
- [x] Create a simple AI test route, such as a 2+2 sanity check
- [x] Use environment variable OPENROUTER_API_KEY
- [x] Ensure the backend can reach the AI provider and parse responses

### Tests and criteria
- AI connectivity test route returns a valid AI response
- Integration test confirms the backend can call OpenRouter once configured
- Failure modes are handled cleanly when the API key is missing

Status (Part 8 - active):
- Started on 2026-06-24: backend OpenRouter sanity route (`/api/ai/sanity`) implemented with error handling and tests.
- Validation so far: backend unit tests pass including AI connectivity tests with mocked provider responses.

Status (Part 8 - completed):
- Completed on 2026-06-24: live provider check passed against OpenRouter.
- Live validation: `GET /api/ai/sanity` returned `200` with response payload containing model `openai/gpt-oss-120b` and content `"4"`.

## Part 9: AI structured output with board context

- [x] Send the current Kanban JSON and user prompt to the AI
- [x] Include optional conversation history in the request
- [x] Parse structured outputs with both a user response and optional board updates
- [x] Apply AI-driven board updates when present

### Tests and criteria
- Structured outputs are validated and applied consistently
- Backend has unit tests for AI request/response handling
- UI receives both a user-facing message and optional board updates

Status (Part 9 - active):
- Started on 2026-06-24: backend endpoint `/api/ai/board` implemented with structured AI output parsing and optional board update persistence.
- Validation so far: backend tests include structured AI endpoint behavior with/without board updates.

## Part 10: AI chat sidebar

- [x] Add a chat sidebar UI to the frontend
- [x] Send messages to the backend AI endpoint
- [x] Display AI responses in a chat view
- [x] Apply board updates from AI responses automatically

### Tests and criteria
- Chat UI interacts with the AI endpoint correctly
- AI responses render in the sidebar
- Board updates from AI refresh the UI automatically
- Integration tests cover chat, message sending, and board updates

Status (Part 10 - active):
- Started on 2026-06-24: AI chat sidebar integrated in Kanban board and connected to backend `/api/ai/board` endpoint.
- Validation so far: frontend tests pass (`vitest`, 14 tests) including chat sidebar behavior.

Status (Part 10 - completed):
- Completed on 2026-06-24: local development validation passed for chat send/response flow and AI-driven board updates.

## Part 11: Final containerization and production validation

- [x] Build the final Docker image for the integrated app
- [x] Serve frontend and backend from the same container
- [x] Verify `http://localhost:8000` renders the fully styled Kanban UI
- [x] Verify authentication works from the containerized app
- [x] Verify board persistence works from the containerized app
- [x] Verify AI assistant works from the containerized app using `OPENROUTER_API_KEY`
- [x] Verify AI abuse protection in container runtime (rate limit, origin validation, input size limits)
- [x] Verify refresh and relogin persistence from the containerized app
- [x] Ensure `.env` is not committed to git
- [x] Ensure virtual environments, node_modules, build outputs, and database files are ignored by git
- [x] Update `AGENTS.md` and `docs/PLAN.md` with final run/test instructions and validation evidence

### Tests and criteria
- Build succeeds with a single deployable image that serves UI + API
- `GET /` on `localhost:8000` returns the production-styled Kanban app (not placeholder)
- Authentication, board edits, drag/drop, and persistence pass manual validation in container runtime
- AI sidebar prompt/response and optional board updates pass manual validation in container runtime
- AI abuse protections are enforced in runtime:
	- excessive requests return 429
	- invalid Origin/Referer returns 403
	- oversized prompt/history/board context returns 422
- Refresh and sign-out/sign-in cycles retain persisted board state
- SQLite is persisted outside app code under `/data/kanban.db`
- Persistence survives `docker compose down` + `docker compose up` and `docker compose up --build`
- Git hygiene checks pass:
	- `.env` is excluded from commits
	- ignore rules cover `.venv*`, `node_modules/`, frontend build outputs (for example `out/`, `.next/`), and SQLite/db artifacts
- Final instructions are documented and reproducible on a clean local machine

Status (Part 11 - completed):
- Added on 2026-06-24: final packaging/cleanup/validation phase scoped to Docker runtime only; no new product features.
- 2026-06-24: backend abuse protection for `/api/ai/board` implemented and covered by tests (`python -m unittest test_ai.py test_ai_board.py`).
- 2026-06-24: Docker packaging/runtime checks completed:
	- `docker compose build --no-cache` succeeded for integrated `app` image.
	- `docker compose up -d` started `app` on `localhost:8000`.
	- Container logs show clean startup and expected requests (`200` on `/` and `/api/ping`).
	- Route validation: `/` -> `200` (static UI), `/api/ping` -> `200`, `/api/ai/sanity` -> `200` with response `"4"`.
- 2026-06-24: persistence architecture refactor completed for local and cloud compatibility:
	- Database path resolution now prioritizes `KANBAN_DB_PATH`, then `KANBAN_DB_DIR`, with default fallback `/data/kanban.db`.
	- Docker runtime image sets `KANBAN_DB_DIR=/data` and creates `/data` automatically.
	- `docker-compose.yml` mounts named volume `kanban_data:/data`.
	- Verified database file location inside container: `/data/kanban.db`.
- 2026-06-24: persistence verification in Docker runtime:
	- Created user in running container and confirmed login success.
	- Ran `docker compose down` then `docker compose up -d`; login for same user remained `200`.
	- Ran `docker compose up --build -d`; login for same user remained `200`.
- 2026-06-24: abuse protection runtime checks in container:
	- invalid `Origin` -> `403`
	- oversized prompt -> `422`
	- repeated `/api/ai/board` calls exceeded per-minute threshold and returned `429`.
- 2026-06-24: git hygiene checks:
	- `.env` not tracked (`git ls-files --error-unmatch .env` failed as expected)
	- ignore rules verified for `.venv*`, `node_modules/`, `.next/`, `out/`, `backend/data/`, `*.db-*`, `*.sqlite-*`, and `*.sqlite3`.
- 2026-06-24: E2E container validation script (`scripts/validate_part11_e2e.py`) executed against running container:
	- Authentication (register/login): `PASS`
	- Board CRUD and persistence (load/save/reload): `PASS`
	- AI endpoint with valid auth: `PASS` (returned AI message `"Columns: Backlog, To Do, In Progress, Review, Done."`)
	- Relogin persistence (logout/relogin/verify board): `PASS`
	- All four E2E test suites passed.

## Quality goals

- Target around 80% unit test coverage when it is sensible; prioritize valuable tests over unnecessary coverage padding
- Robust integration testing of login, board persistence, and AI flows
- Keep implementation simple and avoid unnecessary features
- Every major step must be approved before the next phase begins
