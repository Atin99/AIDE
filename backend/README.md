# Backend API

FastAPI wrapper around existing AIDE engines.

## Run Local

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
```

For multi-iteration design runs, keep the backend connection window at 300 seconds. If you sit behind Render, Nginx, Cloudflare, or another proxy, update that layer's request/read timeout too.

## Main Endpoint

- `POST /api/v1/run`

## Docker Run

```powershell
docker build -t aide-v5-api -f deploy/backend.Dockerfile .
docker run --rm -p 8000:8000 aide-v5-api
```

## Tests

```powershell
python -m unittest backend.tests.test_api
```
