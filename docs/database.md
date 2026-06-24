# Database Schema

This backend uses the normalized relational model from the course.

## Engine and file location

- Engine: SQLite
- Default file: backend/data/kanban.db
- Optional overrides:
	- KANBAN_DB_PATH (full file path)
	- KANBAN_DB_DIR (directory where kanban.db is created)
- The database directory and file are created automatically if missing.

## Idempotent schema initialization

Schema setup is executed on backend startup and is idempotent.

- Table `schema_migrations` tracks applied versions.
- Migration `v1` creates all core tables and indexes.
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
- Rename column by `id`.
- Reorder columns/cards by writing normalized positions in transaction.

## Indexes

- idx_boards_user_id on boards(user_id)
- idx_columns_board_id on "columns"(board_id)
- idx_cards_column_id on cards(column_id)