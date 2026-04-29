import sys, os, time, logging, math
from dataclasses import dataclass, field
from typing import Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.elements import validate_composition
from physics.base import mol_to_wt, wt_to_mol, norm

logger = logging.getLogger("AIDE.pipeline")

FUSIBLE_ELEMENTS = {"Bi", "Sn", "In", "Ga", "Pb", "Cd", "Sb", "Zn", "Hg", "Tl"}
ELECTRONIC_ELEMENTS = {"Cu", "Al", "Ag", "Au", "Sn", "In", "Ga", "Si", "Ge", "Pd", "Pt", "Sb", "As"}
HIGH_MELT_STRUCTURAL_ELEMENTS = {"Fe", "Cr", "Ni", "Co", "Mo", "W", "Nb", "Ta", "Ti", "V", "Zr", "Hf"}
HOT_SECTION_MARKERS = {
    "hot section", "gas path", "gas turbine", "turbine", "turbine blade", "blade",
    "jet engine", "combustor", "afterburner", "exhaust nozzle", "stress rupture",
}
AEROSPACE_STRUCTURE_MARKERS = {
    "airframe", "fuselage", "wing", "wing spar", "skin", "panel", "bulkhead",
    "frame", "aircraft body", "jet body", "body shell", "aerospace structural",
    "aircraft frame", "aircraft structure",
}
HEAVY_STRUCTURE_MARKERS = {
    "crane", "boom", "gantry", "hoist", "frame", "chassis", "body", "bridge",
    "girder", "beam", "bucket", "loader", "excavator", "trailer", "truck body",
    "load bearing", "load-bearing",
}
LIGHTWEIGHT_QUERY_MARKERS = {"lightweight", "low density", "mass critical", "weight critical"}
LIGHTWEIGHT_HEAVY_ELEMENT_WEIGHTS = {
    "W": 2.5,
    "Re": 4.0,
    "Ta": 3.0,
    "Hf": 3.0,
    "Mo": 1.5,
    "Nb": 1.0,
    "Co": 0.8,
}

@dataclass
class PipelineStep:
    step_num: int
    stage: str
    thought: str
    observation: str
    agent: str = ""
    timestamp: float = 0.0
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class Candidate:
    composition: dict
    composition_wt: dict
    rationale: str = ""
    physics_result: dict = field(default_factory=dict)
    ml_predictions: dict = field(default_factory=dict)
    correlations: dict = field(default_factory=dict)
    score: float = 0.0
    screening_score: float = 0.0
    score_source: str = "unscored"
    physics_evaluated: bool = False
    weak_domains: list = field(default_factory=list)
    iteration: int = 0
    result_type: str = "generated"
    provenance: Optional[dict] = None


@dataclass
class PipelineResult:
    candidates: list
    steps: list
    baseline: Optional[Candidate] = None
    iterations_run: int = 0
    converged: bool = False
    best_score: float = 0.0
    total_time: float = 0.0
    explanation: str = ""
    correlation_insights: list = field(default_factory=list)
    generation_stats: dict = field(default_factory=dict)
    mode: str = "design"


def _normalize_wt(comp):
    total = sum(v for v in comp.values() if v > 0)
    if total <= 0:
        return {}
    return {k: v / total for k, v in comp.items() if v > 1e-6}


def _normalize_element_symbol(symbol):
    token = str(symbol or "").strip()
    if not token:
        return None
    if len(token) == 1:
        return token.upper()
    return token[0].upper() + token[1:].lower()


def _normalize_element_map(raw_comp):
    cleaned = {}
    for symbol, value in (raw_comp or {}).items():
        normalized = _normalize_element_symbol(symbol)
        if not normalized:
            continue
        try:
            numeric = float(value)
        except Exception:
            continue
        if numeric <= 0.001:
            continue
        cleaned[normalized] = cleaned.get(normalized, 0.0) + numeric
    return cleaned


def _set_floor(wt, symbol, minimum):
    current = wt.get(symbol, 0.0)
    if current >= minimum:
        return wt
    needed = minimum - current
    others = [k for k in wt.keys() if k != symbol]
    other_total = sum(wt.get(k, 0.0) for k in others)
    if other_total <= 0:
        wt[symbol] = minimum
        return _normalize_wt(wt)
    scale = max(0.0, (other_total - needed) / other_total)
    for key in others:
        wt[key] *= scale
    wt[symbol] = minimum
    return _normalize_wt(wt)


def _apply_caps(wt, caps):
    for symbol, cap in caps.items():
        if symbol in wt:
            wt[symbol] = min(wt[symbol], cap)
    return _normalize_wt(wt)


def _contains_any(text, markers):
    return any(marker in text for marker in markers)


def _structured_llm_generation_enabled():
    value = os.environ.get("AIDE_USE_LLM_GENERATION", "1").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _is_hot_section_query(text):
    return _contains_any(text, HOT_SECTION_MARKERS) or (
        "jet" in text and any(marker in text for marker in ["engine", "turbine", "blade", "combustor", "nozzle"])
    )


def _is_aerospace_structure_query(text):
    return _contains_any(text, AEROSPACE_STRUCTURE_MARKERS) or (
        any(marker in text for marker in ["aircraft", "aerospace", "airplane", "plane", "jet"])
        and any(marker in text for marker in ["body", "frame", "fuselage", "wing", "skin", "panel", "spar", "structure", "structural"])
    )


def _is_heavy_structure_query(text):
    return _contains_any(text, HEAVY_STRUCTURE_MARKERS)


def _is_lightweight_query(text, props=None):
    props = set(props or [])
    return "low_density" in props or _contains_any(text, LIGHTWEIGHT_QUERY_MARKERS)


def _density_target_for_intent(application, constraints=None, props=None, query=""):
    constraints = dict(constraints or {})
    if constraints.get("max_density"):
        return float(constraints["max_density"])
    if not _is_lightweight_query((query or "").lower(), props):
        return None
    defaults = {
        "al_alloy": 3.3,
        "ti_alloy": 5.2,
        "superalloy": 7.8,
        "stainless": 7.4,
        "structural": 5.6,
        "general_structural": 5.6,
        "open_alloy": 5.6,
        "carbon_steel": 5.8,
        "nuclear": 7.0,
        "biomedical": 6.0,
    }
    return float(defaults.get((application or "").lower(), 5.8))


def _intent_required_elements(intent, query=""):
    must = set(intent.get("must_include", []) or [])
    exclude = set(intent.get("exclude_elements", []) or [])
    props = set(intent.get("target_properties", []) or [])
    constraints = dict(intent.get("constraints", {}) or {})
    app = intent.get("application") or ""
    family = (constraints.get("alloy_family") or "").lower()
    q = (query or "").lower()

    if constraints.get("no_ni"):
        exclude.add("Ni")
    if constraints.get("no_co"):
        exclude.add("Co")
    if constraints.get("no_pb"):
        exclude.add("Pb")
    if constraints.get("no_cd"):
        exclude.add("Cd")
    if constraints.get("rohs_compliant"):
        exclude.update({"Pb", "Cd", "Hg"})

    if app in {"stainless", "structural", "carbon_steel"}:
        must.add("Fe")
    if app == "fusible_alloy":
        for preferred in ["Sn", "Bi", "In", "Ga"]:
            if preferred not in exclude:
                must.add(preferred)
                break
    if app == "electronic_alloy":
        if any(k in q for k in ["semiconductor", "wafer"]) and "Si" not in exclude:
            must.add("Si")
        elif any(k in q for k in ["bond wire", "wire bond"]) and "Cu" not in exclude:
            must.add("Cu")
        elif "Cu" not in exclude:
            must.add("Cu")
    if app == "stainless":
        must.add("Cr")
        # Austenitic stainless (marine, corrosion) needs Ni; ferritic does not
        if "Ni" not in exclude and not any(k in q for k in ["ferritic", "430", "409", "no nickel", "ni-free"]):
            must.add("Ni")
    if app == "superalloy":
        if "Ni" not in exclude:
            must.add("Ni")
        elif "Co" not in exclude:
            must.add("Co")
        must.add("Cr")
    if app == "ti_alloy":
        must.add("Ti")
    if app == "al_alloy":
        must.add("Al")
    if app == "cu_alloy":
        must.add("Cu")
        if family == "brass" and "Zn" not in exclude:
            must.add("Zn")
        if family == "bronze" and "Sn" not in exclude:
            must.add("Sn")
        if family == "aluminum_bronze" and "Al" not in exclude:
            must.add("Al")
        if family == "phosphor_bronze":
            if "Sn" not in exclude:
                must.add("Sn")
            if "P" not in exclude:
                must.add("P")
        if family == "silicon_bronze" and "Si" not in exclude:
            must.add("Si")
    if app == "nuclear":
        if "Zr" not in exclude:
            must.add("Zr")

    if "corrosion_resistance" in props or any(k in q for k in ["marine", "chloride", "seawater", "pitting"]):
        if app in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            must.add("Cr")
            if "Mo" not in exclude and (app in {"stainless", "superalloy"} or any(k in q for k in ["marine", "chloride", "seawater", "pitting"])):
                must.add("Mo")

    if "high_temperature_strength" in props or "creep_resistance" in props:
        if "Ni" not in exclude:
            must.add("Ni")
        elif "Co" not in exclude:
            must.add("Co")
        must.add("Cr")

    if "wear_resistance" in props or "hardness" in props:
        if app in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            if "C" not in exclude:
                must.add("C")
            if "V" not in exclude:
                must.add("V")
            if any(k in q for k in ["tungsten", "w-based", "hot hardness"]) and "W" not in exclude:
                must.add("W")

    if constraints.get("cost_level") == "low":
        exclude.update({"Re", "Ta", "Hf"})

    must = sorted(e for e in must if e not in exclude)
    return must, sorted(exclude)


