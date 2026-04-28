"""Quick diagnostic: why are physics scores 0.0?"""
import json, sys, os
sys.path.insert(0, ".")
os.environ["AIDE_ENABLE_REMOTE_LLM"] = "1"

from engines.pipeline import run_pipeline
from llms.intent_parser import classify_intent

query = "Design a marine-grade stainless steel for offshore piping, must resist chloride pitting"
intent = classify_intent(query)

print("=== INTENT ===")
for k, v in intent.items():
    if k == "research_data":
        rd = v
        if rd:
            print(f"  research_data.base_elements = {rd.base_elements}")
            print(f"  research_data.base_min_fraction = {rd.base_min_fraction}")
            print(f"  research_data.mandatory_mechanisms = {rd.mandatory_mechanisms}")
            print(f"  research_data.domain_weights = {dict(list(rd.domain_weights.items())[:8])}")
        else:
            print("  research_data = None")
    else:
        print(f"  {k} = {v}")

result = run_pipeline(
    query=query, intent=intent,
    max_iterations=1, min_iterations=1,
    target_score=80, feedback_limit=1, use_ml=False
)

cands = result.candidates
phys = [c for c in cands if c.physics_evaluated]
print(f"\n=== RESULTS ===")
print(f"Total: {len(cands)}, Physics: {len(phys)}, Best: {result.best_score}")

scores = [c.score for c in phys]
if scores:
    print(f"Physics scores: min={min(scores):.1f}, max={max(scores):.1f}")
    zero_count = sum(1 for s in scores if s == 0.0)
    print(f"Zero-scored: {zero_count}/{len(phys)}")

    # Show top 3 scored
    print("\nTOP 3:")
    for c in sorted(phys, key=lambda c: -c.score)[:3]:
        wt = c.composition_wt or {}
        top5 = sorted(wt.items(), key=lambda x: -x[1])[:5]
        comp = "  ".join(f"{k}:{v*100:.1f}" for k, v in top5)
        print(f"  score={c.score:.1f}  src={c.score_source}  {comp}")

    # Show why zeroed
    zeroed = [c for c in phys if c.score == 0.0]
    if zeroed:
        print(f"\nWHY ZEROED (first 3 of {len(zeroed)}):")
        for c in zeroed[:3]:
            wt = c.composition_wt or {}
            top4 = sorted(wt.items(), key=lambda x: -x[1])[:4]
            comp = "  ".join(f"{k}:{v*100:.1f}" for k, v in top4)
            weak_names = [w.get("name", "?") for w in (c.weak_domains or [])]
            pr = c.physics_result or {}
            base = pr.get("composite_score", "N/A")
            print(f"  comp: {comp}")
            print(f"  base_composite_score: {base}")
            print(f"  weak_domains: {weak_names}")
            print()
