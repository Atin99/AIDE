import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AIDE_USE_LOCAL_INTENT", "0")
os.environ.setdefault("AIDE_ENABLE_REMOTE_LLM", "0")
os.environ.setdefault("AIDE_USE_LLM_INTENT", "0")
os.environ.setdefault("AIDE_USE_LOCAL_LLM", "0")

from engines.pipeline import Candidate, _apply_intent_to_wt, _cheap_candidate_score, _composition_signature, _llm_baseline, run_pipeline
from engines.researcher import ApplicationResearcher, ResearchResult
from physics.base import density_rule_of_mixtures
from llms.intent_parser import classify_intent


class QueryBehaviorTests(unittest.TestCase):
    def test_stainless_intent_conditioning_clamps_exotic_superalloy_recipe(self):
        weird = {"Ni": 0.70, "W": 0.122, "Cr": 0.076, "Nb": 0.075, "Re": 0.026}
        conditioned = _apply_intent_to_wt(
            weird,
            {"application": "stainless", "constraints": {}, "target_properties": ["corrosion_resistance"]},
            "design a stainless alloy for chloride corrosion resistance",
        )

        self.assertGreaterEqual(conditioned.get("Fe", 0.0), 0.49)
        self.assertGreaterEqual(conditioned.get("Cr", 0.0), 0.12)
        self.assertLessEqual(conditioned.get("Re", 0.0), 0.0051)
        self.assertLessEqual(conditioned.get("W", 0.0), 0.0501)

    def test_screening_score_zeroes_out_research_family_mismatch(self):
        research = ResearchResult(
            base_elements=["Fe"],
            base_min_fraction=0.60,
            forbidden_elements=[],
            mandatory_mechanisms=[],
            primary_domains=["Mechanical"],
            domain_weights={"Mechanical": 1.0},
            rationale="Fe-base structural alloy",
        ).validate()
        candidate = Candidate(
            composition={"Ni": 0.70, "W": 0.12, "Cr": 0.08, "Nb": 0.07, "Re": 0.03},
            composition_wt={"Ni": 0.70, "W": 0.12, "Cr": 0.08, "Nb": 0.07, "Re": 0.03},
        )
        score = _cheap_candidate_score(
            candidate,
            {
                "application": "general_structural",
                "constraints": {},
                "must_include": [],
                "exclude_elements": [],
                "research_data": research,
            },
            "design a structural radiation resistant alloy",
        )

        self.assertEqual(score, 0.0)

    def test_fusible_query_maps_to_low_melting_constraints(self):
        intent = classify_intent("design a lead-free low melting fuse alloy for a thermal fuse")
        self.assertEqual(intent["application"], "fusible_alloy")
        self.assertIn("low_melting_point", intent["target_properties"])
        self.assertIn("Pb", intent["exclude_elements"])

    def test_electronics_query_maps_to_electronic_application(self):
        intent = classify_intent("design a chip alloy for interconnect packaging")
        self.assertEqual(intent["application"], "electronic_alloy")
        self.assertIn("conductivity", intent["target_properties"])

    def test_lightweight_aerospace_query_avoids_false_superalloy(self):
        intent = classify_intent("good alloy for jet body, lightweight and strong")
        self.assertEqual(intent["application"], "ti_alloy")
        self.assertIn("low_density", intent["target_properties"])
        self.assertNotIn("high_temperature_strength", intent["target_properties"])
        self.assertLessEqual(intent["constraints"].get("max_density", 99), 5.2)

    def test_rocket_chamber_liner_query_maps_to_superalloy_context(self):
        intent = classify_intent("Recommend an alloy for reusable rocket chamber liner, high heat flux and thermal fatigue")
        self.assertEqual(intent["application"], "superalloy")
        self.assertIn("high_temperature_strength", intent["target_properties"])
        self.assertIn("fatigue_resistance", intent["target_properties"])

    def test_crane_body_query_adds_structural_service_properties(self):
        intent = classify_intent("good alloy for crane body")
        self.assertEqual(intent["application"], "general_structural")
        self.assertIn("high_strength", intent["target_properties"])
        self.assertIn("fatigue_resistance", intent["target_properties"])
        self.assertIn("weldability", intent["target_properties"])

    def test_lightweight_conditioning_caps_heavy_elements(self):
        weird = {"Ni": 0.55, "W": 0.18, "Re": 0.08, "Ta": 0.06, "Cr": 0.13}
        conditioned = _apply_intent_to_wt(
            weird,
            {
                "application": "ti_alloy",
                "constraints": {"max_density": 5.2},
                "target_properties": ["high_strength", "low_density"],
            },
            "design a lightweight aerospace structural alloy",
        )

        self.assertGreaterEqual(conditioned.get("Ti", 0.0), 0.77)
        self.assertLessEqual(conditioned.get("W", 0.0), 0.0102)
        self.assertLessEqual(conditioned.get("Re", 0.0), 0.0021)
        self.assertLessEqual(conditioned.get("Ta", 0.0), 0.0153)

    def test_researcher_uses_family_appropriate_strength_mechanisms(self):
        researcher = ApplicationResearcher()

        superalloy = researcher._heuristic_research(
            "design a high-strength superalloy",
            intent={
                "application": "superalloy",
                "target_properties": ["high_strength", "high_temperature_strength"],
                "constraints": {},
                "exclude_elements": [],
            },
        )
        self.assertIn("gamma_prime", superalloy.mandatory_mechanisms)
        self.assertNotIn("precipitation_hard", superalloy.mandatory_mechanisms)

        titanium = researcher._heuristic_research(
            "design a lightweight titanium alloy with high strength",
            intent={
                "application": "ti_alloy",
                "target_properties": ["high_strength", "low_density"],
                "constraints": {},
                "exclude_elements": [],
            },
        )
        self.assertIn("alpha_beta", titanium.mandatory_mechanisms)
        self.assertNotIn("precipitation_hard", titanium.mandatory_mechanisms)

    def test_crane_body_research_spreads_weight_beyond_mechanical(self):
        researcher = ApplicationResearcher()
        structural = researcher._heuristic_research(
            "good alloy for crane body",
            intent={
                "application": "general_structural",
                "target_properties": ["high_strength", "fatigue_resistance", "weldability"],
                "constraints": {},
                "exclude_elements": [],
            },
        )
        self.assertIn("Mechanical", structural.primary_domains)
        self.assertIn("Fatigue & Fracture", structural.primary_domains)
        self.assertIn("Weldability", structural.primary_domains)
        self.assertGreater(len(structural.domain_weights), 2)

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

    def test_lightweight_pipeline_prefers_low_density_family(self):
        query = "design a lightweight aerospace structural alloy with high strength"
        intent = classify_intent(query)
        intent["n_results"] = 8
        intent["use_ml"] = False
        result = run_pipeline(
            query=query,
            intent=intent,
            max_iterations=1,
            use_ml=False,
        )

        self.assertTrue(result.candidates)
        top = result.candidates[0]
        top_wt = top.composition_wt
        density = density_rule_of_mixtures(top.composition)

        self.assertGreater(
            top_wt.get("Ti", 0.0) + top_wt.get("Al", 0.0),
            top_wt.get("Ni", 0.0) + top_wt.get("Co", 0.0) + top_wt.get("W", 0.0) + top_wt.get("Re", 0.0),
        )
        self.assertIsNotNone(density)
        self.assertLessEqual(density, 6.5)

    def test_crane_body_pipeline_scores_are_not_flat(self):
        query = "good alloy for crane body"
        intent = classify_intent(query)
        intent["n_results"] = 8
        intent["use_ml"] = False
        result = run_pipeline(
            query=query,
            intent=intent,
            max_iterations=1,
            use_ml=False,
        )

        self.assertTrue(result.candidates)
        top_scores = {round(c.score, 2) for c in result.candidates[:5]}
        self.assertGreaterEqual(len(top_scores), 2)
        top = result.candidates[0].composition_wt
        self.assertGreaterEqual(top.get("Fe", 0.0), 0.75)
        self.assertLessEqual(top.get("C", 0.0), 0.0125)
        self.assertLessEqual(top.get("Cr", 0.0), 0.061)

    def test_remote_intent_is_canonicalized_for_heat_spreader_query(self):
        with patch.dict("os.environ", {"AIDE_USE_LLM_INTENT": "1"}, clear=False):
            with patch("llms.intent_parser.llm_available", return_value=True):
                with patch(
                    "llms.intent_parser._ask_llm",
                    return_value={
                        "mode": "design",
                        "application": "hea",
                        "target_properties": [
                            "high thermal conductivity (~200 W/mK)",
                            "low density (~2.7 g/cm³)",
                            "good mechanical strength at room temperature",
                            "good corrosion resistance",
                        ],
                        "notes": "heat spreader alloy",
                    },
                ):
                    intent = classify_intent("Design an alloy for laptop heat spreader, lightweight and thermally conductive")

        self.assertEqual(intent["classifier_source"], "remote_llm+rule")
        self.assertEqual(intent["application"], "al_alloy")
        self.assertIn("conductivity", intent["target_properties"])
        self.assertIn("low_density", intent["target_properties"])
        self.assertIn("high_strength", intent["target_properties"])
        self.assertIn("corrosion_resistance", intent["target_properties"])
        self.assertNotIn("high thermal conductivity (~200 W/mK)", intent["target_properties"])

    def test_remote_intent_family_is_guardrailed_for_rocket_liner_query(self):
        with patch.dict("os.environ", {"AIDE_USE_LLM_INTENT": "1"}, clear=False):
            with patch("llms.intent_parser.llm_available", return_value=True):
                with patch(
                    "llms.intent_parser._ask_llm",
                    return_value={
                        "mode": "design",
                        "application": "hea",
                        "target_properties": [
                            "High temperature strength up to 800 C",
                            "Excellent thermal fatigue resistance",
                            "Corrosion resistance in oxidizing environments",
                        ],
                        "notes": "rocket chamber liner alloy",
                    },
                ):
                    intent = classify_intent("Recommend an alloy for reusable rocket chamber liner, high heat flux and thermal fatigue")

        self.assertEqual(intent["application"], "superalloy")
        self.assertIn("high_temperature_strength", intent["target_properties"])
        self.assertIn("fatigue_resistance", intent["target_properties"])
        self.assertIn("corrosion_resistance", intent["target_properties"])

    def test_remote_intent_numeric_constraints_are_sanitized(self):
        with patch.dict("os.environ", {"AIDE_USE_LLM_INTENT": "1"}, clear=False):
            with patch("llms.intent_parser.llm_available", return_value=True):
                with patch(
                    "llms.intent_parser._ask_llm",
                    return_value={
                        "mode": "design",
                        "application": "al_alloy",
                        "target_properties": ["lightweight", "high thermal conductivity"],
                        "constraints": {"max_density": "2.7 g/cm3"},
                        "notes": "heat spreader alloy",
                    },
                ):
                    intent = classify_intent("Design an alloy for laptop heat spreader, lightweight and thermally conductive")

        self.assertEqual(intent["constraints"]["max_density"], 2.7)

    def test_llm_baseline_normalizes_lowercase_element_symbols(self):
        with patch("llms.client.chat_json", return_value={"comp_wt": {"ti": 0.9, "al": 0.1}, "rationale": "ti-al seed"}):
            baseline = _llm_baseline(
                "design a lightweight aerospace structural alloy",
                {"application": "ti_alloy", "constraints": {}, "target_properties": ["high_strength", "low_density"]},
            )

        self.assertIsNotNone(baseline)
        self.assertIn("Ti", baseline.composition_wt)
        self.assertIn("Al", baseline.composition_wt)


if __name__ == "__main__":
    unittest.main()
