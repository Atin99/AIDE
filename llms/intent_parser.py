import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alloy_db import lookup_alloy
from core.elements import available as available_elements
from core.query_parser import parse_query
from llms.client import ProviderUnavailableError
from llms.client import chat_json, is_available as llm_available

logger = logging.getLogger("AIDE.intent")

MODES = ["design", "modify", "study", "compare", "explore", "geometry", "chat"]

INTENT_SCHEMA = {
    "mode": "design|modify|study|compare|explore|geometry|chat",
    "alloy_name": None,
    "alloy_name_2": None,
    "composition": None,
    "composition_2": None,
    "target_properties": [],
    "problem": None,
    "domains_focus": [],
    "study_topic": None,
    "geometry": None,
    "loading": None,
    "temperature_K": None,
    "environment": None,
    "n_elements": None,
    "n_results": None,
    "constraints": {},
    "base_element": None,
    "only_elements": None,
    "must_include": [],
    "exclude_elements": [],
    "application": None,
    "chat_response": None,
    "notes": ""
}

SYSTEM_PROMPT = """You are AIDE intent extraction engine.
Task: convert one user message into exactly one strict JSON object.
Rules:
1. Return only JSON. No prose. No markdown. No code fences.
2. Use one mode from: design, modify, study, compare, explore, geometry, chat.
3. If user asks comparison, mode must be compare.
4. If user asks explanation/theory only, mode must be study.
5. If user asks greeting/help only, mode must be chat.
6. Otherwise default mode is design.
7. Keep constraints numeric when possible.
8. Preserve explicit element constraints and compositions.
9. Notes must contain the original user intent in short form.
10. Unknown fields are not allowed."""

APPLICATION_DEFAULT_PROPERTIES = {
    "fusible_alloy": ["low_melting_point"],
    "electronic_alloy": ["conductivity", "thermal_stability"],
    "stainless": ["corrosion_resistance", "oxidation_resistance"],
    "structural": ["high_strength", "fatigue_resistance"],
    "superalloy": ["high_temperature_strength", "creep_resistance", "oxidation_resistance"],
    "ti_alloy": ["high_strength", "low_density", "fatigue_resistance"],
    "al_alloy": ["low_density", "high_strength"],
    "nuclear": ["radiation_resistance", "corrosion_resistance"],
    "biomedical": ["biocompatibility", "corrosion_resistance"],
    "refractory": ["high_temperature_strength", "creep_resistance"],
    "hea": ["high_strength", "thermal_stability"],
    "carbon_steel": ["high_strength", "weldability"],
    "cu_alloy": ["conductivity"],
    "open_alloy": ["high_strength"],
    "general_structural": ["high_strength"],
}

PROPERTY_KEYWORDS = {
    "low_melting_point": ["low melting", "low-melting", "fusible", "solder", "reflow", "liquid metal", "thermal fuse", "melt below"],
    "corrosion_resistance": ["corrosion", "rust", "pitting", "chloride", "seawater", "marine"],
    "oxidation_resistance": ["oxidation", "scale", "hot corrosion"],
    "creep_resistance": ["creep", "stress rupture"],
    "high_temperature_strength": ["high temperature", "elevated temperature", "hot section", "turbine", "jet"],
    "fatigue_resistance": ["fatigue", "cyclic", "high cycle", "low cycle"],
    "high_strength": ["strength", "strong", "yield", "ultimate tensile", "uts"],
    "hardness": ["hardness", "hard", "harden"],
    "wear_resistance": ["wear", "abrasion", "erosion", "galling", "tribology"],
    "weldability": ["weld", "weldability"],
    "low_density": ["lightweight", "low density", "mass critical", "weight critical"],
    "conductivity": ["conductivity", "electrical", "wire", "busbar", "conductive", "chip", "interconnect", "bond wire", "leadframe", "packaging"],
    "biocompatibility": ["biocompatible", "implant", "medical", "surgical", "dental"],
    "radiation_resistance": ["radiation", "reactor", "nuclear", "dpa"],
    "thermal_stability": ["phase stability", "thermal stability", "stability"],
}

