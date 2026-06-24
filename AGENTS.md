# The Project Management MVP web app

## Business Requirements

This project is building a Project Management App. Key features:
- A user can sign in
- When signed in, the user sees a Kanban board representing their project
- The Kanban board has fixed columns that can be renamed
- The cards on the Kanban board can be moved with drag and drop, and edited
- There is an AI chat feature in a sidebar; the AI is able to create / edit / move one or more cards

## Limitations

For the MVP, there will only be a user sign in (hardcoded to 'user' and 'password') but the database will support multiple users for future.

For the MVP, there will only be 1 Kanban board per signed in user.

For the MVP, this will run locally (in a docker container)

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Use OpenRouter for the AI calls. An OPENROUTER_API_KEY is in .env in the project root
- Use `openai/gpt-oss-120b` as the model
- Use SQLLite local database for the database, creating a new db if it doesn't exist
- Persist SQLite data under `/data/kanban.db` (never under `/app`)
- Resolve DB path in this order: `KANBAN_DB_PATH` -> `KANBAN_DB_DIR/kanban.db` -> `/data/kanban.db`
- In Docker Compose, mount named volume `kanban_data:/data` so users and boards survive rebuilds/recreation
- Start and Stop server scripts for Mac, PC, Linux in scripts/

## Starting Point

A working MVP of the frontend has been built and is already in frontend. This is not yet designed for the Docker setup. It's a pure frontend-only demo.

## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.

## Final Run and Validation Instructions (Part 11)

This phase is packaging, cleanup, and validation only. Do not add new features.

### Container run sequence

1. Build the final image and start services from project root:
	- `docker compose build --no-cache`
	- `docker compose up -d`
	- `docker compose ps`
2. Validate container health and logs:
	- `docker compose logs --tail=200`
3. Validate app routes:
	- UI: `http://localhost:8000`
	- API sanity: `http://localhost:8000/api/ping`
	- AI sanity (with key configured): `http://localhost:8000/api/ai/sanity`
4. Validate persistence path and file inside container:
	- `docker compose exec app printenv KANBAN_DB_DIR` (expected `/data`)
	- `docker compose exec app sh -lc "ls -la /data"` (expected `kanban.db`)

### Manual validation checklist (must pass in Docker runtime)

1. UI loads fully styled Kanban board from `localhost:8000`.
2. Register/login/logout work correctly.
3. Rename columns, add/edit/move/delete cards, then refresh and confirm persistence.
4. Sign out and sign in again; confirm same board state persists.
5. AI chat sidebar sends prompt, receives response, and applies board updates when returned.
6. Abuse protection checks for AI endpoint:
	- trigger repeated requests and confirm `429` is returned after the per-minute threshold
	- send invalid `Origin` or `Referer` and confirm `403`
	- send oversized prompt/history and confirm `422`

### Environment and git hygiene checks

1. Ensure `.env` is present locally for runtime but not committed:
	- `git ls-files --error-unmatch .env` should fail.
2. Ensure ignore rules include:
	- virtual environments (`.venv`, `.venv-win`, `.venv*`)
	- Node dependencies (`node_modules/`)
	- frontend build outputs (`.next/`, `out/`)
	- database artifacts (`*.db`, `*.sqlite`, `backend/data/` as applicable)
3. Verify with:
	- `git status --ignored`
	- `git check-ignore -v <path>` for representative files

### Completion evidence to capture in docs/PLAN.md

1. Docker build command and result.
2. Docker runtime validation summary.
3. Manual test results for auth, persistence, and AI.
4. Git hygiene verification summary.
5. Persistence verification summary showing user survival across:
	- `docker compose down` + `docker compose up`
	- `docker compose up --build`