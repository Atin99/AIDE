import unittest
from unittest.mock import patch

from llms.client import _is_retriable_http, _request_headers, get_available_providers


class LLMClientTests(unittest.TestCase):
    def test_groq_headers_include_browser_user_agent(self):
        headers = _request_headers({"name": "groq", "api_key": "test-key"})
        self.assertIn("User-Agent", headers)
        self.assertIn("Chrome", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json")

    def test_gemini_retries_transient_errors(self):
        provider = {"name": "gemini"}
        self.assertTrue(_is_retriable_http(provider, 429, "quota exceeded"))
        self.assertTrue(_is_retriable_http(provider, 503, "backend overloaded"))

    def test_groq_cloudflare_1010_is_not_marked_retriable(self):
        provider = {"name": "groq"}
        self.assertFalse(_is_retriable_http(provider, 403, "error code: 1010"))

    def test_remote_provider_list_respects_disable_flag(self):
        with patch.dict("os.environ", {"AIDE_ENABLE_REMOTE_LLM": "0", "GEMINI_API_KEY": "test-key"}, clear=False):
            self.assertEqual(get_available_providers(), [])


if __name__ == "__main__":
    unittest.main()
