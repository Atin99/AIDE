import importlib, time, traceback, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import DomainResult, INFO, norm
from core.elements import validate_composition

DOMAIN_MODULES = [
    ("physics.thermo",                1.5),
    ("physics.hume_rothery",          1.3),
    ("physics.mechanical",            1.2),
    ("physics.corrosion",             1.4),
    ("physics.oxidation",             1.2),
    ("physics.radiation",             1.0),
    ("physics.weldability",           1.0),
    ("physics.creep",                 1.1),
    ("physics.fatigue",               1.1),
    ("physics.grain_boundary",        1.0),
    ("physics.hydrogen",              1.0),
    ("physics.magnetic",              0.8),
    ("physics.thermal",               1.0),
    ("physics.regulatory",            1.2),
    ("physics.electronic_structure",  0.9),
    ("physics.superconductivity",     0.7),
    ("physics.phase_stability",       1.3),
    ("physics.plasticity",            1.1),
    ("physics.diffusion",             0.9),
    ("physics.surface_energy",        0.8),
    ("physics.tribology",             0.9),
    ("physics.acoustic",              0.8),
    ("physics.shape_memory",          0.7),
    ("physics.catalysis",             0.7),
    ("physics.biocompatibility",      0.9),
    ("physics.relativistic",          0.6),
    ("physics.nuclear_fuel",          0.8),
    ("physics.optical",               0.7),
    ("physics.hydrogen_storage",      0.7),
    ("physics.structural_efficiency", 1.1),
    ("physics.calphad_stability",     1.2),
    ("physics.ici",                   1.3),
    ("physics.transformation_kinetics", 1.1),
    ("physics.castability",           0.9),
    ("physics.machinability",         0.8),
]

NEW_DOMAIN_RUNNERS = []
try:
    from physics.new_domains import (
        run_formability, run_am, run_heat_treat,
        run_fracture, run_impact, run_galvanic, run_solidification
    )
    NEW_DOMAIN_RUNNERS = [
        (run_formability,    0.9,  36, "Formability"),
        (run_am,             0.8,  37, "Additive Manufacturing"),
        (run_heat_treat,     1.0,  38, "Heat Treatment Response"),
        (run_fracture,       1.1,  39, "Fracture Mechanics"),
        (run_impact,         1.0,  40, "Impact Toughness"),
        (run_galvanic,       0.9,  41, "Galvanic Compatibility"),
        (run_solidification, 0.9,  42, "Solidification"),
    ]
except ImportError:
    pass


MODULE_DOMAIN_NAME = {
    "physics.thermo": "Thermodynamics",
    "physics.hume_rothery": "Hume-Rothery",
    "physics.mechanical": "Mechanical",
    "physics.corrosion": "Corrosion",
    "physics.oxidation": "Oxidation",
    "physics.radiation": "Radiation Physics",
    "physics.weldability": "Weldability",
    "physics.creep": "Creep",
    "physics.fatigue": "Fatigue & Fracture",
    "physics.grain_boundary": "Grain Boundary",
    "physics.hydrogen": "Hydrogen Embrittlement",
    "physics.magnetic": "Magnetism",
    "physics.thermal": "Thermal Properties",
    "physics.regulatory": "Regulatory & Safety",
    "physics.electronic_structure": "Electronic Structure",
    "physics.superconductivity": "Superconductivity",
    "physics.phase_stability": "Phase Stability",
    "physics.plasticity": "Plasticity",
    "physics.diffusion": "Diffusion",
    "physics.surface_energy": "Surface Energy",
    "physics.tribology": "Tribology & Wear",
    "physics.acoustic": "Acoustic Properties",
    "physics.shape_memory": "Shape Memory",
    "physics.catalysis": "Catalysis",
    "physics.biocompatibility": "Biocompatibility",
    "physics.relativistic": "Relativistic Effects",
    "physics.nuclear_fuel": "Nuclear Fuel Compatibility",
    "physics.optical": "Optical Properties",
    "physics.hydrogen_storage": "Hydrogen Storage",
    "physics.structural_efficiency": "Structural Efficiency",
    "physics.calphad_stability": "CALPHAD Stability",
    "physics.ici": "India Corrosion Index",
    "physics.transformation_kinetics": "Transformation Kinetics",
    "physics.castability": "Castability",
    "physics.machinability": "Machinability",
}

