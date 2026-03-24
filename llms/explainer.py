import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llms.client import chat, is_available as llm_available


EXPLAIN_SYSTEM = """You are AIDE v4, an expert computational metallurgist.
Explain alloy analysis results in clear, actionable language.
1. Explain WHY each domain scored as it did, cite physical mechanisms.
2. For weak domains, suggest specific compositional changes with amounts.
3. Highlight cross-domain trade-offs and synergies.
4. Use metric units and reference specific element roles.
5. Be concise but thorough, 3-5 paragraphs max.
6. Start with a 1-sentence executive summary."""


def synthesize_explanation(query, top_candidates, correlation_insights):
    if not llm_available():
        return _template_synthesis(top_candidates, correlation_insights)
    if not top_candidates:
        return "No candidates were generated for this query."
    best = top_candidates[0]
    comp_str = ", ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(
        best.composition_wt.items(), key=lambda x: -x[1])[:6])
    parts = [f"Query: {query}", f"Best composition: {comp_str}",
             f"Score: {best.score:.1f}/100", f"Rationale: {best.rationale}"]
    if best.physics_result and "domain_results" in best.physics_result:
        strong, weak = [], []
        for dr in best.physics_result["domain_results"]:
            s = dr.score()
            if s >= 75:
                strong.append(f"{dr.domain_name}: {s:.0f}")
            elif s < 45:
                fails = [c.name for c in dr.checks if c.status == "FAIL"]
                weak.append(f"{dr.domain_name}: {s:.0f} (fails: {', '.join(fails[:2])})")
        if strong:
            parts.append(f"\nStrength domains: {'; '.join(strong[:5])}")
        if weak:
            parts.append(f"\nWeak domains: {'; '.join(weak[:5])}")
    if correlation_insights:
        parts.append("\nCross-domain correlations:")
        for ins in correlation_insights[:5]:
            parts.append(f"  - {ins['message']}")
    parts.append("\nProvide comprehensive analysis: executive summary, strengths, weaknesses, "
                 "cross-domain insights, and compositional recommendations.")
    try:
        response = chat([{"role": "system", "content": EXPLAIN_SYSTEM},
                         {"role": "user", "content": "\n".join(parts)}],
                        max_tokens=1000, temperature=0.15)
        return response or _template_synthesis(top_candidates, correlation_insights)
    except Exception:
        return _template_synthesis(top_candidates, correlation_insights)


def explain_results(composition, domain_results, query=""):
    if not llm_available():
        return _template_explain(composition, domain_results)
    comp_str = ", ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(
        composition.items(), key=lambda x: -x[1])[:6])
    weak_domains, strong_domains = [], []
    for dr in domain_results:
        s = dr.score()
        fails = [c.name for c in dr.checks if c.status == "FAIL"]
        if fails or s < 40:
            weak_domains.append(f"  {dr.domain_name}: {s:.0f}/100" +
                                (f" FAIL:[{', '.join(fails[:3])}]" if fails else ""))
        elif s >= 80:
            strong_domains.append(f"  {dr.domain_name}: {s:.0f}/100")
    parts = [f"Query: {query}", f"Composition: {comp_str}"]
    if strong_domains:
        parts.append(f"\nStrong ({len(strong_domains)}):")
        parts.extend(strong_domains[:5])
    if weak_domains:
        parts.append(f"\nWeak ({len(weak_domains)}):")
        parts.extend(weak_domains[:8])
    parts.append("\nProvide balanced analysis with compositional recommendations.")
    try:
        response = chat([{"role": "system", "content": EXPLAIN_SYSTEM},
                         {"role": "user", "content": "\n".join(parts)}],
                        max_tokens=800, temperature=0.1)
        return response or _template_explain(composition, domain_results)
    except Exception:
        return _template_explain(composition, domain_results)