ELEMENT_ALIAS = {
    "Ni": ["ni", "nickel"],
    "Co": ["co", "cobalt"],
    "Cr": ["cr", "chromium"],
    "Mo": ["mo", "molybdenum"],
    "Cu": ["cu", "copper"],
    "Ag": ["ag", "silver"],
    "Au": ["au", "gold"],
    "Al": ["al", "aluminum", "aluminium"],
    "Ti": ["ti", "titanium"],
    "V": ["v", "vanadium"],
    "W": ["w", "tungsten", "wolfram"],
    "Re": ["re", "rhenium"],
    "Ta": ["ta", "tantalum"],
    "Hf": ["hf", "hafnium"],
    "Pb": ["pb", "lead"],
    "Cd": ["cd", "cadmium"],
    "Sn": ["sn", "tin"],
    "Bi": ["bi", "bismuth"],
    "In": ["in", "indium"],
    "Ga": ["ga", "gallium"],
    "Ge": ["ge", "germanium"],
    "Si": ["si", "silicon"],
    "C": ["carbon", "c"],
}

ELEMENT_SET = set(available_elements())


def classify_intent(query, memory=None):
    query = (query or "").strip()
    if not query:
        result = _empty_result("")
        result["classifier_source"] = "empty_query"
        result["intent_core"] = {
            "application": "general_structural",
            "required_properties": ["high_strength"],
            "constraints": {},
        }
        result["intent_debug"] = [{"stage": "input", "status": "empty"}]
        return result

    debug = []
    fallback = _rule_based_intent(query)
    best = dict(fallback)
    source = "rule_based"
    debug.append({"stage": "rule_parse", "status": "ok"})

    if llm_available():
        try:
            remote = _ask_llm(query, memory)
            if isinstance(remote, dict):
                best = _merge_intents(fallback, remote, query)
                source = "remote_llm+rule"
                debug.append({"stage": "remote_llm", "status": "ok"})
            else:
                debug.append({"stage": "remote_llm", "status": "empty"})
        except ProviderUnavailableError as err:
            debug.append({"stage": "remote_llm", "status": "unavailable", "reason": str(err)})
        except Exception as err:
            logger.warning("Remote intent parse failed: %s", err)
            debug.append({"stage": "remote_llm", "status": "failed", "reason": str(err)})
    else:
        debug.append({"stage": "remote_llm", "status": "disabled", "reason": "no_remote_api_key"})

    clean = _validate_and_enrich(query, best)
    clean = _enforce_structured_core(clean, query)
    clean["classifier_source"] = source
    clean["intent_core"] = {
        "application": clean.get("application") or "general_structural",
        "required_properties": list(clean.get("target_properties", [])),
        "constraints": dict(clean.get("constraints", {})),
    }
    clean["intent_debug"] = debug
    return clean


def _merge_intents(rule_intent, llm_intent, query):
    merged = dict(rule_intent)
    for key, value in llm_intent.items():
        if key not in merged:
            continue
        if value in (None, "", [], {}):
            continue
        if key in {"must_include", "exclude_elements", "target_properties", "domains_focus"}:
            merged[key] = _unique(merged.get(key, []) + list(value))
        elif key == "constraints" and isinstance(value, dict):
            merged_constraints = dict(merged.get("constraints", {}))
            merged_constraints.update(value)
            merged["constraints"] = merged_constraints
        else:
            merged[key] = value
    merged.setdefault("notes", query)
    return merged


