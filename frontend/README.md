# Frontend

Static HTML/CSS/JS client for AIDE API.

## Run Local

```powershell
cd frontend
python -m http.server 5173
```

Open `http://localhost:5173`.

Set API Base URL to your backend, for example `http://localhost:8000`.

## Cloudflare Pages

- Deploy the `frontend/` directory as a Pages project.
- Optional Wrangler config is in `frontend/wrangler.toml`.
- Optional proxy function is in `frontend/functions/api/[[path]].js`.
- If using the proxy, set Pages env var `AIDE_BACKEND_URL=https://<backend-domain>`.
- Optional: set `AIDE_PROXY_TIMEOUT_MS=300000` to match the 5-minute backend window.
- Then frontend can use same-origin API calls with base URL equal to frontend domain.
- Without proxy, pass backend URL once via query:
  - `https://<pages-domain>/?api=https://<backend-domain>`
  - it is persisted in browser local storage.

The browser client now waits up to 300 seconds for `/api/v1/run`. If Cloudflare Pages or another edge platform still cuts long requests early, use direct mode (`?api=https://<backend-domain>`) or move the long-running call behind a job/polling flow.
