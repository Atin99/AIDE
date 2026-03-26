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
- Then frontend can use same-origin API calls with base URL equal to frontend domain.
- Without proxy, pass backend URL once via query:
  - `https://<pages-domain>/?api=https://<backend-domain>`
  - it is persisted in browser local storage.