def _default_seed_for_application(application):
    app = (application or "").lower()
    # Metallurgically accurate default seeds — these match real commercial alloy families
    seeds = {
        "fusible_alloy": {"Sn": 0.52, "Bi": 0.28, "In": 0.14, "Ag": 0.04, "Cu": 0.02},
        "electronic_alloy": {"Cu": 0.74, "Sn": 0.12, "Ag": 0.07, "Au": 0.03, "Si": 0.02, "In": 0.02},
        # 316L-type austenitic stainless (the most common marine/corrosion grade)
        "stainless": {"Fe": 0.645, "Cr": 0.17, "Ni": 0.12, "Mo": 0.025, "Mn": 0.02, "Si": 0.01, "C": 0.002, "N": 0.008},
        # A36-type plain structural
        "structural": {"Fe": 0.95, "Mn": 0.02, "Si": 0.02, "C": 0.01},
        "general_structural": {"Fe": 0.95, "Mn": 0.02, "Si": 0.02, "C": 0.01},
        # AISI 1040-type medium carbon
        "carbon_steel": {"Fe": 0.975, "Mn": 0.012, "Si": 0.008, "C": 0.005},
        # IN718-type Ni superalloy
        "superalloy": {"Ni": 0.53, "Cr": 0.19, "Fe": 0.18, "Nb": 0.05, "Mo": 0.03, "Ti": 0.01, "Al": 0.005, "Co": 0.005},
        # Ti-6Al-4V
        "ti_alloy": {"Ti": 0.89, "Al": 0.06, "V": 0.04, "Fe": 0.01},
        # 6061-type
        "al_alloy": {"Al": 0.965, "Mg": 0.01, "Si": 0.006, "Cu": 0.003, "Cr": 0.002, "Fe": 0.007, "Mn": 0.002, "Zn": 0.005},
        # C26000 brass
        "cu_alloy": {"Cu": 0.70, "Zn": 0.28, "Pb": 0.01, "Fe": 0.01},
        # Zircaloy-4
        "nuclear": {"Zr": 0.97, "Sn": 0.015, "Fe": 0.008, "Cr": 0.007},
        # Ti-6Al-7Nb biomedical
        "biomedical": {"Ti": 0.84, "Nb": 0.10, "Zr": 0.04, "Ta": 0.02},
        "open_alloy": {"Fe": 0.22, "Ni": 0.20, "Cr": 0.18, "Co": 0.15, "Ti": 0.12, "Al": 0.13},
    }
    return _normalize_wt(seeds.get(app, {"Fe": 0.94, "Mn": 0.03, "Si": 0.02, "C": 0.01}))


def _apply_intent_to_wt(wt, intent, query=""):
    wt = _normalize_wt(dict(wt or {}))
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))

    must, exclude = _intent_required_elements(intent, query)
    for symbol in exclude:
        wt.pop(symbol, None)
    wt = _normalize_wt(wt)
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))
        for symbol in exclude:
            wt.pop(symbol, None)
        wt = _normalize_wt(wt)
    if not wt:
        wt = {"Fe": 1.0}

    constraints = dict(intent.get("constraints", {}) or {})
    props = set(intent.get("target_properties", []) or [])
    rd = intent.get("research_data")
    app = intent.get("application") or ""
    family = (constraints.get("alloy_family") or "").lower()
    q = (query or "").lower()

    # NOTE: We intentionally do NOT force the researcher's base element here.
    # This allows multi-family diversity — the physics engine scores everything.

    for symbol in must:
        if symbol in exclude:
            continue
        wt = _set_floor(wt, symbol, 0.01)

    # Application-specific constraints ONLY apply if the composition's dominant
    # element already matches the family.  This preserves multi-family diversity:
    # a Ti-dominant composition won't get forced to Fe>=0.65 just because the
    # researcher picked "structural".
    dominant_el = max(wt, key=wt.get) if wt else ""

    if app == "stainless" and dominant_el == "Fe":
        if "Cr" not in exclude:
            wt = _set_floor(wt, "Cr", 0.12)
        is_ferritic = any(k in q for k in ["ferritic", "430", "409", "ni-free"])
        if "Ni" not in exclude and not is_ferritic:
            ni_floor = 0.08
            if any(k in q for k in ["marine", "seawater", "chloride", "316", "pitting", "offshore"]):
                ni_floor = 0.10
            elif any(k in q for k in ["duplex", "2205", "2507"]):
                ni_floor = 0.05
            wt = _set_floor(wt, "Ni", ni_floor)
        if "Mo" not in exclude and any(k in q for k in ["marine", "chloride", "seawater", "pitting", "316", "offshore"]):
            wt = _set_floor(wt, "Mo", 0.02)

    if app in {"structural", "general_structural"} and dominant_el == "Fe":
        if _is_heavy_structure_query(q) or "weldability" in props or "fatigue_resistance" in props:
            wt = _apply_caps(wt, {"C": 0.012})

    if app == "superalloy" and dominant_el in {"Ni", "Co"}:
        if "Cr" not in exclude:
            wt = _set_floor(wt, "Cr", 0.08)

    if app == "ti_alloy" and dominant_el == "Ti":
        pass  # Ti alloys are fine as-is; no extra constraints needed

    if app == "al_alloy" and dominant_el == "Al":
        pass  # Al alloys are fine as-is

    if app == "nuclear" and dominant_el == "Zr":
        pass  # Zr alloys are fine as-is

    if app == "cu_alloy" and dominant_el == "Cu":
        pass  # Cu alloys are fine as-is

    # Toxic element caps apply universally regardless of family
    for toxic in ["Pb", "Cd", "Hg"]:
        if toxic in wt and wt[toxic] > 0.005:
            wt[toxic] = 0.0

    if "corrosion_resistance" in props:
        if intent.get("application") in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            if "Cr" not in exclude:
                wt = _set_floor(wt, "Cr", 0.14)
            if "Mo" not in exclude and any(k in query.lower() for k in ["marine", "chloride", "seawater", "pitting"]):
                wt = _set_floor(wt, "Mo", 0.02)

    if "high_temperature_strength" in props or "creep_resistance" in props:
        # Only force Ni/Co/Cr floors on compositions that are already Ni/Co/Fe-based.
        # A Ti-alloy can also be high-temp (e.g. Ti-6242) without needing 20% Ni.
        if dominant_el in {"Ni", "Co", "Fe"}:
            if "Ni" not in exclude:
                wt = _set_floor(wt, "Ni", 0.20)
            elif "Co" not in exclude:
                wt = _set_floor(wt, "Co", 0.15)
            if "Cr" not in exclude:
                wt = _set_floor(wt, "Cr", 0.12)

    if "wear_resistance" in props or "hardness" in props:
        if intent.get("application") in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            if "C" not in exclude:
                wt = _set_floor(wt, "C", 0.006)
            if "V" not in exclude:
                wt = _set_floor(wt, "V", 0.01)

    if "low_melting_point" in props or intent.get("application") == "fusible_alloy":
        preferred_base = "Sn"
        if any(k in q for k in ["liquid metal", "gallium"]) and "Ga" not in exclude:
            preferred_base = "Ga"
        elif any(k in q for k in ["fuse alloy", "fuse wire", "fusible", "fusible wire", "thermal fuse"]) and "Bi" not in exclude:
            preferred_base = "Bi"
        elif "Sn" in exclude and "Bi" not in exclude:
            preferred_base = "Bi"
        if preferred_base not in exclude:
            wt = _set_floor(wt, preferred_base, 0.30)
        if "In" not in exclude:
            wt = _set_floor(wt, "In", 0.02)
        if any(k in q for k in ["lead-free", "pb-free", "rohs"]):
            for bad in ["Pb", "Cd", "Hg"]:
                wt.pop(bad, None)
        for structural_el, cap in {
            "Fe": 0.12, "Cr": 0.10, "Ni": 0.10, "Co": 0.08, "Mo": 0.06,
            "W": 0.04, "Nb": 0.04, "Ta": 0.03, "Ti": 0.05, "V": 0.04,
        }.items():
            if structural_el in wt:
                wt[structural_el] = min(wt[structural_el], cap)

    if "conductivity" in props or intent.get("application") == "electronic_alloy":
        if any(k in q for k in ["semiconductor", "wafer"]) and "Si" not in exclude:
            wt = _set_floor(wt, "Si", 0.15)
        elif "Cu" not in exclude:
            wt = _set_floor(wt, "Cu", 0.35)
        if any(k in q for k in ["bond wire", "wire bond"]):
            for el, floor in {"Ag": 0.04, "Au": 0.02}.items():
                if el not in exclude:
                    wt = _set_floor(wt, el, floor)
        if any(k in q for k in ["package", "interconnect", "solder bump", "leadframe"]) and "Sn" not in exclude:
            wt = _set_floor(wt, "Sn", 0.06)
        for high_resistivity_el, cap in {
            "Fe": 0.12, "Cr": 0.10, "Mo": 0.08, "W": 0.06, "Nb": 0.05,
            "Ta": 0.05, "Hf": 0.04, "Re": 0.02,
        }.items():
            if high_resistivity_el in wt:
                wt[high_resistivity_el] = min(wt[high_resistivity_el], cap)

    density_target = _density_target_for_intent(app, constraints, props, q)
    if density_target is not None:
        aggressive = density_target <= 5.3
        lightweight_caps = {
            "W": 0.01 if aggressive else 0.04,
            "Re": 0.002 if aggressive else 0.006,
            "Ta": 0.015 if aggressive else 0.03,
            "Hf": 0.01 if aggressive else 0.02,
            "Mo": 0.04 if aggressive else 0.06,
            "Nb": 0.04 if aggressive else 0.08,
            "Co": 0.08 if aggressive else 0.12,
        }
        if app in {"structural", "general_structural", "open_alloy", "ti_alloy", "al_alloy"}:
            lightweight_caps.update({
                "Ni": 0.12 if aggressive else 0.18,
                "Fe": 0.25 if aggressive else 0.40,
            })

        wt = _apply_caps(wt, lightweight_caps)

        # Only force lightweight-base floors when the composition's dominant
        # element already matches — don't coerce a Ni superalloy into Ti-base.
        if app == "ti_alloy" and dominant_el == "Ti" and "Ti" not in exclude:
            wt = _set_floor(wt, "Ti", 0.78)
        elif app == "al_alloy" and dominant_el == "Al" and "Al" not in exclude:
            wt = _set_floor(wt, "Al", 0.88)
        elif app in {"structural", "general_structural", "open_alloy"}:
            if _is_aerospace_structure_query(q) and dominant_el == "Ti" and "Ti" not in exclude:
                wt = _set_floor(wt, "Ti", 0.45)
            elif dominant_el == "Al" and "Al" not in exclude:
                wt = _set_floor(wt, "Al", 0.30)
        elif app == "superalloy" and not _is_hot_section_query(q) and dominant_el in {"Ni", "Co"}:
            if "Ti" not in exclude:
                wt = _set_floor(wt, "Ti", 0.08)
            if "Al" not in exclude:
                wt = _set_floor(wt, "Al", 0.05)

    if constraints.get("cost_level") == "low":
        caps = {"Ni": 0.08, "Co": 0.05, "Re": 0.01, "Ta": 0.01, "Hf": 0.01, "W": 0.06}
        for symbol, cap in caps.items():
            if symbol in wt:
                wt[symbol] = min(wt[symbol], cap)
    if constraints.get("no_pb") or constraints.get("rohs_compliant"):
        wt.pop("Pb", None)
    if constraints.get("no_cd") or constraints.get("rohs_compliant"):
        wt.pop("Cd", None)
    if constraints.get("rohs_compliant"):
        wt.pop("Hg", None)

    if rd and rd.base_elements:
        base = rd.base_elements[0]
        if base in wt:
            wt = _set_floor(wt, base, float(rd.base_min_fraction))

    if app == "stainless":
        if "Fe" not in exclude:
            wt = _set_floor(wt, "Fe", 0.50)
        if "Cr" not in exclude:
            wt = _set_floor(wt, "Cr", 0.12)
    elif app in {"structural", "general_structural"}:
        if "Fe" not in exclude:
            wt = _set_floor(wt, "Fe", 0.65)
    elif app == "carbon_steel":
        if "Fe" not in exclude:
            wt = _set_floor(wt, "Fe", 0.90)
    elif app == "superalloy":
        if "Ni" not in exclude:
            wt = _set_floor(wt, "Ni", 0.45)
        elif "Co" not in exclude:
            wt = _set_floor(wt, "Co", 0.30)
    elif app == "ti_alloy":
        if "Ti" not in exclude:
            wt = _set_floor(wt, "Ti", 0.70)
    elif app == "al_alloy":
        if "Al" not in exclude:
            wt = _set_floor(wt, "Al", 0.80)
    elif app == "nuclear":
        if "Zr" not in exclude:
            wt = _set_floor(wt, "Zr", 0.78)

    for symbol in list(wt.keys()):
        if wt[symbol] < 0.001:
            wt.pop(symbol, None)

    wt = _normalize_wt(wt)
    if not wt:
        wt = _default_seed_for_application(intent.get("application"))
    return wt


