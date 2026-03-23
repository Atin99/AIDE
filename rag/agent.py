
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import retrieve, rag_available
from llms.groq_client import chat, is_available as llm_available


SYSTEM_PROMPT = """You are AIDE v3, an expert computational metallurgist.
You help explain alloy analysis results using retrieved literature.

CRITICAL RULES:
1. You NEVER predict material properties — all numbers are provided.
2. You ALWAYS ground your explanation in the literature provided.
3. You cite papers by author and year.
4. If a FAIL was found, explain the physical reason and suggest a remedy.
5. Be concise — 3-5 sentences per topic."""


def generate_explanation(query: str, top_alloy: dict,
                         domain_results: list,
                         ml_predictions: dict = None) -> str:
    papers = []
    if rag_available():
        comp_str = " ".join(f"{el} {v*100:.0f}%"
                           for el, v in sorted(top_alloy.items(),
                                              key=lambda x: -x[1])[:4])
        papers = retrieve(f"{query} alloy {comp_str}", n_results=4)

    literature_ctx = ""
    if papers:
        literature_ctx = "\n\nRelevant literature:\n" + "\n".join(
            f"- [{p['source']}]: {p['text'][:200]}..." for p in papers)

    fails = []
    warns = []
    for dr in domain_results:
        checks = dr.get("checks", []) if isinstance(dr, dict) else []
        domain_name = dr.get("domain", "") if isinstance(dr, dict) else getattr(dr, "domain_name", "")
        for ch in checks:
            status = ch.get("status", "") if isinstance(ch, dict) else getattr(ch, "status", "")
            name = ch.get("name", "") if isinstance(ch, dict) else getattr(ch, "name", "")
            if status == "FAIL":
                fails.append((domain_name, name))
            elif status == "WARN":
                warns.append((domain_name, name))

    physics_ctx = f"\nPhysics: {len(fails)} FAILs, {len(warns)} WARNs"
    if fails:
        physics_ctx += "\nFails: " + "; ".join(f"{d}: {n}" for d, n in fails[:5])

    ml_ctx = ""
    if ml_predictions:
        ml_ctx = "\nML: " + "; ".join(
            f"{k}={v.get('mean', 0):.2f}±{v.get('sigma', 0):.2f}"
            for k, v in ml_predictions.items() if isinstance(v, dict))

    if llm_available():
        try:
            user_msg = (f"Query: {query}\n"
                       f"Composition: {top_alloy}\n"
                       f"{physics_ctx}{ml_ctx}{literature_ctx}\n\n"
                       f"Explain in 3-5 sentences why this alloy is recommended.")
            response = chat([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ], max_tokens=400)
            if response:
                return response
        except Exception:
            pass

    comp_str = ", ".join(f"{el} {v*100:.1f}%"
                        for el, v in sorted(top_alloy.items(),
                                           key=lambda x: -x[1])[:5])
    explanation = f"Recommended: {comp_str}."
    if fails:
        explanation += f" Note: {len(fails)} domain failures."
    if papers:
        explanation += f" See: {papers[0]['source']}."
    if not llm_available():
        explanation += " (Set GROQ_API_KEY for AI explanations.)"
    return explanation


def lookup_for_reasoning(query: str) -> str:
    if not rag_available():
        return ""
    
    papers = retrieve(query, n_results=2)
    if papers:
        return " | ".join(p['text'][:150] for p in papers)
    return ""
