import random, math
from core.elements import validate_composition, get


ALLOY_BASES_WT = {
    "304SS":     {"Fe":0.705,"Cr":0.185,"Ni":0.092,"Mn":0.018},
    "316L":      {"Fe":0.677,"Cr":0.170,"Ni":0.120,"Mo":0.022,"Mn":0.011},
    "316H":      {"Fe":0.670,"Cr":0.170,"Ni":0.120,"Mo":0.025,"C":0.005,"Mn":0.010},
    "2205DSS":   {"Fe":0.680,"Cr":0.220,"Ni":0.055,"Mo":0.031,"N":0.0014,"Mn":0.0126},
    "2507SDSS":  {"Fe":0.640,"Cr":0.250,"Ni":0.070,"Mo":0.040,"N":0.0027},
    "IN718":     {"Ni":0.525,"Cr":0.190,"Fe":0.185,"Nb":0.052,"Mo":0.030,"Al":0.005,"Ti":0.009,"Co":0.004},
    "IN625":     {"Ni":0.614,"Cr":0.215,"Mo":0.090,"Fe":0.030,"Nb":0.035,"Al":0.004,"Ti":0.002,"C":0.0005,"Mn":0.002,"Si":0.001},
    "Waspaloy":  {"Ni":0.575,"Cr":0.190,"Co":0.135,"Mo":0.043,"Al":0.014,"Ti":0.030,"Fe":0.003,"B":0.0005,"Zr":0.0005},
    "CM247LC":   {"Ni":0.590,"Cr":0.082,"Co":0.094,"W":0.095,"Al":0.056,"Ta":0.030,"Hf":0.015,"Mo":0.005,"C":0.0007,"B":0.0003},
    "Stellite6": {"Co":0.600,"Cr":0.280,"W":0.040,"C":0.012,"Ni":0.025,"Fe":0.015,"Si":0.008,"Mn":0.010},
    "Haynes25":  {"Co":0.500,"Cr":0.200,"W":0.150,"Ni":0.100,"Fe":0.030,"C":0.010,"Mn":0.010},
    "Ti-6Al-4V": {"Ti":0.900,"Al":0.060,"V":0.040},
    "Ti-6242":   {"Ti":0.880,"Al":0.060,"Zr":0.020,"Sn":0.020,"Mo":0.020},
    "Ti-15V-3Cr":{"Ti":0.820,"V":0.150,"Cr":0.030},
    "Ti-B21S":   {"Ti":0.790,"Mo":0.150,"Nb":0.030,"Al":0.030},
    "AA2024-T3": {"Al":0.932,"Cu":0.044,"Mg":0.015,"Mn":0.006,"Fe":0.002,"Si":0.001},
    "AA6061-T6": {"Al":0.969,"Mg":0.010,"Si":0.006,"Cu":0.003,"Mn":0.0015,"Cr":0.002},
    "AA7075-T6": {"Al":0.899,"Zn":0.056,"Mg":0.025,"Cu":0.016,"Cr":0.002,"Mn":0.001,"Si":0.001},
    "AA5083":    {"Al":0.944,"Mg":0.043,"Mn":0.007,"Cr":0.001,"Fe":0.004,"Si":0.001},
    "Cantor":    {"Co":0.200,"Cr":0.200,"Fe":0.200,"Mn":0.200,"Ni":0.200},
    "AlCoCrFeNi":{"Al":0.200,"Co":0.200,"Cr":0.200,"Fe":0.200,"Ni":0.200},
    "TiZrNbMoV": {"Ti":0.200,"Zr":0.200,"Nb":0.200,"Mo":0.200,"V":0.200},
    "CrMoNbVW":  {"Cr":0.200,"Mo":0.200,"Nb":0.200,"V":0.200,"W":0.200},
    "NbMoTaW":   {"Nb":0.250,"Mo":0.250,"Ta":0.250,"W":0.250},
    "HfNbTaTiZr":{"Hf":0.200,"Nb":0.200,"Ta":0.200,"Ti":0.200,"Zr":0.200},
    "AZ31B":     {"Mg":0.960,"Al":0.030,"Zn":0.010},
    "WE43":      {"Mg":0.945,"Y":0.040,"Zr":0.004,"Nd":0.008},
    "CuZn30":    {"Cu":0.700,"Zn":0.300},
    "AlBronze":  {"Cu":0.900,"Al":0.080,"Fe":0.020},
    "Zircaloy4": {"Zr":0.981,"Sn":0.015,"Fe":0.002,"Cr":0.001,"O":0.001},
}

