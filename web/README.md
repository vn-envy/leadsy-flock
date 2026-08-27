# Mission Control (starter)

Next.js 15 app that proxies chat to Flo on Cloud Run.

```bash
cd web
cp .env.example .env.local   # FLOCK_API_URL already points at flock-api
npm install
npm run dev
```

Open http://localhost:3000 — send a brief, Flo answers through `/api/chat` → ADK `/run_sse`.

`@copilotkit/react-core` / `runtime` are installed. `/api/copilotkit` is the AG-UI stub (501) until we wrap the same Cloud Run service.
