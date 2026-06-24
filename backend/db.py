import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_COLUMN_TITLES = [
    "Backlog",
    "To Do",
    "In Progress",
    "Review",
    "Done",
]


def get_db_path() -> Path:
    env_path = os.getenv("KANBAN_DB_PATH")
    if env_path:
        return Path(env_path).expanduser()

    env_dir = os.getenv("KANBAN_DB_DIR")
    if env_dir:
        return Path(env_dir).expanduser() / "kanban.db"

    # Default outside /app for container-friendly persistence.
    return Path("/data/kanban.db")


def ensure_database_directory(db_path: Path | None = None) -> None:
    resolved = db_path or get_db_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)


def initialize_schema(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

    migrations: dict[int, list[str]] = {
        1: [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS "columns" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL CHECK(position >= 0),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(board_id, position),
                FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                column_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL,
                position INTEGER NOT NULL CHECK(position >= 0),
                archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(column_id, position),
                FOREIGN KEY(column_id) REFERENCES "columns"(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_columns_board_id ON \"columns\"(board_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id)",
        ],
        2: [
            "UPDATE \"columns\" SET title = 'To Do' WHERE title = 'Todo'",
        ],
    }

    for version in sorted(migrations.keys()):
        already_applied = connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (version,),
        ).fetchone()
        if already_applied:
            continue

        with connection:
            for statement in migrations[version]:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    resolved = db_path or get_db_path()
    ensure_database_directory(resolved)
    connection = sqlite3.connect(resolved, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize_schema(connection)
    return connection


_connection: sqlite3.Connection | None = None
_connection_path: Path | None = None


def close_db_connection() -> None:
    global _connection
    global _connection_path
    if _connection is not None:
        _connection.close()
    _connection = None
    _connection_path = None


def get_db_connection() -> sqlite3.Connection:
    global _connection
    global _connection_path

    current_path = get_db_path()
    if _connection is None or _connection_path != current_path:
        close_db_connection()
        _connection = get_connection(current_path)
        _connection_path = current_path
    return _connection


def create_user(username: str, password: str) -> int:
    conn = get_db_connection()
    now = utc_now()
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, password, now),
        )
    return int(cursor.lastrowid)


