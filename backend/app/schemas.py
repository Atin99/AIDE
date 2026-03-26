from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class RunOverrides(BaseModel):
    temperature_K: Optional[float] = None
    environment: Optional[str] = None
    n_results: Optional[int] = None
    dpa_rate: Optional[float] = None
    pressure_MPa: Optional[float] = None
    use_ml: Optional[bool] = None
    mode: Optional[str] = None


class IntentClassifyRequest(BaseModel):
    query: str = Field(min_length=1)


class EngineRunRequest(BaseModel):
    query: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None
    overrides: RunOverrides = Field(default_factory=RunOverrides)


class CompositionAnalyzeRequest(BaseModel):
    composition: Dict[str, float]
    basis: Literal["wt", "mol"] = "wt"
    temperature_K: float = 298.0
    environment: Optional[str] = None
    application: Optional[str] = None
    target_properties: List[str] = Field(default_factory=list)
    domains_focus: Optional[List[str]] = None
    domain_priority: Optional[Dict[str, float]] = None
    weight_profile: str = "auto"
    max_domains: Optional[int] = None
    dpa_rate: float = 1e-7
    process: str = "annealed"


class UnifiedRunRequest(BaseModel):
    query: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None
    composition: Optional[Dict[str, float]] = None
    basis: Literal["wt", "mol"] = "wt"
    temperature_K: Optional[float] = None
    environment: Optional[str] = None
    application: Optional[str] = None
    target_properties: List[str] = Field(default_factory=list)
    domains_focus: Optional[List[str]] = None
    domain_priority: Optional[Dict[str, float]] = None
    weight_profile: str = "auto"
    max_domains: Optional[int] = None
    dpa_rate: float = 1e-7
    process: str = "annealed"
    overrides: RunOverrides = Field(default_factory=RunOverrides)


class ApiResponse(BaseModel):
    ok: bool = True
    data: Dict[str, Any]
