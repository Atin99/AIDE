import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor

from ml.features import extract_features, FEATURE_NAMES, N_FEATURES
from ml.gp_surrogate import train_gp, save_gp_models
from ml.multitask_net import train_multitask_net, save_nn, TORCH_AVAILABLE

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def load_jarvis():
    print("\n[1/5] Loading JARVIS-DFT (jarvis-tools, ~200MB auto-download)...")
    t0 = time.time()
    from jarvis.db.figshare import data
    dft_3d = data("dft_3d")
    print(f"  Loaded {len(dft_3d)} entries  ({time.time()-t0:.0f}s)")
    return dft_3d


def parse_jarvis(dft_3d):
    print("[2/5] Featurizing JARVIS entries (composition-only, no CIF files)...")
    rows = []
    skipped = 0
    t0 = time.time()
    for i, entry in enumerate(dft_3d):
        try:
            comp_raw = entry.get("formula", "")
            import re
            matches = re.findall(r'([A-Z][a-z]?)(\d*\.?\d*)', comp_raw)
            if not matches:
                skipped += 1
                continue
            comp = {}
            for sym, cnt in matches:
                comp[sym] = float(cnt) if cnt else 1.0
            total = sum(comp.values())
            if total < 1e-6:
                skipped += 1
                continue
            comp = {k: v/total for k, v in comp.items()}

            features = extract_features(comp)
            if features is None:
                skipped += 1
                continue

            row = {fn: features[j] for j, fn in enumerate(FEATURE_NAMES)}
            row["formation_energy"] = entry.get("formation_energy_peratom", np.nan)
            row["bulk_modulus"] = entry.get("bulk_modulus_kv", np.nan)
            row["shear_modulus"] = entry.get("shear_modulus_gv", np.nan)
            row["source"] = "jarvis"
            rows.append(row)
        except Exception:
            skipped += 1
            continue
        if (i + 1) % 10000 == 0:
            print(f"  Processed {i+1}/{len(dft_3d)}  ({skipped} skipped)")

    df = pd.DataFrame(rows)
    print(f"  Featurized: {len(df)} entries  skipped: {skipped}  ({time.time()-t0:.0f}s)")
    return df


def load_mp_elastic(api_key=None):
    if not api_key:
        api_key = os.environ.get("MP_API_KEY", "")
    if not api_key:
        print("  [MP] No API key — skipping. Set MP_API_KEY env var.")
        return pd.DataFrame()
    try:
        from mp_api.client import MPRester
        print("  Loading Materials Project elastic data...")
        with MPRester(api_key) as mpr:
            docs = mpr.materials.search(
                fields=["composition", "formation_energy_per_atom", "elasticity"],
                has_props=["elasticity"]
            )
        rows = []
        for doc in docs:
            try:
                comp = {str(el): amt for el, amt in doc.composition.fractional_composition.items()}
                features = extract_features(comp)
                if features is None:
                    continue
                row = {fn: features[j] for j, fn in enumerate(FEATURE_NAMES)}
                row["formation_energy"] = doc.formation_energy_per_atom
                row["bulk_modulus"] = doc.elasticity.k_voigt if doc.elasticity else np.nan
                row["shear_modulus"] = doc.elasticity.g_voigt if doc.elasticity else np.nan
                row["source"] = "mp"
                rows.append(row)
            except Exception:
                continue
        df = pd.DataFrame(rows)
        print(f"  MP: {len(df)} elastic entries loaded")
        return df
    except Exception as e:
        print(f"  MP load failed: {e}")
        return pd.DataFrame()