def create_board_for_user(user_id: int, title: str = "My Board") -> int:
    conn = get_db_connection()
    now = utc_now()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO boards (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, now, now),
        )
        board_id = int(cursor.lastrowid)
        for position, column_title in enumerate(DEFAULT_COLUMN_TITLES):
            conn.execute(
                """
                INSERT INTO "columns" (board_id, title, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (board_id, column_title, position, now, now),
            )
    return board_id


def get_user_by_username(username: str) -> sqlite3.Row | None:
    conn = get_db_connection()
    return conn.execute(
        "SELECT id, username, password FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def authenticate_user(username: str, password: str) -> int | None:
    row = get_user_by_username(username)
    if row is None:
        return None
    if row["password"] != password:
        return None
    return int(row["id"])


def register_user(username: str, password: str) -> tuple[int, int]:
    user_id = create_user(username, password)
    board_id = create_board_for_user(user_id)
    return user_id, board_id


def get_or_create_user_board(username: str, password: str = "password") -> tuple[int, int]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        user_id = create_user(username, password)
    else:
        user_id = int(row["id"])

    board = conn.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if board is None:
        board_id = create_board_for_user(user_id)
    else:
        board_id = int(board["id"])

    return user_id, board_id


def get_board_for_user(user_id: int) -> int | None:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return int(row["id"])


def _next_position(table_name: str, parent_field: str, parent_id: int) -> int:
    conn = get_db_connection()
    row = conn.execute(
        f"SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM {table_name} WHERE {parent_field} = ?",
        (parent_id,),
    ).fetchone()
    return int(row["next_pos"])


def add_column(board_id: int, title: str, position: int | None = None) -> int:
    conn = get_db_connection()
    now = utc_now()
    final_position = position if position is not None else _next_position('"columns"', "board_id", board_id)

    with conn:
        conn.execute(
            "UPDATE \"columns\" SET position = position + 1 WHERE board_id = ? AND position >= ?",
            (board_id, final_position),
        )
        cursor = conn.execute(
            """
            INSERT INTO "columns" (board_id, title, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (board_id, title, final_position, now, now),
        )
    return int(cursor.lastrowid)


def rename_column(column_id: int, title: str) -> None:
    conn = get_db_connection()
    with conn:
        conn.execute(
            "UPDATE \"columns\" SET title = ?, updated_at = ? WHERE id = ?",
            (title, utc_now(), column_id),
        )


def reorder_columns(board_id: int, ordered_column_ids: list[int]) -> None:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM \"columns\" WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    existing_ids = [int(row["id"]) for row in rows]
    if sorted(existing_ids) != sorted(ordered_column_ids):
        raise ValueError("Ordered columns must include all and only columns from this board")

    with conn:
        offset = len(ordered_column_ids) + 1000
        for index, column_id in enumerate(ordered_column_ids):
            conn.execute(
                "UPDATE \"columns\" SET position = ? WHERE id = ?",
                (offset + index, column_id),
            )

        for position, column_id in enumerate(ordered_column_ids):
            conn.execute(
                "UPDATE \"columns\" SET position = ?, updated_at = ? WHERE id = ?",
                (position, utc_now(), column_id),
            )


def add_card(
    column_id: int,
    title: str,
    details: str,
    position: int | None = None,
    archived: bool = False,
) -> int:
    conn = get_db_connection()
    now = utc_now()
    final_position = position if position is not None else _next_position("cards", "column_id", column_id)

    with conn:
        conn.execute(
            "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
            (column_id, final_position),
        )
        cursor = conn.execute(
            """
            INSERT INTO cards (column_id, title, details, position, archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (column_id, title, details, final_position, int(archived), now, now),
        )
    return int(cursor.lastrowid)


def reorder_cards(column_id: int, ordered_card_ids: list[int]) -> None:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
        (column_id,),
    ).fetchall()
    existing_ids = [int(row["id"]) for row in rows]
    if sorted(existing_ids) != sorted(ordered_card_ids):
        raise ValueError("Ordered cards must include all and only cards from this column")

    with conn:
        offset = len(ordered_card_ids) + 1000
        for index, card_id in enumerate(ordered_card_ids):
            conn.execute(
                "UPDATE cards SET position = ? WHERE id = ?",
                (offset + index, card_id),
            )

        for position, card_id in enumerate(ordered_card_ids):
            conn.execute(
                "UPDATE cards SET position = ?, updated_at = ? WHERE id = ?",
                (position, utc_now(), card_id),
            )


def load_board(board_id: int) -> dict[str, Any]:
    conn = get_db_connection()
    columns = conn.execute(
        "SELECT id, title, position FROM \"columns\" WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    result_columns: list[dict[str, Any]] = []
    result_cards: dict[str, dict[str, Any]] = {}

    for column in columns:
        cards = conn.execute(
            """
            SELECT id, title, details, position, archived
            FROM cards
            WHERE column_id = ?
            ORDER BY position
            """,
            (int(column["id"]),),
        ).fetchall()
        card_ids: list[str] = []
        for card in cards:
            card_id = str(card["id"])
            card_ids.append(card_id)
            result_cards[card_id] = {
                "id": card_id,
                "title": card["title"],
                "details": card["details"],
                "archived": bool(card["archived"]),
            }

        result_columns.append(
            {
                "id": str(column["id"]),
                "title": column["title"],
                "position": int(column["position"]),
                "cardIds": card_ids,
            }
        )

    return {"columns": result_columns, "cards": result_cards}


def replace_board(board_id: int, board: dict[str, Any]) -> None:
    columns = board.get("columns")
    cards = board.get("cards")

    if not isinstance(columns, list):
        raise ValueError("board.columns must be a list")
    if not isinstance(cards, dict):
        raise ValueError("board.cards must be an object")

    conn = get_db_connection()
    now = utc_now()

    with conn:
        conn.execute("DELETE FROM cards WHERE column_id IN (SELECT id FROM \"columns\" WHERE board_id = ?)", (board_id,))
        conn.execute("DELETE FROM \"columns\" WHERE board_id = ?", (board_id,))

        for column_position, column in enumerate(columns):
            if not isinstance(column, dict):
                raise ValueError("Each column must be an object")

            title = column.get("title")
            card_ids = column.get("cardIds")

            if not isinstance(title, str) or not title.strip():
                raise ValueError("Each column title must be a non-empty string")
            if not isinstance(card_ids, list):
                raise ValueError("Each column cardIds must be a list")

            column_cursor = conn.execute(
                """
                INSERT INTO "columns" (board_id, title, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (board_id, title, column_position, now, now),
            )
            new_column_id = int(column_cursor.lastrowid)

            for card_position, card_id in enumerate(card_ids):
                card_key = str(card_id)
                card_data = cards.get(card_key)
                if not isinstance(card_data, dict):
                    raise ValueError(f"Missing card payload for card id '{card_key}'")

                card_title = card_data.get("title")
                if not isinstance(card_title, str) or not card_title.strip():
                    raise ValueError("Each card title must be a non-empty string")

                details = card_data.get("details")
                if details is None:
                    details = ""
                if not isinstance(details, str):
                    raise ValueError("Card details must be a string")

                archived = bool(card_data.get("archived", False))

                conn.execute(
                    """
                    INSERT INTO cards (column_id, title, details, position, archived, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (new_column_id, card_title, details, card_position, int(archived), now, now),
                )

        conn.execute(
            "UPDATE boards SET updated_at = ? WHERE id = ?",
            (now, board_id),
        )
