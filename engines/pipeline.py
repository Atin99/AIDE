import sys, os, time, logging
from dataclasses import dataclass, field
from typing import Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.elements import validate_composition
from physics.base import mol_to_wt, wt_to_mol, norm

logger = logging.getLogger("AIDE.pipeline")


@dataclass
class PipelineStep:
    step_num: int
    stage: str
    thought: str
    observation: str
    agent: str = ""
    timestamp: float = 0.0
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class Candidate:
    composition: dict
    composition_wt: dict
    rationale: str = ""
    physics_result: dict = field(default_factory=dict)
    ml_predictions: dict = field(default_factory=dict)
    correlations: dict = field(default_factory=dict)
    score: float = 0.0
    weak_domains: list = field(default_factory=list)
    iteration: int = 0


@dataclass
class PipelineResult:
    candidates: list
    steps: list
    baseline: Optional[Candidate] = None
    iterations_run: int = 0
    converged: bool = False
    best_score: float = 0.0
    total_time: float = 0.0
    explanation: str = ""
    correlation_insights: list = field(default_factory=list)
    mode: str = "design"


def _normalize_wt(comp):
    total = sum(v for v in comp.values() if v > 0)
    if total <= 0:
        return {}
    return {k: v / total for k, v in comp.items() if v > 1e-6}


def _set_floor(wt, symbol, minimum):
    current = wt.get(symbol, 0.0)
    if current >= minimum:
        return wt
    needed = minimum - current
    others = [k for k in wt.keys() if k != symbol]
    other_total = sum(wt.get(k, 0.0) for k in others)
    if other_total <= 0:
        wt[symbol] = minimum
        return _normalize_wt(wt)
    scale = max(0.0, (other_total - needed) / other_total)
    for key in others:
        wt[key] *= scale
    wt[symbol] = minimum
    return _normalize_wt(wt)


def _intent_required_elements(intent, query=""):
    must = set(intent.get("must_include", []) or [])
    exclude = set(intent.get("exclude_elements", []) or [])
    props = set(intent.get("target_properties", []) or [])
    constraints = dict(intent.get("constraints", {}) or {})
    app = intent.get("application") or ""
    q = (query or "").lower()

    if constraints.get("no_ni"):
        exclude.add("Ni")
    if constraints.get("no_co"):
        exclude.add("Co")

    if app in {"stainless", "structural", "carbon_steel"}:
        must.add("Fe")
    if app == "stainless":
        must.add("Cr")
    if app == "superalloy":
        if "Ni" not in exclude:
            must.add("Ni")
        elif "Co" not in exclude:
            must.add("Co")
        must.add("Cr")
    if app == "ti_alloy":
        must.add("Ti")
    if app == "al_alloy":
        must.add("Al")
    if app == "cu_alloy":
        must.add("Cu")
    if app == "nuclear":
        if "Zr" not in exclude:
            must.add("Zr")

    if "corrosion_resistance" in props or any(k in q for k in ["marine", "chloride", "seawater", "pitting"]):
        must.add("Cr")
        if "Mo" not in exclude:
            must.add("Mo")

    if "high_temperature_strength" in props or "creep_resistance" in props:
        if "Ni" not in exclude:
            must.add("Ni")
        elif "Co" not in exclude:
            must.add("Co")
        must.add("Cr")

    if "wear_resistance" in props or "hardness" in props:
        if "C" not in exclude:
            must.add("C")
        if "V" not in exclude:
            must.add("V")
        if "W" not in exclude:
            must.add("W")

    if constraints.get("cost_level") == "low":
        exclude.update({"Re", "Ta", "Hf"})

    must = sorted(e for e in must if e not in exclude)
    return must, sorted(exclude)


def _default_seed_for_application(application):
    app = (application or "").lower()
    seeds = {
        "stainless": {"Fe": 0.66, "Cr": 0.19, "Ni": 0.08, "Mo": 0.04, "Mn": 0.02, "N": 0.01},
        "structural": {"Fe": 0.95, "Mn": 0.02, "Si": 0.02, "C": 0.01},
        "general_structural": {"Fe": 0.95, "Mn": 0.02, "Si": 0.02, "C": 0.01},
        "carbon_steel": {"Fe": 0.975, "Mn": 0.012, "Si": 0.008, "C": 0.005},
        "superalloy": {"Ni": 0.56, "Cr": 0.18, "Co": 0.10, "Mo": 0.06, "Al": 0.04, "Ti": 0.03, "Fe": 0.03},
        "ti_alloy": {"Ti": 0.89, "Al": 0.06, "V": 0.04, "Fe": 0.01},
        "al_alloy": {"Al": 0.93, "Mg": 0.03, "Si": 0.02, "Cu": 0.015, "Mn": 0.005},
        "cu_alloy": {"Cu": 0.90, "Zn": 0.08, "Ni": 0.02},
        "nuclear": {"Zr": 0.97, "Sn": 0.015, "Fe": 0.008, "Cr": 0.007},
        "biomedical": {"Ti": 0.84, "Nb": 0.10, "Zr": 0.04, "Ta": 0.02},
        "open_alloy": {"Fe": 0.22, "Ni": 0.20, "Cr": 0.18, "Co": 0.15, "Ti": 0.12, "Al": 0.13},
    }
    return _normalize_wt(seeds.get(app, {"Fe": 0.94, "Mn": 0.03, "Si": 0.02, "C": 0.01}))