def train_xgboost(df, targets):
    print("\n[3/5] Training XGBoost models...")
    report = {}
    feature_cols = FEATURE_NAMES

    for target in targets:
        if target not in df.columns:
            continue
        mask = df[target].notna() & np.isfinite(df[target])
        if mask.sum() < 500:
            print(f"  [{target}] too few valid rows ({mask.sum()}), skipping")
            continue

        X = df.loc[mask, feature_cols].fillna(0).values
        y = df.loc[mask, target].values

        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.1,
                                                      random_state=42)
        model = XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            tree_method="hist", random_state=42, n_jobs=-1,
        )
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
                  verbose=False)
        y_pred = model.predict(X_val)
        r2 = r2_score(y_val, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))

        path = os.path.join(MODELS_DIR, f"{target}.joblib")
        joblib.dump(model, path)
        report[target] = {"r2": round(r2, 4), "rmse": round(rmse, 4),
                           "n_train": len(X_tr)}
        print(f"  [{target}]  R2={r2:.3f}  RMSE={rmse:.3f}  n={len(X_tr)}")

    return report


def train_gp_step(df, targets):
    print("\n[4/5] Training Gaussian Process (5k subsample)...")
    X = df[FEATURE_NAMES].fillna(0).values
    y_dict = {t: df[t].values for t in targets if t in df.columns}
    gp_models = train_gp(X, y_dict, subsample=5000)
    save_gp_models(gp_models)
    return gp_models


def train_nn_step(df, targets):
    if not TORCH_AVAILABLE:
        print("\n[5/5] NN skipped: torch not installed")
        return None
    print("\n[5/5] Training multi-task NN...")
    X = df[FEATURE_NAMES].fillna(0).values
    y_dict = {t: df[t].values for t in targets if t in df.columns}
    model = train_multitask_net(X, y_dict, epochs=80)
    save_nn(model)

    mpea_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "data", "mpea_experimental.csv")
    if os.path.exists(mpea_path) and model is not None:
        print("  Fine-tuning on MPEA experimental data...")
        try:
            import pandas as pd
            mpea = pd.read_csv(mpea_path)
            from ml.transfer_learning import fine_tune_on_mpea, save_transfer_model
            X_exp_rows, y_yield, y_uts = [], [], []
            for _, row in mpea.iterrows():
                try:
                    comp_str = row["composition"]
                    import re
                    matches = re.findall(r'([A-Z][a-z]?)(\d*\.?\d*)', comp_str)
                    comp = {}
                    for sym, cnt in matches:
                        comp[sym] = float(cnt) if cnt else 1.0
                    total = sum(comp.values())
                    if total < 1e-6:
                        continue
                    comp = {k: v/total for k, v in comp.items()}
                    feat = extract_features(comp)
                    if feat is None:
                        continue
                    X_exp_rows.append(feat)
                    y_yield.append(float(row.get("yield_strength_MPa", np.nan)))
                    y_uts.append(float(row.get("UTS_MPa", np.nan)))
                except Exception:
                    continue
            if len(X_exp_rows) > 50:
                X_exp = np.array(X_exp_rows)
                transfer = fine_tune_on_mpea(
                    model, X_exp,
                    {"yield_strength": np.array(y_yield),
                     "UTS": np.array(y_uts)},
                    epochs=100
                )
                save_transfer_model(transfer)
        except Exception as e:
            print(f"  Transfer learning failed: {e}")
    else:
        print("  Transfer learning: place MPEA CSV at data/mpea_experimental.csv")

    return model


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mp", action="store_true")
    ap.add_argument("--max-entries", type=int, default=None)
    args = ap.parse_args()

    TARGETS = ["formation_energy", "bulk_modulus", "shear_modulus"]

    dft_3d = load_jarvis()
    if args.max_entries:
        dft_3d = dft_3d[:args.max_entries]

    df = parse_jarvis(dft_3d)

    if not args.skip_mp:
        df_mp = load_mp_elastic()
        if not df_mp.empty:
            df = pd.concat([df, df_mp], ignore_index=True)
            print(f"  Combined dataset: {len(df)} entries")

    report = train_xgboost(df, TARGETS)
    train_gp_step(df, TARGETS)
    train_nn_step(df, TARGETS)

    report_path = os.path.join(MODELS_DIR, "train_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n Training complete. Report: {report_path}")
    print(f" Models saved to: {MODELS_DIR}")
    print(f"\n Next step: python run.py \"316L stainless steel\" --ml --n 50 --top 3")
