"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Activity,
  Bell,
  Bot,
  Check,
  CircleDot,
  Crown,
  Database,
  LayoutDashboard,
  Lock,
  Mic,
  MicOff,
  MessageSquare,
  Send,
  ShieldAlert,
  Sparkles,
  SquareKanban,
  X
} from "lucide-react";
import clsx from "clsx";
import {
  API_BASE,
  Approval,
  Asset,
  Bootstrap,
  Channel,
  DEPLOYMENT_MODE,
  HealthStatus,
  Message,
  Task,
  decideApproval,
  generateDailyCEOReport,
  generateVisualAsset,
  getBootstrap,
  getHealth,
  queueImageGeneration,
  runDailyCheck,
  sendDirectBotMessage,
  sendFounderMessage,
  wakeBackend
} from "@/lib/api";

type SpeechRecognitionResultItem = {
  readonly transcript: string;
};

type SpeechRecognitionResultLike = {
  readonly isFinal: boolean;
  readonly 0: SpeechRecognitionResultItem;
};

type SpeechRecognitionEventLike = {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    readonly [index: number]: SpeechRecognitionResultLike;
  };
};

type SpeechRecognitionErrorLike = {
  readonly error?: string;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const fallback: Bootstrap = {
  bots: [],
  channels: [
    { key: "founder-command", name: "founder-command", department: "Executive", purpose: "Founder command center", allowed_bots: ["ceo"] }
  ],
  messages: [
    {
      id: "local",
      channel_key: "founder-command",
      sender_key: "ceo",
      sender_name: "CEO Orchestrator Bot",
      sender_type: "bot",
      body: "Backend is still starting. The interface is ready and will connect as soon as FastAPI is online.",
      created_at: new Date().toISOString()
    }
  ],
  tasks: [],
  approvals: [],
  logs: [],
  memory: [],
  assets: [],
  dashboard: { active_bots: 5, configured_bots: 25, pending_approvals: 0, open_tasks: 0, health: "starting" }
};

export default function Home() {
  const [data, setData] = useState<Bootstrap>(fallback);
  const [activeChannel, setActiveChannel] = useState("founder-command");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("Connecting");
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [unlockError, setUnlockError] = useState("");
  const [directMode, setDirectMode] = useState(false);
  const [selectedBot, setSelectedBot] = useState("ceo");
  const [selectedItem, setSelectedItem] = useState<{ type: string; item: Record<string, unknown> } | null>(null);
  const [assetPrompt, setAssetPrompt] = useState("");
  const [generatingAsset, setGeneratingAsset] = useState(false);
  const [dictating, setDictating] = useState(false);
  const [dictationStatus, setDictationStatus] = useState("");
  const [dictationSupported, setDictationSupported] = useState(true);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [backendIssue, setBackendIssue] = useState("");
  const [operationStatus, setOperationStatus] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  async function refresh() {
    try {
      const next = await getBootstrap();
      setData(next);
      setStatus("Online");
      setBackendIssue("");
    } catch {
      setStatus("Backend asleep");
      setBackendIssue("Backend is unavailable or waking up. Free cloud mode may need 30-60 seconds after Wake Backend.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshHealth(timeoutMs = 8000) {
    try {
      const next = await getHealth(timeoutMs);
      setHealth(next);
      setBackendIssue("");
      return next;
    } catch {
      setHealth(null);
      setBackendIssue("Backend did not answer. It may be asleep or temporarily unavailable.");
      return null;
    }
  }

  useEffect(() => {
    setUnlocked(window.localStorage.getItem("khuloud_ai_os_unlocked") === "true");
    setDictationSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
    refresh();
    refreshHealth();
    const openAsset = (event: Event) => {
      const custom = event as CustomEvent<Asset>;
      setSelectedItem({ type: "Generated Visual", item: custom.detail as unknown as Record<string, unknown> });
    };
    window.addEventListener("khuloud-open-asset", openAsset);
    const wsBase = API_BASE.replace("http://", "ws://").replace("https://", "wss://");
    const socket = new WebSocket(`${wsBase}/api/chat/ws`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "message") {
        setData((current) => ({ ...current, messages: [...current.messages, payload.message] }));
      } else {
        refresh();
      }
    };
    socket.onopen = () => setStatus("Live");
    socket.onerror = () => setStatus("Realtime retrying");
    return () => {
      window.removeEventListener("khuloud-open-asset", openAsset);
      recognitionRef.current?.abort();
      socket.close();
    };
  }, []);

  const channelMessages = useMemo(
    () => data.messages.filter((message) => message.channel_key === activeChannel),
    [data.messages, activeChannel]
  );
  const activeChannelInfo = data.channels.find((channel) => channel.key === activeChannel) || data.channels[0];
  const pendingApprovals = data.approvals.filter((approval) => approval.status === "pending");
  const activeBots = data.bots.filter((bot) => bot.active);

  async function submit() {
    if (!draft.trim() || sending) {
      return;
    }
    recognitionRef.current?.stop();
    const body = draft.trim();
    setDraft("");
    setSending(true);
    const optimisticMessage: Message = {
      id: `local-${Date.now()}`,
      channel_key: activeChannel,
      sender_key: "founder",
      sender_name: "Founder",
      sender_type: "founder",
      body,
      metadata: {},
      created_at: new Date().toISOString()
    };
    const routingMessage: Message = {
      id: `routing-${Date.now()}`,
      channel_key: activeChannel,
      sender_key: "ceo",
      sender_name: "CEO Orchestrator Bot",
      sender_type: "bot",
      body: "Routing founder command to the right department bots. Approval gates are being checked now.",
      metadata: {},
      created_at: new Date().toISOString()
    };
    setData((current) => ({ ...current, messages: [...current.messages, optimisticMessage, routingMessage] }));
    try {
      if (directMode) {
        await sendDirectBotMessage(activeChannel, selectedBot, body);
      } else {
        await sendFounderMessage(activeChannel, body);
      }
      await refresh();
    } catch {
      setData((current) => ({
        ...current,
        messages: [
          ...current.messages,
          {
            id: `error-${Date.now()}`,
            channel_key: activeChannel,
            sender_key: "system",
            sender_name: "System",
            sender_type: "bot",
            body: "The message did not reach the backend. Check Docker health and try again.",
            metadata: {},
            created_at: new Date().toISOString()
          }
        ]
      }));
    } finally {
      setSending(false);
    }
  }

  function toggleDictation() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setDictationSupported(false);
      setDictationStatus("Dictation is not supported in this browser. Open KHULOUD AI OS in Chrome or Edge.");
      return;
    }
    if (dictating) {
      recognitionRef.current?.stop();
      setDictating(false);
      setDictationStatus("Dictation stopped.");
      return;
    }

    const recognition = new Recognition();
    const startingDraft = draft.trim();
    let finalTranscript = "";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      let interimTranscript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result[0]?.transcript || "";
        if (result.isFinal) {
          finalTranscript = `${finalTranscript} ${transcript}`.trim();
        } else {
          interimTranscript = `${interimTranscript} ${transcript}`.trim();
        }
      }
      const next = [startingDraft, finalTranscript, interimTranscript].filter(Boolean).join(" ");
      setDraft(next);
      setDictationStatus(interimTranscript ? "Listening..." : "Captured voice input.");
    };
    recognition.onerror = (event) => {
      const error = event.error || "unknown";
      setDictating(false);
      setDictationStatus(error === "not-allowed" ? "Microphone permission was blocked for this browser." : `Dictation stopped: ${error}.`);
    };
    recognition.onend = () => {
      setDictating(false);
      recognitionRef.current = null;
    };
    recognitionRef.current = recognition;
    setDictating(true);
    setDictationStatus("Listening...");
    try {
      recognition.start();
    } catch {
      setDictating(false);
      setDictationStatus("Dictation could not start. Refresh the page and try again.");
    }
  }

  async function decision(approval: Approval, choice: "approve" | "reject") {
    await decideApproval(approval.id, choice, choice === "approve" ? "Approved from founder dashboard." : "Rejected from founder dashboard.");
    await refresh();
  }

  async function createVisual() {
    const prompt = (assetPrompt || draft || "Luxury perfume campaign visual for KHULOUD").trim();
    setGeneratingAsset(true);
    setData((current) => ({
      ...current,
      messages: [
        ...current.messages,
        {
          id: `visual-routing-${Date.now()}`,
          channel_key: activeChannel,
          sender_key: "ceo",
          sender_name: "CEO Orchestrator Bot",
          sender_type: "bot",
          body: "Starting visible visual workstream. Relevant bots are coordinating now, and the generated images will appear directly in chat when ready.",
          metadata: {},
          created_at: new Date().toISOString()
        }
      ]
    }));
    try {
      await generateVisualAsset(prompt, prompt.slice(0, 80) || "Campaign concept board");
      setAssetPrompt("");
      await refresh();
    } finally {
      setGeneratingAsset(false);
    }
  }

  async function wakeCloudBackend() {
    setOperationStatus("Waking backend...");
    try {
      const next = await wakeBackend();
      setHealth(next);
      setBackendIssue("");
      setOperationStatus("Backend answered. Refreshing company data...");
      await refresh();
      setOperationStatus("Backend is awake.");
    } catch {
      setOperationStatus("Backend is still unavailable. Wait a few seconds and try Wake Backend again.");
      setBackendIssue("Wake attempt timed out. Free hosts can take a little while to restart.");
    }
  }

  async function runFounderOperation(kind: "daily_check" | "ceo_report" | "queue_image") {
    setOperationStatus(kind === "daily_check" ? "Running daily check..." : kind === "ceo_report" ? "Generating CEO report..." : "Queueing image generation...");
    try {
      if (kind === "daily_check") {
        await runDailyCheck();
      } else if (kind === "ceo_report") {
        await generateDailyCEOReport();
      } else {
        const prompt = (assetPrompt || draft || "Luxury perfume campaign visual for KHULOUD").trim();
        await queueImageGeneration(prompt, prompt.slice(0, 80) || "Queued visual request");
      }
      await refresh();
      await refreshHealth();
      setOperationStatus("Operation completed and posted into company chat.");
    } catch {
      setOperationStatus("Operation could not run. Try Wake Backend first, then run it again.");
      setBackendIssue("The backend or database was unavailable during this operation.");
    }
  }

  function unlock() {
    const expectedPassword = process.env.NEXT_PUBLIC_LOCAL_UNLOCK_PASSWORD || "khuloud-founder";
    if (password.trim() === expectedPassword) {
      window.localStorage.setItem("khuloud_ai_os_unlocked", "true");
      setUnlocked(true);
      setUnlockError("");
      return;
    }
    setUnlockError("Password did not match. Use khuloud-founder unless you changed NEXT_PUBLIC_LOCAL_UNLOCK_PASSWORD.");
  }

  if (!unlocked) {
    return (
      <main className="grid h-screen place-items-center p-6 text-stone-100">
        <section className="w-full max-w-md rounded-lg border border-line bg-ink/90 p-6 shadow-luxury">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-md border border-gold/50 bg-gold/10 text-gold">
              <Lock size={20} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">KHULOUD AI OS</h1>
              <p className="text-sm text-stone-400">Founder local access</p>
            </div>
          </div>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                unlock();
              }
            }}
            placeholder="Founder password"
            className="mt-6 h-12 w-full rounded-md border border-line bg-obsidian px-4 text-sm text-stone-100 outline-none ring-gold/30 transition focus:ring-2"
          />
          <button onClick={unlock} className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-gold text-sm font-semibold text-obsidian hover:bg-[#e7c982]">
            <Crown size={16} />
            Unlock company OS
          </button>
          {unlockError ? <p className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-xs leading-5 text-red-100">{unlockError}</p> : null}
          <p className="mt-4 text-xs leading-5 text-stone-500">Default local password: khuloud-founder. Change this before sharing the machine or deploying.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen overflow-auto p-3 text-stone-100 lg:h-screen lg:overflow-hidden lg:p-4">
      <div className="grid min-h-screen grid-cols-1 gap-4 lg:h-full lg:min-h-0 lg:grid-cols-[284px_minmax(0,1fr)_360px]">
        <aside className="flex min-h-0 flex-col rounded-lg border border-line bg-ink/90 shadow-luxury">
          <BrandHeader status={status} />
          <div className="border-y border-line p-3">
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Active" value={`${data.dashboard.active_bots}/25`} />
              <Metric label="Approvals" value={String(data.dashboard.pending_approvals)} tone="gold" />
            </div>
          </div>
          <ChannelList channels={data.channels} active={activeChannel} onChange={setActiveChannel} />
        </aside>

        <section className="flex min-h-[640px] flex-col rounded-lg border border-line bg-panel/90 shadow-luxury lg:min-h-0">
          <ChannelHeader channel={activeChannelInfo} loading={loading} />
          <CloudModeBanner backendIssue={backendIssue} />
          <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-5 py-4">
            <div className="mx-auto flex max-w-5xl flex-col gap-3">
              {channelMessages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}
            </div>
          </div>
          <div className="border-t border-line bg-ink/80 p-4">
            <div className="mx-auto mb-3 max-w-5xl">
              <CloudControls
                health={health}
                operationStatus={operationStatus}
                onWake={wakeCloudBackend}
                onDailyCheck={() => runFounderOperation("daily_check")}
                onCEOReport={() => runFounderOperation("ceo_report")}
                onQueueImage={() => runFounderOperation("queue_image")}
              />
            </div>
            <div className="mx-auto mb-3 flex max-w-5xl flex-wrap items-center gap-2">
              <button
                onClick={() => setDirectMode(false)}
                className={clsx("rounded-md border px-3 py-2 text-xs", !directMode ? "border-gold bg-gold/10 text-gold" : "border-line text-stone-400")}
              >
                CEO route
              </button>
              <button
                onClick={() => setDirectMode(true)}
                className={clsx("rounded-md border px-3 py-2 text-xs", directMode ? "border-gold bg-gold/10 text-gold" : "border-line text-stone-400")}
              >
                Talk to bot
              </button>
              {directMode ? (
                <select value={selectedBot} onChange={(event) => setSelectedBot(event.target.value)} className="h-9 rounded-md border border-line bg-obsidian px-3 text-xs text-stone-100 outline-none">
                  {activeBots.map((bot) => (
                    <option key={bot.key} value={bot.key}>{bot.name}</option>
                  ))}
                </select>
              ) : null}
              <button onClick={createVisual} disabled={generatingAsset} className="rounded-md border border-violet/50 bg-violet/20 px-3 py-2 text-xs text-stone-100 disabled:opacity-50">
                {generatingAsset ? "Generating visual..." : "Generate visual"}
              </button>
              <input value={assetPrompt} onChange={(event) => setAssetPrompt(event.target.value)} placeholder="Optional visual prompt" className="h-9 min-w-64 flex-1 rounded-md border border-line bg-obsidian px-3 text-xs text-stone-100 outline-none" />
            </div>
            <div className="mx-auto flex max-w-5xl items-end gap-3">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                placeholder="Command the company. CEO routes work and escalates approvals."
                className="max-h-36 min-h-12 flex-1 resize-none rounded-md border border-line bg-obsidian px-4 py-3 text-sm leading-6 text-stone-100 outline-none ring-gold/30 transition focus:ring-2"
              />
              <button
                onClick={toggleDictation}
                disabled={!dictationSupported}
                title={dictating ? "Stop dictation" : "Start dictation"}
                className={clsx(
                  "grid h-12 w-12 place-items-center rounded-md border transition disabled:cursor-not-allowed disabled:opacity-40",
                  dictating ? "border-gold bg-gold/15 text-gold" : "border-line bg-obsidian text-stone-300 hover:border-gold/60 hover:text-gold"
                )}
              >
                {dictating ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button
                onClick={submit}
                disabled={sending}
                title="Send command"
                className="grid h-12 w-12 place-items-center rounded-md bg-gold text-obsidian transition hover:bg-[#e7c982] disabled:opacity-50"
              >
                <Send size={18} />
              </button>
            </div>
            {dictationStatus ? <p className="mx-auto mt-2 max-w-5xl text-xs text-stone-400">{dictationStatus}</p> : null}
            {sending ? <p className="mx-auto mt-2 max-w-5xl text-xs text-gold">CEO Orchestrator is routing this through active department bots...</p> : null}
          </div>
        </section>

        <aside className="scrollbar-thin min-h-0 overflow-y-auto rounded-lg border border-line bg-ink/90 shadow-luxury">
          <FounderDashboard
            approvals={pendingApprovals}
            tasks={data.tasks}
            activeBots={activeBots}
            memory={data.memory}
            logs={data.logs}
            assets={data.assets}
            onDecision={decision}
            onSelect={setSelectedItem}
          />
        </aside>
      </div>
      {selectedItem ? <DetailDrawer selected={selectedItem} onClose={() => setSelectedItem(null)} /> : null}
    </main>
  );
}

function BrandHeader({ status }: { status: string }) {
  return (
    <div className="p-4">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-md border border-gold/60 bg-gold/10 text-gold">
          <Crown size={20} />
        </div>
        <div>
          <h1 className="text-base font-semibold leading-tight text-stone-50">KHULOUD AI OS</h1>
          <p className="text-xs text-stone-400">Luxury perfume company network</p>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between rounded-md border border-line bg-plum/60 px-3 py-2 text-xs">
        <span className="flex items-center gap-2 text-stone-300">
          <CircleDot size={13} className="text-emerald-400" />
          {status}
        </span>
        <span className="flex items-center gap-1 text-gold">
          <Lock size={12} />
          Local-first
        </span>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "gold" }) {
  return (
    <div className="rounded-md border border-line bg-obsidian/75 p-3">
      <p className="text-[11px] uppercase text-stone-500">{label}</p>
      <p className={clsx("mt-1 text-lg font-semibold", tone === "gold" ? "text-gold" : "text-stone-100")}>{value}</p>
    </div>
  );
}

function ChannelList({ channels, active, onChange }: { channels: Channel[]; active: string; onChange: (key: string) => void }) {
  return (
    <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-2">
      <p className="px-2 py-2 text-[11px] font-semibold uppercase text-stone-500">Departments</p>
      {channels.map((channel) => (
        <button
          key={channel.key}
          onClick={() => onChange(channel.key)}
          className={clsx(
            "mb-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition",
            active === channel.key ? "bg-violet/30 text-stone-50" : "text-stone-400 hover:bg-white/5 hover:text-stone-100"
          )}
        >
          <MessageSquare size={15} />
          <span className="truncate">#{channel.name}</span>
        </button>
      ))}
    </div>
  );
}

function ChannelHeader({ channel, loading }: { channel?: Channel; loading: boolean }) {
  return (
    <header className="flex items-center justify-between border-b border-line px-5 py-4">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-stone-50">#{channel?.name || "founder-command"}</h2>
          {loading ? <span className="text-xs text-stone-500">Loading</span> : null}
        </div>
        <p className="mt-1 max-w-3xl text-sm text-stone-400">{channel?.purpose}</p>
      </div>
      <div className="flex items-center gap-2">
        <IconPill icon={<Activity size={14} />} label="Live chat" />
        <IconPill icon={<ShieldAlert size={14} />} label="Approval gated" />
      </div>
    </header>
  );
}

function CloudModeBanner({ backendIssue }: { backendIssue: string }) {
  return (
    <div className="border-b border-line bg-gold/10 px-5 py-3 text-xs leading-5 text-stone-300">
      <span className="font-semibold text-gold">Free cloud mode warning:</span> services may sleep and are not guaranteed 24/7. The local Docker mode remains the reliable full-stack mode.
      {backendIssue ? <span className="ml-2 text-red-200">{backendIssue}</span> : null}
    </div>
  );
}

function CloudControls({
  health,
  operationStatus,
  onWake,
  onDailyCheck,
  onCEOReport,
  onQueueImage
}: {
  health: HealthStatus | null;
  operationStatus: string;
  onWake: () => void;
  onDailyCheck: () => void;
  onCEOReport: () => void;
  onQueueImage: () => void;
}) {
  return (
    <div className="rounded-md border border-line bg-obsidian/70 p-3">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button onClick={onWake} className="rounded-md border border-gold/50 bg-gold/10 px-3 py-2 text-xs text-gold hover:bg-gold/15">
          Wake Backend
        </button>
        <button onClick={onDailyCheck} className="rounded-md border border-line px-3 py-2 text-xs text-stone-200 hover:border-gold/50">
          Run Daily Check
        </button>
        <button onClick={onCEOReport} className="rounded-md border border-line px-3 py-2 text-xs text-stone-200 hover:border-gold/50">
          Generate Daily CEO Report
        </button>
        <button onClick={onQueueImage} className="rounded-md border border-violet/50 bg-violet/15 px-3 py-2 text-xs text-stone-200 hover:border-gold/50">
          Queue Image Generation
        </button>
        <span className="ml-auto text-[11px] uppercase text-stone-500">{DEPLOYMENT_MODE} mode</span>
      </div>
      <div className="grid gap-2 text-xs sm:grid-cols-2 xl:grid-cols-5">
        <HealthDot label="Frontend" ok note="loaded" />
        <HealthDot label="Backend" ok={Boolean(health)} note={health?.status || "asleep"} />
        <HealthDot label="Database" ok={Boolean(health?.database)} note={health?.database ? "online" : "unknown"} />
        <HealthDot label="AI Model" ok={Boolean(health?.ai_model?.available)} note={health?.ai_model?.available ? health?.ai_model?.model || "online" : "local/offline"} />
        <HealthDot label="Shopify" ok={Boolean(health?.shopify?.configured)} note={health?.shopify?.status || "not configured"} />
      </div>
      {operationStatus ? <p className="mt-3 text-xs text-gold">{operationStatus}</p> : null}
    </div>
  );
}

function HealthDot({ label, ok, note }: { label: string; ok: boolean; note: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-md border border-line bg-ink/80 px-3 py-2">
      <span className={clsx("h-2.5 w-2.5 shrink-0 rounded-full", ok ? "bg-emerald-400" : "bg-stone-600")} />
      <span className="min-w-0">
        <span className="block truncate text-stone-200">{label}</span>
        <span className="block truncate text-[11px] text-stone-500">{note}</span>
      </span>
    </div>
  );
}

function IconPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="flex items-center gap-2 rounded-md border border-line bg-obsidian px-3 py-2 text-xs text-stone-300">
      {icon}
      {label}
    </span>
  );
}

