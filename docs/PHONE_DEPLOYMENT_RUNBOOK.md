# Phone Deployment Runbook

This runbook turns KHULOUD AI OS into a free, phone-accessible cloud dashboard while keeping the local Docker version intact.

## What You Need

- GitHub account.
- Vercel account.
- Render account.
- Supabase account.
- No paid APIs.
- No credit card requirement for the intended free-mode path.

## 1. Create Supabase Free Database

1. Create a new Supabase project.
2. Copy the Postgres connection string.
3. Use the URI form that starts with `postgresql://`.
4. Convert it for the backend by changing the prefix to:

```text
postgresql+psycopg://...
```

Save this as `DATABASE_URL` for Render.

## 2. Push Repo To GitHub

From this folder:

```powershell
git init
git add .
git commit -m "Prepare KHULOUD AI OS cloud-free deployment"
```

Then create a GitHub repo and push:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/khuloud-ai-os.git
git branch -M main
git push -u origin main
```

## 3. Deploy Backend To Render Free

1. In Render, create a new Blueprint or Web Service from the GitHub repo.
2. If using Blueprint, Render reads `render.yaml`.
3. Set these environment variables:

```text
ENVIRONMENT=cloud-free
DATABASE_URL=postgresql+psycopg://...
FRONTEND_BASE_URL=https://your-vercel-url.vercel.app
LOCAL_AUTH_PASSWORD=your-founder-password
SHOPIFY_WEBHOOK_SECRET=change-me-until-shopify-is-connected
```

4. Deploy.
5. Copy the backend URL:

```text
https://your-render-service.onrender.com
```

6. Test:

```text
https://your-render-service.onrender.com/api/health
```

## 4. Deploy Frontend To Vercel Free

1. Import the same GitHub repo into Vercel.
2. Keep the root as the repository root. `vercel.json` points Vercel to `frontend`.
3. Set these environment variables:

```text
NEXT_PUBLIC_DEPLOYMENT_MODE=cloud-free
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
NEXT_PUBLIC_LOCAL_UNLOCK_PASSWORD=your-founder-password
```

4. Deploy.
5. Open the final Vercel URL from your phone.

## 5. Phone Use

1. Open the Vercel URL.
2. Unlock KHULOUD AI OS.
3. Tap `Wake Backend`.
4. Tap `Run Daily Check`.
5. Tap `Generate Daily CEO Report`.
6. Tap `Queue Image Generation` for visuals that should be generated later on the local laptop stack.

## Expected Free-Mode Behavior

- Backend may sleep.
- First wake can take time.
- AI model may show local/offline.
- Shopify may show not configured until credentials are added.
- The dashboard should not crash when services are asleep.

## Local Mode Remains

Local full mode still runs with:

```powershell
.\scripts\start-local.ps1
```

Local URL:

```text
http://localhost:3000
```
