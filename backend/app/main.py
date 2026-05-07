from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.routers import approvals, assets, bots, bootstrap, chat, health, operations, products, shopify, tasks
from app.seed import seed_system


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        init_db()
        db = SessionLocal()
        try:
            seed_system(db, settings.config_dir)
        finally:
            db.close()
    except Exception as exc:
        print(f"Startup warning: database initialization skipped: {exc}", flush=True)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(bootstrap.router)
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(assets.router)
app.include_router(bots.router)
app.include_router(shopify.router)
app.include_router(operations.router)
app.include_router(products.router)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "status": "online"}
