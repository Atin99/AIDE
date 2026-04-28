"""Test the exact backend API path locally."""
import sys, os, json, time
sys.path.insert(0, ".")
os.environ["AIDE_ENABLE_REMOTE_LLM"] = "0"

from backend.app.services.analysis_service import run_unified

t0 = time.time()
payload = {"query": "Design a copper alloy heat spreader for electronics thermal management"}

try:
    result = run_unified(payload)
    elapsed = time.time() - t0
    r = result.get("result", {})
    print(f"Time: {elapsed:.1f}s")
    print(f"Type: {result.get('request_type')}")
    print(f"Top: {len(r.get('top', []))}")
    print(f"Detail: {len(r.get('candidates_detail', []))}")
    print(f"Best: {r.get('best_score')}")
    print(f"PhysEval: {r.get('n_physics_evaluated')}")
    print(f"Iterations: {r.get('iterations')}")
    print(f"Converged: {r.get('converged')}")
    
    # Check if candidates_detail is empty but generation happened
    stats = r.get("generation_stats", {})
    print(f"Gen stats: {json.dumps(stats)}")
    
    if not r.get("candidates_detail"):
        print("WARNING: No candidates in detail!")
        print(f"n_candidates (total pool): {r.get('n_candidates')}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