PROFILE_GROUP_BOOSTS = {
    "balanced": {},
    "structural": {"structural": 2.2, "manufacturing": 1.4, "corrosion": 1.15},
    "corrosion": {"corrosion": 2.8, "thermal": 1.2, "nuclear": 1.2},
    "high_temp": {"thermal": 2.8, "structural": 1.6, "corrosion": 1.2},
    "nuclear": {"nuclear": 3.0, "corrosion": 1.6, "thermal": 1.5, "structural": 1.2},
    "biomedical": {"biomedical": 3.0, "corrosion": 1.6, "structural": 1.2},
    "conductive": {"electronic": 3.0, "thermal": 1.8},
    "manufacturing": {"manufacturing": 2.8, "structural": 1.3},
    "catalysis": {"electronic": 2.1},
}

PROFILE_DOMAIN_BOOSTS = {
    "catalysis": {"Catalysis": 3.2, "Surface Energy": 2.0, "Electronic Structure": 1.8},
    "corrosion": {"Corrosion": 3.0, "India Corrosion Index": 2.6, "Galvanic Compatibility": 2.0},
    "high_temp": {"Creep": 2.8, "Phase Stability": 2.2, "Oxidation": 1.8},
    "nuclear": {"Radiation Physics": 3.0, "Nuclear Fuel Compatibility": 3.2},
}

APPLICATION_PROFILE = {
    "stainless": "corrosion",
    "superalloy": "high_temp",
    "refractory": "high_temp",
    "nuclear": "nuclear",
    "biomedical": "biomedical",
    "cu_alloy": "conductive",
    "carbon_steel": "structural",
    "structural": "structural",
    "al_alloy": "structural",
    "ti_alloy": "structural",
}

PROPERTY_PROFILES = {
    "corrosion_resistance": ["corrosion"],
    "oxidation_resistance": ["corrosion", "high_temp"],
    "creep_resistance": ["high_temp"],
    "high_temperature_strength": ["high_temp"],
    "wear_resistance": ["structural"],
    "hardness": ["structural"],
    "fatigue_resistance": ["structural"],
    "conductivity": ["conductive"],
    "biocompatibility": ["biomedical"],
    "radiation_resistance": ["nuclear"],
}

_MODULE_CACHE = {}

try:
    from physics.domain_graph import DOMAIN_GROUPS as _DG_GROUPS
except Exception:
    _DG_GROUPS = {}


def _canon_domain(name: str) -> str:
    text = str(name or "").strip().lower()
    return "".join(ch for ch in text if ch.isalnum())


def _canon_domain_map(domain_map: dict | None) -> dict[str, float]:
    if not isinstance(domain_map, dict):
        return {}
    clean = {}
    for key, value in domain_map.items():
        try:
            weight = float(value)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        canon = _canon_domain(key)
        if canon:
            clean[canon] = clean.get(canon, 0.0) + weight
    total = sum(clean.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in clean.items()}


_GROUP_CANON = {
    str(group).strip().lower(): {_canon_domain(domain) for domain in domains}
    for group, domains in _DG_GROUPS.items()
}


def _normalize_profile(weight_profile: str | None) -> str:
    text = str(weight_profile or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"", "auto"}:
        return "auto"
    if text in PROFILE_GROUP_BOOSTS:
        return text
    return "balanced"


