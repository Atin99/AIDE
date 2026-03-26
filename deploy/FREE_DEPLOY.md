# Free Deployment Runbook

This project uses a free split deployment architecture.

- Backend API on Hugging Face Spaces (Docker)
- Frontend on Cloudflare Pages (static)

## Prerequisites

- A Hugging Face account (free tier works)
- A Cloudflare account (free tier works)
- Git installed locally

## 1. Deploy Backend on Hugging Face Spaces

### 1.1 Create the bundle

```powershell
powershell -ExecutionPolicy Bypass -File deploy/prepare_hf_space.ps1
```

This creates `deploy/hf_space_bundle/` with everything needed for the Docker Space.

### 1.2 Create a new Hugging Face Space

1. Go to huggingface.co and create a new Space.
2. Set SDK to Docker.
3. Clone the Space repo locally.
4. Copy the contents of `deploy/hf_space_bundle/` into the cloned repo.
5. Commit and push.

### 1.3 Set Space environment variables

| Variable | Value |
|---|---|
| `AIDE_USE_LOCAL_LLM` | `1` |
| `AIDE_LOCAL_FIRST` | `1` |
| `AIDE_USE_LOCAL_INTENT` | `1` |
| `AIDE_USE_LLM_INTENT` | `0` |
| `AIDE_ENABLE_REMOTE_LLM` | `0` |
| `AIDE_API_CORS_ORIGINS` | `https://your-pages-domain.pages.dev` |

### 1.4 Verify

- `https://your-space-url/health` should return `{"ok": true}`
- `https://your-space-url/docs` should show Swagger UI

## 2. Deploy Frontend on Cloudflare Pages

### 2.1 Create a Pages project

1. Go to the Cloudflare dashboard and create a new Pages project.
2. Connect your Git repo or upload `frontend/` as a static site.
3. Set build output directory to `frontend/`.

### 2.2 Configure API connection

Option A - Proxy mode (recommended):
- Set Pages environment variable `AIDE_BACKEND_URL` to your Space URL.
- The `functions/api/[[path]].js` proxy will forward API calls.

Option B - Direct mode:
- Open frontend URL with `?api=https://your-space-url` once.
- The API base is stored in browser localStorage.

## 3. Post-Deploy Checks

1. Open the frontend and verify the health indicator shows connected.
2. Submit a query in Intent + Engine Run.
3. Submit a composition in Composition Analysis.
4. Confirm responses include `request_type` and `result`.

## 4. Cost Controls

- Keep one backend instance on the free tier.
- Keep remote API keys empty to avoid paid LLM calls.
- Use `AIDE_ENABLE_REMOTE_LLM=0` to enforce local-only mode.

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Space build fails | Check that `requirements.txt` has all dependencies. Run `pip install -r requirements.txt` locally first. |
| CORS errors in browser | Set `AIDE_API_CORS_ORIGINS` to your exact frontend URL (no trailing slash). |
| API returns 500 | Check Space logs. Most likely a missing Python package. |
| Health check returns unhealthy | Restart the Space. |
| Frontend shows disconnected | Verify API base URL is correct. Try `?api=https://your-space-url` in the URL bar. |
