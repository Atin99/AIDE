import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

_DEFAULT_RMSE = {
    "formation_energy": 0.12,
    "bulk_modulus":     18.0,
    "shear_modulus":    14.0,
}

UNITS = {
    "formation_energy": "eV/atom",
    "bulk_modulus":     "GPa",
    "shear_modulus":    "GPa",
    "yield_strength":   "MPa",
    "UTS":              "MPa",
}


class FullModelEnsemble:
    def __init__(self):
        self._xgb = {}
        self._gp  = {}
        self._nn  = None
        self._transfer = None
        self._additional_models = []
        self._rmse = dict(_DEFAULT_RMSE)
        self._loaded = False
        self._n_features = None

    def _load(self):
        if self._loaded:
            return

        try:
            import joblib
            for target in ["formation_energy", "bulk_modulus", "shear_modulus"]:
                p = os.path.join(MODELS_DIR, f"{target}.joblib")
                if os.path.exists(p):
                    self._xgb[target] = joblib.load(p)
        except Exception:
            pass

        try:
            from ml.gp_surrogate import load_gp_models
            self._gp = load_gp_models()
        except Exception:
            pass

        try:
            from ml.multitask_net import load_nn
            from ml.features import N_FEATURES
            self._n_features = N_FEATURES
            self._nn = load_nn(N_FEATURES)
            from ml.transfer_learning import load_transfer_model
            self._transfer = load_transfer_model(self._nn)
        except Exception:
            pass

        try:
            from ml.additional_models import ALL_MODEL_CLASSES
            for cls in ALL_MODEL_CLASSES:
                try:
                    m = cls()
                    m.load()
                    if m.models:
                        self._additional_models.append(m)
                except Exception:
                    continue
        except Exception:
            pass

        report_path = os.path.join(MODELS_DIR, "train_report.json")
        if os.path.exists(report_path):
            try:
                with open(report_path) as f:
                    report = json.load(f)
                for target in _DEFAULT_RMSE:
                    if target in report:
                        self._rmse[target] = report[target].get("rmse", _DEFAULT_RMSE[target])
            except Exception:
                pass

        self._loaded = True

    def is_available(self) -> bool:
        self._load()
        return bool(self._xgb or self._additional_models)

    def predict(self, comp: dict) -> dict:
        self._load()
        from ml.features import extract_features
        features = extract_features(comp)
        if features is None:
            return {}

        results = {}
        targets = set(list(self._xgb.keys()) + list(self._rmse.keys()))
        for am in self._additional_models:
            targets.update(am.models.keys())

        for target in targets:
            predictions = []
            
            if target in self._xgb:
                try:
                    predictions.append(float(self._xgb[target].predict(features.reshape(1, -1))[0]))
                except Exception:
                    pass

            for am in self._additional_models:
                if target in am.models:
                    try:
                        preds = am.predict(features)
                        if target in preds:
                            predictions.append(preds[target])
                    except Exception:
                        pass

            gp_sigma = self._rmse.get(target, 0.0)
            if target in self._gp:
                try:
                    from ml.gp_surrogate import predict_with_uncertainty
                    gp_result = predict_with_uncertainty({target: self._gp[target]}, features)
                    predictions.append(gp_result[target]["mean"])
                    gp_sigma = gp_result[target]["sigma"]
                except Exception:
                    pass

            if self._nn is not None:
                try:
                    from ml.multitask_net import predict_nn
                    nn_preds = predict_nn(self._nn, features)
                    if target in nn_preds:
                        predictions.append(nn_preds[target])
                except Exception:
                    pass

            if not predictions:
                continue

            p_arr = np.array(predictions)
            ensemble_mean = float(np.median(p_arr))
            ensemble_spread = float(np.percentile(p_arr, 90) - np.percentile(p_arr, 10)) if len(p_arr) > 2 else float(np.max(p_arr) - np.min(p_arr)) if len(p_arr) > 1 else 0.0
            
            total_sigma = max(gp_sigma, 0.5 * ensemble_spread)

            results[target] = {
                "mean":  ensemble_mean,
                "sigma": total_sigma,
                "unit":  UNITS.get(target, ""),
                "models_used": len(predictions),
            }

        if self._transfer is not None:
            try:
                from ml.transfer_learning import predict_experimental
                exp_preds = predict_experimental(self._transfer, features)
                for t, v in exp_preds.items():
                    results[t] = {"mean": v, "sigma": 50.0, "unit": "MPa",
                                  "note": "transfer learning", "models_used": 1}
            except Exception:
                pass

        return results

    def format_summary(self, predictions: dict) -> str:
        if not predictions:
            return "  ML: no predictions available"
        lines = ["  ML ensemble predictions:"]
        for target, pred in predictions.items():
            if not isinstance(pred, dict):
                continue
            mean = pred.get("mean", 0)
            sigma = pred.get("sigma", 0)
            unit = pred.get("unit", "")
            note = pred.get("note", "")
            models = pred.get("models_used", 1)
            t_str = target.replace("_", " ").title()
            
            extra = []
            if models > 1: extra.append(f"{models} models")
            if note: extra.append(note)
            extra_str = f"  [{', '.join(extra)}]" if extra else ""
            
            lines.append(f"    {t_str:<22}: {mean:8.2f} +/- {sigma:<6.2f} {unit}{extra_str}")
        return "\n".join(lines)


_predictor = None

def get_predictor() -> FullModelEnsemble:
    global _predictor
    if _predictor is None:
        _predictor = FullModelEnsemble()
    return _predictor