def _rule_based_intent(query):
    q = query.lower()
    result = _empty_result(query)

    parsed = parse_query(query)
    _apply_query_parser(result, parsed)
    explicit_comp = _extract_explicit_composition(query)
    if explicit_comp:
        result["composition"] = explicit_comp
        if not result.get("only_elements"):
            result["only_elements"] = sorted(explicit_comp.keys())

    _extract_temperature(result, q)
    _extract_environment(result, q)
    result["target_properties"] = _extract_target_properties(q)
    result["application"] = result.get("application") or _extract_application(q, result["target_properties"])
    result["constraints"] = _extract_constraints(q, parsed)

    _extract_element_exclusions_from_text(result, q)

    if _is_simple_chat(q):
        result["mode"] = "chat"
        result["chat_response"] = "I can design alloys, compare alloys, and analyze compositions. Tell me your application and constraints."
        result["notes"] = query
        return _enforce_structured_core(result, query)

    if _looks_like_compare(q):
        left, right = _split_compare_query(query)
        name_1, comp_1 = _lookup_alloy_phrase(left)
        name_2, comp_2 = _lookup_alloy_phrase(right)

        result["mode"] = "compare"
        result["alloy_name"] = name_1 or (left.strip() if left.strip() else None)
        result["alloy_name_2"] = name_2 or (right.strip() if right.strip() else None)
        result["composition"] = comp_1
        result["composition_2"] = comp_2
        result["notes"] = f"compare {left.strip()} vs {right.strip()}".strip()
        return _enforce_structured_core(result, query)

    if not explicit_comp:
        alloy_name, composition = _lookup_alloy_phrase(query)
        if alloy_name:
            result["alloy_name"] = alloy_name
            result["composition"] = composition

    if _looks_like_modify(q):
        result["mode"] = "modify"
    elif _looks_like_geometry(q):
        result["mode"] = "geometry"
    elif _looks_like_explore(q):
        result["mode"] = "explore"
    elif _looks_like_study(q):
        result["mode"] = "study"
        result["study_topic"] = query
    else:
        result["mode"] = "design"

    result["notes"] = query
    return _enforce_structured_core(result, query)


def _apply_query_parser(result, parsed):
    if not parsed:
        return

    if parsed.get("application"):
        result["application"] = parsed.get("application")
    if parsed.get("only_elements"):
        result["only_elements"] = list(parsed.get("only_elements", []))
    if parsed.get("must_include"):
        result["must_include"] = _unique(result.get("must_include", []) + list(parsed.get("must_include", [])))
    if parsed.get("exclude_elements"):
        result["exclude_elements"] = _unique(result.get("exclude_elements", []) + list(parsed.get("exclude_elements", [])))
    if parsed.get("T_op_K") and not result.get("temperature_K"):
        result["temperature_K"] = float(parsed["T_op_K"])

    if parsed.get("min_PREN"):
        result.setdefault("constraints", {})
        result["constraints"]["min_PREN"] = float(parsed["min_PREN"])

    min_e = parsed.get("min_elements")
    max_e = parsed.get("max_elements")
    if min_e and max_e and min_e == max_e and min_e >= 2:
        result["n_elements"] = int(min_e)


def _extract_temperature(result, q):
    if result.get("temperature_K"):
        return
    m_c = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:deg(?:ree)?s?)?\s*c\b", q)
    if m_c:
        result["temperature_K"] = round(float(m_c.group(1)) + 273.15, 2)
        return
    m_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", q)
    if m_k:
        result["temperature_K"] = round(float(m_k.group(1)), 2)


def _extract_environment(result, q):
    if result.get("environment"):
        return
    env_map = [
        ("marine", "mumbai_coastal"),
        ("ocean", "mumbai_coastal"),
        ("coastal", "mumbai_coastal"),
        ("offshore", "offshore_arabian"),
        ("seawater", "mumbai_coastal"),
        ("chloride", "mumbai_coastal"),
        ("reactor", "reactor_primary_loop"),
    ]
    for key, env in env_map:
        if key in q:
            result["environment"] = env
            return


def _extract_target_properties(q):
    props = []
    for prop, markers in PROPERTY_KEYWORDS.items():
        if any(marker in q for marker in markers):
            props.append(prop)
    fuse_wire_markers = ["fuse wire", "fusible wire", "fuse alloy", "fusible alloy", "thermal fuse"]
    explicit_electrical_markers = [
        "high conductivity", "electrical conductivity", "low resistance", "resistive heating",
        "current rating", "ampere", "amperage", "circuit protection", "overcurrent",
    ]
    if any(marker in q for marker in fuse_wire_markers) and not any(marker in q for marker in explicit_electrical_markers):
        props = [prop for prop in props if prop != "conductivity"]
        if "low_melting_point" not in props:
            props.append("low_melting_point")
    if re.search(r"\b(\d{3,4})\s*c\b", q):
        if "high_temperature_strength" not in props:
            props.append("high_temperature_strength")
        if "creep_resistance" not in props:
            props.append("creep_resistance")
    return props