def _condition_candidate_with_intent(candidate, intent, query, reason_suffix):
    if not candidate:
        return None
    try:
        base_wt = candidate.composition_wt or mol_to_wt(candidate.composition)
        conditioned_wt = _apply_intent_to_wt(base_wt, intent, query)
        mol = validate_composition(wt_to_mol(conditioned_wt))
        rationale = candidate.rationale or "Generated baseline"
        if reason_suffix:
            rationale = f"{rationale} | {reason_suffix}"
        return Candidate(
            composition=mol, 
            composition_wt=conditioned_wt, 
            rationale=rationale,
            result_type=candidate.result_type,
            provenance=candidate.provenance
        )
    except Exception:
        return candidate


def _candidate_weight_like(candidate):
    comp_wt = getattr(candidate, "composition_wt", None) or {}
    if comp_wt:
        return _normalize_wt(comp_wt)
    comp = getattr(candidate, "composition", None) or {}
    try:
        return _normalize_wt(mol_to_wt(comp))
    except Exception:
        return _normalize_wt(comp)


def _candidate_research_violation(candidate, research_data):
    if not research_data:
        return ""
    comp_wt = _candidate_weight_like(candidate)
    violated, reason = research_data.composition_violates_base(comp_wt)
    return reason if violated else ""


def _filter_candidates_against_research(candidates, research_data):
    if not research_data:
        return candidates, 0

    aligned = []
    rejected = []
    for cand in candidates:
        reason = _candidate_research_violation(cand, research_data)
        if not reason:
            aligned.append(cand)
            continue
        cand.screening_score = 0.0
        if not cand.physics_evaluated:
            cand.score = 0.0
            cand.score_source = "rejected_screen"
        if not any(w.get("name") == "Base Material Rejection" for w in cand.weak_domains):
            cand.weak_domains.append({"name": "Base Material Rejection", "score": 0, "fails": [reason]})
        rejected.append(cand)

    if aligned:
        return aligned, len(rejected)
    return candidates, 0


def _summarize_intent(intent, query):
    app = intent.get("application") or "unknown"
    props = intent.get("target_properties", []) or []
    constraints = intent.get("constraints", {}) or {}
    must, exclude = _intent_required_elements(intent, query)
    notes = [
        f"application={app}",
        f"properties={props if props else ['none']}",
        f"must_include={must if must else ['none']}",
        f"exclude={exclude if exclude else ['none']}",
        f"constraints={constraints if constraints else 'none'}",
    ]
    return " | ".join(notes)


def _compact_comp(comp, top=5, digits=2):
    if not comp:
        return "none"
    ranked = sorted(comp.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{sym}:{frac * 100:.{digits}f}%" for sym, frac in ranked[:top])


class BaselinePredictor:
    @staticmethod
    def predict(query, intent):
        from core.data_hub import get_hub
        hub = get_hub()
        if intent.get("alloy_name"):
            alloy = hub.get_alloy(intent["alloy_name"])
            if alloy and alloy.get("composition_wt"):
                wt = alloy["composition_wt"]
                try:
                    mol = validate_composition(wt_to_mol(wt))
                    base = Candidate(composition=mol, composition_wt=wt,
                                     rationale=f"Exact match: {intent['alloy_name']}",
                                     result_type="catalog",
                                     provenance=alloy.get("provenance"))
                    return _condition_candidate_with_intent(
                        base, intent, query, "intent-conditioned seed"
                    )
                except Exception:
                    pass
        from llms.client import is_available
        if is_available():
            baseline = _llm_baseline(query, intent)
            if baseline:
                return _condition_candidate_with_intent(
                    baseline, intent, query, "intent-conditioned seed"
                )
        from core.generator import generate
        try:
            must_include, exclude = _intent_required_elements(intent, query)
            aug_query = query
            rd = intent.get("research_data")
            if rd and rd.base_elements:
                if rd.base_elements[0] not in exclude:
                    must_include = sorted(set(must_include + [rd.base_elements[0]]))
                aug_query += " " + rd.base_elements[0] + " alloy"

            base_hint = intent.get("composition")
            if not base_hint:
                base_hint = _default_seed_for_application(intent.get("application"))
            base_hint = _apply_intent_to_wt(base_hint, intent, query)

            comps = generate(
                query=aug_query,
                n=8,
                application=intent.get("application", ""),
                base_composition=base_hint,
                must_include=must_include,
                exclude_elements=exclude,
            )
            if comps:
                wt = mol_to_wt(comps[0])
                base = Candidate(composition=comps[0], composition_wt=wt,
                                 rationale="Template-based baseline")
                return _condition_candidate_with_intent(
                    base, intent, query, "intent-conditioned seed"
                )
        except Exception:
            pass

        seed = _default_seed_for_application(intent.get("application"))
        seed = _apply_intent_to_wt(seed, intent, query)
        try:
            mol = validate_composition(wt_to_mol(seed))
            return Candidate(composition=mol, composition_wt=seed, rationale="Heuristic baseline seed")
        except Exception:
            return None

def _llm_baseline(query, intent):
    if not _structured_llm_generation_enabled():
        return None
    from llms.client import chat_json
    parts = [
        "Propose one realistic starting alloy composition.",
        f"Request: {query}",
    ]
    
    rd = intent.get("research_data")
    if rd:
        parts.append(f"\nHARD CONSTRAINTS you MUST respect:")
        parts.append(f"  - Base element(s): {rd.base_elements}")
        parts.append(f"  - Base min mass fraction: {rd.base_min_fraction:.2f}")
        parts.append(f"  - Forbidden: {rd.forbidden_elements}")
        parts.append(f"  - Mechanisms to enforce: {rd.mandatory_mechanisms}")
    
    parts.append(
        """Return ONLY JSON:
{"comp_wt": {"Fe": 0.650, "Cr": 0.220}, "rationale": "short baseline reason"}
Rules:
- weight fractions sum to ~1.0
- max 6 elements
- rationale <= 12 words
- use at most 3 decimal places
- no forbidden elements
- base element must remain the highest mass fraction when required"""
    )

    prompt = "\n".join(parts)
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a computational metallurgist. "
                    "Return raw JSON only. Keep compositions realistic and compact."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=220,
        temperature=0.1,
    )
    
    if not result or "comp_wt" not in result:
        return None
    try:
        wt = _normalize_element_map(result["comp_wt"])
        total = sum(wt.values())
        if total == 0:
            return None
        wt = {k: v / total for k, v in wt.items()}
        mol = validate_composition(wt_to_mol(wt))
        
        return Candidate(composition=mol, composition_wt=wt,
                         rationale=result.get("rationale", "LLM reasoning"))
    except Exception as e:
        logger.warning(f"[BASELINE] Failed to parse baseline: {e}")
        return None


_EMERGENCY_SEEDS = {
    "stainless": [
        {"Fe": 0.66, "Cr": 0.18, "Ni": 0.10, "Mo": 0.03, "Mn": 0.02, "Si": 0.01},
        {"Fe": 0.62, "Cr": 0.22, "Ni": 0.06, "Mo": 0.03, "N": 0.02, "Mn": 0.05},
        {"Fe": 0.58, "Cr": 0.25, "Ni": 0.08, "Mo": 0.04, "Cu": 0.02, "Mn": 0.03},
    ],
    "superalloy": [
        {"Ni": 0.60, "Cr": 0.15, "Co": 0.08, "Mo": 0.05, "Al": 0.05, "Ti": 0.04, "W": 0.03},
        {"Ni": 0.55, "Cr": 0.20, "Co": 0.10, "Mo": 0.04, "W": 0.06, "Al": 0.03, "Ti": 0.02},
        {"Ni": 0.52, "Cr": 0.19, "Fe": 0.18, "Nb": 0.05, "Mo": 0.03, "Ti": 0.01, "Al": 0.02},
    ],
    "ti_alloy": [
        {"Ti": 0.90, "Al": 0.06, "V": 0.04},
        {"Ti": 0.85, "Al": 0.06, "Mo": 0.04, "V": 0.03, "Cr": 0.02},
    ],
    "al_alloy": [
        {"Al": 0.90, "Cu": 0.04, "Mg": 0.03, "Mn": 0.02, "Si": 0.01},
        {"Al": 0.87, "Zn": 0.06, "Mg": 0.03, "Cu": 0.02, "Cr": 0.01, "Ti": 0.01},
    ],
    "cu_alloy": [
        {"Cu": 0.70, "Zn": 0.25, "Al": 0.03, "Ni": 0.02},
        {"Cu": 0.88, "Sn": 0.08, "P": 0.01, "Ni": 0.03},
    ],
    "structural": [
        {"Fe": 0.97, "C": 0.004, "Mn": 0.015, "Si": 0.005, "Cr": 0.003, "Mo": 0.003},
        {"Fe": 0.70, "Cr": 0.12, "Ni": 0.08, "Mo": 0.04, "Mn": 0.03, "V": 0.02, "C": 0.005},
    ],
}
_EMERGENCY_SEEDS["general_structural"] = _EMERGENCY_SEEDS["structural"]
_EMERGENCY_SEEDS["nuclear"] = [{"Zr": 0.98, "Nb": 0.01, "Fe": 0.005, "Cr": 0.005}]
_EMERGENCY_SEEDS["biomedical"] = [{"Ti": 0.64, "Nb": 0.24, "Zr": 0.08, "Ta": 0.04}]
_EMERGENCY_SEEDS["refractory"] = [{"Nb": 0.40, "Mo": 0.25, "Ta": 0.20, "W": 0.10, "V": 0.05}]


