from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.services.product_catalog import fetch_product_catalog, product_to_dict, sync_products_to_memory

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products() -> dict:
    settings = get_settings()
    products = await fetch_product_catalog(settings.product_source_url)
    return {
        "source_url": settings.product_source_url,
        "count": len(products),
        "products": [product_to_dict(product) for product in products],
    }


@router.post("/sync")
async def sync_products(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    products = await fetch_product_catalog(settings.product_source_url)
    synced = sync_products_to_memory(db, products, settings.product_source_url)
    return {
        "source_url": settings.product_source_url,
        "synced": synced,
        "products": [product_to_dict(product) for product in products],
    }
