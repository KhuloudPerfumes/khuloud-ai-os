# Free Cloud Deployment Plan

KHULOUD AI OS remains local-first. The free cloud version is a phone-accessible command dashboard, not a guaranteed 24/7 autonomous company runtime.

Free mode goal:

Founder opens the website from phone -> taps Wake Backend -> taps Run Daily Check or Generate Daily CEO Report -> reviews the company chat and task state.

## Target Free Architecture

- Frontend: Vercel free hosting.
- Backend: Render free web service or equivalent free container/web host.
- Database: Supabase free Postgres.
- Redis: optional in free mode. Keep local Redis for full local mode; cloud free mode can degrade when Redis is not configured.
- Qdrant/vector memory: optional in free mode. Keep local Qdrant for full local mode.
- AI/image generation: keep local by default. Cloud mode queues image requests unless a free model provider is explicitly configured.
- Shopify: webhook-ready, but must show disconnected/not configured if credentials are missing.

## Free Mode Rules

- Do not remove localhost/Docker Compose.
- Keep `ENVIRONMENT=local` for the laptop stack.
- Use `ENVIRONMENT=cloud-free` and `NEXT_PUBLIC_DEPLOYMENT_MODE=cloud-free` only for the free cloud deployment.
- Do not use paid APIs.
- Do not require a credit card.
- Assume the backend can sleep.
- The frontend must never crash when backend, database, Redis, Ollama, Qdrant, or Shopify are unavailable.
- Dangerous actions remain approval-gated.

## User Flow From Phone

1. Open the Vercel frontend URL.
2. If the backend status is asleep/unavailable, tap `Wake Backend`.
3. Wait for the backend health status to turn available.
4. Tap `Run Daily Check`.
5. Tap `Generate Daily CEO Report`.
6. For visuals, tap `Queue Image Generation`; generate locally later from the laptop stack unless a free image provider is configured.

## UI Requirements For Free Cloud Mode

The dashboard includes:

- `Wake Backend`
- `Run Daily Check`
- `Generate Daily CEO Report`
- `Queue Image Generation`
- Free cloud warning: "Free cloud mode may sleep and is not guaranteed 24/7."
- Health indicators:
  - Frontend status
  - Backend status
  - Database status
  - AI model status
  - Shopify connection status

Failure behavior:

- If backend is asleep, show a clear warning and `Wake Backend`.
- If database is unavailable, show degraded status and avoid crashing lists/cards.
- If AI model is unavailable, show `local/offline` and avoid blocking daily checks.
- If Shopify is not configured, show `not configured`.
- If image generation is unavailable, queue the task instead of pretending generation succeeded.

## Environment Variables

Frontend on Vercel:

```text
NEXT_PUBLIC_DEPLOYMENT_MODE=cloud-free
NEXT_PUBLIC_API_BASE_URL=https://your-khuloud-backend.onrender.com
NEXT_PUBLIC_LOCAL_UNLOCK_PASSWORD=your-founder-password
```

Backend on Render:

```text
ENVIRONMENT=cloud-free
FRONTEND_BASE_URL=https://your-khuloud-frontend.vercel.app
DATABASE_URL=postgresql+psycopg://postgres:[password]@[supabase-host]:5432/postgres
REDIS_URL=
QDRANT_URL=
OLLAMA_BASE_URL=
OLLAMA_MODEL=local-disabled
LOCAL_AUTH_USERNAME=founder
LOCAL_AUTH_PASSWORD=your-founder-password
SHOPIFY_WEBHOOK_SECRET=change-me-until-configured
```

Local Docker `.env` stays as:

```text
ENVIRONMENT=local
NEXT_PUBLIC_DEPLOYMENT_MODE=local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg://khuloud:khuloud@postgres:5432/khuloud_ai_os
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
```

## Vercel Frontend Steps

1. Push the repo to GitHub.
2. Create a Vercel project from the repo.
3. Set the project root to `frontend` if Vercel does not auto-detect it.
4. Add the frontend environment variables above.
5. Deploy.
6. Open the Vercel URL from phone.

Notes:

- Vercel is only hosting the Next.js frontend in free mode.
- The frontend should be usable even when the backend is asleep.
- Do not put server secrets in `NEXT_PUBLIC_*` variables.

## Render Backend Steps

1. Create a free Render web service from the repo.
2. Use `backend` as the service root if configured through the dashboard.
3. Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Add backend environment variables.
5. Deploy.
6. Test:

```text
https://your-khuloud-backend.onrender.com/api/health
```

Render free services can spin down after inactivity. This is acceptable for cloud-free mode. The dashboard's `Wake Backend` button exists for this reason.

## Supabase Database Steps

1. Create a Supabase free project.
2. Copy the Postgres connection string.
3. Use the pooled or direct connection string that works with SQLAlchemy/psycopg.
4. Set it as `DATABASE_URL` in Render.
5. Let the FastAPI startup create the V1 tables.

Before serious production use, add Alembic migrations. Auto-creating tables is acceptable only for the current V1/free-mode stage.

## Cloud-Free Feature Split

Works in cloud-free mode:

- Login/unlock screen.
- Channel dashboard.
- Health status.
- Wake Backend.
- Daily check.
- Daily CEO report.
- Task and approval viewing.
- Queue image generation.
- Shopify status display.

Local-only or optional in free cloud mode:

- Ollama model execution.
- Heavy image generation.
- Qdrant vector memory.
- Redis-backed long-running workers.
- 24/7 monitoring.

## Implementation Checklist

- Add `NEXT_PUBLIC_DEPLOYMENT_MODE`.
- Keep local Docker Compose unchanged.
- Add timeout-based API calls in the frontend.
- Add graceful backend-asleep messages.
- Add `Wake Backend`.
- Add `/api/operations/daily-check`.
- Add `/api/operations/ceo-report`.
- Add `/api/operations/queue-image`.
- Expand `/api/health` with database, AI model, and Shopify status.
- Add frontend health indicators.
- Confirm local mode still works.

## Upgrade Path Later

When a paid or always-on deployment is allowed:

- Move backend to an always-on host.
- Add managed Redis.
- Add managed vector database or Qdrant Cloud.
- Add a real background worker process.
- Add a cloud model provider or self-hosted GPU image service.
- Add uptime monitoring.
- Add proper auth and RBAC.
- Add Alembic migrations.
