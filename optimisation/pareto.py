import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize as pymoo_minimize
    from pymoo.termination import get_termination
    PYMOO_AVAILABLE = True
except ImportError:
    PYMOO_AVAILABLE = False

from physics.base import density_rule_of_mixtures, PREN_wt


def get_objectives(comp, ml_predictor=None):
    fe = comp.get("Fe", 0)
    cr = comp.get("Cr", 0)

    density = density_rule_of_mixtures(comp) or 8.0
    pren = PREN_wt(comp) if fe > 0.3 and cr > 0.05 else 0.0

    yield_strength = 0.0
    if ml_predictor is not None:
        try:
            pred = ml_predictor.predict(comp)
            yield_strength = pred.get("yield_strength", {}).get("mean", 0.0)
            if yield_strength == 0.0:
                from physics.base import wmean
                hv = wmean(comp, "vickers") or 150
                yield_strength = hv / 3.0
        except Exception:
            pass

    return density, -pren, -yield_strength


class AlloyProblem(Problem):
    def __init__(self, element_list, evaluate_objectives_fn, n_var=None):
        self.element_list = element_list
        self.evaluate_fn = evaluate_objectives_fn
        super().__init__(
            n_var=len(element_list),
            n_obj=3,
            n_constr=0,
            xl=np.zeros(len(element_list)),
            xu=np.ones(len(element_list)),
        )

    def _evaluate(self, X, out, *args, **kwargs):
        F = []
        for x in X:
            x = np.clip(x, 0.001, 1.0)
            x = x / x.sum()
            comp = {el: float(v) for el, v in zip(self.element_list, x)}
            try:
                objs = self.evaluate_fn(comp)
            except Exception:
                objs = (8.0, 0.0, 0.0)
            F.append(objs)
        out["F"] = np.array(F)


def run_pareto(candidates_with_scores, ml_predictor=None, verbose=True):
    if not candidates_with_scores:
        return []

    pareto_data = []
    for comp, score in candidates_with_scores:
        density, neg_pren, neg_yield = get_objectives(comp, ml_predictor)
        pareto_data.append({
            "comp": comp,
            "score": score,
            "density": density,
            "pren": -neg_pren,
            "yield_strength": -neg_yield,
        })

    dominated = set()
    for i, a in enumerate(pareto_data):
        for j, b in enumerate(pareto_data):
            if i == j:
                continue
            if (b["density"] <= a["density"] and
                b["pren"] >= a["pren"] and
                b["yield_strength"] >= a["yield_strength"] and
                (b["density"] < a["density"] or
                 b["pren"] > a["pren"] or
                 b["yield_strength"] > a["yield_strength"])):
                dominated.add(i)
                break

    pareto_front = [d for i, d in enumerate(pareto_data) if i not in dominated]

    if verbose:
        print(f"\n  Pareto front: {len(pareto_front)} non-dominated solutions "
              f"from {len(pareto_data)} candidates")
        print(f"  {'Rank':<5} {'Score':>6}  {'Density':>8}  {'PREN':>6}  {'Yield MPa':>9}  Composition")
        print(f"  {''*70}")
        for i, d in enumerate(sorted(pareto_front, key=lambda x: -x["score"])[:10], 1):
            comp_str = "  ".join(f"{s}:{v*100:.0f}%" for s, v in
                                  sorted(d["comp"].items(), key=lambda x: -x[1])[:4])
            print(f"  #{i:<4} {d['score']:6.1f}  {d['density']:8.3f}  "
                  f"{d['pren']:6.1f}  {d['yield_strength']:9.0f}  {comp_str}")

    return pareto_front
