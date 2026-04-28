from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

from llms.client import chat_json, is_available as llm_available

logger = logging.getLogger("aide.researcher")

HOT_SECTION_MARKERS = [
    "hot section", "gas path", "gas turbine", "turbine", "turbine blade", "blade",
    "jet engine", "combustor", "afterburner", "exhaust nozzle", "stress rupture",
]

AEROSPACE_STRUCTURE_MARKERS = [
    "airframe", "fuselage", "wing", "wing spar", "skin", "panel", "bulkhead",
    "frame", "aircraft body", "jet body", "body shell", "aerospace structural",
    "aircraft frame", "aircraft structure",
]

HEAVY_STRUCTURE_MARKERS = [
    "crane", "boom", "gantry", "hoist", "frame", "chassis", "body", "bridge",
    "girder", "beam", "bucket", "loader", "excavator", "trailer", "truck body",
    "load bearing", "load-bearing",
]

RESEARCH_SCHEMA = """{
  "base_elements": ["<symbol>"],
  "base_min_fraction": <0.0-1.0>,
  "forbidden_elements": ["<symbol>"],
  "mandatory_mechanisms": ["<string>"],
  "primary_domains": ["<string>"],
  "domain_weights": {"<domain>": <weight>},
  "rationale": "<one-sentence explanation>"
}"""

SYSTEM_PROMPT = """You are a senior metallurgist and materials scientist.
Given an alloy application, return one JSON object with physically grounded constraints.
No markdown, no prose."""


@dataclass
class ResearchResult:
    base_elements: list[str]
    base_min_fraction: float
    forbidden_elements: list[str]
    mandatory_mechanisms: list[str]
    primary_domains: list[str]
    domain_weights: dict[str, float]
    rationale: str
    source: str = "heuristic"
    fallback_reason: str = ""

    def validate(self) -> "ResearchResult":
        self.base_elements = [str(e).strip() for e in self.base_elements if str(e).strip()]
        if not self.base_elements:
            raise ValueError("Researcher returned no base elements.")
        if not (0.0 < self.base_min_fraction <= 1.0):
            raise ValueError(f"base_min_fraction {self.base_min_fraction} out of range.")

        self.forbidden_elements = [str(e).strip() for e in self.forbidden_elements if str(e).strip()]
        self.mandatory_mechanisms = [str(m).strip() for m in self.mandatory_mechanisms if str(m).strip()]

        if not self.primary_domains:
            self.primary_domains = ["Mechanical"]
            self.domain_weights = {"Mechanical": 1.0}

        if not self.domain_weights:
            self.domain_weights = {d: 1.0 for d in self.primary_domains}

        total = sum(float(v) for v in self.domain_weights.values() if float(v) > 0)
        if total <= 0:
            self.domain_weights = {"Mechanical": 1.0}
        else:
            self.domain_weights = {
                str(k): float(v) / total
                for k, v in self.domain_weights.items()
                if float(v) > 0
            }

        self.primary_domains = [d for d in self.primary_domains if d in self.domain_weights]
        if not self.primary_domains:
            self.primary_domains = list(self.domain_weights.keys())

        return self

    def composition_violates_base(self, composition: dict[str, float]) -> tuple[bool, str]:
        """Check if composition violates base element constraints.
        
        Returns (violated, reason). A composition is only hard-rejected if
        the base element is completely absent or below 20% of the requirement.
        Moderate shortfalls are handled by the scoring penalty system instead.
        """
        base = self.base_elements[0]
        frac = composition.get(base, 0.0)
        # Only hard-reject if base element is drastically wrong
        # (below 20% of requirement — e.g. Cu alloy with <12% Cu)
        hard_floor = self.base_min_fraction * 0.20
        if frac < hard_floor:
            return (
                True,
                f"Base element {base} at {frac:.3f}, needs >= {self.base_min_fraction:.2f}.",
            )
        for el in self.forbidden_elements:
            if composition.get(el, 0.0) > 0.005:
                return True, f"Forbidden element {el} is present."
        return False, ""

    def base_element_penalty(self, composition: dict[str, float]) -> float:
        """Return a penalty factor (0.0-1.0) for base element shortfall.
        1.0 = fully meets requirement, <1.0 = proportional penalty.
        """
        base = self.base_elements[0]
        frac = composition.get(base, 0.0)
        if frac >= self.base_min_fraction:
            return 1.0
        if self.base_min_fraction <= 0:
            return 1.0
        ratio = frac / self.base_min_fraction
        # Smooth penalty: 50% of requirement → 0.5x score
        return max(0.1, min(1.0, ratio))