def _apply_intent_to_wt(wt, intent, query=""):
    wt = _normalize_wt(dict(wt or {}))
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))

    must, exclude = _intent_required_elements(intent, query)
    for symbol in exclude:
        wt.pop(symbol, None)
    wt = _normalize_wt(wt)
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))
        for symbol in exclude:
            wt.pop(symbol, None)
        wt = _normalize_wt(wt)
    if not wt:
        wt = {"Fe": 1.0}

    constraints = dict(intent.get("constraints", {}) or {})
    props = set(intent.get("target_properties", []) or [])
    rd = intent.get("research_data")

    if rd and rd.base_elements:
        base = rd.base_elements[0]
        if base not in exclude:
            wt[base] = max(wt.get(base, 0.0), max(0.15, float(rd.base_min_fraction) * 1.02))

    for symbol in must:
        if symbol in exclude:
            continue
        wt = _set_floor(wt, symbol, 0.01)

    if "corrosion_resistance" in props:
        if "Cr" not in exclude:
            wt = _set_floor(wt, "Cr", 0.14)
        if "Mo" not in exclude and any(k in query.lower() for k in ["marine", "chloride", "seawater", "pitting"]):
            wt = _set_floor(wt, "Mo", 0.02)

    if "high_temperature_strength" in props or "creep_resistance" in props:
        if "Ni" not in exclude:
            wt = _set_floor(wt, "Ni", 0.20)
        elif "Co" not in exclude:
            wt = _set_floor(wt, "Co", 0.15)
        if "Cr" not in exclude:
            wt = _set_floor(wt, "Cr", 0.12)

    if "wear_resistance" in props or "hardness" in props:
        if "C" not in exclude:
            wt = _set_floor(wt, "C", 0.006)
        if "V" not in exclude:
            wt = _set_floor(wt, "V", 0.01)

    if constraints.get("cost_level") == "low":
        caps = {"Ni": 0.08, "Co": 0.05, "Re": 0.01, "Ta": 0.01, "Hf": 0.01, "W": 0.06}
        for symbol, cap in caps.items():
            if symbol in wt:
                wt[symbol] = min(wt[symbol], cap)

    if rd and rd.base_elements:
        base = rd.base_elements[0]
        if base in wt:
            wt = _set_floor(wt, base, float(rd.base_min_fraction))

    for symbol in list(wt.keys()):
        if wt[symbol] < 0.001:
            wt.pop(symbol, None)

    wt = _normalize_wt(wt)
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))
    return wt


def _condition_candidate_with_intent(candidate, intent, query, reason_suffix):
    if not candidate:
        return None
    try:
        base_wt = candidate.composition_wt or mol_to_wt(candidate.composition)
        conditioned_wt = _apply_intent_to_wt(base_wt, intent, query)
        mol = validate_composition(wt_to_mol(conditioned_wt))
        rationale = candidate.rationale or "Generated baseline"
        if reason_suffix:
            rationale = f"{rationale} | {reason_suffix}"
        return Candidate(composition=mol, composition_wt=conditioned_wt, rationale=rationale)
    except Exception:
        return candidate


def _summarize_intent(intent, query):
    app = intent.get("application") or "unknown"
    props = intent.get("target_properties", []) or []
    constraints = intent.get("constraints", {}) or {}
    must, exclude = _intent_required_elements(intent, query)
    notes = [
        f"application={app}",
        f"properties={props if props else ['none']}",
        f"must_include={must if must else ['none']}",
        f"exclude={exclude if exclude else ['none']}",
        f"constraints={constraints if constraints else 'none'}",
    ]
    return " | ".join(notes)


class BaselinePredictor:
    @staticmethod
    def predict(query, intent):
        from core.data_hub import get_hub
        hub = get_hub()
        if intent.get("alloy_name"):
            alloy = hub.get_alloy(intent["alloy_name"])
            if alloy and alloy.get("composition_wt"):
                wt = alloy["composition_wt"]
                try:
                    mol = validate_composition(wt_to_mol(wt))
                    base = Candidate(composition=mol, composition_wt=wt,
                                     rationale=f"Exact match: {intent['alloy_name']}")
                    return _condition_candidate_with_intent(
                        base, intent, query, "intent-conditioned seed"
                    )
                except Exception:
                    pass
        from llms.client import is_available
        if is_available():
            baseline = _llm_baseline(query, intent)
            if baseline:
                return _condition_candidate_with_intent(
                    baseline, intent, query, "intent-conditioned seed"
                )
        from core.generator import generate
        try:
            must_include, exclude = _intent_required_elements(intent, query)
            aug_query = query
            rd = intent.get("research_data")
            if rd and rd.base_elements:
                if rd.base_elements[0] not in exclude:
                    must_include = sorted(set(must_include + [rd.base_elements[0]]))
                aug_query += " " + rd.base_elements[0] + " alloy"

            base_hint = intent.get("composition")
            if not base_hint:
                base_hint = _default_seed_for_application(intent.get("application"))
            base_hint = _apply_intent_to_wt(base_hint, intent, query)

            comps = generate(
                query=aug_query,
                n=8,
                application=intent.get("application", ""),
                base_composition=base_hint,
                must_include=must_include,
                exclude_elements=exclude,
            )
            if comps:
                wt = mol_to_wt(comps[0])
                base = Candidate(composition=comps[0], composition_wt=wt,
                                 rationale="Template-based baseline")
                return _condition_candidate_with_intent(
                    base, intent, query, "intent-conditioned seed"
                )
        except Exception:
            pass

        seed = _default_seed_for_application(intent.get("application"))
        seed = _apply_intent_to_wt(seed, intent, query)
        try:
            mol = validate_composition(wt_to_mol(seed))
            return Candidate(composition=mol, composition_wt=seed, rationale="Heuristic baseline seed")
        except Exception:
            return None

