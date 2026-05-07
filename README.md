# KHULOUD AI OS

KHULOUD AI OS is a local-first, cloud-ready multi-agent company operating system for Khuloud Perfumes. It uses a Teams/Slack-style interface, a FastAPI orchestration backend, PostgreSQL shared state, Redis queues, Qdrant-ready memory, Ollama local models, and a CrewAI-ready adapter.

V1 activates five AI employees:

- CEO Orchestrator Bot
- Creative Director Bot
- Performance Marketing Bot
- Shopify CRO Bot
- WhatsApp Sales Bot

The remaining 20 company roles are scaffolded in `backend/app/config/bots.yaml` and inactive by default.

## Architecture

- `frontend/`: Next.js, TypeScript, TailwindCSS founder command UI.
- `backend/`: FastAPI API, bot routing, task system, approvals, memory, Shopify webhook ingestion.
- `postgres`: durable relational state.
- `redis`: queue backbone for background jobs and integrations.
- `qdrant`: vector memory service, ready for deeper semantic retrieval.
- `ollama`: local AI runtime.

Main flow:

Founder -> CEO Orchestrator -> Department Bot -> Approval Queue -> Execution Preparation -> Memory -> Reports

## Local Setup

1. Install Docker Desktop.
2. Copy environment variables:

```powershell
Copy-Item .env.example .env
```

3. Start the system:

```powershell
.\scripts\start-local.ps1
```

If local `npm install` is blocked by PowerShell policy or registry access, Docker Compose still builds the frontend inside the Node container once Docker Desktop is installed.

4. Optional: pull the default local model:

```powershell
.\scripts\start-local.ps1 -PullModel
```

5. Open:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/api/health`

Default local UI unlock password:

```text
khuloud-founder
```

This is a laptop-only guard for V1. Replace it with backend sessions or SSO before exposing the app to a network.

## Approval Safety

Bots cannot execute these actions without founder approval:

- spend money
- launch ads
- message customers
- change prices
- refund orders
- edit Shopify live theme
- cancel orders
- make supplier payments

The backend creates approval records whenever a founder request appears to touch restricted actions.

## Shopify Ready

Webhook endpoint:

```text
POST /api/shopify/webhooks/{event_type}
```

Supported future events include orders, abandoned carts, failed payments, COD monitoring, inventory alerts, customer notes, and order summaries. Webhooks are verified with `SHOPIFY_WEBHOOK_SECRET` when configured.

## Notifications

Founder alerts are ready for Telegram or SMTP email. Configure:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `FOUNDER_EMAIL`

## Health Monitoring

```powershell
.\scripts\healthcheck.ps1
```

Docker Compose uses `restart: unless-stopped` and service health checks so the system recovers while the laptop is on.

## Free Cloud Mode

The free cloud version is designed for phone access, not 24/7 operation. Deploy the frontend to Vercel free, the backend to a free web host such as Render, and the database to Supabase free. Heavy Ollama/image work stays local unless a free model provider is configured.

The dashboard includes cloud-safe controls:

- `Wake Backend`
- `Run Daily Check`
- `Generate Daily CEO Report`
- `Queue Image Generation`
- service health indicators for frontend, backend, database, AI model, and Shopify

Free cloud mode may sleep and is not guaranteed 24/7. The UI is expected to degrade gracefully when backend or database services are unavailable.

See [docs/CLOUD_MIGRATION.md](docs/CLOUD_MIGRATION.md) for the full free deployment plan and [docs/PHONE_DEPLOYMENT_RUNBOOK.md](docs/PHONE_DEPLOYMENT_RUNBOOK.md) for the exact phone-accessible deployment steps.

## Next Engineering Milestones

- Add Alembic migrations.
- Add background worker process for Redis queues.
- Add local auth screens and RBAC enforcement.
- Add Qdrant embeddings and retrieval beyond SQL text search.
- Add n8n webhook outbound triggers.
- Add real Shopify data dashboards after credentials are configured.
- Add LangGraph adapter beside the CrewAI-ready orchestration boundary.