APP_ELEMENTS = {
    "stainless":    ["Fe","Cr","Ni","Mo","Mn","N","Si","Cu","Nb","Ti"],
    "structural":   ["Fe","Cr","Ni","Mo","Mn","V","Nb","C","Si"],
    "superalloy":   ["Ni","Co","Cr","Al","Ti","Mo","W","Nb","Re","Ta","Hf"],
    "ti_alloy":     ["Ti","Al","V","Mo","Nb","Zr","Sn","Fe"],
    "al_alloy":     ["Al","Cu","Mg","Si","Zn","Mn","Cr","Fe","Ti"],
    "hea":          ["Fe","Co","Cr","Ni","Mn","Al","Ti","Cu","Mo","V"],
    "refractory":   ["W","Mo","Nb","Ta","V","Cr","Re","Hf","Zr","Ti"],
    "nuclear":      ["Zr","Nb","Mo","Cr","Fe","Ni","V","Ti","W"],
    "biomedical":   ["Ti","Nb","Ta","Zr","Mo","Co","Cr","Fe"],
    "carbon_steel": ["Fe","C","Mn","Si","S","P"],
    "cu_alloy":     ["Cu","Zn","Al","Sn","Ni","Mn","Fe","Si"],
}

OPEN_ALLOY_POOL = sorted(
    set(sym for pool in APP_ELEMENTS.values() for sym in pool)
    | set(sym for comp in ALLOY_BASES_WT.values() for sym in comp.keys())
)
APP_ELEMENTS["open_alloy"] = OPEN_ALLOY_POOL
APP_ELEMENTS["general_structural"] = APP_ELEMENTS["structural"]


def _wt_to_mol(wt_dict):
    mol = {s: wt_dict[s] / get(s).atomic_mass for s in wt_dict}
    total = sum(mol.values())
    return {s: v / total for s, v in mol.items()}


def _normalize_wt(wt_comp):
    total = sum(v for v in wt_comp.values() if v > 0)
    if total <= 0:
        return {}
    return {k: v / total for k, v in wt_comp.items() if v > 1e-6}


def _perturb(wt_comp, sigma=0.02, rng=None):
    rng = rng or random.Random()
    keys = list(wt_comp.keys())
    new = {k: max(1e-4, wt_comp[k] + rng.gauss(0, sigma * wt_comp[k])) for k in keys}
    total = sum(new.values())
    return {k: v / total for k, v in new.items()}


def _random_composition(element_pool, n_elements, base_mandatory, rng):
    remaining_pool = [e for e in element_pool if e not in base_mandatory]
    n_extra = max(0, n_elements - len(base_mandatory))
    n_extra = min(n_extra, len(remaining_pool))
    extra = rng.sample(remaining_pool, n_extra)

    all_elems = list(base_mandatory.keys()) + extra
    wt = {}
    remaining_budget = 1.0
    for e, frac_range in base_mandatory.items():
        lo, hi = frac_range
        f = rng.uniform(lo, hi)
        wt[e] = f
        remaining_budget -= f

    if extra and remaining_budget > 0:
        for e in extra[:-1]:
            f = rng.uniform(0.005, remaining_budget * 0.6)
            wt[e] = f
            remaining_budget -= f
            if remaining_budget < 0.005:
                break
        if extra:
            wt[extra[-1]] = max(0.001, remaining_budget)

    total = sum(wt.values())
    return {k: v / total for k, v in wt.items() if v > 1e-4}