function ChatBubble({ message }: { message: Message }) {
  const founder = message.sender_type === "founder";
  return (
    <article className={clsx("rounded-lg border p-4", founder ? "ml-16 border-gold/40 bg-gold/10" : "mr-10 border-line bg-obsidian/60")}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={clsx("grid h-9 w-9 place-items-center rounded-md", founder ? "bg-gold text-obsidian" : "bg-violet/25 text-gold")}>
            {founder ? <Crown size={17} /> : <Bot size={17} />}
          </div>
          <div>
            <p className="text-sm font-semibold text-stone-100">{message.sender_name}</p>
            <p className="text-xs text-stone-500">{new Date(message.created_at).toLocaleString()}</p>
          </div>
        </div>
        <span className="rounded border border-line px-2 py-1 text-[11px] uppercase text-stone-500">{message.sender_key}</span>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-stone-300">{message.body}</p>
      {message.metadata?.assets?.length ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {message.metadata.assets.map((asset) => (
            <button
              key={asset.id}
              className="overflow-hidden rounded-md border border-line bg-ink text-left transition hover:border-gold/60"
              onClick={() => window.dispatchEvent(new CustomEvent("khuloud-open-asset", { detail: asset }))}
            >
              <AssetPreview asset={asset} className="h-56 w-full bg-obsidian" />
              <div className="p-3">
                <p className="text-sm font-semibold text-stone-100">{asset.title}</p>
                <p className="mt-1 text-xs text-gold">{asset.asset_type.includes("product") ? "Individual product board" : "Campaign board"}</p>
              </div>
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function FounderDashboard({
  approvals,
  tasks,
  activeBots,
  memory,
  logs,
  assets,
  onDecision,
  onSelect
}: {
  approvals: Approval[];
  tasks: Task[];
  activeBots: Bootstrap["bots"];
  memory: Array<Record<string, string>>;
  logs: Array<Record<string, string>>;
  assets: Asset[];
  onDecision: (approval: Approval, choice: "approve" | "reject") => void;
  onSelect: (selected: { type: string; item: Record<string, unknown> }) => void;
}) {
  return (
    <div className="flex flex-col gap-4 p-4">
      <Panel title="Founder Dashboard" icon={<LayoutDashboard size={16} />}>
        <div className="grid grid-cols-2 gap-2">
          <MiniStat label="Open tasks" value={String(tasks.filter((task) => !["completed", "failed", "rejected"].includes(task.status)).length)} />
          <MiniStat label="Pending" value={String(approvals.length)} />
          <MiniStat label="Active bots" value={String(activeBots.length)} />
          <MiniStat label="Memory" value={String(memory.length)} />
        </div>
      </Panel>

      <Panel title="Live Activity" icon={<Activity size={16} />}>
        <div className="flex flex-col gap-2">
          {logs.slice(0, 5).map((log) => (
            <button key={String(log.id)} onClick={() => onSelect({ type: "Activity", item: log })} className="rounded-md border border-line bg-obsidian/50 p-3 text-left text-xs leading-5 text-stone-400 hover:border-gold/50">
              {log.actor_key} - {log.action} - {log.status}
            </button>
          ))}
          {logs.length === 0 ? <EmptyLine text="No activity yet." /> : null}
        </div>
      </Panel>

      <Panel title="Approval Center" icon={<ShieldAlert size={16} />}>
        <div className="flex flex-col gap-3">
          {approvals.length === 0 ? <EmptyLine text="No pending founder approvals." /> : null}
          {approvals.map((approval) => (
            <div key={approval.id} onClick={() => onSelect({ type: "Approval", item: approval as unknown as Record<string, unknown> })} className="cursor-pointer rounded-md border border-gold/30 bg-gold/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs uppercase text-gold">{approval.risk} risk</span>
                <span className="text-xs text-stone-500">{approval.action_type}</span>
              </div>
              <p className="mt-2 text-sm leading-5 text-stone-200">{approval.summary}</p>
              <div className="mt-3 flex gap-2">
                <button onClick={() => onDecision(approval, "approve")} className="flex h-9 flex-1 items-center justify-center gap-2 rounded-md bg-emerald-500/20 text-sm text-emerald-200 hover:bg-emerald-500/30">
                  <Check size={15} />
                  Approve
                </button>
                <button onClick={() => onDecision(approval, "reject")} className="flex h-9 flex-1 items-center justify-center gap-2 rounded-md bg-red-500/20 text-sm text-red-200 hover:bg-red-500/30">
                  <X size={15} />
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Task Board" icon={<SquareKanban size={16} />}>
        <div className="flex flex-col gap-2">
          {tasks.slice(0, 7).map((task) => (
            <button key={task.id} onClick={() => onSelect({ type: "Task", item: task as unknown as Record<string, unknown> })} className="rounded-md border border-line bg-obsidian/60 p-3 text-left hover:border-gold/50">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium text-stone-100">{task.title}</p>
                <StatusBadge status={task.status} />
              </div>
              <p className="mt-2 text-xs leading-5 text-stone-400">{task.next_step}</p>
            </button>
          ))}
        </div>
      </Panel>

      <Panel title="Generated Visuals" icon={<Sparkles size={16} />}>
        <div className="flex flex-col gap-2">
          {assets.slice(0, 4).map((asset) => (
            <button key={asset.id} onClick={() => onSelect({ type: "Generated Visual", item: asset as unknown as Record<string, unknown> })} className="overflow-hidden rounded-md border border-line bg-obsidian/50 text-left hover:border-gold/50">
              <AssetPreview asset={asset} className="h-24 w-full" />
              <div className="p-3">
                <p className="text-sm text-stone-100">{asset.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-stone-500">{asset.prompt}</p>
              </div>
            </button>
          ))}
          {assets.length === 0 ? <EmptyLine text="No generated visuals yet." /> : null}
        </div>
      </Panel>

      <Panel title="Active Employees" icon={<Sparkles size={16} />}>
        <div className="grid gap-2">
          {activeBots.map((bot) => (
            <div key={bot.key} className="flex items-center justify-between rounded-md border border-line bg-obsidian/50 px-3 py-2">
              <div>
                <p className="text-sm text-stone-100">{bot.name}</p>
                <p className="text-xs text-stone-500">{bot.department}</p>
              </div>
              <span className="text-xs text-emerald-300">active</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Shared Memory" icon={<Database size={16} />}>
        <div className="flex flex-col gap-2">
          {memory.slice(0, 5).map((item) => (
            <button key={String(item.id)} onClick={() => onSelect({ type: "Memory", item })} className="rounded-md border border-line bg-obsidian/50 p-3 text-left hover:border-gold/50">
              <p className="text-sm text-stone-100">{item.title}</p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.content}</p>
            </button>
          ))}
        </div>
      </Panel>

      <Panel title="Notifications" icon={<Bell size={16} />}>
        <div className="flex flex-col gap-2">
          {logs.slice(0, 4).map((log) => (
            <p key={log.id} className="rounded-md border border-line bg-obsidian/50 p-3 text-xs leading-5 text-stone-400">
              {log.actor_key} - {log.action} - {log.status}
            </p>
          ))}
          {logs.length === 0 ? <EmptyLine text="No failures or alerts logged." /> : null}
        </div>
      </Panel>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-panel/75 p-3">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-100">
        <span className="text-gold">{icon}</span>
        {title}
      </div>
      {children}
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-obsidian/60 p-3">
      <p className="text-[11px] uppercase text-stone-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-stone-100">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const urgent = ["needs_approval", "failed", "rejected"].includes(status);
  return (
    <span className={clsx("shrink-0 rounded border px-2 py-1 text-[11px]", urgent ? "border-gold/40 text-gold" : "border-line text-stone-400")}>
      {status}
    </span>
  );
}

function EmptyLine({ text }: { text: string }) {
  return <p className="rounded-md border border-line bg-obsidian/50 p-3 text-sm text-stone-500">{text}</p>;
}

function DetailDrawer({ selected, onClose }: { selected: { type: string; item: Record<string, unknown> }; onClose: () => void }) {
  const svg = typeof selected.item.svg === "string" ? selected.item.svg : "";
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55">
      <aside className="h-full w-full max-w-2xl overflow-y-auto border-l border-line bg-ink p-5 shadow-luxury">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase text-gold">{selected.type}</p>
            <h3 className="mt-1 text-xl font-semibold text-stone-50">{String(selected.item.title || selected.item.name || selected.item.action || selected.item.id || "Detail")}</h3>
          </div>
          <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-md border border-line text-stone-300 hover:border-gold/50">
            <X size={17} />
          </button>
        </div>
        {svg ? <AssetPreview asset={selected.item as unknown as Asset} className="mb-4 max-h-[560px] overflow-hidden rounded-lg border border-line bg-obsidian" /> : null}
        <pre className="whitespace-pre-wrap rounded-lg border border-line bg-obsidian p-4 text-xs leading-5 text-stone-300">
          {JSON.stringify(selected.item, null, 2)}
        </pre>
      </aside>
    </div>
  );
}

function AssetPreview({ asset, className }: { asset: Asset; className?: string }) {
  const visual = asset.svg || "";
  if (visual.startsWith("data:image/")) {
    return <img src={visual} alt={asset.title} className={clsx("object-cover", className)} />;
  }
  return <div className={className} dangerouslySetInnerHTML={{ __html: visual }} />;
}
