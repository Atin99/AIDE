"""Check raw physics engine output for a stainless composition."""
import sys
sys.path.insert(0, ".")
from physics.filter import run_all
from physics.base import wt_to_mol
from core.elements import validate_composition

# Same composition as Render candidate #1
wt = {"Fe": 0.608, "Cr": 0.237, "Ni": 0.082, "Mo": 0.072}
mol = validate_composition(wt_to_mol(wt))
r = run_all(mol, T_K=298.0)

print(f"composite_score = {r.get('composite_score', 'MISSING')}")
print(f"n_domains = {r.get('n_domains', 0)}")

domain_results = r.get("domain_results", [])
scores = [dr.score() for dr in domain_results]
if scores:
    print(f"domain_scores: count={len(scores)}, min={min(scores):.1f}, max={max(scores):.1f}")
    for dr in domain_results[:5]:
        print(f"  {dr.domain_name}: {dr.score():.1f}")
else:
    print("NO DOMAIN RESULTS!")
