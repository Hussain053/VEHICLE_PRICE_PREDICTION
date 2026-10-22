"""Backend checks. Run after model training with unittest discovery."""

import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.train_model import FEATURES, parse_horsepower, prepare_training_data


class PredictionApiChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_health_and_dataset_derived_brand_model_options(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["model_loaded"])
        options = self.client.get("/api/options")
        self.assertEqual(options.status_code, 200)
        body = options.json()
        self.assertGreaterEqual(len(body["companies"]), 40)
        self.assertEqual(body["reference_year"], 2026)
        company_values = {company["value"] for company in body["companies"]}
        self.assertIn("maruti", company_values)
        maruti = next(c for c in body["companies"] if c["value"] == "maruti")
        self.assertIn("maruti swift", {model["value"] for model in maruti["models"]})
        for company in body["companies"]:
            self.assertTrue(company["models"])
            self.assertEqual(len(company["models"]), len({m["value"] for m in company["models"]}))

    def test_valid_request_produces_model_prediction(self):
        options = self.client.get("/api/options").json()
        company = options["companies"][0]
        request = {
            "company": company["value"],
            "model": company["models"][0]["value"],
            "vehicle_age": 10,
            "km_driven": 50000,
            "mileage": 18.0,
            "seating_capacity": 5,
            "horsepower": 90.0,
            "engine_cc": 1200.0,
        }
        response = self.client.post("/api/predict", json=request)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertGreater(body["predicted_price_inr"], 0)
        self.assertTrue(body["formatted_price_inr"].startswith("₹"))
        self.assertEqual(body["inputs"], request)

    def test_validation_rejects_wrong_model_missing_input_and_range(self):
        options = self.client.get("/api/options").json()
        company = options["companies"][0]
        request = {
            "company": company["value"],
            "model": company["models"][0]["value"],
            "vehicle_age": 10,
            "km_driven": 50000,
            "mileage": 18.0,
            "seating_capacity": 5,
            "horsepower": 90.0,
            "engine_cc": 1200.0,
        }
        other_company = options["companies"][1]
        mismatch = dict(request, model=other_company["models"][0]["value"])
        self.assertEqual(self.client.post("/api/predict", json=mismatch).status_code, 422)
        missing = dict(request); missing.pop("mileage")
        self.assertEqual(self.client.post("/api/predict", json=missing).status_code, 422)
        limits = options["limits"]["km_driven"]
        outside = dict(request, km_driven=int(limits["max"]) + 1)
        self.assertEqual(self.client.post("/api/predict", json=outside).status_code, 422)

    def test_cors_allows_local_frontend(self):
        response = self.client.options(
            "/api/predict",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), "http://localhost:5173"
        )

    def test_training_data_uses_exact_eight_inputs_and_normalizes_units(self):
        X, y, audit = prepare_training_data()
        self.assertEqual(X.columns.tolist(), FEATURES)
        self.assertEqual(len(X), len(y))
        self.assertTrue((X["engine_cc"] >= 100).all())
        self.assertTrue((X["mileage"] <= 50).all())
        self.assertGreater(audit["excluded_rows"], 0)
        normalized = parse_horsepower(
            __import__("pandas").Series(["100bhp@1rpm", "100 PS", "100 kW", "100 hp"])
        )
        self.assertAlmostEqual(float(normalized.iloc[0]), 100.0, places=3)
        self.assertAlmostEqual(float(normalized.iloc[1]), 98.632, places=2)
        self.assertAlmostEqual(float(normalized.iloc[2]), 134.102, places=2)


if __name__ == "__main__":
    unittest.main()