def explain_candidate(composition, score, rationale, weak_domains, rank=1):
    if not llm_available():
        return _template_candidate(composition, score, rationale, rank)
    comp_str = ", ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(
        composition.items(), key=lambda x: -x[1])[:6])
    weak_str = ""
    if weak_domains:
        items = []
        for wd in weak_domains[:3]:
            if isinstance(wd, dict):
                items.append(f"{wd['name']}: {wd['score']:.0f}/100")
            else:
                items.append(str(wd))
        weak_str = f"\nWeak: {'; '.join(items)}"
    msg = (f"Candidate #{rank}\nComposition: {comp_str}\nScore: {score:.1f}/100\n"
           f"Rationale: {rationale}{weak_str}\n\nExplain in 3-4 sentences.")
    try:
        response = chat([{"role": "system", "content": EXPLAIN_SYSTEM},
                         {"role": "user", "content": msg}], max_tokens=300, temperature=0.1)
        return response or _template_candidate(composition, score, rationale, rank)
    except Exception:
        return _template_candidate(composition, score, rationale, rank)


def explain_comparison(name1, name2, result):
    if not llm_available():
        return _template_comparison(name1, name2, result)
    comparison = result.get("comparison", [])
    wins_1 = sum(1 for c in comparison if c.get("winner") == name1)
    wins_2 = sum(1 for c in comparison if c.get("winner") == name2)
    diffs = sorted(comparison, key=lambda c: abs(c["score_1"] - c["score_2"]), reverse=True)[:5]
    diff_str = "\n".join(f"  {d['domain']}: {name1}={d['score_1']:.0f} vs {name2}={d['score_2']:.0f}"
                         for d in diffs)
    winner = result.get("overall_winner", "")
    msg = (f"Compare {name1} vs {name2}\nWinner: {winner}\n"
           f"Wins: {name1}={wins_1}, {name2}={wins_2}\nDifferences:\n{diff_str}\n\n"
           f"Explain why {winner} wins and what each alloy suits better.")
    try:
        response = chat([{"role": "system", "content": EXPLAIN_SYSTEM},
                         {"role": "user", "content": msg}], max_tokens=400, temperature=0.1)
        return response or _template_comparison(name1, name2, result)
    except Exception:
        return _template_comparison(name1, name2, result)


def explain_single_domain(domain_name, score, checks_str, comp_str):
    if not llm_available():
        return _template_single_domain(domain_name, score, checks_str, comp_str)
    
    msg = (f"Domain: {domain_name}\nScore: {score:.1f}/100\nComposition: {comp_str}\n"
           f"Checks:\n{checks_str}\n\n"
           f"Explain the physical reason behind this score based on the composition and checks. "
           f"Provide absolute values and physical mechanisms. Keep it concise (1-2 paragraphs max).")
    try:
        response = chat([{"role": "system", "content": EXPLAIN_SYSTEM},
                         {"role": "user", "content": msg}], max_tokens=300, temperature=0.1)
        return response or _template_single_domain(domain_name, score, checks_str, comp_str)
    except Exception:
        return _template_single_domain(domain_name, score, checks_str, comp_str)


DOMAIN_REMEDIES = {
    "corrosion": "Increase Cr (>20%) and Mo (>3%) for better PREN.",
    "oxidation": "Increase Al or Cr for protective oxide.",
    "mechanical": "Increase C, N, or V for precipitation hardening.",
    "creep": "Add refractory elements (Mo, W, Re).",
    "fatigue": "Reduce inclusions. Ti and Nb for grain refinement.",
    "hydrogen": "Austenite stabilizers (Ni, Mn, N) resist HE.",
    "biocompatibility": "Replace Ni and Co with Nb, Ta, or Zr.",
    "weldability": "Reduce C below 0.03%. Add Ti or Nb.",
    "radiation": "Use BCC metals (Fe, Cr, W). Minimize Co, Nb.",
    "phase stability": "Adjust VEC and delta parameters.",
    "thermodynamics": "Increase mixing entropy (more equiatomic).",
}


