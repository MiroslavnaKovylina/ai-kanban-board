# Database Schema

This backend uses the normalized relational model from the course.

## Engine and file location

- Engine: SQLite
- Default file: /data/kanban.db
- Optional overrides:
	- KANBAN_DB_PATH (full file path)
	- KANBAN_DB_DIR (directory where kanban.db is created)
- The database directory and file are created automatically if missing.

## Idempotent schema initialization

Schema setup is executed on backend startup and is idempotent.

- Table `schema_migrations` tracks applied versions.
- Migration `v1` creates all core board tables and indexes.
- Migration `v2` normalizes the default "To Do" column title.
- Migration `v3` creates session storage.
- Migration `v4` marks the session-token hashing upgrade; startup hashes any legacy raw session tokens.
- Re-running startup does not duplicate schema or corrupt existing data.

## Core tables

### users

- id INTEGER PRIMARY KEY AUTOINCREMENT
- username TEXT NOT NULL UNIQUE
- password TEXT NOT NULL
- created_at TEXT NOT NULL

Rules:
- `username` is unique.

### boards

- id INTEGER PRIMARY KEY AUTOINCREMENT
- user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
- title TEXT NOT NULL
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL

Rules:
- A board belongs to one user.
- For MVP, one board per user is enforced with `UNIQUE(user_id)`.

### "columns"

- id INTEGER PRIMARY KEY AUTOINCREMENT
- board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE
- title TEXT NOT NULL
- position INTEGER NOT NULL CHECK(position >= 0)
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL
- UNIQUE(board_id, position)

Rules:
- A column belongs to one board.
- `position` starts at 0 and is unique within each board.
- Renaming a column updates `title`.

### cards

- id INTEGER PRIMARY KEY AUTOINCREMENT
- column_id INTEGER NOT NULL REFERENCES "columns"(id) ON DELETE CASCADE
- title TEXT NOT NULL
- details TEXT NOT NULL
- position INTEGER NOT NULL CHECK(position >= 0)
- archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1))
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL
- UNIQUE(column_id, position)

Rules:
- A card belongs to one column.
- `details` is required but can be an empty string.
- `archived` is a soft-delete flag for future use.
- `position` starts at 0 and is unique within each column.

### sessions

- token TEXT PRIMARY KEY
- user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
- created_at TEXT NOT NULL
- expires_at TEXT NOT NULL

Rules:
- `token` stores `sha256(session_token)`, not the raw cookie token.
- Expired sessions are rejected during lookup.
- Logout deletes the matching session row.

## Ordering semantics

- Column ordering is controlled by integer `position` values per board.
- Card ordering is controlled by integer `position` values per column.
- Reorder operations reassign sequential positions `0..n-1` in parent scope.
- Implementation uses temporary offset positions during reorder to avoid transient UNIQUE conflicts.

## Query patterns used in MVP

- Resolve user by username; create if not found.
- Resolve board by user_id; create if not found.
- Load columns ordered by `position` for a board.
- Load cards ordered by `position` for each column.
- Save board state by replacing the board's columns/cards from the submitted board JSON.
- Existing card `archived` values are preserved by the frontend model when loaded and saved.
- Column/card row `created_at` values are not authoritative across full-board saves in this MVP.

## Indexes

- idx_boards_user_id on boards(user_id)
- idx_columns_board_id on "columns"(board_id)
- idx_cards_column_id on cards(column_id)
- idx_sessions_user_id on sessions(user_id)
- idx_sessions_expires_at on sessions(expires_at)