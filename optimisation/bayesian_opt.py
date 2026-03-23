import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from skopt import Optimizer
    from skopt.space import Real
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False


def _normalise(x_raw, element_list):
    x = np.array(x_raw, dtype=float)
    x = np.clip(x, 0.001, 1.0)
    total = x.sum()
    if total < 1e-6:
        x = np.ones_like(x) / len(x)
    else:
        x = x / total
    return {el: float(v) for el, v in zip(element_list, x)}


def run_bayesian_opt(evaluate_fn, seed_compositions, element_list,
                     n_calls=200, n_initial=50, verbose=True):
    if not SKOPT_AVAILABLE:
        print("  Bayesian Opt: scikit-optimize not installed. Falling back to seed compositions.")
        results = []
        for comp in seed_compositions[:n_calls]:
            try:
                score = evaluate_fn(comp)
                results.append((comp, score))
            except Exception:
                pass
        return sorted(results, key=lambda x: -x[1])

    space = [Real(0.001, 1.0, name=el) for el in element_list]
    optimizer = Optimizer(
        dimensions=space,
        base_estimator="GP",
        acq_func="EI",
        acq_optimizer="lbfgs",
        n_initial_points=n_initial,
        random_state=42,
    )

    results = []

    for comp in seed_compositions[:n_initial]:
        x = [comp.get(el, 0.001) for el in element_list]
        try:
            score = evaluate_fn(comp)
            optimizer.tell(x, -score)
            results.append((comp, score))
        except Exception:
            pass

    remaining = n_calls - len(results)
    for i in range(remaining):
        x_next = optimizer.ask()
        comp = _normalise(x_next, element_list)
        try:
            score = evaluate_fn(comp)
        except Exception:
            score = 0.0
        optimizer.tell(x_next, -score)
        results.append((comp, score))
        if verbose and (i + 1) % 50 == 0:
            best = max(r[1] for r in results)
            print(f"  BO iter {i+1}/{remaining}  best_score={best:.1f}")

    return sorted(results, key=lambda x: -x[1])


def run_bo_candidates(args, seed_compositions, parsed):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from physics.filter import run_all

    element_set = set()
    for comp in seed_compositions:
        element_set.update(comp.keys())
    element_list = sorted(element_set)

    def evaluate_fn(comp):
        try:
            r = run_all(comp, T_K=args.T, dpa_rate=args.dpa,
                        thickness_mm=args.thickness,
                        process=args.process, weather=args.weather,
                        verbose=False)
            return r["composite_score"]
        except Exception:
            return 0.0

    results = run_bayesian_opt(
        evaluate_fn=evaluate_fn,
        seed_compositions=seed_compositions,
        element_list=element_list,
        n_calls=args.n,
        n_initial=min(50, len(seed_compositions)),
        verbose=args.verbose,
    )
    return [comp for comp, _ in results]