def _extract_application(q, props=None):
    props = props or []

    if any(k in q for k in ["any alloy", "any composition", "unrestricted composition", "any elements", "no element restriction"]):
        return "open_alloy"
    if any(k in q for k in ["fuse alloy", "fuse wire", "fusible", "fusible wire", "low melting", "low-melting", "solder", "solder alloy", "thermal fuse", "fusible link", "braze filler", "liquid metal"]):
        return "fusible_alloy"
    if any(k in q for k in ["chip alloy", "chip package", "semiconductor", "interconnect", "bond wire", "wire bond", "solder bump", "leadframe", "microelectronics", "electronic packaging"]):
        return "electronic_alloy"
    if any(k in q for k in ["stainless", "duplex", "pitting", "chloride"]):
        return "stainless"
    if any(k in q for k in ["marine", "offshore", "seawater"]) and "steel" in q:
        return "stainless"

    if any(k in q for k in ["inconel", "superalloy", "turbine", "jet", "gas path", "hot section"]):
        return "superalloy"
    if any(k in q for k in ["titanium", "ti-6", "ti alloy", "ti64"]):
        return "ti_alloy"
    if any(k in q for k in ["aluminum", "aluminium", "duralumin", "7xxx", "6xxx", "2xxx"]):
        return "al_alloy"
    if any(k in q for k in ["nuclear", "reactor", "zircaloy", "cladding"]):
        return "nuclear"
    if any(k in q for k in ["implant", "biomedical", "surgical", "dental", "hip", "knee"]):
        return "biomedical"
    if any(k in q for k in ["high entropy", "hea", "cantor", "multiprincipal"]):
        return "hea"
    if any(k in q for k in ["refractory", "ultra high temperature", "above 1200", "1200c", "1500c"]):
        return "refractory"
    if any(k in q for k in ["wire", "busbar", "electrical connector", "copper alloy", "brass", "bronze"]):
        return "cu_alloy"
    if any(k in q for k in ["tool steel", "die steel", "hardfacing", "abrasive slurry"]):
        return "carbon_steel"
    if any(k in q for k in ["carbon steel", "mild steel", "plain carbon"]):
        return "carbon_steel"
    if "steel" in q:
        return "structural"

    if "low_density" in props:
        return "al_alloy"
    if "biocompatibility" in props:
        return "biomedical"
    if "low_melting_point" in props:
        return "fusible_alloy"
    if "conductivity" in props:
        return "electronic_alloy"
    if "high_temperature_strength" in props or "creep_resistance" in props:
        return "superalloy"

    return None


def _extract_constraints(q, parsed):
    constraints = {}

    if parsed and parsed.get("min_PREN"):
        constraints["min_PREN"] = float(parsed["min_PREN"])

    if re.search(r"\b(?:low[-\s]?cost|budget|cheap|cost\s*sensitive|cost-sensitive)\b", q):
        constraints["cost_level"] = "low"

    m_yield = re.search(r"(?:yield|strength)\s*(?:>=|>|at least|minimum|min)?\s*(\d{3,4})\s*mpa", q)
    if m_yield:
        constraints["min_yield_MPa"] = float(m_yield.group(1))

    m_density = re.search(r"(?:density|max density|rho)\s*(?:<=|<|under|below|max)?\s*(\d+(?:\.\d+)?)\s*(?:g/cc|g/cm3|g/cm\^3)", q)
    if m_density:
        constraints["max_density"] = float(m_density.group(1))

    if re.search(r"\bnon[-\s]?magnetic\b", q):
        constraints["non_magnetic"] = True

    if re.search(r"\bno\s+ni\b|\bnickel[-\s]?free\b|\bni[-\s]?free\b|\bwithout\s+nickel\b", q):
        constraints["no_ni"] = True
    if re.search(r"\bno\s+co\b|\bcobalt[-\s]?free\b|\bco[-\s]?free\b|\bwithout\s+cobalt\b", q):
        constraints["no_co"] = True
    if re.search(r"\blead[-\s]?free\b|\bpb[-\s]?free\b|\bwithout\s+lead\b", q):
        constraints["no_pb"] = True
    if re.search(r"\bcadmium[-\s]?free\b|\bcd[-\s]?free\b|\bwithout\s+cadmium\b", q):
        constraints["no_cd"] = True
    if re.search(r"\brohs\b", q):
        constraints["rohs_compliant"] = True

    m_liquidus_c = re.search(r"(?:liquidus|melting(?:\s+point)?)\s*(?:<=|<|under|below|max(?:imum)?)\s*(\d+(?:\.\d+)?)\s*(?:deg(?:ree)?s?)?\s*c\b", q)
    if m_liquidus_c:
        constraints["max_melting_point_K"] = round(float(m_liquidus_c.group(1)) + 273.15, 2)
    m_liquidus_k = re.search(r"(?:liquidus|melting(?:\s+point)?)\s*(?:<=|<|under|below|max(?:imum)?)\s*(\d+(?:\.\d+)?)\s*k\b", q)
    if m_liquidus_k:
        constraints["max_melting_point_K"] = round(float(m_liquidus_k.group(1)), 2)

    return constraints


