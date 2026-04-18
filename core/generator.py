import math
import random
from functools import lru_cache

from core.alloy_db import iter_seed_alloys
from core.elements import available as available_elements, validate_composition, get

APP_ELEMENTS = {
    "fusible_alloy":["Sn","Bi","In","Ga","Pb","Cd","Sb","Zn","Ag","Cu","Tl","Hg"],
    "electronic_alloy":["Cu","Al","Ag","Au","Sn","In","Ga","Si","Ge","Pd","Pt","Ni","Zn","Mg","Sb","As"],
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
    "mg_alloy":     ["Mg","Al","Zn","Mn","Zr","Y","Nd","Ce","Sn"],
    "low_alloy":    ["Fe","C","Mn","Si","Cr","Mo","Ni","V","Nb","Cu"],
    "tool_steel":   ["Fe","C","Cr","Mo","V","W","Mn","Si","Co","Nb"],
}

OPEN_ALLOY_POOL = sorted(
    sym
    for sym in available_elements()
    if sym not in {"He", "Ne", "Ar", "Kr", "Xe", "Rn", "F", "Cl", "Br"}
    and not get(sym).radioactive
)
APP_ELEMENTS["open_alloy"] = OPEN_ALLOY_POOL
APP_ELEMENTS["general_structural"] = APP_ELEMENTS["structural"]


@lru_cache(maxsize=1)
def _catalog_seed_library():
    """Return the authoritative seed priors derived from the catalog loader."""
    seed_library = {}
    for entry in iter_seed_alloys():
        comp = _normalize_wt(entry.get("composition_wt") or {})
        if comp:
            seed_library[entry["key"]] = comp
    return seed_library


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


def _inject_minor_element(wt_comp, element_pool, rng, frac_lo=0.004, frac_hi=0.05):
    candidates = [e for e in element_pool if e not in wt_comp]
    if not candidates:
        return dict(wt_comp)
    add_el = rng.choice(candidates)
    add_frac = rng.uniform(frac_lo, frac_hi)
    scaled = {k: v * (1.0 - add_frac) for k, v in wt_comp.items()}
    scaled[add_el] = add_frac
    return _normalize_wt(scaled)


def _drop_minor_element(wt_comp):
    if len(wt_comp) <= 2:
        return dict(wt_comp)
    drop_el = min(wt_comp.items(), key=lambda item: item[1])[0]
    return _normalize_wt({k: v for k, v in wt_comp.items() if k != drop_el})