def _emergency_seed_candidates(intent, query, target=50):
    """Generate candidates from hardcoded seeds when core.generator fails.
    Pure Python, no external dependencies beyond core.elements."""
    import random as _rng
    rng = _rng.Random(42)

    # Use seeds from ALL families for multi-family diversity
    seeds = []
    for family_seeds in _EMERGENCY_SEEDS.values():
        seeds.extend(family_seeds)
    rng.shuffle(seeds)

    candidates = []
    for seed in seeds:
        # Add the seed itself
        try:
            wt = _apply_intent_to_wt(dict(seed), intent, query)
            mol = validate_composition(wt_to_mol(wt))
            candidates.append(Candidate(
                composition=mol, composition_wt=wt,
                rationale="Emergency seed", score_source="seed",
            ))
        except Exception:
            continue

        # Perturb each seed
        for _ in range(target // max(1, len(seeds))):
            perturbed = {}
            for el, frac in seed.items():
                noise = rng.gauss(0, 0.15)
                perturbed[el] = max(0.001, frac * (1 + noise))
            # Occasionally add a random minor element
            if rng.random() < 0.3:
                minors = ["Cu", "Mn", "Si", "V", "Nb", "N", "Ti", "Al", "W", "Co"]
                el = rng.choice(minors)
                if el not in perturbed:
                    perturbed[el] = rng.uniform(0.005, 0.04)
            total = sum(perturbed.values())
            perturbed = {k: v / total for k, v in perturbed.items()}
            try:
                wt = _apply_intent_to_wt(perturbed, intent, query)
                mol = validate_composition(wt_to_mol(wt))
                candidates.append(Candidate(
                    composition=mol, composition_wt=wt,
                    rationale="Emergency perturbation", score_source="seed",
                ))
            except Exception:
                continue

    return candidates


class MultiCompositionGenerator:
    @staticmethod
    def generate(query, intent, baseline, n=8, iteration=0, feedback=None):
        candidates = []
        if baseline and iteration == 0:
            candidates.append(baseline)

        must_include, exclude = _intent_required_elements(intent, query)
        if must_include:
            intent["must_include"] = sorted(set((intent.get("must_include") or []) + must_include))
        if exclude:
            intent["exclude_elements"] = sorted(set((intent.get("exclude_elements") or []) + exclude))

        initial_len = len(candidates)
        from llms.client import is_available
        if is_available():
            llm_target = max(4, min(8, int(math.ceil(max(1, n) * 0.75))))
            candidates.extend(_llm_generate(query, intent, baseline, llm_target, feedback))

        from core.generator import generate
        try:
            base_comp = baseline.composition_wt if baseline else intent.get("composition")
            if base_comp:
                base_comp = _apply_intent_to_wt(base_comp, intent, query)
            else:
                base_comp = _apply_intent_to_wt(
                    _default_seed_for_application(intent.get("application")), intent, query
                )

            template_comps = generate(
                query=query,
                n=max(n * 2, 18),
                only_elements=intent.get("only_elements"),
                must_include=intent.get("must_include"),
                exclude_elements=intent.get("exclude_elements"),
                application=intent.get("application", ""),
                base_composition=base_comp,
            )
            for comp in template_comps:
                try:
                    wt = _apply_intent_to_wt(mol_to_wt(comp), intent, query)
                    mol = validate_composition(wt_to_mol(wt))
                    candidates.append(
                        Candidate(
                            composition=mol,
                            composition_wt=wt,
                            rationale="Intent-conditioned template variant",
                            iteration=iteration,
                        )
                    )
                except Exception:
                    continue

            exploratory_comps = generate(
                query=query,
                n=max(12, n),
                only_elements=intent.get("only_elements"),
                must_include=intent.get("must_include"),
                exclude_elements=intent.get("exclude_elements"),
                application=intent.get("application", ""),
                base_composition=None,
            )
            for comp in exploratory_comps:
                try:
                    wt = _apply_intent_to_wt(mol_to_wt(comp), intent, query)
                    mol = validate_composition(wt_to_mol(wt))
                    candidates.append(
                        Candidate(
                            composition=mol,
                            composition_wt=wt,
                            rationale="Intent-conditioned exploratory variant",
                            iteration=iteration,
                        )
                    )
                except Exception:
                    continue
        except Exception as gen_err:
            logger.warning("[GENERATE] Template generation failed: %s", gen_err)

        target_floor = max(10, n + 2)
        if len(candidates) < target_floor:
            try:
                relaxed_app = intent.get("application", "")
                extra_target = max(18, target_floor * 3)
                fallback_only = intent.get("only_elements")
                fallback_must = intent.get("must_include")
                fallback_exclude = intent.get("exclude_elements")

                relaxed_batches = []
                if relaxed_app:
                    relaxed_batches.append({
                        "application": relaxed_app,
                        "only_elements": fallback_only,
                        "must_include": fallback_must,
                        "exclude_elements": fallback_exclude,
                    })
                if relaxed_app and relaxed_app != "open_alloy":
                    relaxed_batches.append({
                        "application": "open_alloy",
                        "only_elements": fallback_only,
                        "must_include": fallback_must,
                        "exclude_elements": fallback_exclude,
                    })
                if fallback_only:
                    relaxed_batches.append({
                        "application": "",
                        "only_elements": fallback_only,
                        "must_include": fallback_must,
                        "exclude_elements": fallback_exclude,
                    })

                for batch in relaxed_batches:
                    extra_comps = generate(
                        query=query,
                        n=extra_target,
                        only_elements=batch["only_elements"],
                        must_include=batch["must_include"],
                        exclude_elements=batch["exclude_elements"],
                        application=batch["application"],
                        base_composition=None,
                    )
                    for comp in extra_comps:
                        try:
                            wt = _apply_intent_to_wt(mol_to_wt(comp), intent, query)
                            mol = validate_composition(wt_to_mol(wt))
                            candidates.append(
                                Candidate(
                                    composition=mol,
                                    composition_wt=wt,
                                    rationale="Relaxed exploratory backfill",
                                    iteration=iteration,
                                )
                            )
                        except Exception:
                            continue
                    if len(candidates) >= target_floor * 2:
                        break
            except Exception as fallback_err:
                logger.warning("[GENERATE] Relaxed fallback generation also failed: %s", fallback_err)

        # Emergency inline generation if template+relaxed both failed
        if len(candidates) < max(10, n):
            logger.warning("[GENERATE] Only %d candidates generated, running emergency seed perturbation", len(candidates))
            emergency_seeds = _emergency_seed_candidates(intent, query, target=max(50, n * 3))
            candidates.extend(emergency_seeds)
            logger.info("[GENERATE] Emergency generator added %d candidates", len(emergency_seeds))

        if len(candidates) == initial_len:
            seed_wt = _apply_intent_to_wt(
                _default_seed_for_application(intent.get("application")), intent, query
            )
            try:
                mol = validate_composition(wt_to_mol(seed_wt))
                candidates.append(
                    Candidate(
                        composition=mol,
                        composition_wt=seed_wt,
                        rationale="Heuristic emergency seed",
                        iteration=iteration,
                    )
                )
            except Exception:
                pass
        for cand in candidates:
            cand.iteration = iteration
        return candidates


def _llm_generate(query, intent, baseline, n, feedback=None):
    if not _structured_llm_generation_enabled():
        return []
    from llms.client import chat_json
    target_n = max(3, min(int(n), 8))
    parts = [f"Design query: {query}"]
    if intent.get("application"): parts.append(f"Application: {intent['application']}")
    if intent.get("environment"): parts.append(f"Environment: {intent['environment']}")
    if intent.get("temperature_K"): parts.append(f"Temperature: {intent['temperature_K']:.0f} K")
    if intent.get("must_include"): parts.append(f"Must include: {', '.join(intent['must_include'])}")
    if intent.get("exclude_elements"): parts.append(f"Exclude elements: {', '.join(intent['exclude_elements'])}")
    if intent.get("target_properties"): parts.append(f"Target properties: {', '.join(intent['target_properties'])}")
    
    rd = intent.get("research_data")
    if rd:
        parts.append(f"\nResearcher suggested base: {rd.base_elements} (this is ONE option, not a hard constraint)")
        if rd.forbidden_elements:
            parts.append(f"  - Avoid if possible: {rd.forbidden_elements}")

    if baseline:
        comp_str = _compact_comp(baseline.composition_wt, top=6, digits=2)
        parts.append(f"\nStarting Baseline: {comp_str}")
    if feedback:
        parts.append(f"Best previous score: {feedback.get('best_score', 0):.1f}/100")
        parts.append(f"Weak domains to improve: {feedback.get('weak_summary', 'none')}")
        for index, failed in enumerate(feedback.get("failure_examples") or [], start=1):
            parts.append(
                f"Failure {index}: score={failed.get('score', 0):.1f}; "
                f"{failed.get('composition_summary', 'none')}; "
                f"issue={failed.get('main_issue', 'unknown')}"
            )

    parts.append(f"\nPropose {target_n} diverse alloy compositions as weight fractions summing to 1.0.")
    parts.append("Where metallurgically appropriate, consider exploring multiple alloy families (e.g. Ti, Ni, Al, Fe-based). But prioritise metallurgical correctness for the stated query — do NOT force unrelated families if the query clearly targets one.")
    parts.append("Vary minor additions and element counts across candidates.")
    parts.append("Keep each rationale to 12 words or fewer.")

    system = (
        "You are a computational metallurgist. "
        "Return raw JSON only in this schema: "
        "{\"compositions\": [{\"comp_wt\": {\"Fe\": 0.650}, \"rationale\": \"short text\"}]}. "
        "Use at most 3 decimal places and keep compositions realistic."
    )
    result = chat_json(
        [{"role": "system", "content": system}, {"role": "user", "content": "\n".join(parts)}],
        max_tokens=max(520, 140 * target_n),
        temperature=0.75,
    )
    
    if not result or "compositions" not in result:
        return []
        
    candidates = []
    for item in result["compositions"]:
        try:
            wt = item.get("comp_wt", {})
            if not wt or not isinstance(wt, dict):
                continue
            wt = _normalize_element_map(wt)
            total = sum(wt.values())
            if total < 0.5:
                continue
            wt = {k: v / total for k, v in wt.items()}
            wt = _apply_intent_to_wt(wt, intent, query)
            mol = validate_composition(wt_to_mol(wt))
            
            # No family filtering — we want multi-family diversity
            candidates.append(
                Candidate(
                    composition=mol,
                    composition_wt=wt,
                    rationale=item.get("rationale", ""),
                    score_source="llm_raw",
                )
            )
        except Exception:
            continue
    return candidates


class PhysicsMLEvaluator:
    # Proportional mechanism checks: each returns (ratio 0-1, threshold, description).
    # ratio = how close the composition is to meeting the mechanism requirement.
    _MECHANISM_CHECKS_PROPORTIONAL = {
        "gamma_prime": (
            lambda c: min(1.0, (c.get("Al", 0) + c.get("Ti", 0)) / 0.04) if 0.04 > 0 else 1.0,
            "γ' precipitation favours Al+Ti >= 4 mol%",
        ),
        "precipitation_hard": (
            lambda c: min(1.0, (c.get("Cu", 0) + c.get("Mg", 0) + c.get("Zn", 0)) / 0.005) if 0.005 > 0 else 1.0,
            "Precipitation favours Cu+Mg+Zn >= 0.5 mol%",
        ),
        "martensite": (
            lambda c: min(1.0, c.get("C", 0) / 0.003) if 0.003 > 0 else 1.0,
            "Martensite favours C >= 0.3 mol%",
        ),
        "alpha_beta": (
            lambda c: min(1.0, (c.get("V", 0) + c.get("Mo", 0) + c.get("Nb", 0) + c.get("Cr", 0)) / 0.02) if 0.02 > 0 else 1.0,
            "α+β Ti favours β-stabilisers >= 2 mol%",
        ),
        "solid_solution": (
            lambda c: min(1.0, len([v for v in c.values() if v > 0.005]) / 2.0),
            "Solid solution favours >= 2 solute elements",
        ),
        "carbide": (
            lambda c: min(1.0, (min(c.get("C", 0) / 0.002, 1.0) + min((c.get("Cr", 0) + c.get("W", 0)) / 0.10, 1.0)) / 2.0),
            "Carbide favours C >= 0.2% and (Cr+W) >= 10%",
        ),
    }

    @classmethod
    def _check_mechanisms_penalty(cls, composition, mechanisms):
        """Return (penalty_factor, reasons) where penalty is 0.0-1.0.
        
        1.0 = all mechanisms satisfied. < 1.0 = proportional shortfall.
        Never hard-rejects; the penalty is multiplicative on the score.
        """
        penalties = []
        reasons = []
        for mechanism in mechanisms:
            mech_lower = mechanism.lower().replace(" ", "_").replace("-", "_")
            for keyword, (ratio_fn, msg) in cls._MECHANISM_CHECKS_PROPORTIONAL.items():
                if keyword in mech_lower:
                    ratio = max(0.0, min(1.0, ratio_fn(composition)))
                    if ratio < 1.0:
                        # Smooth penalty: ratio^0.6 so partial fulfilment is gently penalised
                        penalty = max(0.15, ratio ** 0.6)
                        penalties.append(penalty)
                        reasons.append(f"{mechanism} ({ratio:.0%} met): {msg}")
        if not penalties:
            return 1.0, []
        combined = 1.0
        for p in penalties:
            combined *= p
        return max(0.10, combined), reasons

    @staticmethod
    def _overalloying_penalty(composition, query):
        base_frac = max(composition.values())
        solute_frac = 1.0 - base_frac
        solute_count = sum(1 for v in composition.values() if v > 0.005)
        q = query.lower()
        if any(k in q for k in ["fusible", "fusible wire", "low melting", "solder", "thermal fuse", "fuse alloy", "fuse wire"]):
            return math.exp(-0.35 * max(0, solute_count - 5))
        if any(k in q for k in ["chip", "semiconductor", "interconnect", "bond wire", "leadframe"]):
            return math.exp(-0.45 * max(0, solute_count - 6))
        if any(k in q for k in ["electr", "conduct", "wire", "thermal"]) and not any(k in q for k in ["superalloy", "turbine", "jet", "blade", "creep", "900"]):
            return math.exp(-7.0 * solute_frac)
        elif any(k in q for k in ["superalloy", "creep"]) or _is_hot_section_query(q):
            return math.exp(-0.25 * max(0, solute_count - 9))
        elif any(k in q for k in ["biomedical", "implant", "bone"]):
            return math.exp(-0.6 * max(0, solute_count - 4))
        else:
            return math.exp(-0.45 * max(0, solute_count - 6))

    @staticmethod
    def _application_alignment(composition, query="", application="", family="", research_data=None):
        from physics.base import density_rule_of_mixtures, wmean

        wt = _normalize_wt(composition or {})
        if not wt:
            return 0.0, "no-composition"

        if research_data:
            violated, reason = research_data.composition_violates_base(wt)
            if violated:
                # Proportional penalty instead of hard zero
                base_pen = research_data.base_element_penalty(wt)
                return max(0.1, base_pen), f"base-shortfall={reason}"

        q = (query or "").lower()
        app = (application or "").lower()
        family = (family or "").lower()
        fusible_query = app == "fusible_alloy" or any(k in q for k in ["fusible", "fusible wire", "low melting", "low-melting", "solder", "thermal fuse", "fuse alloy", "fuse wire", "liquid metal"])
        electronic_query = app == "electronic_alloy" or any(k in q for k in ["chip", "semiconductor", "interconnect", "bond wire", "wire bond", "leadframe", "microelectronics", "electronic packaging"])

        def _apply_lightweight_alignment(factor):
            density_target = _density_target_for_intent(app, {}, set(), q)
            if density_target is None:
                return max(0.05, min(1.0, factor))

            density = density_rule_of_mixtures(wt_to_mol(wt))
            if density is not None and density > density_target:
                factor *= max(0.08, math.exp(-0.9 * (density - density_target)))

            heavy_burden = sum(wt.get(el, 0.0) * weight for el, weight in LIGHTWEIGHT_HEAVY_ELEMENT_WEIGHTS.items())
            factor *= max(0.08, 1.0 - min(0.92, 0.9 * heavy_burden))
            return max(0.05, min(1.0, factor))

        if fusible_query:
            tm = wmean(wt, "Tm")
            fusible_frac = sum(wt.get(el, 0.0) for el in FUSIBLE_ELEMENTS)
            structural_frac = sum(wt.get(el, 0.0) for el in HIGH_MELT_STRUCTURAL_ELEMENTS)
            tm_factor = 1.0
            if tm is not None:
                tm_factor = max(0.12, min(1.45, 1.55 - max(0.0, tm - 420.0) / 900.0))
            family_factor = max(0.15, min(1.45, 0.55 + 1.20 * fusible_frac - 0.95 * structural_frac))
            toxic_penalty = 1.0
            if any(k in q for k in ["lead-free", "pb-free", "rohs", "cadmium-free", "cd-free"]):
                toxic_frac = composition.get("Pb", 0.0) + composition.get("Cd", 0.0) + composition.get("Hg", 0.0)
                toxic_penalty = max(0.20, 1.0 - 2.5 * toxic_frac)
            multiplier = ((tm_factor + family_factor) / 2.0) * toxic_penalty
            note = f"fusible-alignment={multiplier:.2f} (Tm={tm:.0f}K)" if tm is not None else f"fusible-alignment={multiplier:.2f}"
            return _apply_lightweight_alignment(multiplier), note

        if electronic_query:
            resistivity = wmean(wt, "resistivity")
            thermal_cond = wmean(wt, "thermal_cond")
            electronic_frac = sum(wt.get(el, 0.0) for el in ELECTRONIC_ELEMENTS)
            structural_frac = sum(wt.get(el, 0.0) for el in HIGH_MELT_STRUCTURAL_ELEMENTS)
            rho_factor = 1.0
            if resistivity is not None:
                rho_factor = max(0.25, min(1.35, 1.35 - 0.45 * math.log10(max(resistivity, 1e-3))))
            k_factor = 1.0
            if thermal_cond is not None:
                k_factor = max(0.40, min(1.35, 0.72 + min(thermal_cond, 320.0) / 500.0))
            family_factor = max(0.20, min(1.40, 0.65 + 0.90 * electronic_frac - 0.80 * structural_frac))
            multiplier = (rho_factor + k_factor + family_factor) / 3.0
            note = f"electronics-alignment={multiplier:.2f}"
            return _apply_lightweight_alignment(multiplier), note

        if app == "stainless":
            fe = wt.get("Fe", 0.0)
            cr = wt.get("Cr", 0.0)
            ni = wt.get("Ni", 0.0)
            mo = wt.get("Mo", 0.0)
            exotic = wt.get("Re", 0.0) + wt.get("Ta", 0.0) + wt.get("Hf", 0.0) + max(0.0, wt.get("W", 0.0) - 0.05)
            # Ni contribution: austenitic stainless needs >=8% Ni, penalize if missing
            ni_factor = min(1.0, ni / 0.08) if ni > 0 else 0.35
            # Mo contribution: marine/pitting grades benefit from 2%+ Mo
            mo_bonus = min(1.15, 1.0 + 1.5 * mo) if mo > 0 else 1.0
            factor = min(1.0, fe / 0.50) * min(1.0, cr / 0.12) * ni_factor * mo_bonus * max(0.05, 1.0 - 5.0 * exotic)
            factor = min(1.0, factor)
            return _apply_lightweight_alignment(factor), f"stainless-alignment={factor:.2f}"

        if app in {"structural", "general_structural"}:
            fe = wt.get("Fe", 0.0)
            c_frac = wt.get("C", 0.0)
            cr = wt.get("Cr", 0.0)
            exotic = (
                wt.get("Re", 0.0) + wt.get("Ta", 0.0) + wt.get("Hf", 0.0)
                + max(0.0, wt.get("W", 0.0) - 0.03) + max(0.0, wt.get("Co", 0.0) - 0.05)
            )
            carbon_factor = 1.0 if c_frac <= 0.015 else max(0.08, 1.0 - 18.0 * (c_frac - 0.015))
            chromium_factor = 1.0 if cr <= 0.08 else max(0.20, 1.0 - 4.0 * (cr - 0.08))
            factor = min(1.0, fe / 0.65) * carbon_factor * chromium_factor * max(0.05, 1.0 - 4.0 * exotic)
            return _apply_lightweight_alignment(factor), f"structural-alignment={factor:.2f}"

        if app == "carbon_steel":
            fe = wt.get("Fe", 0.0)
            c_frac = wt.get("C", 0.0)
            exotic = wt.get("Re", 0.0) + wt.get("Ta", 0.0) + wt.get("Hf", 0.0) + wt.get("W", 0.0)
            carbon_factor = 1.0 if 0.0005 <= c_frac <= 0.02 else 0.35
            factor = min(1.0, fe / 0.90) * carbon_factor * max(0.05, 1.0 - 5.0 * exotic)
            return _apply_lightweight_alignment(factor), f"carbon-steel-alignment={factor:.2f}"

        if app == "superalloy":
            ni_co = wt.get("Ni", 0.0) + wt.get("Co", 0.0)
            cr = wt.get("Cr", 0.0)
            low_melt = wt.get("Pb", 0.0) + wt.get("Cd", 0.0) + wt.get("Hg", 0.0) + wt.get("Bi", 0.0)
            factor = min(1.0, ni_co / 0.45) * min(1.0, max(cr, 0.02) / 0.08) * max(0.05, 1.0 - 8.0 * low_melt)
            return _apply_lightweight_alignment(factor), f"superalloy-alignment={factor:.2f}"

        if app == "cu_alloy":
            cu = wt.get("Cu", 0.0)
            factor = min(1.0, cu / 0.60)
            if family == "brass":
                factor *= min(1.0, max(wt.get("Zn", 0.0), 0.01) / 0.20)
            elif family in {"bronze", "phosphor_bronze"}:
                factor *= min(1.0, max(wt.get("Sn", 0.0), 0.01) / 0.05)
            elif family == "aluminum_bronze":
                factor *= min(1.0, max(wt.get("Al", 0.0), 0.01) / 0.04)
            elif family == "silicon_bronze":
                factor *= min(1.0, max(wt.get("Si", 0.0), 0.002) / 0.01)
            factor *= max(0.05, 1.0 - 4.0 * (wt.get("Re", 0.0) + wt.get("Ta", 0.0) + wt.get("Hf", 0.0)))
            return _apply_lightweight_alignment(factor), f"cu-alloy-alignment={factor:.2f}"

        if app == "ti_alloy":
            ti = wt.get("Ti", 0.0)
            off_family = wt.get("Ni", 0.0) + wt.get("Co", 0.0) + wt.get("Cu", 0.0) + wt.get("W", 0.0) + wt.get("Re", 0.0)
            factor = min(1.0, ti / 0.70) * max(0.05, 1.0 - 3.5 * off_family)
            return _apply_lightweight_alignment(factor), f"ti-alignment={factor:.2f}"

        if app == "al_alloy":
            al = wt.get("Al", 0.0)
            off_family = wt.get("W", 0.0) + wt.get("Re", 0.0) + wt.get("Ta", 0.0) + wt.get("Hf", 0.0) + wt.get("Nb", 0.0)
            factor = min(1.0, al / 0.80) * max(0.05, 1.0 - 4.0 * off_family)
            return _apply_lightweight_alignment(factor), f"al-alignment={factor:.2f}"

        if app == "nuclear":
            zr = wt.get("Zr", 0.0)
            off_family = wt.get("Ni", 0.0) + wt.get("Co", 0.0) + wt.get("Cu", 0.0) + wt.get("Re", 0.0)
            factor = min(1.0, zr / 0.78) * max(0.05, 1.0 - 4.5 * off_family)
            return _apply_lightweight_alignment(factor), f"nuclear-alignment={factor:.2f}"

        return _apply_lightweight_alignment(1.0), ""

    @staticmethod
    def evaluate(candidates, query="", T_K=298.0, weather=None, domains_focus=None,
                 constraints=None, dpa_rate=1e-7, pressure_MPa=0.0, research_data=None,
                 intent=None):
        """Evaluate candidates using the 42-domain physics engine.
        
        Score = raw physics composite_score. No additional penalty layers.
        """
        from physics.filter import run_all
        for cand in candidates:
            try:
                priority_map = research_data.domain_weights if research_data else None
                result = run_all(cand.composition, T_K=T_K, weather=weather, verbose=False,
                                 domains_focus=domains_focus, dpa_rate=dpa_rate,
                                 domain_priority=priority_map)
                cand.physics_result = result
                cand.physics_evaluated = True

                cand.score = result.get("composite_score", 0)
                weak = []
                for dr in result.get("domain_results", []):
                    if dr.score() < 50:
                        weak.append({"name": dr.domain_name, "score": dr.score(),
                                     "fails": [c.name for c in dr.checks if c.status == "FAIL"]})
                cand.weak_domains = weak
                cand.score_source = "physics"
                try:
                    from ml.predict import get_predictor
                    predictor = get_predictor()
                    if predictor.is_available():
                        cand.ml_predictions = predictor.predict(cand.composition) or {}
                except Exception:
                    pass
            except Exception as e:
                cand.score = 0.0
                cand.score_source = "physics_error"
                cand.physics_evaluated = True
                cand.physics_result = {"error": str(e)}
        return candidates


def _apply_constraints(cand, constraints):
    from physics.base import density_rule_of_mixtures, PREN_wt, wmean
    violations = []
    if constraints.get("min_PREN"):
        try:
            pren = PREN_wt(cand.composition)
            if pren < constraints["min_PREN"]:
                violations.append(f"PREN {pren:.1f} < {constraints['min_PREN']}")
        except Exception:
            pass
    if constraints.get("max_density"):
        d = density_rule_of_mixtures(cand.composition)
        if d and d > constraints["max_density"]:
            violations.append(f"Density {d:.2f} > {constraints['max_density']}")
    if constraints.get("min_yield_MPa"):
        hv = wmean(cand.composition, "vickers")
        est_yield = hv / 3.0 if hv else 0
        if est_yield < constraints["min_yield_MPa"]:
            violations.append(f"Est. yield {est_yield:.0f} < {constraints['min_yield_MPa']}")
    if constraints.get("max_melting_point_K"):
        tm = wmean(cand.composition, "Tm")
        if tm and tm > constraints["max_melting_point_K"]:
            violations.append(f"Melting point {tm:.0f} K > {constraints['max_melting_point_K']:.0f} K")
    if violations:
        cand.score = max(0, cand.score - 10 * len(violations))
        cand.weak_domains.append({"name": "Constraint Violations", "score": 0, "fails": violations})


class DomainCorrelator:
    CORRELATIONS = [
        {"domains": ("Thermodynamics", "Phase Stability"), "type": "synergy",
         "description": "Thermodynamic stability supports phase stability via mixing entropy."},
        {"domains": ("Mechanical", "Creep"), "type": "trade-off",
         "description": "Precipitation hardening degrades at high-T if precipitates coarsen."},
        {"domains": ("Corrosion", "Biocompatibility"), "type": "synergy",
         "description": "Both depend on stable passive oxide layer. High Cr and Ti benefit both."},
        {"domains": ("Mechanical", "Weldability"), "type": "trade-off",
         "description": "High carbon improves strength but increases HAZ cracking risk."},
        {"domains": ("Corrosion", "Oxidation"), "type": "synergy",
         "description": "Both rely on Cr-based passive layers. High PREN helps oxidation resistance."},
        {"domains": ("Thermal Properties", "Electronic Structure"), "type": "synergy",
         "description": "Wiedemann-Franz law: good electrical conductors are good thermal conductors."},
        {"domains": ("Fatigue & Fracture", "Hydrogen Embrittlement"), "type": "synergy",
         "description": "Both are crack-propagation phenomena. Austenitic structures help both."},
        {"domains": ("Creep", "Oxidation"), "type": "synergy",
         "description": "High-temp alloys need both. Ni-superalloys achieve this synergy naturally."},
        {"domains": ("Grain Boundary", "Weldability"), "type": "trade-off",
         "description": "Strong grain boundaries resist hot cracking but can make welding harder."},
        {"domains": ("Phase Stability", "Transformation Kinetics"), "type": "synergy",
         "description": "Phase-stable alloys resist unwanted transformations during service."},
        {"domains": ("Mechanical", "Formability"), "type": "trade-off",
         "description": "Stronger alloys are harder to form. Balance via TWIP/TRIP mechanisms."},
        {"domains": ("Corrosion", "Galvanic Compatibility"), "type": "synergy",
         "description": "High corrosion resistance gives favorable galvanic position."},
    ]

    @staticmethod
    def correlate(candidates):
        insights = []
        for cand in candidates[:5]:
            if not cand.physics_result or "domain_results" not in cand.physics_result:
                continue
            domain_scores = {dr.domain_name: dr.score() for dr in cand.physics_result["domain_results"]}
            for corr in DomainCorrelator.CORRELATIONS:
                d1, d2 = corr["domains"]
                s1, s2 = domain_scores.get(d1), domain_scores.get(d2)
                if s1 is None or s2 is None:
                    continue
                if corr["type"] == "synergy":
                    if s1 >= 70 and s2 >= 70:
                        insights.append({"type": "positive_synergy", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) show positive synergy. {corr['description']}"})
                    elif s1 < 40 and s2 < 40:
                        insights.append({"type": "coupled_weakness", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) are both weak and linked. {corr['description']}"})
                    elif abs(s1 - s2) > 30:
                        insights.append({"type": "broken_synergy", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"{d1} ({s1:.0f}) and {d2} ({s2:.0f}) usually correlated but diverge. {corr['description']}"})
                elif corr["type"] == "trade-off":
                    if s1 >= 70 and s2 < 40:
                        insights.append({"type": "active_tradeoff", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"Trade-off: {d1} ({s1:.0f}) strong but {d2} ({s2:.0f}) suffers. {corr['description']}"})
                    elif s2 >= 70 and s1 < 40:
                        insights.append({"type": "active_tradeoff", "domains": (d2, d1),
                                         "scores": (s2, s1),
                                         "message": f"Trade-off: {d2} ({s2:.0f}) strong but {d1} ({s1:.0f}) suffers. {corr['description']}"})
                    elif s1 >= 60 and s2 >= 60:
                        insights.append({"type": "resolved_tradeoff", "domains": (d1, d2),
                                         "scores": (s1, s2),
                                         "message": f"Trade-off resolved: Both {d1} ({s1:.0f}) and {d2} ({s2:.0f}) adequate. {corr['description']}"})
        seen = set()
        unique = []
        for ins in insights:
            key = (ins["type"], tuple(sorted(ins["domains"])))
            if key not in seen:
                seen.add(key)
                unique.append(ins)
        return unique[:15]


def _compute_ml_confidence(predictions: dict) -> float:
    if not predictions:
        return 50.0

    _RANGES = {
        "formation_energy": (-1.5, 1.5),
        "bulk_modulus":     (150.0, 150.0),
        "shear_modulus":    (80.0,  80.0),
        "yield_strength":   (500.0, 500.0),
        "UTS":              (700.0, 700.0),
    }

    scores = []
    for target, pred in predictions.items():
        if not isinstance(pred, dict):
            continue
        mean  = pred.get("mean",  None)
        sigma = pred.get("sigma", 0.0)
        if mean is None:
            continue

        centre, half = _RANGES.get(target, (mean, abs(mean) if mean != 0 else 1.0))

        if target == "formation_energy":
            raw = 100.0 * (1.0 - (mean - (centre - half)) / (2.0 * half))
        else:
            raw = 100.0 * (mean - (centre - half)) / (2.0 * half)
        raw = max(0.0, min(100.0, raw))

        rel_unc = (sigma / abs(mean)) if mean != 0 else 1.0
        penalty = max(0.0, 1.0 - rel_unc)
        scores.append(raw * penalty)

    if not scores:
        return 50.0
    return round(sum(scores) / len(scores), 2)


def _cheap_candidate_score(cand, intent: dict, query: str) -> float:
    comp = cand.composition_wt or cand.composition or {}
    must_include = intent.get("must_include") or []
    exclude = set(intent.get("exclude_elements") or [])
    research_data = intent.get("research_data")
    constraints = dict(intent.get("constraints", {}) or {})
    props = set(intent.get("target_properties") or [])

    must_score = 1.0
    if must_include:
        hits = sum(1 for symbol in must_include if comp.get(symbol, 0.0) > 0.004)
        must_score = hits / max(1, len(must_include))

    exclude_penalty = 1.0
    if exclude:
        bad_frac = sum(comp.get(symbol, 0.0) for symbol in exclude)
        exclude_penalty = max(0.05, 1.0 - 8.0 * bad_frac)

    # No family-based penalty — we want multi-family diversity
    density_multiplier = 1.0
    density_target = _density_target_for_intent(intent.get("application", ""), constraints, props, (query or "").lower())
    if density_target is not None:
        from physics.base import density_rule_of_mixtures

        mol_comp = cand.composition or wt_to_mol(_normalize_wt(comp))
        density = density_rule_of_mixtures(mol_comp)
        if density is not None and density > density_target:
            density_multiplier *= max(0.05, math.exp(-0.9 * (density - density_target)))

    return 100.0 * must_score * exclude_penalty * density_multiplier


def _downselect_candidates(candidates: list, limit: int, query: str, intent: dict) -> list:
    if limit <= 0 or len(candidates) <= limit:
        return candidates

    ranked = sorted(
        candidates,
        key=lambda cand: _cheap_candidate_score(cand, intent, query),
        reverse=True,
    )

    buckets = {}
    for cand in ranked:
        comp = cand.composition_wt or cand.composition or {}
        sig = _composition_signature(comp, top_n=3, min_frac=0.02)
        if not sig:
            sig = tuple(sorted(comp.keys())[:3])
        buckets.setdefault(sig, []).append(cand)

    selected = []
    while buckets and len(selected) < limit:
        for sig in list(buckets.keys()):
            if not buckets[sig]:
                buckets.pop(sig, None)
                continue
            selected.append(buckets[sig].pop(0))
            if not buckets[sig]:
                buckets.pop(sig, None)
            if len(selected) >= limit:
                break
    return selected


def _ml_prefilter(candidates: list, intent: dict, use_ml: bool = True, limit: int = 15) -> list:
    if not use_ml:
        return candidates

    try:
        from ml.predict import get_predictor
        predictor = get_predictor()
        if not predictor.is_available():
            return candidates

        target_yield = intent.get("constraints", {}).get("min_yield_MPa", 0) or 0

        scored = []
        for cand in candidates:
            try:
                preds = predictor.predict(cand.composition)
                cand.ml_predictions = preds or {}
            except Exception:
                cand.ml_predictions = {}
                cand.screening_score = max(float(cand.screening_score or 0.0), 50.0)
                if not cand.physics_evaluated:
                    cand.score = round(cand.screening_score, 2)
                    cand.score_source = "screen"
                scored.append((cand, 50.0))
                continue

            if target_yield > 0:
                ml_yield = (cand.ml_predictions
                            .get("yield_strength", {})
                            .get("mean", target_yield))
                if ml_yield < target_yield * 0.70:
                    continue

            ml_conf = _compute_ml_confidence(cand.ml_predictions)
             # Keep a provisional rank for candidates that never reach full physics.
            cand.screening_score = max(float(cand.screening_score or 0.0), ml_conf)
            if not cand.physics_evaluated:
                cand.score = round(cand.screening_score, 2)
                cand.score_source = "ml_prefilter"
            scored.append((cand, ml_conf))

        if not scored:
            logger.warning("[_ml_prefilter] All candidates filtered — returning full list")
            return candidates

        scored.sort(key=lambda x: -x[1])
        return [c for c, _ in scored[:max(1, limit)]]

    except Exception as e:
        logger.warning(f"[_ml_prefilter] Unexpected error ({e}); skipping ML pre-filter")
        return candidates


class Pipeline:
    def __init__(
        self,
        max_iterations=4,
        convergence_threshold=2.0,
        on_step=None,
        constraints=None,
        use_ml=False,
        target_score=85.0,
        feedback_limit=3,
        min_iterations=2,
    ):
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.on_step = on_step or (lambda s: None)
        self.constraints = constraints or {}
        self.use_ml = use_ml
        self.target_score = float(target_score)
        self.feedback_limit = max(1, int(feedback_limit))
        self.min_iterations = max(1, int(min_iterations))
        self.steps = []
        self.all_candidates = []
        self.best_score_history = []
        self.generation_stats = {
            "raw_generated": 0,
            "post_dedupe": 0,
            "downselected_for_physics": 0,
            "physics_evaluated": 0,
            "returned_candidates": 0,
            "iterations": [],
            "config": {
                "max_iterations": self.max_iterations,
                "target_score": self.target_score,
                "feedback_limit": self.feedback_limit,
                "min_iterations": self.min_iterations,
                "use_ml": self.use_ml,
            },
        }

    def _log(self, step_num, stage, thought, observation, agent=""):
        step = PipelineStep(step_num, stage, thought, observation, agent=agent)
        self.steps.append(step)
        self.on_step(step)
        return step

    def run(self, query, intent, T_K=298.0, weather=None, domains_focus=None,
            dpa_rate=1e-7, pressure_MPa=0.0):
        t0 = time.time()
        step_counter = 1

        self._log(
            step_counter,
            "input",
            f"Intent parsed: {_summarize_intent(intent, query)}",
            f"Raw input: '{query}'",
            agent="InputInterpreter",
        )
        step_counter += 1

        self._log(step_counter, "research", f"Researching application: '{query}'",
                  "Finding fundamental physical constraints...", agent="ApplicationResearcher")
        from engines.researcher import ApplicationResearcher
        try:
            research_data = ApplicationResearcher().research(query, intent=intent)
        except Exception as e:
            logger.error(f"Researcher LLM failed: {e}")
            try:
                research_data = ApplicationResearcher()._heuristic_research(query, intent=intent)
                research_data.fallback_reason = str(e)
                research_data.source = "heuristic"
            except Exception:
                research_data = None
        step_counter += 1

        if research_data:
            source = getattr(research_data, "source", "unknown")
            reason = getattr(research_data, "fallback_reason", "")
            obs = f"Base: {research_data.base_elements}, Domains: {research_data.primary_domains}, Source: {source}"
            if reason:
                obs += f", Fallback reason: {reason}"
            self._log(step_counter, "research", f"Research constraints ready (source={source})",
                      obs, agent="ApplicationResearcher")
        else:
            self._log(step_counter, "research", f"Research failed", "Proceeding with generic constraints", agent="ApplicationResearcher")
        step_counter += 1
        intent["research_data"] = research_data

        must_include, exclude_elements = _intent_required_elements(intent, query)
        # NOTE: We do NOT add the researcher's base element to must_include.
        # This allows the generator to explore multiple alloy families freely.

        intent["must_include"] = sorted(set((intent.get("must_include") or []) + must_include))
        intent["exclude_elements"] = sorted(set((intent.get("exclude_elements") or []) + exclude_elements))

        self._log(
            step_counter,
            "constraints",
            f"Generator constraints: must={intent.get('must_include') or []}, exclude={intent.get('exclude_elements') or []}",
            f"must_include={intent.get('must_include') or []}, exclude={intent.get('exclude_elements') or []}, "
            f"application={intent.get('application') or 'unknown'}, constraints={intent.get('constraints') or {}}",
            agent="InputInterpreter",
        )
        step_counter += 1

        self._log(step_counter, "baseline", f"Finding baseline for: '{query}'",
                  "Searching database + LLM...", agent="BaselinePredictor")
        step_counter += 1
        baseline = BaselinePredictor.predict(query, intent)
        if baseline:
            self._log(step_counter, "baseline", f"Baseline: {_fmt_comp(baseline.composition_wt)}",
                      baseline.rationale, agent="BaselinePredictor")
        else:
            self._log(step_counter, "baseline", "No direct match, generating from scratch",
                      "Using template generation", agent="BaselinePredictor")
        step_counter += 1
        best_score = 0.0
        improvement = 0
        iteration = 0
        converged = False
        stop_reason = "max_iterations"
        target_top_n = max(1, int(intent.get("n_results") or 10))
        generation_budget_total = max(int(intent.get("generation_budget") or 0), max(500, target_top_n * 50))
        physics_budget_total = max(int(intent.get("physics_budget") or 0), max(80, target_top_n * 8))
        generation_budget_iter = max(40, math.ceil(generation_budget_total / max(1, self.max_iterations)))
        physics_budget_iter = max(target_top_n * 3, math.ceil(physics_budget_total / max(1, self.max_iterations)))
        self._log(
            step_counter,
            "budget",
            f"Search budget: raw={generation_budget_total}, physics={physics_budget_total}",
            f"per_iteration_generate={generation_budget_iter}, per_iteration_physics={physics_budget_iter}, target_top_n={target_top_n}",
            agent="Pipeline",
        )
        step_counter += 1
        for iteration in range(self.max_iterations):
            feedback = None
            if iteration > 0:
                previous_pool = [c for c in self.all_candidates if c.physics_evaluated or c.weak_domains]
                if previous_pool:
                    feedback = _build_feedback(
                        previous_pool,
                        target_score=self.target_score,
                        limit=self.feedback_limit,
                    )
            self._log(step_counter, "generate",
                      f"Iteration {iteration + 1}: Generating compositions",
                      "Refining from compact cross-iteration feedback" if feedback else "Initial exploration",
                      agent="MultiCompGenerator")
            step_counter += 1
            candidates = MultiCompositionGenerator.generate(
                query, intent, baseline, n=generation_budget_iter, iteration=iteration, feedback=feedback)
            iter_stats = {
                "iteration": iteration + 1,
                "raw_generated": len(candidates),
            }
            self.generation_stats["raw_generated"] += len(candidates)
            pre_dedupe = len(candidates)
            candidates = _dedupe_candidates(candidates, similarity_threshold=0.04)
            post_dedupe_count = len(candidates)
            iter_stats["post_dedupe"] = post_dedupe_count
            self.generation_stats["post_dedupe"] += post_dedupe_count
            for cand in candidates:
                cand.iteration = iteration
                cand.screening_score = round(_cheap_candidate_score(cand, intent, query), 2)
                if not cand.physics_evaluated:
                    cand.score = cand.screening_score
                    cand.score_source = "screen"
            # No family-based filtering — we want multi-family diversity
            self.all_candidates.extend(candidates)
            if post_dedupe_count != pre_dedupe:
                self._log(step_counter, "dedupe",
                          f"Removed repeats: {pre_dedupe} -> {post_dedupe_count}",
                          "Dropped duplicate/near-duplicate compositions",
                          agent="MultiCompGenerator")
                step_counter += 1
            if self.use_ml:
                pre_count = len(candidates)
                candidates = _ml_prefilter(candidates, intent, use_ml=True, limit=max(physics_budget_iter * 2, physics_budget_iter))
                self._log(step_counter, "ml_prefilter",
                          f"ML pre-filter: {pre_count} -> {len(candidates)} candidates",
                          "Dropped low-yield predictions, re-ranked by ML confidence",
                          agent="MLPrefilter")
                step_counter += 1

            pre_screen = len(candidates)
            shortlisted = _downselect_candidates(candidates, physics_budget_iter, query, intent)
            iter_stats["downselected_for_physics"] = len(shortlisted)
            iter_stats["screened_out_before_physics"] = max(0, len(candidates) - len(shortlisted))
            self.generation_stats["downselected_for_physics"] += len(shortlisted)
            if len(shortlisted) != pre_screen:
                self._log(step_counter, "screen",
                          f"Physics shortlist: {pre_screen} -> {len(shortlisted)}",
                          "Cheap intent-alignment ranking + diversity round-robin before full physics",
                          agent="Pipeline")
                step_counter += 1

            self._log(step_counter, "evaluate",
                      f"Evaluating {len(shortlisted)} candidates",
                      "Running physics + ML...", agent="PhysicsMLEvaluator")
            step_counter += 1
            self.generation_stats["physics_evaluated"] += len(shortlisted)
            iter_stats["physics_evaluated"] = len(shortlisted)
            shortlisted = PhysicsMLEvaluator.evaluate(
                shortlisted, query=query, T_K=T_K, weather=weather, domains_focus=domains_focus,
                constraints=self.constraints, dpa_rate=dpa_rate, pressure_MPa=pressure_MPa,
                research_data=research_data, intent=intent)

            if self.use_ml:
                n_combined = 0
                for cand in shortlisted:
                    if cand.ml_predictions:
                        ml_conf = _compute_ml_confidence(cand.ml_predictions)
                        cand.score = round(0.6 * cand.score + 0.4 * ml_conf, 2)
                        cand.score_source = "physics_ml"
                        n_combined += 1
                if n_combined:
                    logger.debug(f"[Pipeline] Combined score applied to {n_combined} candidates")
            iter_best = max((c.score for c in shortlisted), default=0)
            improvement = iter_best - best_score
            best_score = max(best_score, iter_best)
            self.best_score_history.append(best_score)
            self._log(step_counter, "evaluate",
                      f"Best: {iter_best:.1f}/100 (delta {improvement:+.1f})",
                      f"Overall best: {best_score:.1f}/100", agent="PhysicsMLEvaluator")
            step_counter += 1
            iter_stats["master_pool_after_iteration"] = len(self.all_candidates)
            self.generation_stats["iterations"].append(iter_stats)
            if best_score >= self.target_score:
                converged = True
                stop_reason = "target_score_reached"
                self._log(
                    step_counter,
                    "converge",
                    f"Target reached ({best_score:.1f}/{self.target_score:.1f})",
                    "Stopping early to save time and tokens",
                    agent="Pipeline",
                )
                step_counter += 1
                break
            if iteration + 1 >= self.min_iterations and improvement < self.convergence_threshold and best_score >= max(70.0, self.target_score - 15.0):
                converged = True
                stop_reason = "converged"
                self._log(step_counter, "converge", "Converged", "Further improvement looks marginal", agent="Pipeline")
                step_counter += 1
                break
        pre_final_dedupe = len(self.all_candidates)
        self.all_candidates = _dedupe_candidates(self.all_candidates, similarity_threshold=0.03)
        if len(self.all_candidates) != pre_final_dedupe:
            self._log(step_counter, "dedupe",
                      f"Cross-iteration unique set: {pre_final_dedupe} -> {len(self.all_candidates)}",
                      "Keeping only unique candidate compositions",
                      agent="Pipeline")
            step_counter += 1
        self.all_candidates.sort(key=_candidate_sort_key, reverse=True)
        self.generation_stats["returned_candidates"] = len(self.all_candidates)
        self.generation_stats["stop_reason"] = stop_reason
        self._log(step_counter, "correlate", "Analyzing cross-domain correlations",
                  "Finding synergies...", agent="DomainCorrelator")
        step_counter += 1
        correlation_insights = DomainCorrelator.correlate(self.all_candidates)
        explanation = ""
        try:
            from llms.explainer import synthesize_explanation
            explanation = synthesize_explanation(query, self.all_candidates[:3], correlation_insights)
        except Exception:
            pass
        self._log(step_counter, "explain", "Synthesizing explanation",
                  f"{len(correlation_insights)} correlations found", agent="Explainer")
        return PipelineResult(
            candidates=self.all_candidates, steps=self.steps, baseline=baseline,
            iterations_run=iteration + 1,
            converged=converged,
            best_score=best_score, total_time=time.time() - t0,
            explanation=explanation, correlation_insights=correlation_insights,
            generation_stats=self.generation_stats,
            mode=intent.get("mode", "design"))


def _fmt_comp(comp, top=6):
    return "  ".join(f"{s}:{v*100:.1f}%" for s, v in sorted(comp.items(), key=lambda x: -x[1])[:top])


def _composition_distance(comp_a, comp_b):
    keys = set(comp_a) | set(comp_b)
    return sum(abs(comp_a.get(k, 0.0) - comp_b.get(k, 0.0)) for k in keys)


def _composition_signature(comp, top_n=4, min_frac=0.03):
    ranked = sorted(comp.items(), key=lambda item: (-item[1], item[0]))
    return tuple(sym for sym, frac in ranked[:top_n] if frac >= min_frac)


def _dedupe_candidates(candidates, similarity_threshold=0.02):
    # Keep highest scoring instances first where possible.
    ranked = sorted(candidates, key=_candidate_sort_key, reverse=True)
    unique = []
    for cand in ranked:
        comp = cand.composition_wt or cand.composition or {}
        if not comp:
            continue
        cand_sig = _composition_signature(comp)
        if any(
            _composition_distance(comp, (u.composition_wt or u.composition or {})) <= similarity_threshold
            or (
                cand_sig
                and cand_sig == _composition_signature(u.composition_wt or u.composition or {})
                and _composition_distance(comp, (u.composition_wt or u.composition or {})) <= similarity_threshold * 2.5
            )
            for u in unique
        ):
            continue
        unique.append(cand)
    return unique


def _candidate_physics_score(candidate):
    physics = getattr(candidate, "physics_result", None) or {}
    score = physics.get("composite_score")
    return float(score) if score is not None else None


def _candidate_rank_score(candidate):
    return float(getattr(candidate, "score", 0.0) or 0.0)


def _candidate_sort_key(candidate):
    physics_score = _candidate_physics_score(candidate)
    screening_score = float(getattr(candidate, "screening_score", 0.0) or 0.0)
    rank_score = _candidate_rank_score(candidate)
    physics_first = 1 if getattr(candidate, "physics_evaluated", False) else 0
    return (
        physics_first,
        rank_score if physics_first else screening_score,
        physics_score if physics_score is not None else -1.0,
        screening_score,
    )


def _build_feedback(candidates, target_score=85.0, limit=3):
    if not candidates:
        return {"best_score": 0, "weak_summary": "no data", "weak_details": [], "failure_examples": []}
    ranked = sorted(candidates, key=_candidate_sort_key, reverse=True)
    best = ranked[0]
    all_weak = {}
    for c in ranked:
        for w in c.weak_domains:
            name = w["name"]
            if name not in all_weak or w["score"] < all_weak[name]["score"]:
                all_weak[name] = w
    weak_sorted = sorted(all_weak.values(), key=lambda w: w["score"])[:5]
    failures = []
    seen_signatures = set()
    for cand in ranked:
        comp = cand.composition_wt or cand.composition or {}
        if not comp:
            continue
        signature = _composition_signature(comp, top_n=4, min_frac=0.02)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        weak = sorted(cand.weak_domains, key=lambda item: item.get("score", 100))
        main_issue = weak[0]["name"] if weak else ("missed target score" if cand.score < target_score else "improve margins")
        failures.append(
            {
                "score": round(float(cand.score or 0.0), 2),
                "composition": comp,
                "composition_summary": _compact_comp(comp, top=5, digits=2),
                "main_issue": main_issue,
                "physics_evaluated": bool(cand.physics_evaluated),
            }
        )
        if len(failures) >= max(1, int(limit)):
            break
    return {
        "best_score": best.score,
        "top_candidate": best.composition_wt,
        "weak_summary": ", ".join(w["name"] for w in weak_sorted) if weak_sorted else "none",
        "weak_details": weak_sorted,
        "failure_examples": failures,
    }


def run_pipeline(query, intent, on_step=None, max_iterations=4, T_K=298.0,
                 weather=None, constraints=None, dpa_rate=1e-7, pressure_MPa=0.0,
                 use_ml=False, target_score=85.0, feedback_limit=3, min_iterations=2):
    merged = dict(intent.get("constraints", {}))
    if constraints:
        merged.update(constraints)
    pipeline = Pipeline(max_iterations=max_iterations, on_step=on_step,
                        constraints=merged, use_ml=use_ml,
                        target_score=target_score, feedback_limit=feedback_limit,
                        min_iterations=min_iterations)
    return pipeline.run(query=query, intent=intent, T_K=T_K, weather=weather,
                        domains_focus=intent.get("domains_focus"), dpa_rate=dpa_rate,
                        pressure_MPa=pressure_MPa)
