import os
import unittest

os.environ.setdefault("AIDE_USE_LOCAL_INTENT", "0")
os.environ.setdefault("AIDE_ENABLE_REMOTE_LLM", "0")
os.environ.setdefault("AIDE_USE_LLM_INTENT", "0")
os.environ.setdefault("AIDE_USE_LOCAL_LLM", "0")

from engines.pipeline import _composition_signature, run_pipeline
from llms.intent_parser import classify_intent


class QueryBehaviorTests(unittest.TestCase):
    def test_fusible_query_maps_to_low_melting_constraints(self):
        intent = classify_intent("design a lead-free low melting fuse alloy for a thermal fuse")
        self.assertEqual(intent["application"], "fusible_alloy")
        self.assertIn("low_melting_point", intent["target_properties"])
        self.assertIn("Pb", intent["exclude_elements"])

    def test_electronics_query_maps_to_electronic_application(self):
        intent = classify_intent("design a chip alloy for interconnect packaging")
        self.assertEqual(intent["application"], "electronic_alloy")
        self.assertIn("conductivity", intent["target_properties"])

    def test_fusible_pipeline_prefers_fusible_families(self):
        intent = classify_intent("design a lead-free low melting fuse alloy")
        intent["n_results"] = 8
        intent["use_ml"] = False
        result = run_pipeline(
            query="design a lead-free low melting fuse alloy",
            intent=intent,
            max_iterations=1,
            use_ml=False,
        )
        self.assertTrue(result.candidates)
        top = result.candidates[0].composition_wt
        fusible_mass = sum(top.get(el, 0.0) for el in ["Sn", "Bi", "In", "Ga", "Zn", "Sb"])
        structural_mass = sum(top.get(el, 0.0) for el in ["Fe", "Cr", "Ni", "Co", "Mo", "W", "Nb", "Ta"])
        self.assertGreater(fusible_mass, structural_mass)
        self.assertLessEqual(top.get("Pb", 0.0), 1e-9)

    def test_top_candidates_show_family_diversity(self):
        intent = classify_intent("design a chip alloy for interconnect packaging")
        intent["n_results"] = 12
        intent["use_ml"] = False
        result = run_pipeline(
            query="design a chip alloy for interconnect packaging",
            intent=intent,
            max_iterations=1,
            use_ml=False,
        )
        signatures = {
            _composition_signature(c.composition_wt, top_n=3)
            for c in result.candidates[:6]
            if c.composition_wt
        }
        self.assertGreaterEqual(len(signatures), 3)


if __name__ == "__main__":
    unittest.main()