def _llm_baseline(query, intent):
    from llms.client import chat_json
    parts = [f"Given this alloy design request, propose ONE single realistic starting composition.",
             f"Request: {query}"]
    
    rd = intent.get("research_data")
    if rd:
        parts.append(f"\nHARD CONSTRAINTS you MUST respect:")
        parts.append(f"  - Base element(s): {rd.base_elements}")
        parts.append(f"  - Base min mass fraction: {rd.base_min_fraction:.2f}")
        parts.append(f"  - Forbidden: {rd.forbidden_elements}")
        parts.append(f"  - Mechanisms to enforce: {rd.mandatory_mechanisms}")
    
    parts.append("""Return ONLY JSON:
{"comp_wt": {"Fe": 0.65, "Cr": 0.22}, "rationale": "why this is the best starting point"}
Rules: weight fractions summing to ~1.0, NO forbidden elements, and base element must strictly be the highest mass.""")

    prompt = "\n".join(parts)
    result = chat_json(
        [{"role": "system", "content": "You are an expert computational metallurgist. Return ONLY valid JSON."},
         {"role": "user", "content": prompt}], max_tokens=500, temperature=0.1)
    
    if not result or "comp_wt" not in result:
        return None
    try:
        wt = {k: float(v) for k, v in result["comp_wt"].items() if float(v) > 0.001}
        total = sum(wt.values())
        if total == 0:
            return None
        wt = {k: v / total for k, v in wt.items()}
        mol = validate_composition(wt_to_mol(wt))
        
        if rd:
            violated, reason = rd.composition_violates_base(mol)
            if violated:
                logger.warning(f"[BASELINE] LLM baseline violated constraint: {reason}")
                return None
        
        return Candidate(composition=mol, composition_wt=wt,
                         rationale=result.get("rationale", "LLM reasoning"))
    except Exception as e:
        logger.warning(f"[BASELINE] Failed to parse baseline: {e}")
        return None


