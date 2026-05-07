import html
import base64
import json
import textwrap
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage, GeneratedAsset
from app.core.config import get_settings
from app.services.logging import log_action
from app.services.memory import add_memory
from app.services.product_catalog import fetch_product_catalog, product_context, select_relevant_products, sync_products_to_memory
from app.services.realtime import manager

router = APIRouter(prefix="/api/assets", tags=["assets"])


class AssetRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=2000)
    title: str = "Campaign concept board"
    created_by: str = "creative_director"
    channel_key: str = "founder-command"


@router.post("/generate")
async def generate_asset(payload: AssetRequest, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    source_products = []
    source_context = "No product catalog context available."
    try:
        products = await fetch_product_catalog(settings.product_source_url)
        sync_products_to_memory(db, products, settings.product_source_url)
        source_products = select_relevant_products(payload.prompt, products)
        source_context = product_context(source_products)
    except Exception as exc:
        source_context = f"Product catalog could not be loaded from {settings.product_source_url}: {exc}"

    await _create_and_broadcast_message(
        db,
        channel_key=payload.channel_key,
        sender_key="ceo",
        sender_name="CEO Orchestrator Bot",
        body=(
            "Visual generation route opened.\n\n"
            "Creative Director owns the luxury art direction. Performance Marketing is checking thumb-stop value. "
            "Shopify CRO is checking product-board usefulness for the product page and WhatsApp sales flow."
        ),
    )
    await _create_and_broadcast_message(
        db,
        channel_key=payload.channel_key,
        sender_key="creative_director",
        sender_name="Creative Director Bot",
        body=(
            f"Building the image direction now: {payload.prompt}\n\n"
            f"Product source: {settings.product_source_url}\n"
            f"Reference products found: {', '.join(product.title for product in source_products) if source_products else 'none'}"
        ),
    )
    await _create_and_broadcast_message(
        db,
        channel_key=payload.channel_key,
        sender_key="performance_marketing",
        sender_name="Performance Marketing Bot",
        body="Reviewing this as a paid-social visual: strong bottle visibility, clear contrast, no tiny text, and immediate luxury signal.",
    )
    await _create_and_broadcast_message(
        db,
        channel_key=payload.channel_key,
        sender_key="shopify_cro",
        sender_name="Shopify CRO Bot",
        body="Preparing a separate product board so the output can be reviewed for product-page hero, bundle card, and WhatsApp recommendation use.",
    )

    campaign_prompt = (
        f"Luxury perfume campaign board for KHULOUD Perfumes. {payload.prompt}.\n"
        f"Use these actual Khuloud product references and product image URLs as source inspiration:\n{source_context}\n"
        "Preserve the product identity, bottle silhouette, label mood, and luxury cues. Black luxury background, deep purple shadows, gold highlights, editorial product photography, no UI, no text overlays, high-end advertising visual."
    )
    product_prompt = (
        f"Individual product board image for KHULOUD Perfumes. {payload.prompt}.\n"
        f"Use these actual Khuloud product references and product image URLs as source inspiration:\n{source_context}\n"
        "Preserve the product identity, bottle silhouette, label mood, and luxury cues. Centered product, clean product photography, no UI, no text overlays."
    )
    campaign_image = await _generated_bitmap(
        campaign_prompt,
        source_products,
    )
    product_image = await _generated_bitmap(
        product_prompt,
        source_products,
    )
    campaign_visual = campaign_image or _campaign_svg(payload.title, payload.prompt)
    product_visual = product_image or _product_board_svg(payload.title, payload.prompt)
    asset_type = "campaign_board_image" if campaign_image else "campaign_board_svg"
    product_asset_type = "product_board_image" if product_image else "product_board_svg"
    asset = GeneratedAsset(title=payload.title[:240], prompt=payload.prompt, asset_type=asset_type, created_by=payload.created_by, svg=campaign_visual)
    product_asset = GeneratedAsset(
        title=f"{payload.title[:210]} - Product Board",
        prompt=payload.prompt,
        asset_type=product_asset_type,
        created_by=payload.created_by,
        svg=product_visual,
    )
    db.add_all([asset, product_asset])
    db.commit()
    db.refresh(asset)
    db.refresh(product_asset)

    add_memory(
        db,
        scope="approved_creatives",
        title=f"Generated visual board: {payload.title}",
        content=(
            f"Prompt: {payload.prompt}\n"
            f"Product source: {settings.product_source_url}\n"
            f"Reference products: {', '.join(product.title for product in source_products)}\n"
            f"Reference images: {', '.join(image.src for product in source_products for image in product.images[:2])}\n"
            f"Campaign board: {asset.id}\nProduct board: {product_asset.id}"
        ),
        created_by=payload.created_by,
        source="visual_generator",
    )
    log_action(db, payload.created_by, "generate_visual_asset", "asset", asset.id, details=payload.prompt)

    message = ChatMessage(
        channel_key=payload.channel_key,
        sender_key=payload.created_by,
        sender_name="Creative Director Bot",
        sender_type="bot",
        body=(
            f"Generated visuals for {payload.title}.\n\n"
            f"Product source used: {settings.product_source_url}\n"
            f"Reference products: {', '.join(product.title for product in source_products) if source_products else 'No matching product source found'}.\n\n"
            "Campaign image is embedded below for immediate review.\n"
            "A separate individual product board image was also created and saved in Generated Visuals.\n\n"
            "You can reply in this chat with changes like: make it more citrus, change bottle color, add Arabic luxury cues, or create a Meta ad version."
        ),
        metadata_json=json.dumps(
            {
                "assets": [
                    _asset_dict(asset),
                    _asset_dict(product_asset),
                ]
            }
        ),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    await manager.broadcast(
        {
            "type": "message",
            "message": {
                "id": message.id,
                "channel_key": message.channel_key,
                "sender_key": message.sender_key,
                "sender_name": message.sender_name,
                "sender_type": message.sender_type,
                "body": message.body,
                "metadata": {
                    "assets": [
                        _asset_dict(asset),
                        _asset_dict(product_asset),
                    ]
                },
                "created_at": message.created_at.isoformat(),
            },
        }
    )
    await manager.broadcast({"type": "asset_created", "asset_id": asset.id})
    await manager.broadcast({"type": "asset_created", "asset_id": product_asset.id})
    return {"asset": _asset_dict(asset), "product_board": _asset_dict(product_asset)}


@router.get("/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_db)) -> dict:
    asset = db.query(GeneratedAsset).filter(GeneratedAsset.id == asset_id).one()
    return {"asset": _asset_dict(asset)}


def _asset_dict(asset: GeneratedAsset) -> dict:
    return {
        "id": asset.id,
        "title": asset.title,
        "prompt": asset.prompt,
        "asset_type": asset.asset_type,
        "created_by": asset.created_by,
        "svg": asset.svg,
        "created_at": asset.created_at.isoformat(),
    }


async def _create_and_broadcast_message(
    db: Session,
    *,
    channel_key: str,
    sender_key: str,
    sender_name: str,
    body: str,
) -> ChatMessage:
    message = ChatMessage(
        channel_key=channel_key,
        sender_key=sender_key,
        sender_name=sender_name,
        sender_type="bot",
        body=body,
        metadata_json=json.dumps({}),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    await manager.broadcast(
        {
            "type": "message",
            "message": {
                "id": message.id,
                "channel_key": message.channel_key,
                "sender_key": message.sender_key,
                "sender_name": message.sender_name,
                "sender_type": message.sender_type,
                "body": message.body,
                "metadata": {},
                "created_at": message.created_at.isoformat(),
            },
        }
    )
    return message


async def _generated_bitmap(prompt: str, source_products: list | None = None) -> str | None:
    gemini_image = await _gemini_bitmap(prompt, source_products or [])
    if gemini_image:
        return gemini_image
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1280&height=720&model=flux&nologo=true&private=true&seed={abs(hash(prompt)) % 1000000}"
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                return None
            encoded = base64.b64encode(response.content).decode("ascii")
            return f"data:{content_type};base64,{encoded}"
    except Exception:
        return None


async def _gemini_bitmap(prompt: str, source_products: list) -> str | None:
    settings = get_settings()
    if settings.image_generation_provider.lower() not in {"gemini", "nanobanana", "nano-banana"}:
        return None
    if not settings.gemini_api_key:
        return None
    parts: list[dict] = [{"text": prompt}]
    for product in source_products[:2]:
        for image in product.images[:2]:
            encoded = await _download_image_as_inline_data(image.src)
            if encoded:
                parts.append(encoded)
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image:generateContent?key={settings.gemini_api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(endpoint, json={"contents": [{"parts": parts}]})
            response.raise_for_status()
            data = response.json()
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    return f"data:{mime_type};base64,{inline['data']}"
    except Exception:
        return None
    return None


async def _download_image_as_inline_data(url: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/png")
            if not content_type.startswith("image/"):
                return None
            return {
                "inlineData": {
                    "mimeType": content_type,
                    "data": base64.b64encode(response.content).decode("ascii"),
                }
            }
    except Exception:
        return None


def _campaign_svg(title: str, prompt: str) -> str:
    safe_title = html.escape(title)
    safe_prompt = html.escape(prompt)
    wrapped = textwrap.wrap(prompt, width=42)[:7]
    lines = "".join(
        f'<text x="74" y="{220 + index * 30}" fill="#d8cfbd" font-size="18">{html.escape(line)}</text>'
        for index, line in enumerate(wrapped)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#06050a"/>
      <stop offset="0.55" stop-color="#1b1027"/>
      <stop offset="1" stop-color="#08070b"/>
    </linearGradient>
    <radialGradient id="gold" cx="0.55" cy="0.45" r="0.5">
      <stop offset="0" stop-color="#f1d58b"/>
      <stop offset="1" stop-color="#6f5526"/>
    </radialGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <rect x="46" y="44" width="1188" height="632" rx="18" fill="none" stroke="#3a2d48"/>
  <text x="72" y="104" fill="#d7b56d" font-size="20" font-family="Arial" letter-spacing="3">KHULOUD PERFUMES</text>
  <text x="72" y="158" fill="#fff8e8" font-size="52" font-family="Arial" font-weight="700">{safe_title}</text>
  <text x="74" y="194" fill="#8e829d" font-size="16" font-family="Arial">AI-generated campaign concept board</text>
  {lines}
  <g transform="translate(792 122)">
    <rect x="0" y="260" width="290" height="86" rx="18" fill="#050407" stroke="#d7b56d" opacity="0.9"/>
    <rect x="85" y="76" width="120" height="300" rx="28" fill="#0d0a11" stroke="#d7b56d" stroke-width="4"/>
    <rect x="104" y="18" width="82" height="80" rx="18" fill="#101018" stroke="#69503a"/>
    <rect x="114" y="120" width="62" height="132" rx="10" fill="url(#gold)"/>
    <text x="145" y="177" text-anchor="middle" fill="#07060a" font-size="19" font-family="Arial" font-weight="700">K</text>
    <text x="145" y="205" text-anchor="middle" fill="#211705" font-size="12" font-family="Arial">EAU DE PARFUM</text>
    <path d="M-70 150 C 30 40, 260 30, 392 164" fill="none" stroke="#6d46c8" stroke-width="5" opacity="0.55"/>
    <path d="M-30 440 C 82 500, 250 500, 360 424" fill="none" stroke="#d7b56d" stroke-width="3" opacity="0.55"/>
  </g>
  <text x="74" y="632" fill="#d7b56d" font-size="22" font-family="Arial">Founder approval required before public campaign use.</text>
</svg>"""


def _product_board_svg(title: str, prompt: str) -> str:
    safe_title = html.escape(title)
    wrapped = textwrap.wrap(prompt, width=34)[:5]
    lines = "".join(
        f'<text x="760" y="{258 + index * 28}" fill="#d8cfbd" font-size="16">{html.escape(line)}</text>'
        for index, line in enumerate(wrapped)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
  <defs>
    <linearGradient id="pbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#050407"/>
      <stop offset="0.48" stop-color="#160d21"/>
      <stop offset="1" stop-color="#080507"/>
    </linearGradient>
    <radialGradient id="citrus" cx="0.5" cy="0.5" r="0.58">
      <stop offset="0" stop-color="#ffe6a3"/>
      <stop offset="0.38" stop-color="#d7b56d"/>
      <stop offset="1" stop-color="#3f2c10"/>
    </radialGradient>
  </defs>
  <rect width="1080" height="1080" fill="url(#pbg)"/>
  <text x="76" y="98" fill="#d7b56d" font-size="24" font-family="Arial" letter-spacing="4">KHULOUD PERFUMES</text>
  <text x="76" y="160" fill="#fff8e8" font-size="54" font-family="Arial" font-weight="700">{safe_title}</text>
  <text x="76" y="202" fill="#9b8cab" font-size="20" font-family="Arial">Individual product board</text>
  <circle cx="370" cy="560" r="245" fill="#120c18" stroke="#342344"/>
  <path d="M190 660 C260 495,470 415,620 260" fill="none" stroke="#d7b56d" stroke-width="10" opacity="0.28"/>
  <path d="M190 720 C320 770,505 760,640 690" fill="none" stroke="#6d46c8" stroke-width="8" opacity="0.35"/>
  <rect x="294" y="280" width="160" height="470" rx="36" fill="#08070b" stroke="#d7b56d" stroke-width="5"/>
  <rect x="323" y="350" width="102" height="210" rx="16" fill="url(#citrus)"/>
  <rect x="326" y="206" width="96" height="110" rx="20" fill="#111019" stroke="#6f5526" stroke-width="4"/>
  <text x="374" y="442" text-anchor="middle" fill="#080507" font-size="42" font-family="Arial" font-weight="700">K</text>
  <text x="374" y="486" text-anchor="middle" fill="#221705" font-size="16" font-family="Arial">CITRUS</text>
  <text x="374" y="512" text-anchor="middle" fill="#221705" font-size="16" font-family="Arial">REVERENCE</text>
  <text x="760" y="218" fill="#d7b56d" font-size="22" font-family="Arial">Board Notes</text>
  {lines}
  <text x="760" y="456" fill="#d7b56d" font-size="20" font-family="Arial">Use cases</text>
  <text x="760" y="492" fill="#d8cfbd" font-size="16">Product page hero</text>
  <text x="760" y="522" fill="#d8cfbd" font-size="16">Meta ad still frame</text>
  <text x="760" y="552" fill="#d8cfbd" font-size="16">WhatsApp product card</text>
  <text x="760" y="620" fill="#d7b56d" font-size="20" font-family="Arial">Approval Gate</text>
  <text x="760" y="656" fill="#d8cfbd" font-size="16">Founder approval required</text>
  <text x="760" y="684" fill="#d8cfbd" font-size="16">before public campaign use.</text>
  <rect x="70" y="880" width="940" height="118" rx="18" fill="none" stroke="#3a2d48"/>
  <text x="100" y="930" fill="#fff8e8" font-size="26" font-family="Arial">Luxury, bright citrus, intimate warmth, premium restraint.</text>
  <text x="100" y="966" fill="#9b8cab" font-size="18" font-family="Arial">Editable direction: reply with changes in the chat thread.</text>
</svg>"""
