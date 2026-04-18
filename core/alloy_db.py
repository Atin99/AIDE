from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Iterator


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "alloys.json"
SEED_ALLOY_TAG = "seed_alloy"
CATEGORY_ENUM = {
    "aluminium",
    "carbon_steel",
    "cobalt",
    "copper",
    "electronic",
    "fusible",
    "hea",
    "low_alloy",
    "magnesium",
    "nuclear",
    "refractory",
    "stainless",
    "superalloy",
    "titanium",
    "tool_steel",
}
REQUIRED_FIELDS = {
    "aliases",
    "applications",
    "category",
    "composition_wt",
    "key",
    "properties",
    "provenance",
    "subcategory",
    "tags",
}
TOTAL_TOLERANCE = 1e-2

_CATALOG_CACHE: dict[str, dict[str, Any]] | None = None
_ALIAS_INDEX: dict[str, str] | None = None


class CatalogValidationError(ValueError):
    """Raised when the persisted alloy catalog violates runtime invariants."""


def _normalize_lookup_name(text: str) -> str:
    """Normalize alloy keys and aliases for robust lookup matching."""
    return str(text or "").strip().upper().replace(" ", "").replace("-", "")


def _unique_strings(values: list[Any]) -> list[str]:
    """Return ordered unique non-empty strings from a list-like input."""
    seen = set()
    ordered: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _normalize_composition(comp: dict[str, Any], key: str) -> dict[str, float]:
    """Validate and normalize one composition map to a unit-fraction basis."""
    if not isinstance(comp, dict) or not comp:
        raise CatalogValidationError(f"{key}: composition_wt must be a non-empty object.")

    normalized: dict[str, float] = {}
    for symbol, value in comp.items():
        symbol_text = str(symbol).strip()
        if not symbol_text:
            raise CatalogValidationError(f"{key}: composition contains an empty element symbol.")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as err:
            raise CatalogValidationError(f"{key}: invalid composition value for {symbol_text}: {value!r}") from err
        if numeric <= 0:
            raise CatalogValidationError(f"{key}: composition value for {symbol_text} must be positive.")
        normalized[symbol_text] = numeric

    total = sum(normalized.values())
    if total <= 0:
        raise CatalogValidationError(f"{key}: composition total must be positive.")
    if total > 1.0 + TOTAL_TOLERANCE:
        raise CatalogValidationError(f"{key}: composition total {total:.6f} exceeds 100 wt%.")
    return {symbol: value / total for symbol, value in normalized.items()}


def _validate_provenance(provenance: Any, key: str) -> dict[str, Any]:
    """Validate provenance structure for one alloy entry."""
    if not isinstance(provenance, dict):
        raise CatalogValidationError(f"{key}: provenance must be an object.")

    source = str(provenance.get("source") or "").strip()
    if not source:
        raise CatalogValidationError(f"{key}: provenance.source is required.")

    year = provenance.get("year")
    if year not in (None, ""):
        try:
            year = int(year)
        except (TypeError, ValueError) as err:
            raise CatalogValidationError(f"{key}: provenance.year must be an integer or null.") from err

    clean = {"source": source, "year": year}
    confidence = str(provenance.get("confidence") or "").strip()
    if confidence:
        clean["confidence"] = confidence
    return clean


