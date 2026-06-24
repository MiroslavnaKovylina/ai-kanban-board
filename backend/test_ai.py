import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from db import close_db_connection
from main import app, _reset_auth_guards_for_tests


class AiApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        _reset_auth_guards_for_tests()
        self.previous_openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["KANBAN_DB_PATH"] = str(self.db_path)
        os.environ["AUTH_RATE_LIMIT_ATTEMPTS"] = "10"
        self.client = TestClient(app)
        response = self.client.post(
            "/api/auth/register",
            json={"username": "ai-sanity-user", "password": "pw"},
        )
        self.assertEqual(response.status_code, 200)

    def tearDown(self) -> None:
        close_db_connection()
        _reset_auth_guards_for_tests()
        os.environ.pop("KANBAN_DB_PATH", None)
        os.environ.pop("AUTH_RATE_LIMIT_ATTEMPTS", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        if self.previous_openrouter_key is not None:
            os.environ["OPENROUTER_API_KEY"] = self.previous_openrouter_key
        self.temp_dir.cleanup()

    def test_ai_sanity_requires_authentication(self) -> None:
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.get("/api/ai/sanity")
        self.assertEqual(response.status_code, 401)

    def test_ai_sanity_missing_key_returns_503(self) -> None:
        previous = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            response = self.client.get("/api/ai/sanity")
            self.assertEqual(response.status_code, 503)
        finally:
            if previous is not None:
                os.environ["OPENROUTER_API_KEY"] = previous

    @patch("ai.httpx.post")
    def test_ai_sanity_success(self, mock_post) -> None:
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_response = unittest.mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "4",
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        response = self.client.get("/api/ai/sanity")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["response"], "4")

    @patch("ai.httpx.post")
    def test_ai_sanity_provider_failure_returns_502(self, mock_post) -> None:
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        mock_post.side_effect = httpx.HTTPError("network failure")

        response = self.client.get("/api/ai/sanity")
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