class MultiCompositionGenerator:
    @staticmethod
    def generate(query, intent, baseline, n=8, iteration=0, feedback=None):
        candidates = []
        if baseline and iteration == 0:
            candidates.append(baseline)

        must_include, exclude = _intent_required_elements(intent, query)
        if must_include:
            intent["must_include"] = sorted(set((intent.get("must_include") or []) + must_include))
        if exclude:
            intent["exclude_elements"] = sorted(set((intent.get("exclude_elements") or []) + exclude))

        initial_len = len(candidates)
        from llms.client import is_available
        if is_available():
            candidates.extend(_llm_generate(query, intent, baseline, n, feedback))

        from core.generator import generate
        try:
            base_comp = baseline.composition_wt if baseline else intent.get("composition")
            if base_comp:
                base_comp = _apply_intent_to_wt(base_comp, intent, query)
            else:
                base_comp = _apply_intent_to_wt(
                    _default_seed_for_application(intent.get("application")), intent, query
                )

            template_comps = generate(
                query=query,
                n=max(n, 12),
                only_elements=intent.get("only_elements"),
                must_include=intent.get("must_include"),
                exclude_elements=intent.get("exclude_elements"),
                application=intent.get("application", ""),
                base_composition=base_comp,
            )
            for comp in template_comps:
                try:
                    wt = _apply_intent_to_wt(mol_to_wt(comp), intent, query)
                    mol = validate_composition(wt_to_mol(wt))
                    candidates.append(
                        Candidate(
                            composition=mol,
                            composition_wt=wt,
                            rationale="Intent-conditioned template variant",
                            iteration=iteration,
                        )
                    )
                except Exception:
                    continue

            exploratory_comps = generate(
                query=query,
                n=max(8, n // 2),
                only_elements=intent.get("only_elements"),
                must_include=intent.get("must_include"),
                exclude_elements=intent.get("exclude_elements"),
                application=intent.get("application", ""),
                base_composition=None,
            )
            for comp in exploratory_comps:
                try:
                    wt = _apply_intent_to_wt(mol_to_wt(comp), intent, query)
                    mol = validate_composition(wt_to_mol(wt))
                    candidates.append(
                        Candidate(
                            composition=mol,
                            composition_wt=wt,
                            rationale="Intent-conditioned exploratory variant",
                            iteration=iteration,
                        )
                    )
                except Exception:
                    continue
        except Exception:
            pass

        if len(candidates) == initial_len:
            seed_wt = _apply_intent_to_wt(
                _default_seed_for_application(intent.get("application")), intent, query
            )
            try:
                mol = validate_composition(wt_to_mol(seed_wt))
                candidates.append(
                    Candidate(
                        composition=mol,
                        composition_wt=seed_wt,
                        rationale="Heuristic emergency seed",
                        iteration=iteration,
                    )
                )
            except Exception:
                pass
        return candidates


def _llm_generate(query, intent, baseline, n, feedback=None):
    from llms.client import chat_json
    parts = [f"Design query: {query}"]
    if intent.get("application"): parts.append(f"Application: {intent['application']}")
    if intent.get("environment"): parts.append(f"Environment: {intent['environment']}")
    if intent.get("temperature_K"): parts.append(f"Temperature: {intent['temperature_K']:.0f} K")
    if intent.get("must_include"): parts.append(f"Must include: {', '.join(intent['must_include'])}")
    if intent.get("exclude_elements"): parts.append(f"Exclude elements: {', '.join(intent['exclude_elements'])}")
    if intent.get("target_properties"): parts.append(f"Target properties: {', '.join(intent['target_properties'])}")
    
    rd = intent.get("research_data")
    if rd:
        parts.append(f"\nHARD CONSTRAINTS you MUST respect:")
        parts.append(f"  - Base element(s): {rd.base_elements}")
        parts.append(f"  - Base min mass fraction: {rd.base_min_fraction:.2f}")
        parts.append(f"  - Forbidden: {rd.forbidden_elements}")
        parts.append(f"  - Mechanisms to enforce: {rd.mandatory_mechanisms}")

    if baseline:
        comp_str = ", ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(
            baseline.composition_wt.items(), key=lambda x: -x[1])[:6])
        parts.append(f"\nStarting Baseline: {comp_str}")
    if feedback:
        parts.append(f"Best previous score: {feedback.get('best_score', 0):.1f}/100")
        parts.append(f"Weak domains to improve: {feedback.get('weak_summary', 'none')}")
        
    parts.append(f"\nPropose {n} DIVERSE alloy compositions as weight fractions summing to 1.0.")
    parts.append("Vary element ratios, add or remove minor alloying elements. ALWAYS keep the base element dominant.")
    
    system = ("You are an expert computational metallurgist. "
              "Return ONLY JSON: {\"compositions\": [{\"comp_wt\": {\"Fe\": 0.65}, \"rationale\": \"...\"}]}")
    result = chat_json([{"role": "system", "content": system},
                        {"role": "user", "content": "\n".join(parts)}], max_tokens=2000, temperature=0.7)
    
    if not result or "compositions" not in result:
        return []
        
    candidates = []
    for item in result["compositions"]:
        try:
            wt = item.get("comp_wt", {})
            if not wt or not isinstance(wt, dict):
                continue
            wt = {k: float(v) for k, v in wt.items() if float(v) > 0.001}
            total = sum(wt.values())
            if total < 0.5:
                continue
            wt = {k: v / total for k, v in wt.items()}
            wt = _apply_intent_to_wt(wt, intent, query)
            mol = validate_composition(wt_to_mol(wt))
            
            if rd:
                violated, reason = rd.composition_violates_base(mol)
                if violated:
                    logger.debug(f"[_llm_generate] Skipping candidate - {reason}")
                    continue
                    
            candidates.append(Candidate(composition=mol, composition_wt=wt,
                                        rationale=item.get("rationale", "")))
        except Exception:
            continue
    return candidates