def _extract_explicit_composition(text):
    if not text:
        return None
    matches = re.findall(
        r"\b([A-Z][a-z]?)\s*(?:[:=]\s*|\s+)(\d+(?:\.\d+)?)\s*(?:wt%|at%|mass%|%)?",
        text,
    )
    if len(matches) < 2:
        return None

    comp = {}
    for symbol, val in matches:
        if symbol not in ELEMENT_SET:
            continue
        try:
            num = float(val)
        except Exception:
            continue
        if num <= 0:
            continue
        comp[symbol] = num

    if len(comp) < 2:
        return None

    total = sum(comp.values())
    if total <= 0:
        return None
    if total > 1.5:
        comp = {k: v / 100.0 for k, v in comp.items()}
    total = sum(comp.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in comp.items()}


def _extract_element_exclusions_from_text(result, q):
    for symbol, aliases in ELEMENT_ALIAS.items():
        for alias in aliases:
            patterns = [
                rf"\bno\s+{re.escape(alias)}\b",
                rf"\bwithout\s+{re.escape(alias)}\b",
                rf"\b{re.escape(alias)}[-\s]?free\b",
            ]
            if any(re.search(p, q) for p in patterns):
                if symbol not in result["exclude_elements"]:
                    result["exclude_elements"].append(symbol)
                break


def _apply_family_guidance(result, q):
    family = None
    if "aluminum bronze" in q or "aluminium bronze" in q:
        family = "aluminum_bronze"
    elif "phosphor bronze" in q:
        family = "phosphor_bronze"
    elif "silicon bronze" in q:
        family = "silicon_bronze"
    elif "bronze" in q:
        family = "bronze"
    elif "brass" in q:
        family = "brass"

    if not family:
        return

    result["application"] = "cu_alloy"
    result["constraints"]["alloy_family"] = family

    def add_must(symbol):
        if symbol not in result["exclude_elements"] and symbol not in result["must_include"]:
            result["must_include"].append(symbol)

    def add_prop(prop):
        if prop not in result["target_properties"]:
            result["target_properties"].append(prop)

    conductivity_markers = PROPERTY_KEYWORDS.get("conductivity", [])
    explicit_conductivity = any(marker in q for marker in conductivity_markers)

    add_must("Cu")

    if family == "brass":
        add_must("Zn")
        add_prop("corrosion_resistance")
        if explicit_conductivity or "conductivity" not in result["target_properties"]:
            add_prop("conductivity")
        return

    if "conductivity" in result["target_properties"] and not explicit_conductivity:
        result["target_properties"] = [prop for prop in result["target_properties"] if prop != "conductivity"]

    if family == "bronze":
        add_must("Sn")
        add_prop("wear_resistance")
        add_prop("corrosion_resistance")
    elif family == "aluminum_bronze":
        add_must("Al")
        add_prop("high_strength")
        add_prop("wear_resistance")
        add_prop("corrosion_resistance")
    elif family == "phosphor_bronze":
        add_must("Sn")
        add_must("P")
        add_prop("fatigue_resistance")
        add_prop("wear_resistance")
        add_prop("corrosion_resistance")
    elif family == "silicon_bronze":
        add_must("Si")
        add_prop("corrosion_resistance")
        add_prop("weldability")


