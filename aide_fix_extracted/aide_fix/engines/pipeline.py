"""
engines/pipeline.py  —  AIDE v4 Core Pipeline

Critical fixes vs old version:
  1. ResearchResult is PASSED INTO BaselinePredictor — never ignored
  2. BaselinePredictor LLM prompt contains the exact base constraints
  3. PhysicsMLEvaluator hard-rejects compositions that violate researcher findings
  4. Scoring is weighted by researcher's domain_weights — not a flat 42-domain average
  5. Over-alloying penalty is physics-derived (Matthiessen / solid-solution scattering proxy)
"""

from __future__ import annotations
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from llms.client import chat_json
from engines.researcher import ApplicationResearcher, ResearchResult

logger = logging.getLogger("aide.pipeline")


# ═══════════════════════════════════════════════════════════════════════════
# BASELINE PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════

BASELINE_SYSTEM = """You are an expert alloy designer. Given an application description 
AND strict compositional constraints, produce a realistic starting alloy composition.

Rules you MUST follow:
- The base element(s) MUST occupy at least the specified minimum fraction.
- Only include elements that are physically justified for this application.
- Output ONLY a JSON object: {"Element": mol_fraction, ...} summing to exactly 1.0.
- No explanations, no markdown, just the JSON dict."""


class BaselinePredictor:
    def predict(self, query: str, research: ResearchResult) -> dict[str, float]:
        """
        Generates a baseline composition.
        The ResearchResult is INJECTED into the prompt — this is the core fix.
        The LLM cannot return a composition that ignores the base constraint
        because the constraint is stated explicitly in the prompt.
        """
        logger.info(f"[BASELINE] Finding baseline for: '{query}'")

        constraint_block = (
            f"HARD CONSTRAINTS (you MUST respect these):\n"
            f"  - Base element(s): {research.base_elements}\n"
            f"  - Base element minimum mol-fraction: {research.base_min_fraction:.2f} "
            f"(i.e. the base MUST be the dominant element by a large margin)\n"
            f"  - Forbidden elements (must NOT appear): {research.forbidden_elements}\n"
            f"  - Mandatory mechanisms to enable: {research.mandatory_mechanisms}\n"
            f"  - Rationale: {research.rationale}\n"
        )

        user_prompt = (
            f"Design a baseline alloy for: \"{query}\"\n\n"
            f"{constraint_block}\n"
            f"Return ONLY a JSON dict of element symbols to mol-fractions, summing to 1.0.\n"
            f"Example format: {{\"Al\": 0.92, \"Cu\": 0.045, \"Mg\": 0.025, \"Mn\": 0.01}}"
        )

        raw = chat_json(
            system=BASELINE_SYSTEM,
            user=user_prompt,
            temperature=0.15,
            schema_hint='{"Element": mol_fraction, ...} summing to 1.0',
        )

        composition = self._parse_and_validate(raw, research)
        readable = " ".join(f"{el}:{v*100:.1f}%" for el, v in composition.items())
        logger.info(f"[BASELINE] Baseline: {readable}")
        return composition

    def _parse_and_validate(
        self,
        raw: Any,
        research: ResearchResult,
    ) -> dict[str, float]:
        if not isinstance(raw, dict):
            raise ValueError(f"Baseline LLM returned non-dict: {raw}")

        # Parse & normalise
        comp = {k: float(v) for k, v in raw.items() if isinstance(v, (int, float))}
        total = sum(comp.values())
        if total == 0:
            raise ValueError("Baseline composition sums to zero.")
        comp = {k: v / total for k, v in comp.items()}

        # HARD CHECK: does it honour the base constraint?
        violated, reason = research.composition_violates_base(comp)
        if violated:
            raise ValueError(
                f"Baseline LLM produced a composition violating base constraints: {reason}\n"
                f"Composition: {comp}"
            )
        return comp


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-COMPOSITION GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

GENERATOR_SYSTEM = """You are an expert alloy designer generating diverse candidate alloys.
Each composition must strictly respect the base element constraint provided.
Return ONLY a JSON array of composition dicts, each summing to 1.0.
No prose, no markdown."""


