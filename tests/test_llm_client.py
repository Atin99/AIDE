import unittest
from unittest.mock import patch

from llms.client import _build_payload, _is_retriable_http, _request_headers, get_available_providers


class LLMClientTests(unittest.TestCase):
    def test_openrouter_headers_include_app_identity(self):
        headers = _request_headers({"name": "openrouter", "api_key": "test-key"})
        self.assertEqual(headers["HTTP-Referer"], "http://localhost:9000/app/")
        self.assertEqual(headers["X-OpenRouter-Title"], "AIDE v5")

    def test_openrouter_json_payload_enables_response_healing(self):
        payload = _build_payload(
            {"name": "openrouter", "model": "openai/gpt-oss-20b:free", "json_mode": "response_format"},
            [{"role": "user", "content": "hello"}],
            max_tokens=128,
            temperature=0.0,
            force_json=True,
        )
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["plugins"], [{"id": "response-healing"}])

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

    def test_provider_order_prefers_free_openrouter_path(self):
        with patch.dict(
            "os.environ",
            {
                "AIDE_ENABLE_REMOTE_LLM": "1",
                "OPENROUTER_API_KEY": "or-key",
                "GEMINI_API_KEY": "gm-key",
                "GROQ_API_KEY": "gr-key",
            },
            clear=True,
        ):
            providers = get_available_providers()
            self.assertEqual(
                [provider["name"] for provider in providers[:4]],
                ["openrouter", "openrouter_router", "gemini", "groq"],
            )
            self.assertEqual(providers[0]["model"], "openai/gpt-oss-20b:free")
            self.assertEqual(providers[1]["model"], "openrouter/free")

    def test_json_order_can_prefer_groq_after_openrouter(self):
        with patch.dict(
            "os.environ",
            {
                "AIDE_ENABLE_REMOTE_LLM": "1",
                "OPENROUTER_API_KEY": "or-key",
                "GEMINI_API_KEY": "gm-key",
                "GROQ_API_KEY": "gr-key",
                "AIDE_LLM_JSON_PROVIDER_ORDER": "openrouter,groq,openrouter_router,gemini",
            },
            clear=True,
        ):
            providers = get_available_providers(task="json")
            self.assertEqual(
                [provider["name"] for provider in providers[:4]],
                ["openrouter", "groq", "openrouter_router", "gemini"],
            )

    def test_remote_provider_list_respects_disable_flag(self):
        with patch.dict("os.environ", {"AIDE_ENABLE_REMOTE_LLM": "0", "GEMINI_API_KEY": "test-key"}, clear=False):
            self.assertEqual(get_available_providers(), [])


if __name__ == "__main__":
    unittest.main()
