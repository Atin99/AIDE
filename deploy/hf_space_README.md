---
title: AIDE v5 API
sdk: docker
app_port: 8000
---

# AIDE v5 API

Containerized FastAPI backend for alloy analysis.

## Endpoints

- `GET /health`
- `GET /api/v1/domains`
- `POST /api/v1/run`

## Notes

- Keep `AIDE_ENABLE_REMOTE_LLM=0` for local-only LLM behavior.
- Set `AIDE_API_CORS_ORIGINS` to your frontend URL for production.
