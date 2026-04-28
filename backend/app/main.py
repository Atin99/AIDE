import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from llms.client import get_available_providers
from llms.client import remote_llm_enabled

from .schemas import ApiResponse
from .schemas import CompositionAnalyzeRequest
from .schemas import EngineRunRequest
from .schemas import IntentClassifyRequest
from .schemas import UnifiedRunRequest
from .services.analysis_service import classify_query
from .services.analysis_service import list_alloys
from .services.analysis_service import list_domains
from .services.analysis_service import run_composition_analysis
from .services.analysis_service import run_engine
from .services.analysis_service import run_unified
from .services.serialization import serialize_any

logger = logging.getLogger("AIDE.api")


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """Emit startup diagnostics once for the remote-only API runtime."""
    logger.info("AIDE v5 API starting")
    logger.info("CORS origins: %s", origins)
    providers = [
        f"{provider['label']} [{provider['model']}]"
        for provider in get_available_providers()
    ]
    logger.info("Remote LLM mode: %s", "enabled" if remote_llm_enabled() else "disabled")
    logger.info("Configured remote LLM providers: %s", providers or ["none"])
    yield


app = FastAPI(
    title="AIDE v5 API",
    version="0.3.0",
    description="API wrapper for AIDE alloy design and analysis engines.",
    lifespan=app_lifespan,
)


def _cors_origins():
    raw = os.environ.get("AIDE_API_CORS_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, elapsed)
    return response


@app.get("/", response_model=ApiResponse)
def root():
    return {
        "ok": True,
        "data": {
            "name": "AIDE v5 API",
            "version": "0.3.0",
            "docs": "/docs",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/health", response_model=ApiResponse)
def health():
    providers = get_available_providers()
    return {
        "ok": True,
        "data": {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reasoning_pipeline": {
                "intent_llm_enabled": os.environ.get("AIDE_USE_LLM_INTENT", "1").strip().lower() in {"1", "true", "yes", "on"},
                "research_llm_enabled": os.environ.get("AIDE_USE_LLM_RESEARCH", "1").strip().lower() in {"1", "true", "yes", "on"},
                "generation_llm_enabled": os.environ.get("AIDE_USE_LLM_GENERATION", "1").strip().lower() in {"1", "true", "yes", "on"},
            },
            "remote_llm": {
                "enabled": remote_llm_enabled(),
                "providers": [
                    {
                        "name": provider["name"],
                        "label": provider.get("label", provider["name"]),
                        "model": provider["model"],
                        "tier": provider.get("tier", "unknown"),
                    }
                    for provider in providers
                ],
            },
        },
    }


@app.get("/api/v1/alloys", response_model=ApiResponse)
def get_alloys():
    return {"ok": True, "data": {"alloys": list_alloys()}}


@app.get("/api/v1/domains", response_model=ApiResponse)
def get_domains():
    return {"ok": True, "data": {"domains": list_domains()}}


@app.post("/api/v1/run", response_model=ApiResponse)
def run_unified_endpoint(payload: UnifiedRunRequest):
    try:
        result = run_unified(payload.model_dump(exclude_none=True))
        return {"ok": True, "data": serialize_any(result)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/intent/classify", response_model=ApiResponse)
def classify_intent_endpoint(payload: IntentClassifyRequest):
    try:
        intent = classify_query(payload.query)
        return {"ok": True, "data": {"intent": serialize_any(intent)}}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/engine/run", response_model=ApiResponse)
def run_engine_endpoint(payload: EngineRunRequest):
    try:
        result = run_engine(
            query=payload.query,
            intent=payload.intent,
            overrides=payload.overrides.model_dump(exclude_none=True),
        )
        return {"ok": True, "data": serialize_any(result)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/composition/analyze", response_model=ApiResponse)
def analyze_composition_endpoint(payload: CompositionAnalyzeRequest):
    try:
        result = run_composition_analysis(
            composition=payload.composition,
            basis=payload.basis,
            temperature_K=payload.temperature_K,
            environment=payload.environment,
            application=payload.application,
            target_properties=payload.target_properties,
            domains_focus=payload.domains_focus,
            domain_priority=payload.domain_priority,
            weight_profile=payload.weight_profile,
            max_domains=payload.max_domains,
            dpa_rate=payload.dpa_rate,
            process=payload.process,
        )
        return {"ok": True, "data": serialize_any(result)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/app/{rest_of_path:path}")
def serve_frontend(rest_of_path: str):
    if not rest_of_path or rest_of_path == "/":
        rest_of_path = "index.html"
    file_path = FRONTEND_DIR / rest_of_path
    if file_path.is_file():
        media = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        return FileResponse(file_path, media_type=media.get(file_path.suffix, "application/octet-stream"))
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