def _active_profiles(application: str | None, target_properties: list | None, weight_profile: str | None) -> list[str]:
    selected = []
    normalized_profile = _normalize_profile(weight_profile)
    if normalized_profile not in {"auto", "balanced"}:
        selected.append(normalized_profile)

    if normalized_profile == "auto":
        app = str(application or "").strip().lower()
        mapped = APPLICATION_PROFILE.get(app)
        if mapped:
            selected.append(mapped)
        for prop in target_properties or []:
            for prof in PROPERTY_PROFILES.get(str(prop).strip(), []):
                selected.append(prof)
    if not selected:
        selected.append("balanced")

    ordered = []
    seen = set()
    for prof in selected:
        if prof in PROFILE_GROUP_BOOSTS and prof not in seen:
            seen.add(prof)
            ordered.append(prof)
    return ordered or ["balanced"]


def _effective_multiplier(domain_name: str, profiles: list[str], priority_map: dict[str, float]) -> float:
    canon = _canon_domain(domain_name)
    multiplier = 1.0

    for profile in profiles:
        group_boosts = PROFILE_GROUP_BOOSTS.get(profile, {})
        for group, factor in group_boosts.items():
            domains = _GROUP_CANON.get(group, set())
            if canon in domains:
                multiplier = max(multiplier, float(factor))

        domain_boosts = PROFILE_DOMAIN_BOOSTS.get(profile, {})
        for key, factor in domain_boosts.items():
            if _canon_domain(key) == canon:
                multiplier = max(multiplier, float(factor))

    if priority_map:
        priority = priority_map.get(canon, 0.0)
        if priority > 0:
            multiplier *= (1.0 + 3.0 * priority)

    return multiplier


def _matches_focus(domain_name: str, module_name: str, domains_focus: list | None) -> bool:
    if not domains_focus:
        return True
    dn = str(domain_name or "").lower()
    mn = str(module_name or "").lower().replace("_", " ")
    for kw in domains_focus:
        key = str(kw or "").strip().lower()
        if not key:
            continue
        if key in dn or key in mn:
            return True
    return False


def _resolve_module(mod_name: str):
    mod = _MODULE_CACHE.get(mod_name)
    if mod is None:
        mod = importlib.import_module(mod_name)
        _MODULE_CACHE[mod_name] = mod
    return mod


