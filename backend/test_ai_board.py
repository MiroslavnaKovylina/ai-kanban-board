import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from db import close_db_connection
from main import app, _reset_ai_guards_for_tests, _reset_auth_guards_for_tests


class AiBoardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        _reset_ai_guards_for_tests()
        _reset_auth_guards_for_tests()
        os.environ["KANBAN_DB_PATH"] = str(self.db_path)
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "10"
        os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "20"
        os.environ["AI_DAILY_IP_LIMIT"] = "0"
        os.environ["AI_MAX_PROMPT_CHARS"] = "2000"
        os.environ["AI_MAX_HISTORY_MESSAGES"] = "20"
        os.environ["AI_MAX_HISTORY_CHARS"] = "8000"
        os.environ["AI_ALLOW_HEADERLESS"] = "1"
        self.client = TestClient(app)

        reg = self.client.post(
            "/api/auth/register",
            json={"username": "ai-user", "password": "pw"},
        )
        self.assertEqual(reg.status_code, 200)

    def tearDown(self) -> None:
        _reset_ai_guards_for_tests()
        _reset_auth_guards_for_tests()
        close_db_connection()
        os.environ.pop("KANBAN_DB_PATH", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("AUTH_RATE_LIMIT_ATTEMPTS", None)
        os.environ.pop("AI_RATE_LIMIT_PER_MINUTE", None)
        os.environ.pop("AI_DAILY_IP_LIMIT", None)
        os.environ.pop("AI_MAX_PROMPT_CHARS", None)
        os.environ.pop("AI_MAX_HISTORY_MESSAGES", None)
        os.environ.pop("AI_MAX_HISTORY_CHARS", None)
        os.environ.pop("AI_ALLOW_HEADERLESS", None)
        self.temp_dir.cleanup()

    @patch("routes.ai_board.openrouter_board_structured_response")
    def test_ai_board_returns_message_without_update(self, mock_ai) -> None:
        mock_ai.return_value = {
            "message": "No changes needed.",
            "board": None,
        }

        response = self.client.post(
            "/api/ai/board",
            json={
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

    @patch("routes.ai_board.openrouter_board_structured_response")
    def test_ai_board_applies_board_update(self, mock_ai) -> None:
        updated = {
            "columns": [
                {"id": "todo", "title": "To Do", "cardIds": ["card-1"]},
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
                "prompt": "Add one task",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["board_updated"])
        self.assertEqual(data["message"], "Added one card.")

        titles = [col["title"] for col in data["board"]["columns"]]
        self.assertEqual(titles, ["To Do", "Done"])

    def test_ai_board_requires_valid_auth(self) -> None:
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.post(
            "/api/ai/board",
            json={
                "prompt": "Do something",
            },
        )
        self.assertEqual(response.status_code, 401)

    @patch("routes.ai_board.openrouter_board_structured_response")
    def test_ai_board_rate_limit_returns_429(self, mock_ai) -> None:
        os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "1"
        mock_ai.return_value = {
            "message": "OK",
            "board": None,
        }

        first = self.client.post(
            "/api/ai/board",
            json={
                "prompt": "First request",
            },
        )
        second = self.client.post(
            "/api/ai/board",
            json={
                "prompt": "Second request",
            },
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Rate limit exceeded", second.json()["detail"])

    @patch("routes.ai_board.openrouter_board_structured_response")
    def test_ai_board_rejects_invalid_origin(self, mock_ai) -> None:
        mock_ai.return_value = {
            "message": "OK",
            "board": None,
        }

        response = self.client.post(
            "/api/ai/board",
            headers={"origin": "http://evil.example"},
            json={
                "prompt": "Do this",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Invalid origin", response.json()["detail"])

    def test_ai_board_rejects_oversized_prompt(self) -> None:
        os.environ["AI_MAX_PROMPT_CHARS"] = "10"
        response = self.client.post(
            "/api/ai/board",
            json={
                "prompt": "This prompt is definitely longer than ten chars",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Prompt is too large", response.json()["detail"])

    def test_ai_board_rejects_oversized_history(self) -> None:
        os.environ["AI_MAX_HISTORY_CHARS"] = "5"
        response = self.client.post(
            "/api/ai/board",
            json={
                "prompt": "ok",
                "history": [{"role": "user", "content": "too long"}],
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("History content is too large", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
