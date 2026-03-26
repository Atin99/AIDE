import os
import unittest

from fastapi.testclient import TestClient

os.environ.setdefault("AIDE_USE_LOCAL_INTENT", "0")
os.environ.setdefault("AIDE_ENABLE_REMOTE_LLM", "0")
os.environ.setdefault("AIDE_USE_LLM_INTENT", "0")

from backend.app.main import app


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("version", body["data"])
        self.assertIn("docs", body["data"])

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["status"], "healthy")

    def test_domains(self):
        response = self.client.get("/api/v1/domains")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        domains = body["data"]["domains"]
        self.assertGreaterEqual(len(domains), 35)

    def test_unified_engine_run(self):
        response = self.client.post(
            "/api/v1/run",
            json={"query": "design a corrosion resistant stainless alloy"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["request_type"], "engine_run")
        self.assertIn("result", body["data"])

    def test_unified_composition_run(self):
        response = self.client.post(
            "/api/v1/run",
            json={
                "composition": {"Fe": 0.68, "Cr": 0.19, "Ni": 0.1, "Mo": 0.03},
                "basis": "wt",
                "temperature_K": 298.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["request_type"], "composition_analyze")
        self.assertIn("result", body["data"])

    def test_empty_payload_returns_error(self):
        response = self.client.post("/api/v1/run", json={})
        self.assertIn(response.status_code, [400, 422, 500])


if __name__ == "__main__":
    unittest.main()
