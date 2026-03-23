import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def suggest_experiments(top_candidates, gp_models, feature_extractor_fn,
                        n_suggest=3, verbose=True):
    if not gp_models:
        return []

    suggestions = []
    for comp, score in top_candidates:
        try:
            features = feature_extractor_fn(comp)
            sigma_vals = {}
            for target, m in gp_models.items():
                Xs = m["scaler"].transform(features.reshape(1, -1))
                _, sigma = m["gp"].predict(Xs, return_std=True)
                sigma_vals[target] = float(sigma[0])
        except Exception:
            continue

        primary_sigma = sigma_vals.get("bulk_modulus", sigma_vals.get(
            list(sigma_vals.keys())[0], 0.0) if sigma_vals else 0.0)

        eig = primary_sigma

        suggestions.append({
            "comp": comp,
            "score": score,
            "sigma_bulk": sigma_vals.get("bulk_modulus", 0.0),
            "sigma_Ef": sigma_vals.get("formation_energy", 0.0),
            "sigma_G": sigma_vals.get("shear_modulus", 0.0),
            "eig": eig,
        })

    suggestions.sort(key=lambda x: -x["eig"])
    suggestions = suggestions[:n_suggest]

    if verbose and suggestions:
        print(f"\n  Active Learning — Top {len(suggestions)} synthesis targets "
              f"(highest GP uncertainty):")
        print(f"  {'#':<3} {'Score':>6}  {'sigma_B (GPa)':>13}  Composition")
        print(f"  {''*60}")
        for i, s in enumerate(suggestions, 1):
            comp_str = "  ".join(f"{el}:{v*100:.0f}%"
                                  for el, v in sorted(s["comp"].items(),
                                                       key=lambda x: -x[1])[:4])
            print(f"  #{i:<2} {s['score']:6.1f}  {s['sigma_bulk']:13.1f}  {comp_str}")
            bulk_mean_str = ""
            try:
                from ml.gp_surrogate import predict_with_uncertainty
                feat = feature_extractor_fn(s["comp"])
                from ml.gp_surrogate import load_gp_models
                gps = load_gp_models()
                if gps:
                    pred = predict_with_uncertainty(gps, feat)
                    bm = pred.get("bulk_modulus", {})
                    if bm:
                        bulk_mean_str = (f"     Predicted bulk modulus: "
                                         f"{bm['mean']:.0f} +/- {bm['sigma']:.0f} GPa")
            except Exception:
                pass
            if bulk_mean_str:
                print(bulk_mean_str)
            print(f"     Expected information gain: {s['eig']:.2f}  "
                  f"(high uncertainty = high synthesis priority)")

    return suggestions
