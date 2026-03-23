import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from ml.features import extract_features, FEATURE_NAMES


def explain_prediction(xgb_model, comp: dict, target: str = "bulk_modulus",
                        top_n: int = 5, verbose: bool = True) -> dict:
    if not SHAP_AVAILABLE:
        return {"explanation": "SHAP not available. pip install shap"}

    try:
        features = extract_features(comp)
        X = features.reshape(1, -1)
        explainer = shap.TreeExplainer(xgb_model)
        shap_values = explainer.shap_values(X)[0]
    except Exception as e:
        return {"explanation": f"SHAP error: {e}"}

    pairs = list(zip(FEATURE_NAMES, shap_values))
    pairs_sorted = sorted(pairs, key=lambda x: abs(x[1]), reverse=True)
    top = pairs_sorted[:top_n]

    parts = []
    for feat, val in top:
        direction = "+" if val > 0 else ""
        feat_short = feat.replace("_mean", "").replace("_std", " variability")
        parts.append(f"{feat_short} ({direction}{val:.3f})")

    explanation = (f"{target.replace('_', ' ').title()} prediction driven by: "
                   + ", ".join(parts))

    if verbose:
        print(f"\n  SHAP explanation ({target}):")
        print(f"  {explanation}")

    return {
        "feature_names": FEATURE_NAMES,
        "shap_values": shap_values.tolist(),
        "top_features": [(f, float(v)) for f, v in top],
        "explanation": explanation,
    }


def explain_all_targets(xgb_models: dict, comp: dict, verbose: bool = True) -> dict:
    results = {}
    for target, model in xgb_models.items():
        results[target] = explain_prediction(model, comp, target=target,
                                              verbose=verbose)
    return results
