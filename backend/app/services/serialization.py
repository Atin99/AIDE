from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import date
from datetime import datetime
from typing import Any

from physics.base import Check
from physics.base import DomainResult


def _serialize_check(check: Check) -> dict[str, Any]:
    return {
        "name": check.name,
        "status": check.status,
        "value": check.value,
        "unit": check.unit,
        "message": check.message,
        "citation": check.citation,
        "formula": check.formula,
        "score": check.score,
    }


def _serialize_domain(domain: DomainResult) -> dict[str, Any]:
    return {
        "domain_id": domain.domain_id,
        "domain_name": domain.domain_name,
        "score": domain.score(),
        "n_pass": domain.n_pass,
        "n_warn": domain.n_warn,
        "n_fail": domain.n_fail,
        "error": domain.error,
        "checks": [_serialize_check(check) for check in domain.checks],
    }


def serialize_any(value: Any) -> Any:
    if isinstance(value, DomainResult):
        return _serialize_domain(value)
    if isinstance(value, Check):
        return _serialize_check(value)
    if isinstance(value, dict):
        return {str(k): serialize_any(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_any(item) for item in value]
    if isinstance(value, set):
        return [serialize_any(item) for item in sorted(value)]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return serialize_any(asdict(value))
    return value
