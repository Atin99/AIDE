import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AIDE_USE_LOCAL_INTENT", "0")
os.environ.setdefault("AIDE_ENABLE_REMOTE_LLM", "0")
os.environ.setdefault("AIDE_USE_LLM_INTENT", "0")
os.environ.setdefault("AIDE_USE_LOCAL_LLM", "0")

from engines.modes import DesignEngine
from engines.pipeline import Candidate, PipelineResult, _build_feedback, _candidate_sort_key, run_pipeline


def _candidate(tag, score=0.0, physics_evaluated=False):
    base = {
        "a": {"Fe": 0.70, "Cr": 0.20, "Ni": 0.10},
        "b": {"Fe": 0.64, "Cr": 0.22, "Mo": 0.14},
        "c": {"Ni": 0.55, "Cr": 0.20, "Co": 0.15, "Al": 0.10},
        "d": {"Fe": 0.68, "Cr": 0.18, "Mn": 0.14},
        "e": {"Ni": 0.50, "Cr": 0.24, "Mo": 0.16, "Ti": 0.10},
        "f": {"Fe": 0.66, "Cr": 0.19, "Ni": 0.09, "Mo": 0.06},
    }[tag]
    weak = []
    physics_result = {}
    if physics_evaluated:
        weak = [{"name": "Corrosion", "score": 42, "fails": ["passive film instability"]}]
        physics_result = {"composite_score": score, "domain_results": [], "n_domains": 0}
    return Candidate(
        composition=dict(base),
        composition_wt=dict(base),
        rationale=tag,
        score=score,
        screening_score=score,
        score_source="physics" if physics_evaluated else "screen",
        physics_evaluated=physics_evaluated,
        weak_domains=weak,
        physics_result=physics_result,
    )


class PipelineIterationPoolTests(unittest.TestCase):
    def test_physics_candidates_sort_above_screen_only_candidates(self):
        screen = _candidate("c", score=100.0, physics_evaluated=False)
        physics = _candidate("a", score=0.0, physics_evaluated=True)
        physics.physics_result = {"composite_score": 59.7, "domain_results": [], "n_domains": 0}
        physics.screening_score = 100.0

        ranked = sorted([screen, physics], key=_candidate_sort_key, reverse=True)

        self.assertIs(ranked[0], physics)
        self.assertIs(ranked[1], screen)

    def test_feedback_is_pruned_to_top_three_failures(self):
        candidates = [
            _candidate("a", score=84.0, physics_evaluated=True),
            _candidate("b", score=82.0, physics_evaluated=True),
            _candidate("c", score=79.0, physics_evaluated=True),
            _candidate("d", score=75.0, physics_evaluated=True),
            _candidate("e", score=71.0, physics_evaluated=True),
        ]

        feedback = _build_feedback(candidates, target_score=85.0, limit=3)

        self.assertEqual(len(feedback["failure_examples"]), 3)
        self.assertEqual([entry["score"] for entry in feedback["failure_examples"]], [84.0, 82.0, 79.0])
        self.assertIn("Corrosion", feedback["weak_summary"])

    def test_run_pipeline_returns_full_master_pool(self):
        generated_feedback = []

        def fake_generate(query, intent, baseline, n=8, iteration=0, feedback=None):
            generated_feedback.append(feedback)
            if iteration == 0:
                return [_candidate("a"), _candidate("b"), _candidate("c")]
            return [_candidate("d"), _candidate("e")]

        def fake_downselect(candidates, limit, query, intent):
            return candidates[:1]

        def fake_evaluate(candidates, **kwargs):
            score_map = {"a": 72.0, "d": 78.0}
            for cand in candidates:
                cand.score = score_map[cand.rationale]
                cand.score_source = "physics"
                cand.physics_evaluated = True
                cand.physics_result = {"composite_score": cand.score, "domain_results": [], "n_domains": 0}
                cand.weak_domains = [{"name": "Fatigue & Fracture", "score": 48, "fails": ["reserve margin"]}]
            return candidates

        def fake_screen_score(cand, intent, query):
            return {"a": 62.0, "b": 58.0, "c": 52.0, "d": 61.0, "e": 49.0}[cand.rationale]

        with patch("engines.researcher.ApplicationResearcher.research", return_value=None), \
             patch("engines.pipeline.BaselinePredictor.predict", return_value=None), \
             patch("engines.pipeline.MultiCompositionGenerator.generate", side_effect=fake_generate), \
             patch("engines.pipeline._downselect_candidates", side_effect=fake_downselect), \
             patch("engines.pipeline.PhysicsMLEvaluator.evaluate", side_effect=fake_evaluate), \
             patch("engines.pipeline._cheap_candidate_score", side_effect=fake_screen_score), \
             patch("engines.pipeline.DomainCorrelator.correlate", return_value=[]):
            result = run_pipeline(
                query="design a corrosion resistant stainless alloy",
                intent={"application": "stainless", "n_results": 5, "use_ml": False},
                max_iterations=2,
                target_score=85.0,
                feedback_limit=3,
                min_iterations=2,
                use_ml=False,
            )

        self.assertEqual(len(result.candidates), 5)
        self.assertEqual(len([cand for cand in result.candidates if cand.physics_evaluated]), 2)
        self.assertEqual(result.generation_stats["returned_candidates"], 5)
        self.assertIsNone(generated_feedback[0])
        self.assertIsNotNone(generated_feedback[1])
        self.assertLessEqual(len(generated_feedback[1]["failure_examples"]), 3)

    def test_design_engine_returns_full_candidate_detail_pool(self):
        fake_result = PipelineResult(
            candidates=[
                _candidate("a", score=81.0, physics_evaluated=True),
                _candidate("b", score=78.0, physics_evaluated=True),
                _candidate("c", score=54.0, physics_evaluated=False),
                _candidate("d", score=49.0, physics_evaluated=False),
            ],
            steps=[],
            baseline=None,
            iterations_run=4,
            converged=False,
            best_score=81.0,
            total_time=1.2,
            explanation="",
            correlation_insights=[],
            generation_stats={"raw_generated": 4, "physics_evaluated": 2, "returned_candidates": 4},
        )

        with patch("engines.modes.run_pipeline", return_value=fake_result):
            result = DesignEngine.run(
                {"application": "stainless", "n_results": 2, "use_ml": False},
                verbose=False,
            )

        self.assertEqual(len(result["top"]), 2)
        # candidates_detail now only includes physics-evaluated candidates
        self.assertEqual(len(result["candidates_detail"]), 2)
        self.assertEqual(result["pipeline_config"]["max_iterations"], 4)
        self.assertEqual(result["best_physics_score"], 81.0)
        self.assertEqual(result["best_rank_score"], 81.0)
        self.assertEqual(result["candidates_detail"][0]["physics_score"], 81.0)
        self.assertTrue(all(c["physics_evaluated"] for c in result["candidates_detail"]))


if __name__ == "__main__":
    unittest.main()
