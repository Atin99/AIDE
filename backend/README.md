# Backend API

FastAPI wrapper around existing AIDE engines.

## Run Local

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

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