class PhysicsMLEvaluator:
    _MECHANISM_CHECKS = {
        "gamma_prime": (lambda c: c.get("Al", 0) + c.get("Ti", 0) >= 0.04, "γ' precipitation requires Al+Ti >= 4 mol%"),
        "precipitation_hard": (lambda c: c.get("Cu", 0) + c.get("Mg", 0) + c.get("Zn", 0) >= 0.005, "Precipitation requires Cu+Mg+Zn >= 0.5 mol%"),
        "martensite": (lambda c: c.get("C", 0) >= 0.003, "Martensite requires C >= 0.3 mol%"),
        "alpha_beta": (lambda c: (c.get("V",0)+c.get("Mo",0)+c.get("Nb",0)+c.get("Cr",0)) >= 0.02, "α+β Ti needs β-stabilisers >= 2 mol%"),
        "solid_solution": (lambda c: len([v for v in c.values() if v > 0.005]) >= 2, "Solid solution requires >=2 solute elements"),
        "carbide": (lambda c: c.get("C", 0) >= 0.002 and c.get("Cr", 0) + c.get("W", 0) >= 0.10, "Carbide needs C >= 0.2% and (Cr+W) >= 10%"),
    }

    @classmethod
    def _check_mechanisms(cls, composition, mechanisms):
        for mechanism in mechanisms:
            mech_lower = mechanism.lower().replace(" ", "_").replace("-", "_")
            for keyword, (check_fn, msg) in cls._MECHANISM_CHECKS.items():
                if keyword in mech_lower:
                    if not check_fn(composition):
                        return f"Mandatory mechanism '{mechanism}' failed: {msg}"
        return None

    @staticmethod
    def _overalloying_penalty(composition, query):
        import math
        base_frac = max(composition.values())
        solute_frac = 1.0 - base_frac
        solute_count = sum(1 for v in composition.values() if v > 0.005)
        q = query.lower()
        if any(k in q for k in ["electr", "conduct", "wire", "thermal"]):
            return math.exp(-9.0 * solute_frac)
        elif any(k in q for k in ["turbine", "superalloy", "creep", "jet"]):
            return math.exp(-0.25 * max(0, solute_count - 9))
        elif any(k in q for k in ["biomedical", "implant", "bone"]):
            return math.exp(-0.6 * max(0, solute_count - 4))
        else:
            return math.exp(-0.45 * max(0, solute_count - 6))

    @staticmethod
    def evaluate(candidates, query="", T_K=298.0, weather=None, domains_focus=None,
                 constraints=None, dpa_rate=1e-7, pressure_MPa=0.0, research_data=None):
        from physics.filter import run_all
        import math
        for cand in candidates:
            try:
                result = run_all(cand.composition, T_K=T_K, weather=weather, verbose=False,
                                 domains_focus=domains_focus, dpa_rate=dpa_rate)
                cand.physics_result = result
                
                base_score = result.get("composite_score", 0)
                weak = []
                domain_scores = {}
                for dr in result.get("domain_results", []):
                    domain_scores[dr.domain_name] = dr.score()
                    if dr.score() < 50:
                        weak.append({"name": dr.domain_name, "score": dr.score(),
                                     "fails": [c.name for c in dr.checks if c.status == "FAIL"]})
                cand.weak_domains = weak
                cand.score = base_score
                
                if research_data:
                    violated, reason = research_data.composition_violates_base(cand.composition)
                    if violated:
                        cand.score = 0
                        cand.weak_domains.append({"name": "Base Material Rejection", "score": 0, "fails": [reason]})
                    
                    if cand.score > 0:
                        mech_reason = PhysicsMLEvaluator._check_mechanisms(cand.composition, research_data.mandatory_mechanisms)
                        if mech_reason:
                            cand.score = 0
                            cand.weak_domains.append({"name": "Critical Mechanism Rejection", "score": 0, "fails": [mech_reason]})

                    if cand.score > 0:
                        primary_weight_total = sum(research_data.domain_weights.values())
                        residual_weight = max(0.0, 1.0 - primary_weight_total) / max(1, len(domain_scores) - len(research_data.domain_weights))
                        weighted_sum = 0.0
                        weight_used = 0.0
                        for d_name, d_score in domain_scores.items():
                            w = research_data.domain_weights.get(d_name, residual_weight)
                            weighted_sum += w * d_score
                            weight_used += w
                        weighted_score = (weighted_sum / weight_used) if weight_used > 0 else base_score
                        
                        penalty = PhysicsMLEvaluator._overalloying_penalty(cand.composition, query)
                        cand.score = round(weighted_score * penalty, 2)
                        
                        if penalty < 0.8:
                            cand.weak_domains.append({"name": "Over-alloying Penalty", "score": int(penalty*100), "fails": ["Excessive solute additions for application"]})

                if constraints and cand.score > 0:
                    _apply_constraints(cand, constraints)
                try:
                    from ml.predict import get_predictor
                    predictor = get_predictor()
                    if predictor.is_available():
                        cand.ml_predictions = predictor.predict(cand.composition) or {}
                except Exception:
                    pass
            except Exception as e:
                cand.score = 0.0
                cand.physics_result = {"error": str(e)}
        return candidates


def _apply_constraints(cand, constraints):
    from physics.base import density_rule_of_mixtures, PREN_wt, wmean
    violations = []
    if constraints.get("min_PREN"):
        try:
            pren = PREN_wt(cand.composition)
            if pren < constraints["min_PREN"]:
                violations.append(f"PREN {pren:.1f} < {constraints['min_PREN']}")
        except Exception:
            pass
    if constraints.get("max_density"):
        d = density_rule_of_mixtures(cand.composition)
        if d and d > constraints["max_density"]:
            violations.append(f"Density {d:.2f} > {constraints['max_density']}")
    if constraints.get("min_yield_MPa"):
        hv = wmean(cand.composition, "vickers")
        est_yield = hv / 3.0 if hv else 0
        if est_yield < constraints["min_yield_MPa"]:
            violations.append(f"Est. yield {est_yield:.0f} < {constraints['min_yield_MPa']}")
    if violations:
        cand.score = max(0, cand.score - 10 * len(violations))
        cand.weak_domains.append({"name": "Constraint Violations", "score": 0, "fails": violations})