def _validate_record(record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Validate one raw JSON catalog record and return normalized runtime data."""
    if not isinstance(record, dict):
        raise CatalogValidationError("Catalog entries must be JSON objects.")

    missing = sorted(REQUIRED_FIELDS - set(record.keys()))
    if missing:
        raise CatalogValidationError(f"Catalog record missing required fields: {missing}")

    key = str(record.get("key") or "").strip()
    if not key:
        raise CatalogValidationError("Catalog record key cannot be empty.")

    category = str(record.get("category") or "").strip()
    if category.lower() not in CATEGORY_ENUM:
        raise CatalogValidationError(f"{key}: unsupported category {category!r}.")

    normalized = {
        "category": category,
        "subcategory": str(record.get("subcategory") or "").strip(),
        "composition_wt": _normalize_composition(record.get("composition_wt") or {}, key),
        "aliases": _unique_strings(list(record.get("aliases") or [])),
        "properties": dict(record.get("properties") or {}),
        "applications": _unique_strings(list(record.get("applications") or [])),
        "tags": _unique_strings(list(record.get("tags") or [])),
        "provenance": _validate_provenance(record.get("provenance"), key),
    }
    return key, normalized


def load_catalog(force_reload: bool = False) -> dict[str, dict[str, Any]]:
    """Load, validate, and cache the authoritative alloy catalog from disk."""
    global _CATALOG_CACHE
    global _ALIAS_INDEX

    if _CATALOG_CACHE is not None and not force_reload:
        return _CATALOG_CACHE

    if not CATALOG_PATH.is_file():
        raise CatalogValidationError(f"Catalog file not found: {CATALOG_PATH}")

    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records = payload.get("alloys")
    if not isinstance(records, list) or not records:
        raise CatalogValidationError("Catalog payload must contain a non-empty 'alloys' array.")

    catalog: dict[str, dict[str, Any]] = {}
    alias_index: dict[str, str] = {}
    for raw in records:
        key, entry = _validate_record(raw)
        normalized_key = _normalize_lookup_name(key)
        if normalized_key in alias_index or key in catalog:
            raise CatalogValidationError(f"{key}: duplicate catalog key.")

        catalog[key] = entry
        alias_index[normalized_key] = key

        for alias in entry["aliases"]:
            normalized_alias = _normalize_lookup_name(alias)
            owner = alias_index.get(normalized_alias)
            if owner and owner != key:
                raise CatalogValidationError(f"{key}: alias {alias!r} collides with {owner!r}.")
            alias_index[normalized_alias] = key

    _CATALOG_CACHE = catalog
    _ALIAS_INDEX = alias_index
    return catalog


def refresh_catalog() -> dict[str, dict[str, Any]]:
    """Force a reload of the authoritative alloy catalog from disk."""
    return load_catalog(force_reload=True)


def iter_by_category(category: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield catalog entries, optionally restricted to one category."""
    catalog = load_catalog()
    wanted = str(category or "").strip().lower()
    for key, entry in catalog.items():
        if wanted and entry.get("category", "").lower() != wanted:
            continue
        yield {"key": key, **entry}


def iter_seed_alloys(category: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield catalog entries tagged as seed priors for candidate generation."""
    for entry in iter_by_category(category):
        tags = set(entry.get("tags") or [])
        if SEED_ALLOY_TAG in tags:
            yield entry


def lookup_alloy(name: str) -> dict[str, Any] | None:
    """Resolve an alloy key or alias, with a partial-match fallback."""
    if not str(name or "").strip():
        return None

    catalog = load_catalog()
    alias_index = _ALIAS_INDEX or {}
    normalized = _normalize_lookup_name(name)

    direct_key = alias_index.get(normalized)
    if direct_key:
        return {"key": direct_key, **catalog[direct_key]}

    for candidate_key, entry in catalog.items():
        key_name = _normalize_lookup_name(candidate_key)
        if normalized in key_name or key_name in normalized:
            return {"key": candidate_key, **entry}
        for alias in entry.get("aliases", []):
            alias_name = _normalize_lookup_name(alias)
            if normalized in alias_name or alias_name in normalized:
                return {"key": candidate_key, **entry}
    return None


def get_alloys_by_category(category: str) -> list[dict[str, Any]]:
    """Return all catalog entries in one category."""
    return list(iter_by_category(category))


def search_alloys(query: str) -> list[dict[str, Any]]:
    """Search catalog entries by key, alias, family labels, and applications."""
    q = str(query or "").strip().lower()
    if not q:
        return []

    matches: list[dict[str, Any]] = []
    for key, entry in load_catalog().items():
        searchable = " ".join(
            [
                key,
                entry.get("category", ""),
                entry.get("subcategory", ""),
                " ".join(entry.get("aliases", [])),
                " ".join(entry.get("applications", [])),
                " ".join(entry.get("tags", [])),
            ]
        ).lower()
        if q in searchable:
            matches.append({"key": key, **entry})
    return matches


ALLOY_DATABASE = load_catalog()
