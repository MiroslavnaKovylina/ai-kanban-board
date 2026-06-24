import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from db import close_db_connection
from main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        os.environ["KANBAN_DB_PATH"] = str(self.db_path)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        close_db_connection()
        os.environ.pop("KANBAN_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_register_and_login_success(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={"username": "user1", "password": "password1"},
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertTrue(register_response.json()["success"])

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "password1"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["success"])

    def test_register_duplicate_username_returns_409(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "dup", "password": "pw"},
        )
        response = self.client.post(
            "/api/auth/register",
            json={"username": "dup", "password": "pw2"},
        )
        self.assertEqual(response.status_code, 409)

    def test_login_invalid_credentials_returns_401(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "u2", "password": "pw"},
        )
        response = self.client.post(
            "/api/auth/login",
            json={"username": "u2", "password": "bad"},
        )
        self.assertEqual(response.status_code, 401)

    def test_load_and_save_board(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "u3", "password": "pw"},
        )

        load_response = self.client.post(
            "/api/board/load",
            json={"username": "u3", "password": "pw"},
        )
        self.assertEqual(load_response.status_code, 200)
        board = load_response.json()["board"]
        self.assertIn("columns", board)
        self.assertIn("cards", board)

        new_board = {
            "columns": [
                {"id": "todo", "title": "To Do", "cardIds": ["c1"]},
                {"id": "done", "title": "Done", "cardIds": []},
            ],
            "cards": {
                "c1": {
                    "id": "c1",
                    "title": "Task",
                    "details": "",
                    "archived": False,
                }
            },
        }

        save_response = self.client.post(
            "/api/board/save",
            json={
                "username": "u3",
                "password": "pw",
                "board": new_board,
            },
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(save_response.json()["success"])

        reloaded = self.client.post(
            "/api/board/load",
            json={"username": "u3", "password": "pw"},
        )
        self.assertEqual(reloaded.status_code, 200)
        self.assertEqual(len(reloaded.json()["board"]["columns"]), 2)

    def test_save_board_invalid_payload_returns_422(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "u4", "password": "pw"},
        )

        invalid_board = {
            "columns": [{"id": "todo", "title": "To Do", "cardIds": ["missing"]}],
            "cards": {},
        }
        response = self.client.post(
            "/api/board/save",
            json={
                "username": "u4",
                "password": "pw",
                "board": invalid_board,
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