class DomainCorrelator:
    CORRELATIONS = [
        {"domains": ("Thermodynamics", "Phase Stability"), "type": "synergy",
         "description": "Thermodynamic stability supports phase stability via mixing entropy."},
        {"domains": ("Mechanical", "Creep"), "type": "trade-off",
         "description": "Precipitation hardening degrades at high-T if precipitates coarsen."},
        {"domains": ("Corrosion", "Biocompatibility"), "type": "synergy",
         "description": "Both depend on stable passive oxide layer. High Cr and Ti benefit both."},
        {"domains": ("Mechanical", "Weldability"), "type": "trade-off",
         "description": "High carbon improves strength but increases HAZ cracking risk."},
        {"domains": ("Corrosion", "Oxidation"), "type": "synergy",
         "description": "Both rely on Cr-based passive layers. High PREN helps oxidation resistance."},
        {"domains": ("Thermal Properties", "Electronic Structure"), "type": "synergy",
         "description": "Wiedemann-Franz law: good electrical conductors are good thermal conductors."},
        {"domains": ("Fatigue & Fracture", "Hydrogen Embrittlement"), "type": "synergy",
         "description": "Both are crack-propagation phenomena. Austenitic structures help both."},
        {"domains": ("Creep", "Oxidation"), "type": "synergy",
         "description": "High-temp alloys need both. Ni-superalloys achieve this synergy naturally."},
        {"domains": ("Grain Boundary", "Weldability"), "type": "trade-off",
         "description": "Strong grain boundaries resist hot cracking but can make welding harder."},
        {"domains": ("Phase Stability", "Transformation Kinetics"), "type": "synergy",
         "description": "Phase-stable alloys resist unwanted transformations during service."},
        {"domains": ("Mechanical", "Formability"), "type": "trade-off",
         "description": "Stronger alloys are harder to form. Balance via TWIP/TRIP mechanisms."},
        {"domains": ("Corrosion", "Galvanic Compatibility"), "type": "synergy",
         "description": "High corrosion resistance gives favorable galvanic position."},
    ]

    @staticmethod
    def correlate(candidates):
        insights = []
        for cand in candidates[:5]:
            if not cand.physics_result or "domain_results" not in cand.physics_result:
                continue
            domain_scores = {dr.domain_name: dr.score() for dr in cand.physics_result["domain_results"]}
            for corr in DomainCorrelator.CORRELATIONS:
                d1, d2 = corr["domains"]
                s1, s2 = domain_scores.get(d1), domain_scores.get(d2)
                if s1 is None or s2 is None:
                    continue
                if corr["type"] == "synergy":
                    if s1 >= 70 and s2 >= 70:
                        insights.append({"type": "positive_synergy", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) show positive synergy. {corr['description']}"})
                    elif s1 < 40 and s2 < 40:
                        insights.append({"type": "coupled_weakness", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) are both weak and linked. {corr['description']}"})
                    elif abs(s1 - s2) > 30:
                        insights.append({"type": "broken_synergy", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) usually correlated but diverge. {corr['description']}"})
                elif corr["type"] == "trade-off":
                    if s1 >= 70 and s2 < 40:
                        insights.append({"type": "active_tradeoff", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"Trade-off: {d1} ({s1:.0f}) strong but {d2} ({s2:.0f}) suffers. {corr['description']}"})
                    elif s2 >= 70 and s1 < 40:
                        insights.append({"type": "active_tradeoff", "domains": (d2, d1),
                                         "scores": (s2, s1),
                                         "message": f"Trade-off: {d2} ({s2:.0f}) strong but {d1} ({s1:.0f}) suffers. {corr['description']}"})
                    elif s1 >= 60 and s2 >= 60:
                        insights.append({"type": "resolved_tradeoff", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"Trade-off resolved: Both {d1} ({s1:.0f}) and {d2} ({s2:.0f}) adequate. {corr['description']}"})
        seen = set()
        unique = []
        for ins in insights:
            key = (ins["type"], tuple(sorted(ins["domains"])))
            if key not in seen:
                seen.add(key)
                unique.append(ins)
        return unique[:15]


def _compute_ml_confidence(predictions: dict) -> float:
    if not predictions:
        return 50.0

    _RANGES = {
        "formation_energy": (-1.5, 1.5),
        "bulk_modulus":     (150.0, 150.0),
        "shear_modulus":    (80.0,  80.0),
        "yield_strength":   (500.0, 500.0),
        "UTS":              (700.0, 700.0),
    }

    scores = []
    for target, pred in predictions.items():
        if not isinstance(pred, dict):
            continue
        mean  = pred.get("mean",  None)
        sigma = pred.get("sigma", 0.0)
        if mean is None:
            continue

        centre, half = _RANGES.get(target, (mean, abs(mean) if mean != 0 else 1.0))

        if target == "formation_energy":
            raw = 100.0 * (1.0 - (mean - (centre - half)) / (2.0 * half))
        else:
            raw = 100.0 * (mean - (centre - half)) / (2.0 * half)
        raw = max(0.0, min(100.0, raw))

        rel_unc = (sigma / abs(mean)) if mean != 0 else 1.0
        penalty = max(0.0, 1.0 - rel_unc)
        scores.append(raw * penalty)

    if not scores:
        return 50.0
    return round(sum(scores) / len(scores), 2)


def _ml_prefilter(candidates: list, intent: dict, use_ml: bool = True) -> list:
    if not use_ml:
        return candidates

    try:
        from ml.predict import get_predictor
        predictor = get_predictor()
        if not predictor.is_available():
            return candidates

        target_yield = intent.get("constraints", {}).get("min_yield_MPa", 0) or 0

        scored = []
        for cand in candidates:
            try:
                preds = predictor.predict(cand.composition)
                cand.ml_predictions = preds or {}
            except Exception:
                cand.ml_predictions = {}
                scored.append((cand, 50.0))
                continue

            if target_yield > 0:
                ml_yield = (cand.ml_predictions
                            .get("yield_strength", {})
                            .get("mean", target_yield))
                if ml_yield < target_yield * 0.70:
                    continue

            ml_conf = _compute_ml_confidence(cand.ml_predictions)
            scored.append((cand, ml_conf))

        if not scored:
            logger.warning("[_ml_prefilter] All candidates filtered — returning full list")
            return candidates

        scored.sort(key=lambda x: -x[1])
        return [c for c, _ in scored[:15]]

    except Exception as e:
        logger.warning(f"[_ml_prefilter] Unexpected error ({e}); skipping ML pre-filter")
        return candidates


class Pipeline:
    def __init__(self, max_iterations=4, convergence_threshold=2.0, on_step=None,
                 constraints=None, use_ml=False):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.on_step = on_step or (lambda s: None)
        self.constraints = constraints or {}
        self.use_ml = use_ml
        self.steps = []
        self.all_candidates = []
        self.best_score_history = []

    def _log(self, step_num, stage, thought, observation, agent=""):
        step = PipelineStep(step_num, stage, thought, observation, agent=agent)
        self.steps.append(step)
        self.on_step(step)
        return step

    def run(self, query, intent, T_K=298.0, weather=None, domains_focus=None,
            dpa_rate=1e-7, pressure_MPa=0.0):
        t0 = time.time()
        step_counter = 1

        self._log(
            step_counter,
            "input",
            f"Intent parsed: {_summarize_intent(intent, query)}",
            f"Raw input: '{query}'",
            agent="InputInterpreter",
        )
        step_counter += 1

        self._log(step_counter, "research", f"Researching application: '{query}'",
                  "Finding fundamental physical constraints...", agent="ApplicationResearcher")
        from engines.researcher import ApplicationResearcher
        try:
            research_data = ApplicationResearcher().research(query, intent=intent)
        except Exception as e:
            logger.error(f"Researcher LLM failed: {e}")
            try:
                research_data = ApplicationResearcher()._heuristic_research(query, intent=intent)
                research_data.fallback_reason = str(e)
                research_data.source = "heuristic"
            except Exception:
                research_data = None
        step_counter += 1

        if research_data:
            source = getattr(research_data, "source", "unknown")
            reason = getattr(research_data, "fallback_reason", "")
            obs = f"Base: {research_data.base_elements}, Domains: {research_data.primary_domains}, Source: {source}"
            if reason:
                obs += f", Fallback reason: {reason}"
            self._log(step_counter, "research", f"Research constraints ready (source={source})",
                      obs, agent="ApplicationResearcher")
        else:
            self._log(step_counter, "research", f"Research failed", "Proceeding with generic constraints", agent="ApplicationResearcher")
        step_counter += 1
        intent["research_data"] = research_data

        must_include, exclude_elements = _intent_required_elements(intent, query)
        if research_data and research_data.base_elements and research_data.base_elements[0] not in exclude_elements:
            must_include = sorted(set(must_include + [research_data.base_elements[0]]))

        intent["must_include"] = sorted(set((intent.get("must_include") or []) + must_include))
        intent["exclude_elements"] = sorted(set((intent.get("exclude_elements") or []) + exclude_elements))

        self._log(
            step_counter,
            "constraints",
            f"Generator constraints: must={intent.get('must_include') or []}, exclude={intent.get('exclude_elements') or []}",
            f"must_include={intent.get('must_include') or []}, exclude={intent.get('exclude_elements') or []}, "
            f"application={intent.get('application') or 'unknown'}, constraints={intent.get('constraints') or {}}",
            agent="InputInterpreter",
        )
        step_counter += 1

        self._log(step_counter, "baseline", f"Finding baseline for: '{query}'",
                  "Searching database + LLM...", agent="BaselinePredictor")
        step_counter += 1
        baseline = BaselinePredictor.predict(query, intent)
        if baseline:
            self._log(step_counter, "baseline", f"Baseline: {_fmt_comp(baseline.composition_wt)}",
                      baseline.rationale, agent="BaselinePredictor")
        else:
            self._log(step_counter, "baseline", "No direct match, generating from scratch",
                      "Using template generation", agent="BaselinePredictor")
        step_counter += 1
        best_score = 0.0
        improvement = 0
        iteration = 0
        for iteration in range(self.max_iterations):
            feedback = None
            if iteration > 0:
                prev = [c for c in self.all_candidates if c.iteration == iteration - 1]
                feedback = _build_feedback(prev)
            self._log(step_counter, "generate",
                      f"Iteration {iteration + 1}: Generating compositions",
                      "Refining" if feedback else "Initial exploration",
                      agent="MultiCompGenerator")
            step_counter += 1
            candidates = MultiCompositionGenerator.generate(
                query, intent, baseline, n=max(intent.get('n_results', 50) // max(1, self.max_iterations), 8), iteration=iteration, feedback=feedback)
            pre_dedupe = len(candidates)
            candidates = _dedupe_candidates(candidates, similarity_threshold=0.02)
            if len(candidates) != pre_dedupe:
                self._log(step_counter, "dedupe",
                          f"Removed repeats: {pre_dedupe} -> {len(candidates)}",
                          "Dropped duplicate/near-duplicate compositions",
                          agent="MultiCompGenerator")
                step_counter += 1
            if self.use_ml:
                pre_count = len(candidates)
                candidates = _ml_prefilter(candidates, intent, use_ml=True)
                self._log(step_counter, "ml_prefilter",
                          f"ML pre-filter: {pre_count} -> {len(candidates)} candidates",
                          "Dropped low-yield predictions, re-ranked by ML confidence",
                          agent="MLPrefilter")
                step_counter += 1

            self._log(step_counter, "evaluate",
                      f"Evaluating {len(candidates)} candidates",
                      "Running physics + ML...", agent="PhysicsMLEvaluator")
            step_counter += 1
            candidates = PhysicsMLEvaluator.evaluate(
                candidates, T_K=T_K, weather=weather, domains_focus=domains_focus,
                constraints=self.constraints, dpa_rate=dpa_rate, pressure_MPa=pressure_MPa,
                research_data=research_data)

            if self.use_ml:
                n_combined = 0
                for cand in candidates:
                    if cand.ml_predictions:
                        ml_conf = _compute_ml_confidence(cand.ml_predictions)
                        cand.score = round(0.6 * cand.score + 0.4 * ml_conf, 2)
                        n_combined += 1
                if n_combined:
                    logger.debug(f"[Pipeline] Combined score applied to {n_combined} candidates")
            for cand in candidates:
                cand.iteration = iteration
            self.all_candidates.extend(candidates)
            iter_best = max(c.score for c in candidates) if candidates else 0
            improvement = iter_best - best_score
            best_score = max(best_score, iter_best)
            self.best_score_history.append(best_score)
            self._log(step_counter, "evaluate",
                      f"Best: {iter_best:.1f}/100 (delta {improvement:+.1f})",
                      f"Overall best: {best_score:.1f}/100", agent="PhysicsMLEvaluator")
            step_counter += 1
            if iteration > 0 and improvement < self.convergence_threshold:
                self._log(step_counter, "converge", "Converged", "Stopping", agent="Pipeline")
                step_counter += 1
                break
        pre_final_dedupe = len(self.all_candidates)
        self.all_candidates = _dedupe_candidates(self.all_candidates, similarity_threshold=0.015)
        if len(self.all_candidates) != pre_final_dedupe:
            self._log(step_counter, "dedupe",
                      f"Cross-iteration unique set: {pre_final_dedupe} -> {len(self.all_candidates)}",
                      "Keeping only unique candidate compositions",
                      agent="Pipeline")
            step_counter += 1
        self.all_candidates.sort(key=lambda c: -c.score)
        self._log(step_counter, "correlate", "Analyzing cross-domain correlations",
                  "Finding synergies...", agent="DomainCorrelator")
        step_counter += 1
        correlation_insights = DomainCorrelator.correlate(self.all_candidates)
        explanation = ""
        try:
            from llms.explainer import synthesize_explanation
            explanation = synthesize_explanation(query, self.all_candidates[:3], correlation_insights)
        except Exception:
            pass
        self._log(step_counter, "explain", "Synthesizing explanation",
                  f"{len(correlation_insights)} correlations found", agent="Explainer")
        return PipelineResult(
            candidates=self.all_candidates, steps=self.steps, baseline=baseline,
            iterations_run=iteration + 1,
            converged=(improvement < self.convergence_threshold if iteration > 0 else False),
            best_score=best_score, total_time=time.time() - t0,
            explanation=explanation, correlation_insights=correlation_insights,
            mode=intent.get("mode", "design"))


def _fmt_comp(comp, top=6):
    return "  ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(comp.items(), key=lambda x: -x[1])[:top])


def _composition_distance(comp_a, comp_b):
    keys = set(comp_a) | set(comp_b)
    return sum(abs(comp_a.get(k, 0.0) - comp_b.get(k, 0.0)) for k in keys)


def _dedupe_candidates(candidates, similarity_threshold=0.02):
    # Keep highest scoring instances first where possible.
    ranked = sorted(candidates, key=lambda c: getattr(c, "score", 0.0), reverse=True)
    unique = []
    for cand in ranked:
        comp = cand.composition_wt or cand.composition or {}
        if not comp:
            continue
        if any(_composition_distance(comp, (u.composition_wt or u.composition or {})) <= similarity_threshold
               for u in unique):
            continue
        unique.append(cand)
    return unique


def _build_feedback(candidates):
    if not candidates:
        return {"best_score": 0, "weak_summary": "no data", "weak_details": []}
    best = max(candidates, key=lambda c: c.score)
    all_weak = {}
    for c in candidates:
        for w in c.weak_domains:
            name = w["name"]
            if name not in all_weak or w["score"] < all_weak[name]["score"]:
                all_weak[name] = w
    weak_sorted = sorted(all_weak.values(), key=lambda w: w["score"])[:5]
    return {"best_score": best.score, "top_candidate": best.composition_wt,
            "weak_summary": ", ".join(w["name"] for w in weak_sorted) if weak_sorted else "none",
            "weak_details": weak_sorted}


def run_pipeline(query, intent, on_step=None, max_iterations=4, T_K=298.0,
                 weather=None, constraints=None, dpa_rate=1e-7, pressure_MPa=0.0,
                 use_ml=False):
    merged = dict(intent.get("constraints", {}))
    if constraints:
        merged.update(constraints)
    pipeline = Pipeline(max_iterations=max_iterations, on_step=on_step,
                        constraints=merged, use_ml=use_ml)
    return pipeline.run(query=query, intent=intent, T_K=T_K, weather=weather,
                        domains_focus=intent.get("domains_focus"), dpa_rate=dpa_rate,
                        pressure_MPa=pressure_MPa)
