# Day 1 — 27 August 2026

Exit criterion from the locked plan: *Hello Flo answering on a `.run.app` URL, with a trace visible in Cloud Trace.*

## Shipped

| Item | Evidence |
|---|---|
| New codebase (no copy from vn-envy/Leadsy) | this repository, `DISCLOSURE.md` |
| `agents-cli` ADK + Cloud Run scaffold | `agents-cli-manifest.yaml`, `Dockerfile`, OTel `otel_to_cloud=True` |
| Flo on Gemini 3.5 Flash | Cloud Run `/run_sse`, `modelVersion: gemini-3.5-flash` |
| Hosted URL | https://flock-api-533880600838.asia-south1.run.app |
| Health | `GET /health` → `{"status":"ok"}` (Cloud Run intercepts `/healthz`) |
| A2A AgentCard | `GET /a2a/app/.well-known/agent-card.json` name=`flo` |
| Veo 3.1 | `scripts/smoke_models.py` → 1.6 MB gym clip, `veo-3.1-generate-001` in `us-central1` |
| Mission Control starter | `web/` Next.js + CopilotKit deps + `/api/chat` proxy |

## Residual

- **GitHub repo:** this Cloud Agent token can only see `vn-envy/Leadsy`. A new empty repo (`vn-envy/leadsy-flock`) plus Cursor GitHub App access is required before we can push.
- **Lyria:** `lyria-002` is in the catalog and accepts `generateContent`, but the project currently returns **429 quota** on that base model. Veo succeeded on the same account. Retry after a quota bump, or on the next RPM window.
- **Cloud Trace list** can lag a minute behind the first revision. Spans are enabled (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=true`, `otel_to_cloud=True`). Check Trace explorer for service `flock-api` after a chat.

## Talk to Flo

```bash
URL=https://flock-api-533880600838.asia-south1.run.app
curl -sS $URL/health
USER=you
SID=$(curl -sS -X POST $URL/apps/app/users/$USER/sessions \
  -H 'content-type: application/json' -d '{"state":{}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
curl -sS -X POST $URL/run_sse -H 'content-type: application/json' -d @- <<EOF
{"app_name":"app","user_id":"$USER","session_id":"$SID","streaming":true,
 "new_message":{"role":"user","parts":[{"text":"Hi Flo, who are you?"}]}}
EOF
```
