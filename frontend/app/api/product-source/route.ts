import { NextResponse } from "next/server";

const SOURCE_URL = process.env.KHULOUD_PRODUCT_SOURCE_URL || "https://khuloudperfumes.com";

type ShopifyProduct = {
  title: string;
  handle: string;
  body_html?: string;
  tags?: string[];
  images?: Array<{ src: string; alt?: string }>;
};

export async function GET() {
  const response = await fetch(`${SOURCE_URL.replace(/\/$/, "")}/products.json?limit=250`, {
    next: { revalidate: 900 }
  });
  if (!response.ok) {
    return NextResponse.json({ sourceUrl: SOURCE_URL, count: 0, products: [] }, { status: 502 });
  }
  const data = await response.json();
  const products = (data.products || []).map((product: ShopifyProduct) => ({
    title: product.title,
    handle: product.handle,
    url: `${SOURCE_URL.replace(/\/$/, "")}/products/${product.handle}`,
    description: cleanHtml(product.body_html || ""),
    tags: product.tags || [],
    images: (product.images || []).map((image) => ({ src: image.src, alt: image.alt || product.title }))
  }));
  return NextResponse.json({ sourceUrl: SOURCE_URL, count: products.length, products });
}

function cleanHtml(value: string) {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}
