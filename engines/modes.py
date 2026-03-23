import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.elements import validate_composition
from core.alloy_db import lookup_alloy, search_alloys, ALLOY_DATABASE
from physics.filter import run_all
from physics.base import norm, wmean, density_rule_of_mixtures, vec, delta_size, PREN_wt, mol_to_wt, wt_to_mol
from engines.pipeline import run_pipeline, PipelineResult, Candidate
from core.data_hub import get_hub


def _fmt_comp(comp, top=6):
    return "  ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(comp.items(), key=lambda x: -x[1])[:top])


def _convert_wt_to_mol(wt_comp):
    try:
        return validate_composition(wt_to_mol(wt_comp))
    except Exception:
        return validate_composition(wt_comp)


class DesignEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        alloy = intent.get("alloy_name", "")
        props = ", ".join(intent.get("target_properties", []))
        base_query = intent.get("notes", "")
        query_parts = []
        if alloy:
            query_parts.append(f"alloy {alloy}")
        if intent.get("application"):
            query_parts.append(f"application {intent['application']}")
        if props:
            query_parts.append(f"target properties {props}")
        if base_query:
            query_parts.append(base_query)
        if not query_parts:
            query = "general alloy design"
        else:
            query = "; ".join(dict.fromkeys(query_parts))
        T_K = intent.get("temperature_K") or 298.0
        weather = intent.get("environment")
        top_n = min(intent.get("n_results") or 10, 20)
        result = run_pipeline(query=query, intent=intent, on_step=on_step,
                              max_iterations=4, T_K=T_K, weather=weather,
                              constraints=intent.get("constraints", {}),
                              dpa_rate=intent.get("dpa_rate", 1e-7),
                              pressure_MPa=intent.get("pressure_MPa", 0.0),
                              use_ml=intent.get("use_ml", False))
        top = []
        for cand in result.candidates[:top_n]:
            if cand.physics_result and "composite_score" in cand.physics_result:
                top.append((cand.composition, cand.physics_result))
        return {
            "mode": "design", "top": top, "n_candidates": len(result.candidates),
            "n_domains": top[0][1].get("n_domains", 0) if top else 0,
            "thinking_steps": [{"step": s.step_num, "thought": s.thought,
                                "action": s.stage, "observation": s.observation,
                                "agent": s.agent} for s in result.steps],
            "iterations": result.iterations_run, "converged": result.converged,
            "best_score": result.best_score, "total_time": result.total_time,
            "explanation": result.explanation,
            "correlation_insights": result.correlation_insights,
            "candidates_detail": [{"composition": c.composition,
                                   "composition_wt": c.composition_wt,
                                   "rationale": c.rationale, "score": c.score,
                                   "ml_predictions": c.ml_predictions,
                                   "weak_domains": c.weak_domains}
                                  for c in result.candidates[:top_n]]}


class ModifyEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        alloy_name = intent.get("alloy_name", "Unknown")
        comp_wt = intent.get("composition")
        if not comp_wt:
            hub = get_hub()
            alloy = hub.get_alloy(alloy_name)
            if alloy:
                comp_wt = alloy["composition_wt"]
            else:
                return {"mode": "modify", "error": f"Unknown alloy: {alloy_name}"}
        comp = _convert_wt_to_mol(comp_wt)
        T_K = intent.get("temperature_K") or 298.0
        original = run_all(comp, T_K=T_K, weather=intent.get("environment"), verbose=verbose)
        weak = sorted(original["domain_results"], key=lambda dr: dr.score())[:5]
        modify_intent = dict(intent)
        modify_intent["notes"] = (f"Improve {alloy_name}. Current: {_fmt_comp(comp)}. "
                                  f"Weak: {', '.join(dr.domain_name for dr in weak if dr.score() < 60)}.")
        result = run_pipeline(query=modify_intent["notes"], intent=modify_intent,
                              on_step=on_step, max_iterations=3, T_K=T_K,
                              weather=intent.get("environment"),
                              use_ml=intent.get("use_ml", False))
        modifications = []
        for cand in result.candidates[:5]:
            if cand.physics_result and "composite_score" in cand.physics_result:
                delta = cand.physics_result["composite_score"] - original["composite_score"]
                modifications.append({"description": cand.rationale or "Pipeline modification",
                                      "composition": cand.composition,
                                      "result": cand.physics_result, "delta_score": delta,
                                      "improved": delta > 0})
        modifications.sort(key=lambda x: -x["delta_score"])
        return {"mode": "modify", "alloy_name": alloy_name,
                "original_composition": comp, "original_result": original,
                "weak_domains": [(dr.domain_name, dr.score()) for dr in weak],
                "modifications": modifications, "explanation": result.explanation,
                "correlation_insights": result.correlation_insights,
                "thinking_steps": [{"step": s.step_num, "thought": s.thought,
                                    "action": s.stage, "observation": s.observation}
                                   for s in result.steps]}


class StudyEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        topic = intent.get("study_topic") or intent.get("notes", "")
        comp_wt = intent.get("composition")
        alloy_name = intent.get("alloy_name")
        result = {"mode": "study", "topic": topic, "sections": [],
                  "thinking_steps": [], "correlation_insights": []}
        if not comp_wt and alloy_name:
            hub = get_hub()
            alloy = hub.get_alloy(alloy_name)
            if alloy:
                comp_wt = alloy["composition_wt"]
                result["alloy_name"] = alloy_name
        if not comp_wt:
            from core.generator import generate
            try:
                candidates = generate(query=topic, n=5)
                if candidates:
                    comp_wt = mol_to_wt(candidates[0])
                else:
                    comp_wt = {"Fe": 0.60, "Cr": 0.18, "Ni": 0.10, "Mn": 0.02, "Mo": 0.10}
            except Exception:
                comp_wt = {"Fe": 0.60, "Cr": 0.18, "Ni": 0.10, "Mn": 0.02, "Mo": 0.10}
        comp = _convert_wt_to_mol(comp_wt)
        T_K = intent.get("temperature_K") or 298.0
        analysis = run_all(comp, T_K=T_K, verbose=True, domains_focus=intent.get("domains_focus"))
        result["analysis"] = analysis
        result["composition"] = comp
        for dr in analysis["domain_results"]:
            section = {"domain": dr.domain_name, "score": dr.score(), "checks": []}
            for ch in dr.checks:
                section["checks"].append({"name": ch.name, "status": ch.status,
                                          "value": ch.value, "unit": ch.unit,
                                          "message": ch.message, "citation": ch.citation,
                                          "formula": ch.formula})
            result["sections"].append(section)
        from engines.pipeline import DomainCorrelator, Candidate as PCandidate
        temp_cand = PCandidate(composition=comp, composition_wt=comp_wt, physics_result=analysis)
        result["correlation_insights"] = DomainCorrelator.correlate([temp_cand])
        try:
            from llms.explainer import explain_results
            result["explanation"] = explain_results(comp, analysis["domain_results"], topic)
        except Exception:
            result["explanation"] = ""
        hub = get_hub()
        papers = hub.search_papers(topic)
        if papers:
            result["papers"] = papers[:5]
        return result


class CompareEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        name1 = intent.get("alloy_name") or "Alloy A"
        name2 = intent.get("alloy_name_2") or "Alloy B"
        comp1_wt = intent.get("composition")
        comp2_wt = intent.get("composition_2")
        hub = get_hub()
        if not comp1_wt:
            a = hub.get_alloy(name1)
            if a:
                comp1_wt = a["composition_wt"]
        if not comp2_wt:
            a = hub.get_alloy(name2)
            if a:
                comp2_wt = a["composition_wt"]
        if not comp1_wt or not comp2_wt:
            return {"mode": "compare", "error": "Could not find both alloys."}
        comp1 = _convert_wt_to_mol(comp1_wt)
        comp2 = _convert_wt_to_mol(comp2_wt)
        T_K = intent.get("temperature_K") or 298.0
        r1 = run_all(comp1, T_K=T_K, verbose=True)
        r2 = run_all(comp2, T_K=T_K, verbose=True)
        comparison = []
        for dr1, dr2 in zip(r1["domain_results"], r2["domain_results"]):
            comparison.append({"domain": dr1.domain_name, "score_1": dr1.score(),
                               "score_2": dr2.score(),
                               "winner": (name1 if dr1.score() > dr2.score()
                                          else (name2 if dr2.score() > dr1.score() else "Tie"))})
        return {"mode": "compare",
                "alloy_1": {"name": name1, "composition": comp1, "result": r1,
                            "cost_usd_kg": hub.estimate_cost(comp1_wt)},
                "alloy_2": {"name": name2, "composition": comp2, "result": r2,
                            "cost_usd_kg": hub.estimate_cost(comp2_wt)},
                "comparison": comparison,
                "overall_winner": name1 if r1["composite_score"] > r2["composite_score"] else name2}


class ExploreEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        query = intent.get("notes", "")
        constraints = intent.get("constraints", {})
        hub = get_hub()
        db_matches = hub.search_alloys(query)
        result = run_pipeline(query=query, intent=intent, on_step=on_step,
                              max_iterations=2, T_K=intent.get("temperature_K") or 298.0,
                              weather=intent.get("environment"),
                              use_ml=intent.get("use_ml", False))
        passing = []
        for cand in result.candidates:
            if cand.physics_result and _passes_constraints(cand.composition, cand.physics_result, constraints):
                passing.append((cand.composition, cand.physics_result))
        return {"mode": "explore", "query": query, "constraints": constraints,
                "db_matches": db_matches, "generated_matches": passing[:20],
                "total_checked": len(result.candidates), "total_pass": len(passing),
                "thinking_steps": [{"step": s.step_num, "thought": s.thought,
                                    "action": s.stage, "observation": s.observation}
                                   for s in result.steps]}


class GeometryEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        geometry = intent.get("geometry", {})
        loading = intent.get("loading", "tensile")
        comp_wt = intent.get("composition")
        alloy_name = intent.get("alloy_name")
        T_K = intent.get("temperature_K") or 298.0
        hub = get_hub()
        if not comp_wt and alloy_name:
            a = hub.get_alloy(alloy_name)
            if a:
                comp_wt = a["composition_wt"]
        if comp_wt:
            comp = _convert_wt_to_mol(comp_wt)
            physics = run_all(comp, T_K=T_K, verbose=True)
            try:
                from engineering.calculations import full_engineering_analysis
                eng = full_engineering_analysis(comp, geometry, loading, T_K)
            except Exception as e:
                eng = {"error": str(e)}
            return {"mode": "geometry", "alloy_name": alloy_name, "composition": comp,
                    "geometry": geometry, "loading": loading,
                    "physics_result": physics, "engineering_result": eng}
        geo_intent = dict(intent)
        geo_intent["notes"] = f"structural alloy for {geometry.get('shape', 'plate')} under {loading}"
        result = run_pipeline(query=geo_intent["notes"], intent=geo_intent,
                              on_step=on_step, max_iterations=2, T_K=T_K)
        scored = []
        for cand in result.candidates[:20]:
            if cand.physics_result:
                try:
                    from engineering.calculations import stress_analysis
                    eng = stress_analysis(cand.composition, geometry, loading)
                    if eng.get("safety_factor", 0) > 1.5:
                        scored.append((cand.composition, cand.physics_result, eng))
                except Exception:
                    pass
        scored.sort(key=lambda x: (-x[1]["composite_score"], -x[2].get("safety_factor", 0)))
        return {"mode": "geometry", "geometry": geometry, "loading": loading,
                "suitable_alloys": scored[:10], "total_checked": len(result.candidates),
                "total_suitable": len(scored)}


class ChatEngine:
    @staticmethod
    def run(intent, verbose=False, on_step=None):
        query = intent.get("notes", "")
        chat_response = intent.get("chat_response")
        if chat_response:
            return {"mode": "chat", "response": chat_response, "query": query}
        from llms.client import is_available
        if is_available():
            try:
                from llms.client import chat as llm_chat_raw
                response = llm_chat_raw([
                    {"role": "system", "content": "You are AIDE v4, an expert metallurgy assistant."},
                    {"role": "user", "content": query}], max_tokens=500)
                return {"mode": "chat", "response": response or "Could not process that.", "query": query}
            except Exception:
                pass
        return {"mode": "chat", "response": "I'm AIDE v4. Ask me to design, study, compare, or modify alloys.",
                "query": query}


def _passes_constraints(comp, result, constraints):
    if constraints.get("min_PREN"):
        try:
            if PREN_wt(comp) < constraints["min_PREN"]:
                return False
        except Exception:
            pass
    if constraints.get("max_density"):
        d = density_rule_of_mixtures(comp)
        if d and d > constraints["max_density"]:
            return False
    if constraints.get("min_yield_MPa"):
        hv = wmean(comp, "vickers")
        if hv and hv / 3.0 < constraints["min_yield_MPa"]:
            return False
    return True


ENGINES = {
    "design": DesignEngine, "modify": ModifyEngine, "study": StudyEngine,
    "compare": CompareEngine, "explore": ExploreEngine, "geometry": GeometryEngine,
    "chat": ChatEngine,
}


def route(intent, verbose=False, on_step=None):
    mode = intent.get("mode", "design")
    engine = ENGINES.get(mode, DesignEngine)
    return engine.run(intent, verbose=verbose, on_step=on_step)
