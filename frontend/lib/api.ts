export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window === "undefined"
    ? "http://backend:8000"
    : window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : "https://khuloud-ai-os-backend.onrender.com");

export const DEPLOYMENT_MODE = process.env.NEXT_PUBLIC_DEPLOYMENT_MODE || "local";

export type HealthStatus = {
  status: string;
  mode?: string;
  database?: boolean;
  redis?: boolean;
  ai_model?: {
    available: boolean;
    provider: string;
    model: string;
    base_url: string;
  };
  shopify?: {
    configured: boolean;
    status: string;
  };
};

export type Bot = {
  key: string;
  name: string;
  department: string;
  active: boolean;
  authority_level: string;
};

export type Channel = {
  key: string;
  name: string;
  department: string;
  purpose: string;
  allowed_bots: string[];
};

export type Message = {
  id: string;
  channel_key: string;
  sender_key: string;
  sender_name: string;
  sender_type: string;
  body: string;
  metadata?: {
    assets?: Asset[];
    auto_visual_request?: boolean;
    task_id?: string;
    queue?: string;
    cloud_ai?: boolean;
  };
  created_at: string;
};

export type ChatResponse = {
  founder_message: Message;
  bot_messages: Message[];
  task_id: string | null;
  approval_id: string | null;
};

export type Task = {
  id: string;
  title: string;
  owner_key: string;
  objective: string;
  status: string;
  priority: string;
  risk: string;
  next_step: string;
  approval_needed: boolean;
  deadline: string;
  related_channel: string;
};

export type Approval = {
  id: string;
  task_id?: string;
  requested_by: string;
  action_type: string;
  summary: string;
  risk: string;
  status: string;
  founder_note: string;
  created_at: string;
};

export type Asset = {
  id: string;
  title: string;
  prompt: string;
  asset_type: string;
  created_by: string;
  svg: string;
  created_at: string;
};

export type ProductSource = {
  title: string;
  handle: string;
  url: string;
  description: string;
  tags: string[];
  images: Array<{ src: string; alt: string }>;
};

export type Bootstrap = {
  bots: Bot[];
  channels: Channel[];
  messages: Message[];
  tasks: Task[];
  approvals: Approval[];
  logs: Array<Record<string, string>>;
  memory: Array<Record<string, string>>;
  assets: Asset[];
  dashboard: {
    active_bots: number;
    configured_bots: number;
    pending_approvals: number;
    open_tasks: number;
    health: string;
  };
};

export async function getBootstrap(): Promise<Bootstrap> {
  const response = await fetchWithTimeout(`${API_BASE}/api/bootstrap`, { cache: "no-store" }, 12000);
  if (!response.ok) {
    throw new Error("Unable to load KHULOUD AI OS backend");
  }
  return response.json();
}

export async function getHealth(timeoutMs = 8000): Promise<HealthStatus> {
  const response = await fetchWithTimeout(`${API_BASE}/api/health`, { cache: "no-store" }, timeoutMs);
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json();
}

export async function wakeBackend(): Promise<HealthStatus> {
  return getHealth(30000);
}

export async function sendFounderMessage(channelKey: string, body: string): Promise<ChatResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel_key: channelKey, body })
  }, 20000);
  if (!response.ok) {
    throw new Error("Message failed");
  }
  return response.json();
}

export async function sendDirectBotMessage(channelKey: string, botKey: string, body: string): Promise<ChatResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/chat/direct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel_key: channelKey, bot_key: botKey, body })
  }, 20000);
  if (!response.ok) {
    throw new Error("Direct bot message failed");
  }
  return response.json();
}

export async function generateCloudBotReply(payload: {
  botKey: string;
  botName: string;
  department?: string;
  userText: string;
  existingBody?: string;
}) {
  const response = await fetchWithTimeout("/api/cloud-ai", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }, 24000);
  if (!response.ok) {
    throw new Error("Cloud AI reply failed");
  }
  return response.json() as Promise<{ body: string }>;
}

export async function generateVisualAsset(prompt: string, title = "Campaign concept board", channelKey = "founder-command") {
  const enrichedPrompt = await enrichPromptWithProductSource(prompt);
  const response = await fetchWithTimeout(`${API_BASE}/api/assets/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: enrichedPrompt, title, created_by: "creative_director", channel_key: channelKey })
  }, 120000);
  if (!response.ok) {
    throw new Error("Image generation failed");
  }
  return response.json();
}

export async function getProductSource() {
  const response = await fetchWithTimeout("/api/product-source", { cache: "no-store" }, 20000);
  if (!response.ok) {
    throw new Error("Product source unavailable");
  }
  return response.json() as Promise<{ sourceUrl: string; count: number; products: ProductSource[] }>;
}

async function enrichPromptWithProductSource(prompt: string) {
  try {
    const catalog = await getProductSource();
    const relevant = selectRelevantProducts(prompt, catalog.products).slice(0, 4);
    if (!relevant.length) {
      return prompt;
    }
    const context = relevant.map((product) => {
      const images = product.images.slice(0, 4).map((image) => image.src).join(", ");
      return `Product: ${product.title}\nURL: ${product.url}\nDescription: ${product.description.slice(0, 500)}\nReference images: ${images}`;
    }).join("\n\n");
    return `${prompt}\n\nUse actual Khuloud product source context from ${catalog.sourceUrl}. Preserve the referenced product identity, bottle/packaging look, and luxury cues. Product context:\n${context}`;
  } catch {
    return prompt;
  }
}

function selectRelevantProducts(prompt: string, products: ProductSource[]) {
  const words = new Set(prompt.toLowerCase().match(/[a-z0-9]+/g)?.filter((word) => word.length > 2) || []);
  const scored = products.map((product) => {
    const haystack = [product.title, product.handle, product.description, product.tags.join(" ")].join(" ").toLowerCase();
    let score = 0;
    words.forEach((word) => {
      if (product.title.toLowerCase().includes(word)) score += 3;
      if (haystack.includes(word)) score += 1;
    });
    return { product, score };
  }).filter((item) => item.score > 0);
  if (!scored.length) {
    return products.slice(0, 4);
  }
  return scored.sort((a, b) => b.score - a.score).map((item) => item.product);
}

export async function decideApproval(id: string, decision: "approve" | "reject", founderNote: string) {
  const response = await fetchWithTimeout(`${API_BASE}/api/approvals/${id}/${decision}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ founder_note: founderNote })
  }, 20000);
  if (!response.ok) {
    throw new Error("Approval decision failed");
  }
  return response.json();
}

export async function runDailyCheck() {
  return postOperation("/api/operations/daily-check");
}

export async function generateDailyCEOReport() {
  return postOperation("/api/operations/ceo-report");
}

export async function queueImageGeneration(prompt: string, title = "Queued visual request") {
  return postOperation("/api/operations/queue-image", { prompt, title });
}

async function postOperation(path: string, body?: Record<string, string>) {
  const response = await fetchWithTimeout(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  }, 30000);
  if (!response.ok) {
    throw new Error("Operation failed");
  }
  return response.json();
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }
}