def _sample_element_count(app, rng):
    if app in {"fusible_alloy", "electronic_alloy", "cu_alloy"}:
        return rng.choice([2, 2, 3, 3, 4, 4, 5, 6])
    if app == "open_alloy":
        return rng.choice([3, 4, 5, 6, 7, 8, 9, 10])
    if app == "hea":
        return rng.choice([4, 5, 5, 6, 6, 7, 8])
    return rng.choice([3, 4, 4, 5, 5, 6, 7, 8])


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
    elif any(w in q for w in ["fuse alloy", "fuse wire", "fusible", "fusible wire", "low melting", "low-melting", "solder", "solder alloy", "thermal fuse", "fusible link", "liquid metal"]):
        app = "fusible_alloy"
    elif any(w in q for w in ["chip alloy", "chip package", "semiconductor", "interconnect", "bond wire", "wire bond", "solder bump", "leadframe", "microelectronics", "electronic packaging"]):
        app = "electronic_alloy"
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
    elif any(w in q for w in ["magnesium", "mg alloy", "az31", "az91", "lightweight mg"]):
        app = "mg_alloy"
    elif any(w in q for w in ["4140", "4340", "low alloy", "engineering steel", "alloy steel"]):
        app = "low_alloy"
    elif any(w in q for w in ["tool steel", "die steel", "h13", "m2", "d2", "hss"]):
        app = "tool_steel"
    elif any(w in q for w in ["plain carbon steel", "carbon steel", "mild steel"]):
        app = "carbon_steel"
    else:
        app = "structural"

    base_mandatory = {
        "fusible_alloy": {"Sn": (0.30, 0.80)},
        "electronic_alloy": {"Cu": (0.35, 0.90)},
        "stainless": {"Fe": (0.50, 0.80), "Cr": (0.12, 0.28)},
        "superalloy": {"Ni": (0.45, 0.75)},
        "ti_alloy": {"Ti": (0.70, 0.95)},
        "al_alloy": {"Al": (0.80, 0.97)},
        "cu_alloy": {"Cu": (0.60, 0.99)},
        "nuclear": {"Zr": (0.80, 0.99)},
        "biomedical": {"Ti": (0.55, 0.90)},
        "carbon_steel": {"Fe": (0.95, 0.99), "C": (0.001, 0.01)},
        "mg_alloy": {"Mg": (0.85, 0.97)},
        "low_alloy": {"Fe": (0.90, 0.97)},
        "tool_steel": {"Fe": (0.75, 0.95)},
        "open_alloy": {},
        "general_structural": {"Fe": (0.50, 0.85)},
        "structural": {"Fe": (0.50, 0.85)},
    }.get(app, {})

    if app == "fusible_alloy":
        if any(w in q for w in ["lead-free", "pb-free", "rohs"]):
            base_mandatory = {"Sn": (0.40, 0.85)}
        elif any(w in q for w in ["liquid metal", "gallium"]):
            base_mandatory = {"Ga": (0.40, 0.85)}
        elif any(w in q for w in ["thermal fuse", "fusible", "fuse alloy"]):
            base_mandatory = {"Bi": (0.30, 0.80)}
    elif app == "electronic_alloy":
        if any(w in q for w in ["semiconductor", "wafer"]):
            base_mandatory = {"Si": (0.40, 0.90)}
        elif any(w in q for w in ["solder bump", "reflow", "bga", "package"]):
            base_mandatory = {"Sn": (0.40, 0.90)}
        elif any(w in q for w in ["bond wire", "wire bond"]):
            base_mandatory = {"Cu": (0.45, 0.95)}
    elif app == "cu_alloy":
        if any(w in q for w in ["aluminum bronze", "aluminium bronze"]):
            base_mandatory = {"Cu": (0.75, 0.95), "Al": (0.05, 0.14)}
        elif "phosphor bronze" in q:
            base_mandatory = {"Cu": (0.82, 0.97), "Sn": (0.03, 0.12), "P": (0.002, 0.02)}
        elif "silicon bronze" in q:
            base_mandatory = {"Cu": (0.85, 0.97), "Si": (0.01, 0.05)}
        elif "bronze" in q:
            base_mandatory = {"Cu": (0.76, 0.94), "Sn": (0.06, 0.16)}
        elif "brass" in q:
            base_mandatory = {"Cu": (0.55, 0.80), "Zn": (0.22, 0.45)}

    elem_pool = APP_ELEMENTS.get(app, APP_ELEMENTS["structural"])

    candidates_wt = []

    if base_composition:
        base_norm = _normalize_wt(base_composition)
        if base_norm:
            candidates_wt.append(base_norm)
            n_local = max(6, n // 3)
            for _ in range(n_local):
                candidates_wt.append(_perturb(base_norm, sigma=0.03, rng=rng))
                candidates_wt.append(_perturb(base_norm, sigma=0.07, rng=rng))
                candidates_wt.append(_inject_minor_element(_perturb(base_norm, sigma=0.04, rng=rng), elem_pool, rng))
                candidates_wt.append(_drop_minor_element(_perturb(base_norm, sigma=0.05, rng=rng)))
    else:
        seed_library = _catalog_seed_library()
        relevant_keys = [k for k, wt in seed_library.items() if _is_relevant(wt, app)]
        if not relevant_keys:
            relevant_keys = list(seed_library.keys())

        n_per_base = max(2, (n // 2) // max(len(relevant_keys), 1))
        for base_key in relevant_keys:
            wt_base = seed_library[base_key]
            candidates_wt.append(wt_base)
            for _ in range(n_per_base):
                candidates_wt.append(_perturb(wt_base, sigma=0.03, rng=rng))
                candidates_wt.append(_inject_minor_element(_perturb(wt_base, sigma=0.05, rng=rng), elem_pool, rng))
                candidates_wt.append(_drop_minor_element(_perturb(wt_base, sigma=0.04, rng=rng)))

    n_random = max(n, 50) if base_composition else max(n - len(candidates_wt), 50)
    for _ in range(n_random):
        n_el = _sample_element_count(app, rng)
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
        n_el = _sample_element_count(app, rng)
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


def _is_relevant(weight_map, app):
    WT = weight_map
    if app == "fusible_alloy": return WT.get("Sn", 0) + WT.get("Bi", 0) + WT.get("In", 0) + WT.get("Ga", 0) + WT.get("Pb", 0) > 0.35
    if app == "electronic_alloy": return WT.get("Cu", 0) + WT.get("Sn", 0) + WT.get("Al", 0) + WT.get("Ag", 0) + WT.get("Au", 0) + WT.get("Si", 0) + WT.get("Ge", 0) > 0.35
    if app == "stainless":   return WT.get("Fe", 0) > 0.4 and WT.get("Cr", 0) > 0.1
    if app == "superalloy":  return WT.get("Ni", 0) > 0.3 or WT.get("Co", 0) > 0.3
    if app == "ti_alloy":    return WT.get("Ti", 0) > 0.5
    if app == "al_alloy":    return WT.get("Al", 0) > 0.5
    if app == "nuclear":     return WT.get("Zr", 0) > 0.5
    if app == "hea":         return len(WT) >= 4
    if app == "refractory":  return WT.get("W", 0) + WT.get("Mo", 0) + WT.get("Nb", 0) > 0.2
    if app == "biomedical":  return WT.get("Ti", 0) > 0.5
    if app == "carbon_steel":return WT.get("Fe", 0) > 0.90
    if app == "mg_alloy":    return WT.get("Mg", 0) > 0.8
    if app == "low_alloy":   return WT.get("Fe", 0) > 0.85 and WT.get("Cr", 0) < 0.05
    if app == "tool_steel":  return WT.get("Fe", 0) > 0.7 and WT.get("C", 0) > 0.003
    if app == "cu_alloy":    return WT.get("Cu", 0) > 0.5
    return WT.get("Fe", 0) > 0.3