class MultiCompGenerator:
    def generate(
        self,
        query: str,
        baseline: dict[str, float],
        research: ResearchResult,
        n: int = 8,
        iteration: int = 1,
    ) -> list[dict[str, float]]:
        logger.info(f"[GENERATE] Iteration {iteration}: Generating {n} compositions")

        baseline_str = ", ".join(f"{el}:{v:.4f}" for el, v in baseline.items())

        constraint_block = (
            f"HARD CONSTRAINTS:\n"
            f"  - Base elements: {research.base_elements}\n"
            f"  - Base min mol-fraction: {research.base_min_fraction:.2f}\n"
            f"  - Forbidden: {research.forbidden_elements}\n"
            f"  - Must enable mechanisms: {research.mandatory_mechanisms}"
        )

        user_prompt = (
            f"Application: \"{query}\"\n"
            f"Starting baseline: {baseline_str}\n\n"
            f"{constraint_block}\n\n"
            f"Generate {n} diverse alloy candidates as perturbations and alternatives "
            f"to the baseline. Vary element ratios, add or remove minor alloying elements "
            f"(always keeping the base element dominant at ≥{research.base_min_fraction:.0%}).\n"
            f"Return a JSON array of {n} dicts, each mapping element symbols to mol-fractions "
            f"summing to 1.0."
        )

        raw = chat_json(
            system=GENERATOR_SYSTEM,
            user=user_prompt,
            temperature=0.7,
            schema_hint=f"[{{\"Element\": mol_fraction, ...}}, ...] — array of {n} dicts",
        )

        if not isinstance(raw, list):
            raw = [raw]   # LLM returned single dict — wrap it

        candidates = []
        for item in raw:
            try:
                comp = {k: float(v) for k, v in item.items()}
                total = sum(comp.values())
                comp = {k: v / total for k, v in comp.items()}
                violated, reason = research.composition_violates_base(comp)
                if violated:
                    logger.debug(f"[GENERATE] Skipped candidate — {reason}")
                    continue
                candidates.append(comp)
            except Exception as e:
                logger.debug(f"[GENERATE] Skipped malformed candidate: {e}")

        if not candidates:
            logger.warning("[GENERATE] LLM candidates all invalid — falling back to perturbation")
            candidates = self._perturb(baseline, research, n)

        return candidates

    def _perturb(
        self,
        baseline: dict[str, float],
        research: ResearchResult,
        n: int,
    ) -> list[dict[str, float]]:
        """
        Pure perturbation fallback — still respects base constraint mathematically.
        """
        base_el = research.base_elements[0]
        results = []
        for _ in range(n):
            comp = dict(baseline)
            for el in list(comp.keys()):
                if el != base_el:
                    comp[el] *= random.uniform(0.7, 1.3)
            total = sum(comp.values())
            comp = {k: v / total for k, v in comp.items()}
            # Re-enforce base constraint
            if comp.get(base_el, 0) < research.base_min_fraction:
                deficit = research.base_min_fraction - comp[base_el]
                comp[base_el] += deficit
                total = sum(comp.values())
                comp = {k: v / total for k, v in comp.items()}
            results.append(comp)
        return results


# ═══════════════════════════════════════════════════════════════════════════
# PHYSICS ML EVALUATOR  —  Hard rejection + dynamic weighting
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EvalResult:
    composition:        dict[str, float]
    score:              float
    domain_scores:      dict[str, float] = field(default_factory=dict)
    rejection_reason:   Optional[str]    = None
    passed_hard_gates:  bool             = True