def generate(query: str, n: int = 300, seed: int = 42,
             only_elements: list = None,
             must_include: list = None,
             exclude_elements: list = None,
             application: str = "",
             base_composition: dict = None) -> list:
    rng = random.Random(seed)
    q = query.lower()
    must_include = must_include or []
    exclude_elements = exclude_elements or []

    if only_elements:
        return _generate_within_elements(only_elements, must_include, n, rng)

    if application:
        app = application
    elif any(w in q for w in ["any alloy", "any composition", "no restriction", "unrestricted", "any elements"]):
        app = "open_alloy"
    elif any(w in q for w in ["stainless", "316", "304", "duplex", "marine", "corrosion", "bridge", "chloride"]):
        app = "stainless"
    elif any(w in q for w in ["superalloy", "turbine", "jet", "nickel", "in718", "inconel", "creep"]):
        app = "superalloy"
    elif any(w in q for w in ["titanium", "ti-6", "ti64", "ti alloy", "aero"]):
        app = "ti_alloy"
    elif any(w in q for w in ["aluminium", "aluminum", "al alloy", "lightweight", "duralumin"]):
        app = "al_alloy"
    elif any(w in q for w in ["copper", "brass", "bronze", "cu alloy", "wire", "busbar"]):
        app = "cu_alloy"
    elif any(w in q for w in ["nuclear", "reactor", "cladding", "zircaloy", "zirconium"]):
        app = "nuclear"
    elif any(w in q for w in ["hea", "high entropy", "cantor", "multiprincipal"]):
        app = "hea"
    elif any(w in q for w in ["refractory", "high temperature", ">1000", "1200", "1500"]):
        app = "refractory"
    elif any(w in q for w in ["biomedical", "implant", "surgical", "bone", "hip", "dental"]):
        app = "biomedical"
    elif any(w in q for w in ["plain carbon steel", "carbon steel", "mild steel"]):
        app = "carbon_steel"
    else:
        app = "structural"

    base_mandatory = {
        "stainless": {"Fe": (0.50, 0.80), "Cr": (0.12, 0.28)},
        "superalloy": {"Ni": (0.45, 0.75)},
        "ti_alloy": {"Ti": (0.70, 0.95)},
        "al_alloy": {"Al": (0.80, 0.97)},
        "cu_alloy": {"Cu": (0.60, 0.99)},
        "nuclear": {"Zr": (0.80, 0.99)},
        "biomedical": {"Ti": (0.55, 0.90)},
        "carbon_steel": {"Fe": (0.95, 0.99), "C": (0.001, 0.01)},
        "open_alloy": {},
        "general_structural": {"Fe": (0.50, 0.85)},
        "structural": {"Fe": (0.50, 0.85)},
    }.get(app, {})

    elem_pool = APP_ELEMENTS.get(app, APP_ELEMENTS["structural"])

    candidates_wt = []

    if base_composition:
        base_norm = _normalize_wt(base_composition)
        if base_norm:
            candidates_wt.append(base_norm)
            n_local = max(6, n // 3)
            for _ in range(n_local):
                candidates_wt.append(_perturb(base_norm, sigma=0.025, rng=rng))
                candidates_wt.append(_perturb(base_norm, sigma=0.05, rng=rng))
    else:
        relevant_keys = [k for k in ALLOY_BASES_WT if _is_relevant(k, app)]
        if not relevant_keys:
            relevant_keys = list(ALLOY_BASES_WT.keys())

        n_per_base = max(2, (n // 2) // max(len(relevant_keys), 1))
        for base_key in relevant_keys:
            wt_base = ALLOY_BASES_WT[base_key]
            candidates_wt.append(wt_base)
            for _ in range(n_per_base):
                candidates_wt.append(_perturb(wt_base, sigma=0.025, rng=rng))

    n_random = max(n, 50) if base_composition else max(n - len(candidates_wt), 50)
    for _ in range(n_random):
        n_el = rng.choice([3, 4, 4, 5, 5, 5, 6])
        wt_new = _random_composition(elem_pool, n_el, base_mandatory, rng)
        candidates_wt.append(wt_new)

    if app == "hea":
        for n_el in [4, 5, 5, 5, 6]:
            chosen = rng.sample(elem_pool, min(n_el, len(elem_pool)))
            eq = {e: 1.0/len(chosen) for e in chosen}
            candidates_wt.append(eq)

    if exclude_elements:
        candidates_wt = [
            {s: f for s, f in comp.items() if s not in exclude_elements}
            for comp in candidates_wt
        ]
        candidates_wt = [
            {s: f / sum(c.values()) for s, f in c.items()}
            for c in candidates_wt if sum(c.values()) > 0.5
        ]

    if must_include:
        strict = [c for c in candidates_wt if all(c.get(e, 0) > 0.005 for e in must_include)]
        if strict:
            candidates_wt = strict
        else:
            min_hits = max(1, len(must_include) // 2)
            relaxed = [
                c for c in candidates_wt
                if sum(1 for e in must_include if c.get(e, 0) > 0.003) >= min_hits
            ]
            if relaxed:
                candidates_wt = relaxed

    if base_composition:
        base_norm = _normalize_wt(base_composition)
        rng.shuffle(candidates_wt)
        if base_norm:
            candidates_wt.insert(0, base_norm)

    candidates_mol = []
    seen = set()
    for wt_comp in candidates_wt:
        try:
            mol_comp = _wt_to_mol(wt_comp)
            mol_comp = validate_composition(mol_comp)
            key = tuple(sorted((s, round(f, 3)) for s, f in mol_comp.items()))
            if key not in seen:
                seen.add(key)
                candidates_mol.append(mol_comp)
                if len(candidates_mol) >= n:
                    break
        except Exception:
            continue

    while len(candidates_mol) < n:
        n_el = rng.choice([3, 4, 5])
        wt_new = _random_composition(elem_pool, n_el, base_mandatory, rng)
        try:
            mol_comp = validate_composition(_wt_to_mol(wt_new))
            candidates_mol.append(mol_comp)
        except Exception:
            pass

    return candidates_mol[:n]


def _generate_within_elements(allowed, must_include, n, rng):
    if len(allowed) < 2:
        raise ValueError(f"Need at least 2 allowed elements, got: {allowed}")

    candidates = []
    n_allowed = len(allowed)

    for i in range(n * 3):
        if len(candidates) >= n:
            break
        n_use = min(rng.randint(max(2, len(must_include)), n_allowed), n_allowed)
        chosen = list(must_include)
        remaining = [e for e in allowed if e not in chosen]
        extra = min(n_use - len(chosen), len(remaining))
        if extra > 0:
            chosen.extend(rng.sample(remaining, extra))
        if len(chosen) < 2:
            continue

        fracs = {}
        if must_include:
            for e in must_include:
                fracs[e] = rng.uniform(0.05, 0.50)

        others = [e for e in chosen if e not in fracs]
        rem = 1.0 - sum(fracs.values())
        if rem < 0.01 * len(others):
            continue

        for e in others[:-1]:
            f = rng.uniform(0.01, rem * 0.7)
            fracs[e] = f
            rem -= f
        if others:
            fracs[others[-1]] = max(0.001, rem)

        try:
            mol = validate_composition(fracs)
            candidates.append(mol)
        except Exception:
            continue

    if len(allowed) >= 2:
        for n_el in range(2, min(len(allowed)+1, 7)):
            for _ in range(5):
                extra_count = min(n_el - len(must_include),
                                 len(allowed) - len(must_include))
                if extra_count < 0:
                    continue
                chosen = list(must_include) + rng.sample(
                    [e for e in allowed if e not in must_include],
                    extra_count
                )
                if len(chosen) < 2:
                    continue
                eq = {e: 1.0/len(chosen) for e in chosen}
                try:
                    candidates.append(validate_composition(eq))
                except Exception:
                    pass

    return candidates[:n]


def _is_relevant(base_key, app):
    WT = ALLOY_BASES_WT[base_key]
    if app == "stainless":   return WT.get("Fe", 0) > 0.4 and WT.get("Cr", 0) > 0.1
    if app == "superalloy":  return WT.get("Ni", 0) > 0.3 or WT.get("Co", 0) > 0.3
    if app == "ti_alloy":    return WT.get("Ti", 0) > 0.5
    if app == "al_alloy":    return WT.get("Al", 0) > 0.5
    if app == "nuclear":     return WT.get("Zr", 0) > 0.5
    if app == "hea":         return len(WT) >= 4
    if app == "refractory":  return WT.get("W", 0) + WT.get("Mo", 0) + WT.get("Nb", 0) > 0.2
    if app == "biomedical":  return WT.get("Ti", 0) > 0.5
    if app == "carbon_steel":return WT.get("Fe", 0) > 0.90
    return WT.get("Fe", 0) > 0.3