def run_all(comp: dict, T_K: float = 298.0, dpa_rate: float = 1e-7,
            T_irr_K: float = 723.0, thickness_mm: float = 25.0,
            process: str = "annealed", weather: str = None,
            verbose: bool = False, domains_focus: list = None,
            application: str = None, target_properties: list = None,
            domain_priority: dict = None, weight_profile: str = "auto",
            max_domains: int = None) -> dict:
    comp = validate_composition(comp)
    priority_map = _canon_domain_map(domain_priority)
    profiles = _active_profiles(application, target_properties or [], weight_profile)
    plan = []

    for mod_name, weight in DOMAIN_MODULES:
        domain_name = MODULE_DOMAIN_NAME.get(
            mod_name, mod_name.split(".")[-1].replace("_", " ").title()
        )
        if not _matches_focus(domain_name, mod_name, domains_focus):
            continue
        multiplier = _effective_multiplier(domain_name, profiles, priority_map)
        plan.append({
            "kind": "module",
            "runner": mod_name,
            "domain_id": 0,
            "domain_name": domain_name,
            "base_weight": float(weight),
            "effective_weight": float(weight) * multiplier,
        })

    for runner_fn, weight, dom_id, dom_name in NEW_DOMAIN_RUNNERS:
        if not _matches_focus(dom_name, dom_name, domains_focus):
            continue
        multiplier = _effective_multiplier(dom_name, profiles, priority_map)
        plan.append({
            "kind": "callable",
            "runner": runner_fn,
            "domain_id": int(dom_id),
            "domain_name": dom_name,
            "base_weight": float(weight),
            "effective_weight": float(weight) * multiplier,
        })

    if max_domains and not domains_focus:
        try:
            max_domains = int(max_domains)
        except (TypeError, ValueError):
            max_domains = None
        if max_domains and max_domains > 0 and len(plan) > max_domains:
            plan = sorted(plan, key=lambda x: x["effective_weight"], reverse=True)[:max_domains]

    results = []
    for item in plan:
        t0 = time.time()
        try:
            if item["kind"] == "module":
                mod = _resolve_module(item["runner"])
                dr = mod.run(
                    comp, T_K=T_K, dpa_rate=dpa_rate, T_irr_K=T_irr_K,
                    thickness_mm=thickness_mm, process=process, weather=weather
                )
            else:
                runner_fn = item["runner"]
                dr = runner_fn(
                    comp, T_K=T_K, dpa_rate=dpa_rate, T_irr_K=T_irr_K,
                    thickness_mm=thickness_mm, process=process, weather=weather
                )
        except Exception as e:
            dr = DomainResult(item["domain_id"], item["domain_name"],
                              [INFO("Error", None, "", str(e), "")],
                              error=str(e))
            if verbose:
                traceback.print_exc()
        ms = (time.time() - t0) * 1000
        if verbose:
            print(f"  {dr.one_line()}  ({ms:.0f}ms)")
        results.append((dr, item["base_weight"], item["effective_weight"]))

    total_base = sum(base for _, base, _ in results) if results else 1.0
    total_effective = sum(eff for _, _, eff in results) if results else 1.0
    composite_raw = sum(dr.score() * base for dr, base, _ in results) / total_base if results else 0.0
    weighted_mean = sum(dr.score() * eff for dr, _, eff in results) / total_effective if results else 0.0

    # --- Penalised composite: punish uneven & catastrophic profiles ---
    # An alloy scoring 80 everywhere beats one scoring 100×4 + 0×1.
    domain_scores = [dr.score() for dr, _, _ in results]
    if domain_scores and weighted_mean > 0:
        import statistics
        n_domains = len(domain_scores)
        min_score = min(domain_scores)
        # 1) Coefficient-of-variation penalty  (std/mean penalises spread)
        if n_domains > 1:
            stdev = statistics.stdev(domain_scores)
            cv = stdev / max(1.0, weighted_mean)
        else:
            cv = 0.0
        cv_penalty = max(0.5, 1.0 - 0.5 * cv)       # at most halves the score
        # 2) Catastrophe penalty for any domain < 20
        if min_score >= 20:
            catastrophe = 1.0
        else:
            catastrophe = max(0.25, min_score / 20.0)  # 0 → 0.25, 10 → 0.75, 20 → 1.0
        composite = weighted_mean * cv_penalty * catastrophe
    else:
        composite = weighted_mean

    fails = [(dr.domain_name, ch) for dr, _, _ in results for ch in dr.checks if ch.status == "FAIL"]
    warnings = [(dr.domain_name, ch) for dr, _, _ in results for ch in dr.checks if ch.status == "WARN"]
    passes = [(dr.domain_name, ch) for dr, _, _ in results for ch in dr.checks if ch.status == "PASS"]
    used_weights = {
        dr.domain_name: (eff / total_effective if total_effective > 0 else 0.0)
        for dr, _, eff in results
    }

    return {
        "domain_results": [dr for dr, _, _ in results],
        "composite_score": composite,
        "composite_score_raw": composite_raw,
        "composite_score_weighted_mean": weighted_mean,
        "n_pass": len(passes),
        "n_warn": len(warnings),
        "n_fail": len(fails),
        "n_domains": len(results),
        "fails": fails,
        "warnings": warnings,
        "domain_weights_used": used_weights,
        "weight_profiles_used": profiles,
        "weight_profile_mode": _normalize_profile(weight_profile),
        "application_context": application,
        "properties_context": list(target_properties or []),
    }


def run_specific_domains(comp: dict, domain_names: list, **kwargs) -> dict:
    return run_all(comp, domains_focus=domain_names, **kwargs)
