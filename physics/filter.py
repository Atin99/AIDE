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


def run_all(comp: dict, T_K: float = 298.0, dpa_rate: float = 1e-7,
            T_irr_K: float = 723.0, thickness_mm: float = 25.0,
            process: str = "annealed", weather: str = None,
            verbose: bool = False, domains_focus: list = None) -> dict:
    comp = validate_composition(comp)
    results = []

    for mod_name, weight in DOMAIN_MODULES:
        domain_short = mod_name.split(".")[-1].replace("_", " ")
        if domains_focus and not any(kw.lower() in domain_short.lower() for kw in domains_focus):
            continue

        t0 = time.time()
        try:
            mod = importlib.import_module(mod_name)
            dr = mod.run(comp, T_K=T_K, dpa_rate=dpa_rate, T_irr_K=T_irr_K,
                         thickness_mm=thickness_mm,
                         process=process, weather=weather)
        except Exception as e:
            dr = DomainResult(0, domain_short.title(),
                              [INFO("Error", None, "", str(e), "")],
                              error=str(e))
            if verbose:
                traceback.print_exc()
        ms = (time.time() - t0) * 1000
        if verbose:
            print(f"  {dr.one_line()}  ({ms:.0f}ms)")
        results.append((dr, weight))

    for runner_fn, weight, dom_id, dom_name in NEW_DOMAIN_RUNNERS:
        if domains_focus and not any(kw.lower() in dom_name.lower() for kw in domains_focus):
            continue

        t0 = time.time()
        try:
            dr = runner_fn(comp, T_K=T_K, dpa_rate=dpa_rate, T_irr_K=T_irr_K,
                           thickness_mm=thickness_mm,
                           process=process, weather=weather)
        except Exception as e:
            dr = DomainResult(dom_id, dom_name,
                              [INFO("Error", None, "", str(e), "")],
                              error=str(e))
            if verbose:
                traceback.print_exc()
        ms = (time.time() - t0) * 1000
        if verbose:
            print(f"  {dr.one_line()}  ({ms:.0f}ms)")
        results.append((dr, weight))

    total_w = sum(w for _, w in results) if results else 1
    composite = sum(dr.score() * w for dr, w in results) / total_w if results else 0
    fails = [(dr.domain_name, ch) for dr, _ in results for ch in dr.checks if ch.status == "FAIL"]
    warnings = [(dr.domain_name, ch) for dr, _ in results for ch in dr.checks if ch.status == "WARN"]
    passes = [(dr.domain_name, ch) for dr, _ in results for ch in dr.checks if ch.status == "PASS"]

    return {
        "domain_results": [dr for dr, _ in results],
        "composite_score": composite,
        "n_pass": len(passes),
        "n_warn": len(warnings),
        "n_fail": len(fails),
        "n_domains": len(results),
        "fails": fails,
        "warnings": warnings,
    }


def run_specific_domains(comp: dict, domain_names: list, **kwargs) -> dict:
    return run_all(comp, domains_focus=domain_names, **kwargs)
