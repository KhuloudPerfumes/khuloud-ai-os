export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window === "undefined"
    ? "http://backend:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`);

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
  };
  created_at: string;
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

export async function sendFounderMessage(channelKey: string, body: string) {
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

export async function sendDirectBotMessage(channelKey: string, botKey: string, body: string) {
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

export async function generateVisualAsset(prompt: string, title = "Campaign concept board") {
  const response = await fetchWithTimeout(`${API_BASE}/api/assets/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, title, created_by: "creative_director", channel_key: "founder-command" })
  }, 120000);
  if (!response.ok) {
    throw new Error("Image generation failed");
  }
  return response.json();
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
