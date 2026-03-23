
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.elements import get
from physics.base import norm, delta_size, vec, delta_S_mix, delta_H_mix, omega_param

PROP_NAMES = [
    "Tm",
    "E",
    "G",
    "B",
    "nu",
    "density",
    "thermal_cond",
    "thermal_exp",
    "electronegativity",
    "atomic_mass",
    "valence_e",
    "radius",
]

FEATURE_NAMES = (
    [f"{p}_{stat}" for p in PROP_NAMES for stat in ("mean","std","min","max")]
    + ["delta", "VEC", "dSmix", "dHmix", "omega", "n_elements",
       "max_conc", "entropy_norm",
       "struct_fcc", "struct_bcc", "struct_mixed"]
)
N_FEATURES = len(FEATURE_NAMES)


def _get_prop(sym: str, prop: str) -> float | None:
    el = get(sym)
    if el is None:
        return None
    val = getattr(el, prop, None)
    if prop == "density" and val is not None and val < 1.0:
        return None
    return val


def extract(comp: dict, fallback: dict | None = None) -> list[float]:
    c = norm(comp)
    syms = list(c.keys())
    fracs = [c[s] for s in syms]

    stat_feats = []
    for prop in PROP_NAMES:
        vals = []
        weights = []
        for sym, xi in zip(syms, fracs):
            v = _get_prop(sym, prop)
            if v is not None:
                vals.append(v)
                weights.append(xi)

        if not vals:
            fb = (fallback or {}).get(prop, 0.0)
            stat_feats.extend([fb, 0.0, fb, fb])
            continue

        w_total = sum(weights)
        w_total = max(w_total, 1e-12)
        wmean = sum(v * w / w_total for v, w in zip(vals, weights))

        wstd = math.sqrt(
            sum(w * (v - wmean) ** 2 for v, w in zip(vals, weights)) / w_total
        )

        stat_feats.extend([wmean, wstd, min(vals), max(vals)])

    try:
        delt = delta_size(c)
    except Exception:
        delt = 0.0

    try:
        vec_val = vec(c)
    except Exception:
        vec_val = 0.0

    try:
        ds = delta_S_mix(c)
    except Exception:
        ds = 0.0

    try:
        dh = delta_H_mix(c)
        dh = dh if dh is not None else 0.0
    except Exception:
        dh = 0.0

    try:
        om = omega_param(c)
        om = om if om is not None else 0.0
    except Exception:
        om = 0.0

    n_el = len(syms)
    max_xi = max(fracs)
    import math as _m
    if n_el > 1:
        ent_norm = abs(ds) / (8.31446 * _m.log(n_el))
    else:
        ent_norm = 0.0

    phys_feats = [delt, vec_val, abs(ds), dh, om, n_el, max_xi, ent_norm]

    is_fcc   = 1.0 if vec_val >= 8.0  else 0.0
    is_bcc   = 1.0 if vec_val <  6.87 else 0.0
    is_mixed = 1.0 if 6.87 <= vec_val < 8.0 else 0.0
    struct_feats = [is_fcc, is_bcc, is_mixed]

    features = stat_feats + phys_feats + struct_feats
    assert len(features) == N_FEATURES, f"Expected {N_FEATURES}, got {len(features)}"
    return features


def build_fallback(training_rows: list[dict]) -> dict:
    from statistics import median
    prop_vals = {p: [] for p in PROP_NAMES}
    for comp in training_rows:
        c = norm(comp)
        for sym in c:
            for prop in PROP_NAMES:
                v = _get_prop(sym, prop)
                if v is not None:
                    prop_vals[prop].append(v)
    return {p: median(vals) if vals else 0.0 for p, vals in prop_vals.items()}
