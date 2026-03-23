import os, sys
import numpy as np
import joblib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from sklearn.preprocessing import StandardScaler

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
GP_SUBSAMPLE = 5000
TARGETS = ["formation_energy", "bulk_modulus", "shear_modulus"]

def build_kernel():
    return (ConstantKernel(1.0, (1e-3, 1e3))
            * Matern(length_scale=1.0, nu=2.5)
            + WhiteKernel(noise_level=0.1))

def train_gp(X, y_dict, subsample=GP_SUBSAMPLE):
    rng = np.random.RandomState(42)
    n = min(subsample, len(X))
    idx = rng.choice(len(X), n, replace=False)
    X_sub = X[idx]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_sub)
    models = {}
    for target in TARGETS:
        if target not in y_dict:
            continue
        y = y_dict[target][idx]
        mask = np.isfinite(y)
        if mask.sum() < 100:
            continue
        gp = GaussianProcessRegressor(kernel=build_kernel(), n_restarts_optimizer=3,
                                       normalize_y=True, alpha=1e-6)
        print(f"  GP [{target}]: fitting {mask.sum()} pts...")
        gp.fit(X_scaled[mask], y[mask])
        models[target] = {"gp": gp, "scaler": scaler}
        print(f"  GP [{target}]: kernel = {gp.kernel_}")
    return models

def save_gp_models(models):
    os.makedirs(MODELS_DIR, exist_ok=True)
    for target, m in models.items():
        path = os.path.join(MODELS_DIR, f"gp_{target}.joblib")
        joblib.dump(m, path)
        print(f"  Saved {path}")

def load_gp_models():
    models = {}
    for target in TARGETS:
        path = os.path.join(MODELS_DIR, f"gp_{target}.joblib")
        if os.path.exists(path):
            models[target] = joblib.load(path)
    return models

def predict_with_uncertainty(models, X):
    result = {}
    for target, m in models.items():
        Xs = m["scaler"].transform(X.reshape(1, -1))
        mean, sigma = m["gp"].predict(Xs, return_std=True)
        result[target] = {"mean": float(mean[0]), "sigma": float(sigma[0])}
    return result