class ApplicationResearcher:
    def research(self, query: str, intent: dict | None = None) -> ResearchResult:
        logger.info("[RESEARCH] Researching application: '%s'", query)

        llm_error = ""
        if self._structured_llm_enabled() and llm_available():
            try:
                raw = self._ask_llm(query, intent=intent)
                if isinstance(raw, dict):
                    result = self._parse(raw)
                    result = self._blend_with_intent(result, intent).validate()
                    result.source = "llm"
                    logger.info(
                        "[RESEARCH] LLM constraints: base=%s min_frac=%.0f%% mechanisms=%s",
                        result.base_elements,
                        result.base_min_fraction * 100.0,
                        result.mandatory_mechanisms,
                    )
                    return result
                llm_error = "empty_or_invalid_llm_response"
            except Exception as err:
                llm_error = str(err)
                logger.warning("[RESEARCH] LLM research failed: %s", err)
        else:
            llm_error = "disabled_by_config" if not self._structured_llm_enabled() else "llm_unavailable"

        fallback = self._heuristic_research(query, intent=intent)
        fallback.source = "heuristic"
        fallback.fallback_reason = llm_error
        logger.info(
            "[RESEARCH] Heuristic constraints: base=%s min_frac=%.0f%% domains=%s reason=%s",
            fallback.base_elements,
            fallback.base_min_fraction * 100.0,
            fallback.primary_domains,
            llm_error,
        )
        return fallback

    def _ask_llm(self, query: str, intent: dict | None = None) -> dict | None:
        intent_hint = ""
        if intent:
            app = intent.get("application") or ""
            props = ", ".join(intent.get("target_properties", []))
            excludes = ", ".join(intent.get("exclude_elements", []))
            constraints = intent.get("constraints", {})
            intent_hint = (
                f"\nKnown application: {app}"
                f"\nKnown target properties: {props}"
                f"\nExcluded elements: {excludes}"
                f"\nConstraints: {constraints}"
            )

        user_prompt = (
            f"Application / alloy description: \"{query}\""
            f"{intent_hint}\n\n"
            "Determine physical and compositional constraints for this alloy.\n"
            "Return one JSON object matching this schema exactly:\n"
            f"{RESEARCH_SCHEMA}"
        )

        return chat_json(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\nSchema:\n" + RESEARCH_SCHEMA},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            retries=2,
        )

    def _parse(self, raw: dict) -> ResearchResult:
        try:
            return ResearchResult(
                base_elements=[str(e).strip() for e in raw["base_elements"]],
                base_min_fraction=float(raw["base_min_fraction"]),
                forbidden_elements=[str(e).strip() for e in raw.get("forbidden_elements", [])],
                mandatory_mechanisms=[str(m).strip() for m in raw.get("mandatory_mechanisms", [])],
                primary_domains=[str(d).strip() for d in raw.get("primary_domains", ["Mechanical"])],
                domain_weights={
                    str(k): float(v)
                    for k, v in raw.get("domain_weights", {"Mechanical": 1.0}).items()
                },
                rationale=str(raw.get("rationale", "")),
                source="llm",
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError(f"Researcher returned malformed data: {err}; raw={raw}")

    def _blend_with_intent(self, result: ResearchResult, intent: dict | None) -> ResearchResult:
        if not intent:
            return result

        excludes = set(result.forbidden_elements)
        excludes.update(intent.get("exclude_elements", []) or [])

        constraints = intent.get("constraints", {}) or {}
        if constraints.get("no_ni"):
            excludes.add("Ni")
        if constraints.get("no_co"):
            excludes.add("Co")

        base_hint = intent.get("base_element")
        if base_hint:
            result.base_elements = [str(base_hint)]

        if result.base_elements and result.base_elements[0] in excludes:
            replacement = self._choose_base(["Fe", "Ni", "Co", "Ti", "Al", "Zr", "Cu"], excludes)
            result.base_elements = [replacement]

        result.forbidden_elements = sorted(excludes)
        return result

    def _heuristic_research(self, query: str, intent: dict | None = None) -> ResearchResult:
        intent = intent or {}
        q = (query or "").lower()
        app = intent.get("application") or self._infer_application(q)

        properties = set(intent.get("target_properties", []) or [])
        properties.update(self._infer_properties(q))

        constraints = dict(intent.get("constraints", {}) or {})
        excludes = set(intent.get("exclude_elements", []) or [])
        if constraints.get("no_ni"):
            excludes.add("Ni")
        if constraints.get("no_co"):
            excludes.add("Co")

        base_candidates = {
            "fusible_alloy": ["Sn", "Bi", "In", "Ga"],
            "electronic_alloy": ["Cu", "Sn", "Al", "Ag", "Au", "Si", "Ge"],
            "stainless": ["Fe"],
            "structural": ["Fe"],
            "carbon_steel": ["Fe"],
            "superalloy": ["Ni", "Co", "Fe"],
            "ti_alloy": ["Ti"],
            "al_alloy": ["Al"],
            "nuclear": ["Zr", "Fe"],
            "biomedical": ["Ti", "Co", "Fe"],
            "refractory": ["Nb", "Mo", "W", "Ta"],
            "cu_alloy": ["Cu"],
            "hea": ["Fe", "Ni", "Co"],
            "open_alloy": ["Fe", "Ni", "Ti", "Al", "Cu", "Co", "Zr"],
            "general_structural": ["Fe"],
        }
        base_min = {
            "fusible_alloy": 0.35,
            "electronic_alloy": 0.40,
            "stainless": 0.50,
            "structural": 0.62,
            "carbon_steel": 0.92,
            "superalloy": 0.45,
            "ti_alloy": 0.72,
            "al_alloy": 0.82,
            "nuclear": 0.78,
            "biomedical": 0.55,
            "refractory": 0.50,
            "cu_alloy": 0.60,
            "hea": 0.20,
            "open_alloy": 0.20,
            "general_structural": 0.60,
        }

        selected_base = self._choose_base(base_candidates.get(app, ["Fe"]), excludes)
        selected_min = base_min.get(app, 0.60)

        mandatory_mechanisms = []
        if "corrosion_resistance" in properties or app in {"stainless", "nuclear", "biomedical"}:
            mandatory_mechanisms.append("solid_solution")
        if "high_temperature_strength" in properties or "creep_resistance" in properties or app in {"superalloy", "refractory"}:
            if selected_base in {"Ni", "Co"} and "Ni" not in excludes:
                mandatory_mechanisms.append("gamma_prime")
            mandatory_mechanisms.append("solid_solution")
        if "wear_resistance" in properties or "hardness" in properties:
            if app in {"stainless", "superalloy", "structural", "carbon_steel", "general_structural", "open_alloy"}:
                mandatory_mechanisms.append("carbide")
            else:
                mandatory_mechanisms.append("solid_solution")
        if "high_strength" in properties and app == "al_alloy":
            mandatory_mechanisms.append("precipitation_hard")
        if app == "fusible_alloy":
            mandatory_mechanisms.append("solid_solution")

        if app == "ti_alloy" and ("high_strength" in properties or "fatigue_resistance" in properties):
            mandatory_mechanisms.append("alpha_beta")
            mandatory_mechanisms.append("solid_solution")
        if app == "superalloy" and "high_strength" in properties:
            mandatory_mechanisms.append("gamma_prime")

        mandatory_mechanisms = self._unique(mandatory_mechanisms)

        primary_domains = []
        if "corrosion_resistance" in properties:
            primary_domains.extend(["Corrosion", "Oxidation"])
        if "high_temperature_strength" in properties or "creep_resistance" in properties:
            primary_domains.extend(["Creep", "Phase Stability", "Oxidation"])
        if "wear_resistance" in properties or "hardness" in properties:
            primary_domains.extend(["Tribology & Wear", "Mechanical"])
        if "fatigue_resistance" in properties:
            primary_domains.append("Fatigue & Fracture")
        if "conductivity" in properties:
            primary_domains.extend(["Thermal Properties", "Electronic Structure"])
        if "low_melting_point" in properties or app == "fusible_alloy":
            primary_domains.extend(["Thermodynamics", "Thermal Properties"])
        if app == "electronic_alloy":
            primary_domains.extend(["Electronic Structure", "Thermal Properties"])
        if "low_density" in properties:
            primary_domains.append("Structural Efficiency")
        if app in {"structural", "general_structural", "carbon_steel"} or self._is_heavy_structure_query(q):
            primary_domains.extend(["Fatigue & Fracture", "Weldability", "Fracture Mechanics", "Impact Toughness"])
        if "biocompatibility" in properties or app == "biomedical":
            primary_domains.append("Biocompatibility")
        if app == "nuclear" or "radiation_resistance" in properties:
            primary_domains.append("Nuclear Fuel Compatibility")

        if "Mechanical" not in primary_domains:
            primary_domains.append("Mechanical")

        primary_domains = self._unique(primary_domains)
        domain_weights = self._make_weights(primary_domains)

        rationale = f"Heuristic inference from app={app}, properties={sorted(properties)}, excludes={sorted(excludes)}"

        return ResearchResult(
            base_elements=[selected_base],
            base_min_fraction=selected_min,
            forbidden_elements=sorted(excludes),
            mandatory_mechanisms=mandatory_mechanisms,
            primary_domains=primary_domains,
            domain_weights=domain_weights,
            rationale=rationale,
            source="heuristic",
        ).validate()

    def _infer_application(self, q: str) -> str:
        if any(k in q for k in ["fuse alloy", "fuse wire", "fusible", "fusible wire", "low melting", "low-melting", "solder", "solder alloy", "thermal fuse", "fusible link", "braze filler", "liquid metal"]):
            return "fusible_alloy"
        if any(k in q for k in ["chip alloy", "chip package", "semiconductor", "interconnect", "bond wire", "wire bond", "solder bump", "leadframe", "microelectronics", "electronic packaging"]):
            return "electronic_alloy"
        if any(k in q for k in ["stainless", "duplex", "marine", "chloride", "pitting"]):
            return "stainless"
        if any(k in q for k in ["any alloy", "any composition", "unrestricted composition", "any elements", "no element restriction"]):
            return "open_alloy"
        if any(k in q for k in ["titanium", "ti-6", "ti alloy"]):
            return "ti_alloy"
        if any(k in q for k in ["aluminum", "aluminium", "duralumin"]):
            return "al_alloy"
        if self._is_aerospace_structure_query(q) and "lightweight" in q and not self._is_hot_section_query(q):
            return "ti_alloy"
        if any(k in q for k in ["superalloy", "inconel", "creep"]) or self._is_hot_section_query(q):
            return "superalloy"
        if any(k in q for k in ["nuclear", "reactor", "zircaloy", "cladding"]):
            return "nuclear"
        if any(k in q for k in ["implant", "biomedical", "surgical", "dental"]):
            return "biomedical"
        if any(k in q for k in ["refractory", "1200c", "1500c", "ultra high temperature"]):
            return "refractory"
        if any(k in q for k in ["wire", "busbar", "copper", "bronze", "brass"]):
            return "cu_alloy"
        if any(k in q for k in ["tool steel", "die steel", "hardfacing", "abrasive slurry"]):
            return "carbon_steel"
        if any(k in q for k in ["carbon steel", "mild steel", "plain carbon"]):
            return "carbon_steel"
        if any(k in q for k in ["steel", "structural"]):
            return "structural"
        return "general_structural"

    def _infer_properties(self, q: str) -> list[str]:
        mapping = {
            "low_melting_point": ["low melting", "low-melting", "fusible", "solder", "reflow", "liquid metal", "thermal fuse"],
            "corrosion_resistance": ["corrosion", "rust", "pitting", "chloride", "marine"],
            "high_temperature_strength": ["high temperature", "elevated temperature", "hot section", "turbine", "gas turbine", "jet engine", "blade", "combustor"],
            "creep_resistance": ["creep", "stress rupture"],
            "wear_resistance": ["wear", "abrasion", "erosion", "tribology"],
            "hardness": ["hardness", "hard"],
            "fatigue_resistance": ["fatigue", "cyclic"],
            "high_strength": ["strength", "strong", "yield", "ultimate tensile", "uts"],
            "low_density": ["lightweight", "low density", "mass critical", "weight critical"],
            "conductivity": ["conductivity", "electrical", "wire", "chip", "interconnect", "bond wire", "leadframe", "packaging"],
            "biocompatibility": ["biomedical", "implant", "biocompatible"],
            "radiation_resistance": ["radiation", "reactor", "nuclear", "dpa"],
        }
        props = []
        for name, keys in mapping.items():
            if any(k in q for k in keys):
                props.append(name)

        if self._is_heavy_structure_query(q):
            props.extend(["fatigue_resistance", "weldability"])

        fuse_wire_markers = ["fuse wire", "fusible wire", "fuse alloy", "fusible alloy", "thermal fuse"]
        explicit_electrical_markers = [
            "high conductivity", "electrical conductivity", "low resistance", "resistive heating",
            "current rating", "ampere", "amperage", "circuit protection", "overcurrent",
        ]
        if any(marker in q for marker in fuse_wire_markers) and not any(marker in q for marker in explicit_electrical_markers):
            props = [prop for prop in props if prop != "conductivity"]
            if "low_melting_point" not in props:
                props.append("low_melting_point")

        m_c = re.search(r"(\d{3,4})\s*c\b", q)
        if m_c and float(m_c.group(1)) >= 550:
            props.extend(["high_temperature_strength", "creep_resistance"])

        return self._unique(props)

    def _is_hot_section_query(self, q: str) -> bool:
        return any(marker in q for marker in HOT_SECTION_MARKERS) or (
            "jet" in q and any(marker in q for marker in ["engine", "turbine", "blade", "combustor", "nozzle"])
        )

    def _is_aerospace_structure_query(self, q: str) -> bool:
        return any(marker in q for marker in AEROSPACE_STRUCTURE_MARKERS) or (
            any(marker in q for marker in ["aircraft", "aerospace", "airplane", "plane", "jet"])
            and any(marker in q for marker in ["body", "frame", "fuselage", "wing", "skin", "panel", "spar", "structure", "structural"])
        )

    def _is_heavy_structure_query(self, q: str) -> bool:
        return any(marker in q for marker in HEAVY_STRUCTURE_MARKERS)

    def _structured_llm_enabled(self) -> bool:
        value = os.environ.get("AIDE_USE_LLM_RESEARCH", "1").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _choose_base(self, candidates: list[str], excludes: set[str]) -> str:
        for element in candidates:
            if element not in excludes:
                return element
        for fallback in ["Fe", "Sn", "Cu", "Ti", "Al", "Zr", "Bi"]:
            if fallback not in excludes:
                return fallback
        return "Fe"

    def _make_weights(self, domains: list[str]) -> dict[str, float]:
        n = len(domains)
        if n <= 0:
            return {"Mechanical": 1.0}
        weights = {}
        remaining = 1.0
        current = 0.38
        for idx, domain in enumerate(domains):
            if idx == n - 1:
                weights[domain] = max(0.05, remaining)
                break
            w = max(0.08, current)
            w = min(w, remaining - 0.05 * (n - idx - 1))
            weights[domain] = w
            remaining -= w
            current *= 0.72

        total = sum(weights.values())
        if total <= 0:
            return {"Mechanical": 1.0}
        return {k: v / total for k, v in weights.items()}

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        ordered = []
        for value in values:
            text = str(value).strip()
            if text and text not in seen:
                seen.add(text)
                ordered.append(text)
        return ordered
