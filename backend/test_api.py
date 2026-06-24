import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from db import close_db_connection
from main import SESSION_COOKIE_NAME, app, _reset_auth_guards_for_tests


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        _reset_auth_guards_for_tests()
        os.environ["KANBAN_DB_PATH"] = str(self.db_path)
        os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "10"
        os.environ["AUTH_RATE_LIMIT_WINDOW_SECONDS"] = "300"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        close_db_connection()
        _reset_auth_guards_for_tests()
        os.environ.pop("KANBAN_DB_PATH", None)
        os.environ.pop("AUTH_RATE_LIMIT_ATTEMPTS", None)
        os.environ.pop("AUTH_RATE_LIMIT_WINDOW_SECONDS", None)
        self.temp_dir.cleanup()

    def test_register_and_login_success(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={"username": "user1", "password": "password1"},
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertTrue(register_response.json()["success"])
        self.assertIn(SESSION_COOKIE_NAME, self.client.cookies)

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["username"], "user1")

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "password1"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["success"])
        self.assertIn(SESSION_COOKIE_NAME, self.client.cookies)

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

    def test_auth_trims_usernames(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={"username": " trimmed-user ", "password": "pw"},
        )
        self.assertEqual(register_response.status_code, 200)

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "trimmed-user", "password": "pw"},
        )
        self.assertEqual(login_response.status_code, 200)

    def test_load_and_save_board(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "u3", "password": "pw"},
        )

        load_response = self.client.post(
            "/api/board/load",
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
                "board": new_board,
            },
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(save_response.json()["success"])

        reloaded = self.client.post(
            "/api/board/load",
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
                "board": invalid_board,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_protected_board_routes_require_session_cookie(self) -> None:
        response = self.client.post("/api/board/load")
        self.assertEqual(response.status_code, 401)

    def test_logout_deletes_session(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "u5", "password": "pw"},
        )
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_secure_cookie_setting_is_consistent_for_login_register_logout(self) -> None:
        os.environ["SESSION_COOKIE_SECURE"] = "true"
        try:
            register_response = self.client.post(
                "/api/auth/register",
                json={"username": "secure-cookie-user", "password": "pw"},
            )
            self.assertIn("secure", register_response.headers["set-cookie"].lower())

            login_response = self.client.post(
                "/api/auth/login",
                json={"username": "secure-cookie-user", "password": "pw"},
            )
            self.assertIn("secure", login_response.headers["set-cookie"].lower())

            logout_response = self.client.post("/api/auth/logout")
            self.assertIn("secure", logout_response.headers["set-cookie"].lower())
        finally:
            os.environ.pop("SESSION_COOKIE_SECURE", None)

    def test_login_rate_limit_returns_429_by_username(self) -> None:
        os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "1"
        self.client.post(
            "/api/auth/register",
            json={"username": "limited-user", "password": "pw"},
        )

        first = self.client.post(
            "/api/auth/login",
            json={"username": "limited-user", "password": "bad"},
        )
        second = self.client.post(
            "/api/auth/login",
            json={"username": "limited-user", "password": "bad"},
        )

        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Retry-After", second.headers)

    def test_register_rate_limit_returns_429_by_ip(self) -> None:
        os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "1"

        first = self.client.post(
            "/api/auth/register",
            json={"username": "first-rate-user", "password": "pw"},
        )
        second = self.client.post(
            "/api/auth/register",
            json={"username": "second-rate-user", "password": "pw"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Retry-After", second.headers)


if __name__ == "__main__":
    unittest.main()
