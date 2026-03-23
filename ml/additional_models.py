
import os, json, numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
TARGETS = ["formation_energy", "bulk_modulus", "shear_modulus"]


class RFModel:
    NAME = "random_forest"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, n_estimators=200, max_depth=12):
        from sklearn.ensemble import RandomForestRegressor
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 20:
                continue
            m = RandomForestRegressor(
                n_estimators=n_estimators, max_depth=max_depth,
                min_samples_leaf=3, n_jobs=-1, random_state=42,
            )
            m.fit(X[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        for target, m in self.models.items():
            results[target] = float(m.predict(X.reshape(1, -1))[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"rf_{target}.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"rf_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)


class ExtraTreesModel:
    NAME = "extra_trees"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, n_estimators=200, max_depth=15):
        from sklearn.ensemble import ExtraTreesRegressor
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 20:
                continue
            m = ExtraTreesRegressor(
                n_estimators=n_estimators, max_depth=max_depth,
                min_samples_leaf=2, n_jobs=-1, random_state=42,
            )
            m.fit(X[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        for target, m in self.models.items():
            results[target] = float(m.predict(X.reshape(1, -1))[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"et_{target}.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"et_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)


class LightGBMModel:
    NAME = "lightgbm"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, n_estimators=300, max_depth=8, lr=0.05):
        try:
            import lightgbm as lgb
        except ImportError:
            return

        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 20:
                continue
            m = lgb.LGBMRegressor(
                n_estimators=n_estimators, max_depth=max_depth,
                learning_rate=lr, min_child_samples=5,
                subsample=0.8, colsample_bytree=0.8,
                random_state=42, verbose=-1,
            )
            m.fit(X[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        for target, m in self.models.items():
            results[target] = float(m.predict(X.reshape(1, -1))[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"lgbm_{target}.joblib"))

    def load(self):
        try:
            import joblib
            for target in TARGETS:
                p = os.path.join(MODELS_DIR, f"lgbm_{target}.joblib")
                if os.path.exists(p):
                    self.models[target] = joblib.load(p)
        except Exception:
            pass


class RidgeModel:
    NAME = "ridge"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, alpha=1.0):
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler().fit(X)
        X_s = self.scaler.transform(X)
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 10:
                continue
            m = Ridge(alpha=alpha)
            m.fit(X_s[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        if not hasattr(self, 'scaler'):
            return results
        X_s = self.scaler.transform(X.reshape(1, -1))
        for target, m in self.models.items():
            results[target] = float(m.predict(X_s)[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"ridge_{target}.joblib"))
        if hasattr(self, 'scaler'):
            joblib.dump(self.scaler, os.path.join(MODELS_DIR, "ridge_scaler.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"ridge_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)
        sp = os.path.join(MODELS_DIR, "ridge_scaler.joblib")
        if os.path.exists(sp):
            self.scaler = joblib.load(sp)


class KNNModel:
    NAME = "knn"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, n_neighbors=7):
        from sklearn.neighbors import KNeighborsRegressor
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler().fit(X)
        X_s = self.scaler.transform(X)
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < n_neighbors + 1:
                continue
            m = KNeighborsRegressor(n_neighbors=n_neighbors, weights='distance')
            m.fit(X_s[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        if not hasattr(self, 'scaler'):
            return results
        X_s = self.scaler.transform(X.reshape(1, -1))
        for target, m in self.models.items():
            results[target] = float(m.predict(X_s)[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"knn_{target}.joblib"))
        if hasattr(self, 'scaler'):
            joblib.dump(self.scaler, os.path.join(MODELS_DIR, "knn_scaler.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"knn_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)
        sp = os.path.join(MODELS_DIR, "knn_scaler.joblib")
        if os.path.exists(sp):
            self.scaler = joblib.load(sp)


class SVRModel:
    NAME = "svr"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, C=10.0, epsilon=0.1):
        from sklearn.svm import SVR
        from sklearn.preprocessing import StandardScaler
        self.scaler_X = StandardScaler().fit(X)
        X_s = self.scaler_X.transform(X)
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 20:
                continue
            m = SVR(kernel='rbf', C=C, epsilon=epsilon)
            m.fit(X_s[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        if not hasattr(self, 'scaler_X'):
            return results
        X_s = self.scaler_X.transform(X.reshape(1, -1))
        for target, m in self.models.items():
            results[target] = float(m.predict(X_s)[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"svr_{target}.joblib"))
        if hasattr(self, 'scaler_X'):
            joblib.dump(self.scaler_X, os.path.join(MODELS_DIR, "svr_scaler.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"svr_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)
        sp = os.path.join(MODELS_DIR, "svr_scaler.joblib")
        if os.path.exists(sp):
            self.scaler_X = joblib.load(sp)


class AdaBoostModel:
    NAME = "adaboost"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, n_estimators=100, lr=0.1):
        from sklearn.ensemble import AdaBoostRegressor
        from sklearn.tree import DecisionTreeRegressor
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 20:
                continue
            base = DecisionTreeRegressor(max_depth=4)
            m = AdaBoostRegressor(
                estimator=base, n_estimators=n_estimators,
                learning_rate=lr, random_state=42,
            )
            m.fit(X[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        for target, m in self.models.items():
            results[target] = float(m.predict(X.reshape(1, -1))[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"ada_{target}.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"ada_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)


class LassoModel:
    NAME = "lasso"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, alpha=0.1):
        from sklearn.linear_model import Lasso
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler().fit(X)
        X_s = self.scaler.transform(X)
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 10:
                continue
            m = Lasso(alpha=alpha, max_iter=5000)
            m.fit(X_s[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        if not hasattr(self, 'scaler'):
            return results
        X_s = self.scaler.transform(X.reshape(1, -1))
        for target, m in self.models.items():
            results[target] = float(m.predict(X_s)[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"lasso_{target}.joblib"))
        if hasattr(self, 'scaler'):
            joblib.dump(self.scaler, os.path.join(MODELS_DIR, "lasso_scaler.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"lasso_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)
        sp = os.path.join(MODELS_DIR, "lasso_scaler.joblib")
        if os.path.exists(sp):
            self.scaler = joblib.load(sp)


class ElasticNetModel:
    NAME = "elasticnet"

    def __init__(self):
        self.models = {}

    def train(self, X, Y_dict, alpha=0.1, l1_ratio=0.5):
        from sklearn.linear_model import ElasticNet
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler().fit(X)
        X_s = self.scaler.transform(X)
        for target, y in Y_dict.items():
            mask = ~np.isnan(y)
            if mask.sum() < 10:
                continue
            m = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=5000)
            m.fit(X_s[mask], y[mask])
            self.models[target] = m

    def predict(self, X):
        results = {}
        if not hasattr(self, 'scaler'):
            return results
        X_s = self.scaler.transform(X.reshape(1, -1))
        for target, m in self.models.items():
            results[target] = float(m.predict(X_s)[0])
        return results

    def save(self):
        import joblib
        for target, m in self.models.items():
            joblib.dump(m, os.path.join(MODELS_DIR, f"enet_{target}.joblib"))
        if hasattr(self, 'scaler'):
            joblib.dump(self.scaler, os.path.join(MODELS_DIR, "enet_scaler.joblib"))

    def load(self):
        import joblib
        for target in TARGETS:
            p = os.path.join(MODELS_DIR, f"enet_{target}.joblib")
            if os.path.exists(p):
                self.models[target] = joblib.load(p)
        sp = os.path.join(MODELS_DIR, "enet_scaler.joblib")
        if os.path.exists(sp):
            self.scaler = joblib.load(sp)


ALL_MODEL_CLASSES = [
    RFModel, ExtraTreesModel, LightGBMModel, RidgeModel,
    KNNModel, SVRModel, AdaBoostModel, LassoModel, ElasticNetModel,
]

def get_all_model_names():
    return [cls.NAME for cls in ALL_MODEL_CLASSES]

def create_model(name):
    for cls in ALL_MODEL_CLASSES:
        if cls.NAME == name:
            return cls()
    raise ValueError(f"Unknown model: {name}")
