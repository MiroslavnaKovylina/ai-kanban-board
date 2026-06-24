import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from db import close_db_connection
from main import app


class AiBoardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        os.environ["KANBAN_DB_PATH"] = str(self.db_path)
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        self.client = TestClient(app)

        reg = self.client.post(
            "/api/auth/register",
            json={"username": "ai-user", "password": "pw"},
        )
        self.assertEqual(reg.status_code, 200)

    def tearDown(self) -> None:
        close_db_connection()
        os.environ.pop("KANBAN_DB_PATH", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        self.temp_dir.cleanup()

    @patch("main.openrouter_board_structured_response")
    def test_ai_board_returns_message_without_update(self, mock_ai) -> None:
        mock_ai.return_value = {
            "message": "No changes needed.",
            "board": None,
        }

        response = self.client.post(
            "/api/ai/board",
            json={
                "username": "ai-user",
                "password": "pw",
                "prompt": "Summarize current board",
                "history": [{"role": "user", "content": "hello"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "No changes needed.")
        self.assertFalse(data["board_updated"])
        self.assertIn("columns", data["board"])

    @patch("main.openrouter_board_structured_response")
    def test_ai_board_applies_board_update(self, mock_ai) -> None:
        updated = {
            "columns": [
                {"id": "todo", "title": "Todo", "cardIds": ["card-1"]},
                {"id": "done", "title": "Done", "cardIds": []},
            ],
            "cards": {
                "card-1": {
                    "id": "card-1",
                    "title": "Write release notes",
                    "details": "Today",
                    "archived": False,
                }
            },
        }
        mock_ai.return_value = {
            "message": "Added one card.",
            "board": updated,
        }

        response = self.client.post(
            "/api/ai/board",
            json={
                "username": "ai-user",
                "password": "pw",
                "prompt": "Add one task",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["board_updated"])
        self.assertEqual(data["message"], "Added one card.")

        titles = [col["title"] for col in data["board"]["columns"]]
        self.assertEqual(titles, ["Todo", "Done"])

    def test_ai_board_requires_valid_auth(self) -> None:
        response = self.client.post(
            "/api/ai/board",
            json={
                "username": "ai-user",
                "password": "bad",
                "prompt": "Do something",
            },
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