class PhysicsMLEvaluator:
    """
    Evaluates alloy candidates against physics domains.

    Scoring formula (replaces flat 42-domain average):
        final_score = weighted_domain_score × overalloying_penalty

    Hard gates (score = 0.0 immediately):
        1. Base element fraction < research.base_min_fraction
        2. Forbidden element present
        3. LLM-derived mandatory mechanism fails a basic quantitative check
    """

    def __init__(self, domain_evaluators: dict[str, callable]):
        """
        domain_evaluators: domain_name -> fn(composition) -> float[0,100]
        Pass your existing 42-domain evaluator functions here.
        """
        self.domain_evaluators = domain_evaluators

    def evaluate_batch(
        self,
        compositions: list[dict[str, float]],
        query: str,
        research: ResearchResult,
    ) -> list[EvalResult]:
        logger.info(f"[EVALUATE] Evaluating {len(compositions)} candidates")
        results = [self._evaluate_one(c, query, research) for c in compositions]
        valid   = [r for r in results if r.passed_hard_gates]
        invalid = len(results) - len(valid)
        if invalid:
            logger.info(f"[EVALUATE] Hard-rejected {invalid} candidates")
        if valid:
            best = max(valid, key=lambda r: r.score)
            logger.info(f"[EVALUATE] Best: {best.score:.1f}/100")
        return results

    def _evaluate_one(
        self,
        composition: dict[str, float],
        query:       str,
        research:    ResearchResult,
    ) -> EvalResult:

        # ── GATE 1: Base constraint ───────────────────────────────────────
        violated, reason = research.composition_violates_base(composition)
        if violated:
            return EvalResult(composition=composition, score=0.0,
                              rejection_reason=reason, passed_hard_gates=False)

        # ── GATE 2: Mandatory mechanism quantitative checks ───────────────
        mech_result = self._check_mechanisms(composition, research.mandatory_mechanisms)
        if mech_result is not None:
            return EvalResult(composition=composition, score=0.0,
                              rejection_reason=mech_result, passed_hard_gates=False)

        # ── Soft scoring: researcher-weighted domains ─────────────────────
        domain_scores = self._run_domains(composition)

        # Apply researcher's weights — only domains the researcher listed count
        # at their prescribed weights; all others contribute at residual weight
        primary_weight_total = sum(research.domain_weights.values())
        residual_weight       = max(0.0, 1.0 - primary_weight_total) / max(
            1, len(domain_scores) - len(research.domain_weights)
        )

        weighted_sum = 0.0
        weight_used  = 0.0
        for domain, score in domain_scores.items():
            w = research.domain_weights.get(domain, residual_weight)
            weighted_sum += w * score
            weight_used  += w

        weighted_score = weighted_sum / weight_used if weight_used > 0 else 50.0

        # ── Over-alloying penalty ─────────────────────────────────────────
        penalty = self._overalloying_penalty(composition, query, research)
        final   = round(weighted_score * penalty, 2)

        return EvalResult(
            composition=composition,
            score=final,
            domain_scores=domain_scores,
            passed_hard_gates=True,
        )

    # ── Mechanism checks ─────────────────────────────────────────────────────
    # These are QUANTITATIVE physics gates, not lookup tables.
    # The mechanism names come from the LLM researcher — we map them to
    # standard metallurgical criteria at runtime.

    _MECHANISM_CHECKS = {
        # keyword fragment -> (check_fn, failure_message_template)
        "gamma_prime": (
            lambda c: c.get("Al", 0) + c.get("Ti", 0) >= 0.04,
            "γ' precipitation requires Al+Ti ≥ 4 mol% — got {:.3f}"
        ),
        "precipitation_hard": (
            lambda c: c.get("Cu", 0) + c.get("Mg", 0) + c.get("Zn", 0) >= 0.005,
            "Precipitation hardening requires Cu+Mg+Zn ≥ 0.5 mol% — got {:.4f}"
        ),
        "martensite": (
            lambda c: c.get("C", 0) >= 0.003,
            "Martensite requires C ≥ 0.3 mol% — got {:.4f} (blade/tool impossible)"
        ),
        "alpha_beta": (
            lambda c: (c.get("V",0)+c.get("Mo",0)+c.get("Nb",0)+c.get("Cr",0)) >= 0.02,
            "α+β Ti microstructure requires β-stabilisers ≥ 2 mol% — got {:.3f}"
        ),
        "solid_solution": (
            lambda c: len([v for v in c.values() if v > 0.005]) >= 2,
            "Solid solution strengthening requires ≥2 solute elements"
        ),
        "carbide": (
            lambda c: c.get("C", 0) >= 0.002 and c.get("Cr", 0) + c.get("W", 0) >= 0.10,
            "Carbide dispersion requires C ≥ 0.2% and (Cr+W) ≥ 10% — got C={:.4f}"
        ),
    }

    def _check_mechanisms(
        self,
        composition: dict[str, float],
        mechanisms:  list[str],
    ) -> Optional[str]:
        """Returns a rejection reason string, or None if all mechanisms pass."""
        for mechanism in mechanisms:
            mech_lower = mechanism.lower().replace(" ", "_").replace("-", "_")
            for keyword, (check_fn, msg_template) in self._MECHANISM_CHECKS.items():
                if keyword in mech_lower:
                    passed = check_fn(composition)
                    if not passed:
                        # Compute the relevant quantity for the error message
                        relevant_sum = sum(
                            composition.get(el, 0)
                            for el in ["Al","Ti","Cu","Mg","Zn","C","V","Mo","Nb","Cr","W"]
                        )
                        return (
                            f"Mandatory mechanism '{mechanism}' failed: "
                            + msg_template.format(relevant_sum)
                        )
        return None

    # ── Domain runner ─────────────────────────────────────────────────────────

    def _run_domains(self, composition: dict[str, float]) -> dict[str, float]:
        scores = {}
        for domain, fn in self.domain_evaluators.items():
            try:
                scores[domain] = float(fn(composition))
            except Exception as e:
                logger.debug(f"[EVALUATE] Domain {domain} error: {e}")
                scores[domain] = 50.0   # neutral — don't crash the run
        return scores

    # ── Over-alloying penalty ─────────────────────────────────────────────────

    def _overalloying_penalty(
        self,
        composition: dict[str, float],
        query:       str,
        research:    ResearchResult,
    ) -> float:
        """
        Physics-derived penalty. Uses Matthiessen's rule proxy for conductivity
        applications; solute-strengthening saturation for structural.
        Returns a multiplier ∈ (0, 1].
        """
        base_frac    = max(composition.values())
        solute_frac  = 1.0 - base_frac
        solute_count = sum(1 for v in composition.values() if v > 0.005)
        q = query.lower()

        if any(k in q for k in ["electr", "conduct", "wire", "thermal"]):
            # Matthiessen proxy: each solute atom scatters conduction electrons
            # Resistivity ∝ Σ(ci) → penalty = exp(-k * solute_frac)
            penalty = math.exp(-9.0 * solute_frac)

        elif any(k in q for k in ["turbine", "superalloy", "creep", "jet"]):
            # Superalloys tolerate high complexity — penalise only extreme cases
            excess  = max(0, solute_count - 9)
            penalty = math.exp(-0.25 * excess)

        elif any(k in q for k in ["biomedical", "implant", "bone"]):
            # Biocompatibility: fewer elements = lower ion-release risk
            excess  = max(0, solute_count - 4)
            penalty = math.exp(-0.6 * excess)

        else:
            # General: solid-solution saturation after ~6 alloying elements
            excess  = max(0, solute_count - 6)
            penalty = math.exp(-0.45 * excess)

        return max(0.001, penalty)   # never exactly zero from penalty alone


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL DESIGN ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class DesignEngine:
    """
    Orchestrates the full pipeline. Researcher output flows explicitly
    into every downstream stage — nothing is ever silently bypassed.
    """

    def __init__(self, domain_evaluators: dict[str, callable], max_iterations: int = 3):
        self.researcher  = ApplicationResearcher()
        self.baseline    = BaselinePredictor()
        self.generator   = MultiCompGenerator()
        self.evaluator   = PhysicsMLEvaluator(domain_evaluators)
        self.max_iters   = max_iterations

    def run(self, query: str, n_candidates: int = 8) -> dict:
        # 1. Research — produces ResearchResult
        research = self.researcher.research(query)

        # 2. Baseline — receives ResearchResult, cannot ignore it
        baseline_comp = self.baseline.predict(query, research)

        best_score    = -1.0
        best_result   = None
        all_results   = []

        for iteration in range(1, self.max_iters + 1):
            # 3. Generate candidates — constrained by ResearchResult
            candidates = self.generator.generate(
                query, baseline_comp, research,
                n=n_candidates, iteration=iteration
            )
            candidates.append(baseline_comp)   # always include baseline

            # 4. Evaluate — hard gates + dynamic weighting
            results = self.evaluator.evaluate_batch(candidates, query, research)
            all_results.extend(results)

            valid = [r for r in results if r.passed_hard_gates]
            if not valid:
                logger.warning(f"[PIPELINE] Iteration {iteration}: no valid candidates passed gates")
                continue

            iter_best = max(valid, key=lambda r: r.score)
            delta     = iter_best.score - best_score

            if iter_best.score > best_score:
                best_score  = iter_best.score
                best_result = iter_best
                baseline_comp = iter_best.composition   # update anchor

            logger.info(f"[Pipeline] [CONVERGE] Iteration {iteration} best: {best_score:.1f} (delta {delta:+.1f})")
            if delta < 0.5 and iteration > 1:
                logger.info("[Pipeline] [CONVERGE] Converged")
                break

        if best_result is None:
            reasons = list({r.rejection_reason for r in all_results if r.rejection_reason})
            raise RuntimeError(
                f"Pipeline produced no valid alloys for '{query}'.\n"
                f"Rejection reasons: {reasons}"
            )

        return {
            "query":        query,
            "research":     research,
            "best":         best_result,
            "all_results":  all_results,
        }
