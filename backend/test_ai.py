import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from main import app


class AiApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

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
