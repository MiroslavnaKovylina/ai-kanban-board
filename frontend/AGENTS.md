# Frontend AGENTS

## Current frontend state

The frontend is a Next.js app in `frontend/` with a single page at `src/app/page.tsx` that renders the Kanban board.

### Primary features

- `KanbanBoard` is the root client component.
- Drag-and-drop powered by `@dnd-kit/core` and `@dnd-kit/sortable`.
- Columns can be renamed inline.
- Cards can be added and deleted.
- Card move behavior is handled entirely in local React state.
- The UI uses Tailwind CSS and modern React.

### Key files

- `src/app/page.tsx` — renders `KanbanBoard`
- `src/components/KanbanBoard.tsx` — main board behavior, state management, drag/drop handlers
- `src/components/KanbanColumn.tsx` — column presentation, inline rename, droppable target, card list
- `src/components/KanbanCard.tsx` — sortable card item with delete action
- `src/components/KanbanCardPreview.tsx` — drag overlay preview
- `src/components/NewCardForm.tsx` — add card form with title/details inputs
- `src/lib/kanban.ts` — board model, initial demo data, card movement helpers, ID creation

### Current tests

- `src/lib/kanban.test.ts` — unit tests for `moveCard` logic
- `src/components/KanbanBoard.test.tsx` — component tests for rendering, renaming, adding, deleting cards

### Current limitations

- No backend integration yet
- No authentication or login flow
- Board state is not persisted beyond the session
- No AI or OpenRouter connectivity
- No database or API routes exist in the current frontend

### Dependencies

- `next`, `react`, `react-dom`
- `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`
- `clsx`
- Tailwind CSS for styling
- `vitest`, `@testing-library/react`, `@testing-library/user-event`, `playwright` for tests

### Notes for an agent

- Keep the existing board behavior intact while introducing backend integration.
- Add authentication and persistence in discrete steps.
- Preserve current tests and expand coverage to meet the 80% unit coverage goal.
- Later phases should move state from local React state to backend-driven data.