def _is_simple_chat(q):
    chat_markers = [
        "hi", "hello", "hey", "thanks", "thank you", "who are you",
        "what can you do", "help", "good morning", "good evening",
    ]
    has_chat = any(marker in q for marker in chat_markers)
    has_material_signal = any(
        marker in q for marker in [
            "alloy", "steel", "inconel", "titanium", "aluminum", "aluminium",
            "corrosion", "weld", "strength", "composition", "design",
            "compare", "modify", "study", "material",
        ]
    )
    token_count = len(q.split())
    return has_chat and not has_material_signal and token_count <= 8


def _looks_like_compare(q):
    return any(k in q for k in [" vs ", " versus ", " compare ", " against "])


def _split_compare_query(query):
    lowered = query.lower()
    for sep in [" versus ", " vs ", " against "]:
        idx = lowered.find(sep)
        if idx >= 0:
            left = query[:idx]
            right = query[idx + len(sep):]
            left = re.sub(r"^\s*compare\s+", "", left, flags=re.IGNORECASE)
            return left.strip(), right.strip()
    m = re.search(r"compare\s+(.+?)\s+and\s+(.+)", query, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return query.strip(), ""


def _lookup_alloy_phrase(text):
    clean = (text or "").strip().strip(",.;:")
    if not clean:
        return None, None

    direct = lookup_alloy(clean)
    if direct:
        return direct["key"], direct.get("composition_wt")

    parts = [p.strip() for p in re.split(r"[,\|/]", clean) if p.strip()]
    for part in parts:
        found = lookup_alloy(part)
        if found:
            return found["key"], found.get("composition_wt")

    candidate_tokens = re.findall(r"\b[A-Za-z]*\d+[A-Za-z0-9\-]*\b", clean)
    candidate_tokens = [tok for tok in candidate_tokens if re.search(r"[A-Za-z]", tok)]
    keyword_tokens = re.findall(
        r"\b(?:inconel|zircaloy|duralumin|waspaloy|stellite|cantor)\b",
        clean,
        flags=re.IGNORECASE,
    )
    tokens = list(dict.fromkeys(candidate_tokens + keyword_tokens))
    for token in tokens:
        found = lookup_alloy(token)
        if found:
            return found["key"], found.get("composition_wt")

    return None, None


def _looks_like_modify(q):
    return any(k in q for k in [
        "modify", "improve", "optimize", "tune", "fix", "upgrade", "increase", "reduce"
    ])


def _looks_like_geometry(q):
    return any(k in q for k in [
        "geometry", "beam", "plate", "thickness", "stress", "strain", "load",
        "pressure vessel", "safety factor", "mechanical design",
    ])


def _looks_like_explore(q):
    return any(k in q for k in [
        "find", "search", "scan", "list", "top", "best", "explore", "across"
    ]) and "compare" not in q


def _looks_like_study(q):
    return any(k in q for k in [
        "what is", "explain", "why", "how", "theory", "concept",
        "difference between", "tell me about", "study",
    ])


def _ask_llm(query, memory=None):
    schema_text = json.dumps(INTENT_SCHEMA, ensure_ascii=True)
    system_prompt = (
        SYSTEM_PROMPT
        + "\nReturn valid JSON only."
        + "\nSchema:\n"
        + schema_text
    )
    messages = [{"role": "system", "content": system_prompt}]
    if memory:
        context = memory.get_context_for_llm()
        if context:
            messages.extend(context)
    messages.append({"role": "user", "content": query})
    return chat_json(messages, max_tokens=900, temperature=0.0, retries=2)


def _validate_and_enrich(query, llm_result):
    clean = _empty_result(query)
    for key, value in llm_result.items():
        if key in clean and value is not None:
            clean[key] = value
    if clean["mode"] not in MODES:
        clean["mode"] = "design"
    for key in ("target_properties", "domains_focus", "must_include", "exclude_elements"):
        if not isinstance(clean.get(key), list):
            clean[key] = []
    if not isinstance(clean.get("constraints"), dict):
        clean["constraints"] = {}
    _resolve_alloy(clean, "alloy_name", "composition")
    _resolve_alloy(clean, "alloy_name_2", "composition_2")
    if clean["mode"] != "compare":
        clean["alloy_name_2"] = None
        clean["composition_2"] = None
    if clean["mode"] != "study":
        clean["study_topic"] = None
    if clean["mode"] != "chat":
        clean["chat_response"] = None
    if not clean.get("notes"):
        clean["notes"] = query
    return clean


def _enforce_structured_core(result, query):
    q = (query or "").lower()

    if not isinstance(result.get("constraints"), dict):
        result["constraints"] = {}
    if not isinstance(result.get("target_properties"), list):
        result["target_properties"] = []
    if not isinstance(result.get("must_include"), list):
        result["must_include"] = []
    if not isinstance(result.get("exclude_elements"), list):
        result["exclude_elements"] = []

    parsed = parse_query(query)
    _apply_query_parser(result, parsed)

    explicit_comp = _extract_explicit_composition(query)
    if explicit_comp:
        result["composition"] = explicit_comp
        if not result.get("only_elements"):
            result["only_elements"] = sorted(explicit_comp.keys())

    result["target_properties"] = _unique(result["target_properties"] + _extract_target_properties(q))

    if not result.get("application"):
        result["application"] = _extract_application(q, result["target_properties"])
    if not result.get("application") and result.get("composition"):
        result["application"] = _application_from_composition(result["composition"])
    if not result.get("application"):
        result["application"] = "general_structural"

    extra_constraints = _extract_constraints(q, parsed)
    result["constraints"].update(extra_constraints)

    _extract_element_exclusions_from_text(result, q)
    _apply_property_guidance(result, q)
    _apply_family_guidance(result, q)

    if result["constraints"].get("no_ni") and "Ni" not in result["exclude_elements"]:
        result["exclude_elements"].append("Ni")
    if result["constraints"].get("no_co") and "Co" not in result["exclude_elements"]:
        result["exclude_elements"].append("Co")
    if result["constraints"].get("no_pb") and "Pb" not in result["exclude_elements"]:
        result["exclude_elements"].append("Pb")
    if result["constraints"].get("no_cd") and "Cd" not in result["exclude_elements"]:
        result["exclude_elements"].append("Cd")
    if result["constraints"].get("rohs_compliant"):
        for restricted in ["Pb", "Cd", "Hg"]:
            if restricted not in result["exclude_elements"]:
                result["exclude_elements"].append(restricted)

    if not result["target_properties"]:
        result["target_properties"] = list(APPLICATION_DEFAULT_PROPERTIES.get(
            result["application"], ["high_strength"]
        ))

    if result["temperature_K"] and result["temperature_K"] >= 873:
        for p in ["high_temperature_strength", "creep_resistance", "oxidation_resistance"]:
            if p not in result["target_properties"]:
                result["target_properties"].append(p)

    result["must_include"] = _unique(result["must_include"])
    result["exclude_elements"] = _unique(result["exclude_elements"])
    result["must_include"] = [e for e in result["must_include"] if e not in result["exclude_elements"]]

    if result.get("n_elements") and isinstance(result["n_elements"], str):
        try:
            result["n_elements"] = int(result["n_elements"])
        except Exception:
            result["n_elements"] = None

    if not result.get("notes"):
        result["notes"] = query

    return result


def _application_from_composition(composition):
    if not composition:
        return None
    dominant = max(composition.items(), key=lambda x: x[1])[0]
    if dominant == "Fe":
        return "structural"
    if dominant in {"Ni", "Co"}:
        return "superalloy"
    if dominant in {"Bi", "Sn", "In", "Ga", "Pb", "Cd"}:
        return "fusible_alloy"
    if dominant == "Ti":
        return "ti_alloy"
    if dominant == "Al":
        return "al_alloy"
    if dominant == "Cu":
        return "cu_alloy"
    if dominant in {"Ag", "Au", "Si", "Ge"}:
        return "electronic_alloy"
    if dominant == "Zr":
        return "nuclear"
    return "open_alloy"


def _apply_property_guidance(result, q):
    props = set(result.get("target_properties") or [])
    app = result.get("application")
    constraints = result.get("constraints", {})

    def add_must(el):
        if el not in result["must_include"] and el not in result["exclude_elements"]:
            result["must_include"].append(el)

    if "corrosion_resistance" in props:
        if app in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            add_must("Cr")
            if app in {"stainless", "superalloy"} or any(k in q for k in ["marine", "chloride", "seawater"]):
                add_must("Mo")

    if "high_temperature_strength" in props or "creep_resistance" in props:
        if "Ni" not in result["exclude_elements"]:
            add_must("Ni")
        elif "Co" not in result["exclude_elements"]:
            add_must("Co")
        add_must("Cr")

    if "wear_resistance" in props or "hardness" in props:
        if app in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
            if "C" not in result["exclude_elements"]:
                add_must("C")
            if "V" not in result["exclude_elements"]:
                add_must("V")

    if "conductivity" in props:
        if app is None or app == "general_structural":
            result["application"] = "electronic_alloy"
        if result["application"] == "electronic_alloy":
            if any(k in q for k in ["semiconductor", "chip", "wafer", "package", "interconnect"]):
                if "Cu" not in result["exclude_elements"]:
                    add_must("Cu")
            else:
                add_must("Cu")
        else:
            add_must("Cu")

    if "low_melting_point" in props:
        if app is None or app in {"general_structural", "open_alloy"}:
            result["application"] = "fusible_alloy"
        for preferred in ["Sn", "Bi", "In", "Ga"]:
            if preferred not in result["exclude_elements"]:
                add_must(preferred)
                break
        for unsafe_default in ["Hg", "Cd", "Tl"]:
            if unsafe_default not in result["exclude_elements"] and unsafe_default.lower() not in q:
                result["exclude_elements"].append(unsafe_default)

    if result.get("application") == "fusible_alloy":
        electrical_fuse_markers = [
            "electrical fuse", "current", "amp", "overcurrent", "circuit protection", "low resistance", "high conductivity"
        ]
        if any(marker in q for marker in electrical_fuse_markers):
            if "conductivity" not in result["target_properties"]:
                result["target_properties"].append("conductivity")

    if "low_density" in props and result.get("application") == "general_structural":
        if "Ti" not in result["exclude_elements"]:
            result["application"] = "ti_alloy"
        else:
            result["application"] = "al_alloy"

    if constraints.get("cost_level") == "low":
        for expensive in ["Re", "Ta", "Hf"]:
            if expensive not in result["exclude_elements"]:
                result["exclude_elements"].append(expensive)
    if constraints.get("rohs_compliant"):
        for restricted in ["Pb", "Cd", "Hg"]:
            if restricted not in result["exclude_elements"]:
                result["exclude_elements"].append(restricted)



def _resolve_alloy(result, name_key, comp_key):
    name = result.get(name_key)
    if not name:
        return
    alloy = lookup_alloy(name)
    if alloy:
        result[name_key] = alloy["key"]
        if not result.get(comp_key):
            result[comp_key] = alloy.get("composition_wt")


def _empty_result(query):
    return {
        "mode": "design", "alloy_name": None, "alloy_name_2": None,
        "composition": None, "composition_2": None,
        "target_properties": [], "problem": None,
        "domains_focus": [], "study_topic": None,
        "geometry": None, "loading": None,
        "temperature_K": None, "environment": None,
        "n_elements": None, "n_results": None,
        "constraints": {}, "base_element": None,
        "only_elements": None, "must_include": [],
        "exclude_elements": [], "application": None,
        "chat_response": None, "notes": query,
    }


def _unique(values):
    seen = set()
    ordered = []
    for value in values:
        if value is None:
            continue
        item = str(value).strip()
        if not item:
            continue
        if len(item) <= 3 and item[0].isalpha():
            item = item[0].upper() + item[1:].lower()
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _no_llm_fallback(query):
    result = _empty_result(query)
    result["mode"] = "design"
    alloy = lookup_alloy(query.strip())
    if alloy:
        result["alloy_name"] = alloy["key"]
        result["composition"] = alloy.get("composition_wt")
    return _enforce_structured_core(result, query)
