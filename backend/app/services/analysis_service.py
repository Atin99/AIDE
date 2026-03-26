import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_env()

from core.alloy_db import ALLOY_DATABASE
from core.elements import validate_composition
from engines.modes import route
from llms.intent_parser import classify_intent
from physics.base import wt_to_mol
from physics.filter import DOMAIN_MODULES
from physics.filter import MODULE_DOMAIN_NAME
from physics.filter import NEW_DOMAIN_RUNNERS
from physics.filter import run_all


def list_alloys():
    alloys = []
    for key, data in ALLOY_DATABASE.items():
        alloys.append({
            "key": key,
            "category": data.get("category", ""),
            "subcategory": data.get("subcategory", ""),
            "composition_wt": data.get("composition_wt", {}),
            "properties": data.get("properties", {}),
            "applications": data.get("applications", []),
        })
    return alloys


def list_domains() -> list[dict[str, Any]]:
    domains = []
    for index, (module_name, _) in enumerate(DOMAIN_MODULES, start=1):
        domains.append(
            {
                "domain_id": index,
                "domain_name": MODULE_DOMAIN_NAME.get(module_name, module_name),
            }
        )
    for _, _, domain_id, domain_name in NEW_DOMAIN_RUNNERS:
        domains.append({"domain_id": int(domain_id), "domain_name": domain_name})
    domains.sort(key=lambda item: item["domain_id"])
    return domains


def _merge_payload(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (patch or {}).items():
        if value in (None, ""):
            continue
        merged[key] = value
    return merged


def _apply_overrides(intent: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = deepcopy(intent)
    if not overrides:
        return payload
    for key, value in overrides.items():
        if value is None:
            continue
        payload[key] = value
    return payload


def classify_query(query: str) -> Dict[str, Any]:
    return classify_intent(query)


def run_engine(query: Optional[str], intent: Optional[Dict[str, Any]], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {}
    if query:
        payload = classify_intent(query)
    if intent:
        payload = _merge_payload(payload, intent)

    if not payload:
        raise ValueError("Provide query or intent.")

    payload = _apply_overrides(payload, overrides)
    payload.setdefault("mode", "design")
    payload.setdefault("temperature_K", 298.0)
    if payload.get("n_results") is None:
        payload["n_results"] = 10
    if payload.get("dpa_rate") is None:
        payload["dpa_rate"] = 1e-7
    if payload.get("pressure_MPa") is None:
        payload["pressure_MPa"] = 0.0
    if payload.get("use_ml") is None:
        payload["use_ml"] = False

    result = route(payload, verbose=False)
    return {"intent": payload, "result": result}


def run_composition_analysis(
    composition: Dict[str, float],
    basis: str,
    temperature_K: float,
    environment: Optional[str],
    application: Optional[str],
    target_properties: list[str],
    domains_focus: Optional[list[str]],
    domain_priority: Optional[Dict[str, float]],
    weight_profile: str,
    max_domains: Optional[int],
    dpa_rate: float,
    process: str,
) -> Dict[str, Any]:
    if not composition:
        raise ValueError("Composition cannot be empty.")

    if basis == "wt":
        comp_mol = validate_composition(wt_to_mol(composition))
    else:
        comp_mol = validate_composition(composition)

    result = run_all(
        comp_mol,
        T_K=temperature_K,
        weather=environment,
        domains_focus=domains_focus,
        application=application,
        target_properties=target_properties,
        domain_priority=domain_priority,
        weight_profile=weight_profile,
        max_domains=max_domains,
        dpa_rate=dpa_rate,
        process=process,
    )

    return {"composition_mol": comp_mol, "result": result}


def _lookup_alloy_by_query(query: str):
    """Try to resolve a natural language query as a known alloy name."""
    if not query:
        return None
    q = query.strip().lower()
    # Exact match (case-insensitive)
    for key, data in ALLOY_DATABASE.items():
        if key.lower() == q:
            return data
    # Partial match
    for key, data in ALLOY_DATABASE.items():
        if q in key.lower() or key.lower() in q:
            return data
    return None


def run_unified(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("composition"):
        temperature = payload.get("temperature_K")
        if temperature is None:
            temperature = 298.0
        result = run_composition_analysis(
            composition=payload["composition"],
            basis=payload.get("basis", "wt"),
            temperature_K=float(temperature),
            environment=payload.get("environment"),
            application=payload.get("application"),
            target_properties=list(payload.get("target_properties") or []),
            domains_focus=payload.get("domains_focus"),
            domain_priority=payload.get("domain_priority"),
            weight_profile=payload.get("weight_profile", "auto"),
            max_domains=payload.get("max_domains"),
            dpa_rate=float(payload.get("dpa_rate", 1e-7)),
            process=payload.get("process", "annealed"),
        )
        return {
            "request_type": "composition_analyze",
            "intent": None,
            **result,
        }

    # Try alloy name shortcut before slow LLM pipeline
    query = payload.get("query", "")
    alloy_match = _lookup_alloy_by_query(query)
    if alloy_match:
        comp = alloy_match.get("composition_wt", {})
        if comp:
            result = run_composition_analysis(
                composition=comp,
                basis="wt",
                temperature_K=float(payload.get("temperature_K", 298.0)),
                environment=payload.get("environment"),
                application=payload.get("application"),
                target_properties=list(payload.get("target_properties") or []),
                domains_focus=payload.get("domains_focus"),
                domain_priority=payload.get("domain_priority"),
                weight_profile=payload.get("weight_profile", "auto"),
                max_domains=payload.get("max_domains"),
                dpa_rate=float(payload.get("dpa_rate", 1e-7)),
                process=payload.get("process", "annealed"),
            )
            return {
                "request_type": "alloy_lookup",
                "matched_alloy": alloy_match.get("category", "") + " / " + alloy_match.get("subcategory", ""),
                "intent": None,
                **result,
            }

    overrides = dict(payload.get("overrides") or {})
    result = run_engine(
        query=query,
        intent=payload.get("intent"),
        overrides=overrides,
    )
    return {
        "request_type": "engine_run",
        **result,
    }

