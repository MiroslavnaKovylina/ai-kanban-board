# Frontend AGENTS

## Current frontend state

The frontend is a static-export Next.js app in `frontend/`. FastAPI serves the exported files from the integrated Docker image.

### Primary features

- `src/app/page.tsx` wraps `KanbanBoard` in `AuthGuard`.
- Auth is cookie-session based. `src/lib/auth.ts` calls backend auth endpoints with `credentials: "include"` and never stores passwords in local storage.
- `AuthGuard` validates the session through `GET /api/auth/me`.
- `KanbanBoard` loads board state from the backend, persists board edits, and renders the AI chat sidebar.
- Drag-and-drop uses `@dnd-kit/core` and `@dnd-kit/sortable`.
- Columns can be renamed inline, cards can be added/deleted/moved, and AI responses can update the board.

### Key files

- `src/app/page.tsx` - protected board page
- `src/app/login/page.tsx` - login route
- `src/components/LoginPage.tsx` - sign in and create-account UI
- `src/components/AuthGuard.tsx` - session check before rendering the board
- `src/components/KanbanBoard.tsx` - main board behavior, backend persistence, AI integration
- `src/components/AiChatSidebar.tsx` - AI chat UI
- `src/lib/auth.ts` - same-origin API client for auth, board, and AI endpoints
- `src/lib/kanban.ts` - board model, initial data, card movement helpers, ID creation

### Tests

- `src/lib/*.test.ts` - auth and Kanban helper tests
- `src/components/*.test.tsx` - login, board, and AI chat component tests
- `tests/kanban.spec.ts` - Playwright E2E coverage

### Notes for an agent

- Keep the frontend compatible with static export; do not rely on Next.js server middleware.
- Preserve same-origin API calls for the Docker runtime.
- Do not reintroduce username/password local storage.
- Keep board persistence calls scoped to actual completed edits to avoid excessive full-board saves.
