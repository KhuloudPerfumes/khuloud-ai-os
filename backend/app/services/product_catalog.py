import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.models import MemoryItem


@dataclass
class ProductImage:
    src: str
    alt: str = ""


@dataclass
class ProductSource:
    title: str
    handle: str
    url: str
    description: str
    images: list[ProductImage]
    tags: list[str]


async def fetch_product_catalog(source_url: str, limit: int = 250) -> list[ProductSource]:
    base_url = source_url.rstrip("/")
    products_url = f"{base_url}/products.json?limit={limit}"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(products_url)
        response.raise_for_status()
        data = response.json()
    products: list[ProductSource] = []
    for item in data.get("products", []):
        images = [
            ProductImage(src=image.get("src", ""), alt=image.get("alt") or item.get("title", ""))
            for image in item.get("images", [])
            if image.get("src")
        ]
        products.append(
            ProductSource(
                title=item.get("title", "Untitled product"),
                handle=item.get("handle", ""),
                url=urljoin(base_url, f"/products/{item.get('handle', '')}"),
                description=_clean_html(item.get("body_html", "")),
                images=images,
                tags=item.get("tags", []) or [],
            )
        )
    return products


def select_relevant_products(prompt: str, products: list[ProductSource], limit: int = 4) -> list[ProductSource]:
    words = {word for word in re.findall(r"[a-z0-9]+", prompt.lower()) if len(word) > 2}
    scored: list[tuple[int, ProductSource]] = []
    for product in products:
        haystack = " ".join([product.title, product.handle, product.description, " ".join(product.tags)]).lower()
        score = sum(3 for word in words if word in product.title.lower())
        score += sum(1 for word in words if word in haystack)
        if score:
            scored.append((score, product))
    if not scored:
        return products[:limit]
    return [product for _, product in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def product_context(products: list[ProductSource]) -> str:
    lines: list[str] = []
    for product in products:
        image_urls = ", ".join(image.src for image in product.images[:3])
        description = product.description[:420] if product.description else "No product description found."
        lines.append(
            f"Product: {product.title}\n"
            f"URL: {product.url}\n"
            f"Description: {description}\n"
            f"Reference images: {image_urls}"
        )
    return "\n\n".join(lines)


def sync_products_to_memory(db: Session, products: list[ProductSource], source_url: str) -> int:
    count = 0
    for product in products:
        title = f"Product catalog: {product.title}"
        existing = db.query(MemoryItem).filter(MemoryItem.scope == "product_catalog", MemoryItem.title == title).one_or_none()
        content = (
            f"Source: {source_url}\n"
            f"Product URL: {product.url}\n"
            f"Handle: {product.handle}\n"
            f"Tags: {', '.join(product.tags)}\n"
            f"Description: {product.description}\n"
            f"Images: {', '.join(image.src for image in product.images)}"
        )
        if existing:
            existing.content = content
            existing.source = "khuloudperfumes.com"
            existing.created_by = "product_catalog_sync"
        else:
            db.add(
                MemoryItem(
                    scope="product_catalog",
                    title=title,
                    content=content,
                    source="khuloudperfumes.com",
                    created_by="product_catalog_sync",
                )
            )
        count += 1
    db.commit()
    return count


def product_to_dict(product: ProductSource) -> dict:
    return {
        "title": product.title,
        "handle": product.handle,
        "url": product.url,
        "description": product.description,
        "tags": product.tags,
        "images": [{"src": image.src, "alt": image.alt} for image in product.images],
    }


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(unescape(without_tags).split())