def _template_synthesis(top_candidates, correlation_insights):
    if not top_candidates:
        return "No candidates generated."
    best = top_candidates[0]
    comp_str = ", ".join(f"{s} {v*100:.1f}%" for s, v in sorted(
        best.composition_wt.items(), key=lambda x: -x[1])[:5])
    lines = [f"Best Composition: {comp_str}", f"Score: {best.score:.1f}/100"]
    if best.rationale:
        lines.append(f"Rationale: {best.rationale}")
    if correlation_insights:
        lines.append("\nCross-Domain Insights:")
        for ins in correlation_insights[:5]:
            lines.append(f"- {ins['message']}")
    return "\n".join(lines)


def _template_explain(composition, domain_results):
    comp_str = ", ".join(f"{s} {v*100:.1f}%" for s, v in sorted(
        composition.items(), key=lambda x: -x[1])[:5])
    fails, strong = [], []
    for dr in domain_results:
        for c in dr.checks:
            if c.status == "FAIL":
                fails.append((dr.domain_name, c.name))
        if dr.score() >= 80:
            strong.append(dr.domain_name)
    lines = [f"Composition: {comp_str}"]
    if strong:
        lines.append(f"\nStrengths: {', '.join(strong[:5])}")
    if fails:
        lines.append(f"\nIssues ({len(fails)}):")
        seen = set()
        for domain, check in fails[:5]:
            lines.append(f"- {domain}: {check}")
            if domain.lower() not in seen:
                seen.add(domain.lower())
                for key, remedy in DOMAIN_REMEDIES.items():
                    if key in domain.lower():
                        lines.append(f"  Remedy: {remedy}")
                        break
    return "\n".join(lines)


def _template_candidate(composition, score, rationale, rank):
    comp_str = ", ".join(f"{s} {v*100:.1f}%" for s, v in sorted(
        composition.items(), key=lambda x: -x[1])[:5])
    quality = "strong" if score >= 70 else ("moderate" if score >= 50 else "needs improvement")
    return f"Candidate #{rank} ({quality}, {score:.1f}/100)\nComposition: {comp_str}"


def _template_comparison(name1, name2, result):
    winner = result.get("overall_winner", "Unknown")
    comparison = result.get("comparison", [])
    wins_1 = sum(1 for c in comparison if c.get("winner") == name1)
    wins_2 = sum(1 for c in comparison if c.get("winner") == name2)
    return f"{winner} wins overall ({wins_1} vs {wins_2} domain wins)."


def _template_single_domain(domain_name, score, checks_str, comp_str):
    lines = [ln.strip() for ln in str(checks_str or "").splitlines() if ln.strip()]
    fails = [ln for ln in lines if ln.startswith("[FAIL]")]
    warns = [ln for ln in lines if ln.startswith("[WARN]")]
    passes = [ln for ln in lines if ln.startswith("[PASS]")]
    infos = [ln for ln in lines if ln.startswith("[INFO]")]

    quality = "strong" if score >= 75 else ("mixed" if score >= 45 else "weak")
    summary = (
        f"{domain_name} is {quality} ({score:.1f}/100) for {comp_str}. "
        f"Checks: PASS={len(passes)}, WARN={len(warns)}, FAIL={len(fails)}, INFO={len(infos)}."
    )

    details = []
    if fails:
        details.append("Critical limits failing:")
        details.extend(f"- {ln[7:]}" for ln in fails[:3])
    elif warns:
        details.append("Main caution points:")
        details.extend(f"- {ln[7:]}" for ln in warns[:3])
    elif passes:
        details.append("Main drivers of this score:")
        details.extend(f"- {ln[7:]}" for ln in passes[:3])

    remedy = ""
    lower_text = f"{domain_name} {checks_str}".lower()
    for key, text in DOMAIN_REMEDIES.items():
        if key in lower_text:
            remedy = text
            break
    if remedy:
        details.append(f"Recommended composition direction: {remedy}")

    if not details:
        details.append("No detailed checks were available for this domain.")

    return summary + "\n\n" + "\n".join(details)
