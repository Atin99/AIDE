import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alloy_db import lookup_alloy
from core.elements import available as available_elements
from core.query_parser import parse_query
from llms.client import chat_json, extract_json, is_available as llm_available

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

SYSTEM_PROMPT = """You are AIDE's intent extractor.
Return ONLY one JSON object.
Extract these fields exactly:
- mode
- alloy_name, alloy_name_2
- composition, composition_2
- application
- target_properties
- constraints
- only_elements, must_include, exclude_elements
- temperature_K, environment
- notes
Prefer design mode unless clear evidence for study/compare/chat/geometry/modify/explore.
Never return prose or markdown."""

APPLICATION_DEFAULT_PROPERTIES = {
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
    "cu_alloy": ["conductivity", "corrosion_resistance"],
    "open_alloy": ["high_strength"],
    "general_structural": ["high_strength"],
}

PROPERTY_KEYWORDS = {
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
    "conductivity": ["conductivity", "electrical", "wire", "busbar", "conductive"],
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
    "Al": ["al", "aluminum", "aluminium"],
    "Ti": ["ti", "titanium"],
    "V": ["v", "vanadium"],
    "W": ["w", "tungsten", "wolfram"],
    "Re": ["re", "rhenium"],
    "Ta": ["ta", "tantalum"],
    "Hf": ["hf", "hafnium"],
    "C": ["carbon", "c"],
}

ELEMENT_SET = set(available_elements())
_LOCAL_LLM_UNAVAILABLE_UNTIL = 0.0


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

    if _use_local_llm_intent():
        local_result, local_error = _ask_local_llm(query, memory=memory)
        if isinstance(local_result, dict):
            best = _merge_intents(fallback, local_result, query)
            source = "local_llm+rule"
            debug.append({"stage": "local_llm", "status": "ok"})
        else:
            debug.append({"stage": "local_llm", "status": "failed", "reason": local_error or "unavailable"})

    if source == "rule_based" and _use_remote_llm_intent() and llm_available():
        try:
            remote = _ask_llm(query, memory)
            if isinstance(remote, dict):
                best = _merge_intents(fallback, remote, query)
                source = "remote_llm+rule"
                debug.append({"stage": "remote_llm", "status": "ok"})
        except Exception as err:
            logger.warning("Remote intent parse failed: %s", err)
            debug.append({"stage": "remote_llm", "status": "failed", "reason": str(err)})

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


def _use_local_llm_intent():
    return os.environ.get("AIDE_USE_LOCAL_INTENT", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _use_remote_llm_intent():
    return os.environ.get("AIDE_USE_LLM_INTENT", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _intent_local_models():
    forced = os.environ.get("AIDE_LOCAL_INTENT_MODEL", "").strip()
    listed = os.environ.get("AIDE_LOCAL_INTENT_MODELS", "").strip()
    shared = os.environ.get("AIDE_LOCAL_LLM_MODELS", "").strip()

    models = []
    if forced:
        models.append(forced)

    for src in (listed, shared):
        if not src:
            continue
        for token in src.split(","):
            model = token.strip()
            if model and model not in models:
                models.append(model)

    defaults = [
        "phi3:mini",
        "qwen2:1.5b",
        "qwen2.5:1.5b",
        "qwen2.5:3b",
        "llama3.2:3b",
        "mistral:7b-instruct",
    ]
    for model in defaults:
        if model not in models:
            models.append(model)
    return models


def _ask_local_llm(query, memory=None):
    global _LOCAL_LLM_UNAVAILABLE_UNTIL
    if time.time() < _LOCAL_LLM_UNAVAILABLE_UNTIL:
        return None, "recently_unavailable"

    models = _intent_local_models()
    endpoint = os.environ.get("AIDE_LOCAL_LLM_URL", "http://127.0.0.1:11434/api/generate")
    timeout = float(os.environ.get("AIDE_LOCAL_LLM_TIMEOUT", "1.2"))

    schema_text = json.dumps(INTENT_SCHEMA, indent=2)
    prompt_parts = [
        SYSTEM_PROMPT,
        "Return exactly one JSON object with this shape:",
        schema_text,
        f"User input: {query}",
    ]
    if memory:
        try:
            context = memory.get_context_for_llm()
            if context:
                compact = []
                for msg in context[-4:]:
                    role = msg.get("role", "user")
                    content = (msg.get("content", "") or "").strip()
                    if content:
                        compact.append(f"{role}: {content[:240]}")
                if compact:
                    prompt_parts.append("Recent context:\n" + "\n".join(compact))
        except Exception:
            pass

    for model in models:
        payload = {
            "model": model,
            "prompt": "\n\n".join(prompt_parts),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(body)
            response_text = (obj.get("response") or "").strip()
            if not response_text:
                continue
            parsed = extract_json(response_text)
            if isinstance(parsed, dict):
                return parsed, None
        except urllib.error.HTTPError as err:
            detail = ""
            try:
                detail = err.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(err)
            if "not found" in detail.lower() and "model" in detail.lower():
                continue
            return None, f"http_error: {err.code}"
        except urllib.error.URLError as err:
            _LOCAL_LLM_UNAVAILABLE_UNTIL = time.time() + 120.0
            return None, f"network_error: {err}"
        except Exception:
            continue

    _LOCAL_LLM_UNAVAILABLE_UNTIL = time.time() + 30.0
    return None, "no_local_model_available"


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
    if "conductivity" in props:
        return "cu_alloy"
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
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\nReturn valid JSON only."}]
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

    if result["constraints"].get("no_ni") and "Ni" not in result["exclude_elements"]:
        result["exclude_elements"].append("Ni")
    if result["constraints"].get("no_co") and "Co" not in result["exclude_elements"]:
        result["exclude_elements"].append("Co")

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
    if dominant == "Ti":
        return "ti_alloy"
    if dominant == "Al":
        return "al_alloy"
    if dominant == "Cu":
        return "cu_alloy"
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
        if "C" not in result["exclude_elements"]:
            add_must("C")
        if "V" not in result["exclude_elements"]:
            add_must("V")

    if "conductivity" in props:
        if app is None or app == "general_structural":
            result["application"] = "cu_alloy"
        add_must("Cu")

    if "low_density" in props and result.get("application") == "general_structural":
        if "Ti" not in result["exclude_elements"]:
            result["application"] = "ti_alloy"
        else:
            result["application"] = "al_alloy"

    if constraints.get("cost_level") == "low":
        for expensive in ["Re", "Ta", "Hf"]:
            if expensive not in result["exclude_elements"]:
                result["exclude_elements"].append(expensive)



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
