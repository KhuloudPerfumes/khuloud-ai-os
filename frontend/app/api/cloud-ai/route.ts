import { NextResponse } from "next/server";

type CloudAiPayload = {
  botKey: string;
  botName: string;
  department?: string;
  userText: string;
  existingBody?: string;
};

const roleBriefs: Record<string, string> = {
  ceo: "CEO Orchestrator: route the work, name owners, detect approval gates, summarize decisions, and give the founder a clear operating next step.",
  creative_director: "Creative Director: luxury perfume art direction, campaign visuals, packaging, product boards, and refined brand taste.",
  performance_marketing: "Performance Marketing: Meta ads, ROAS, CAC, CTR, test plans, scaling logic, and spend approval gates.",
  shopify_cro: "Shopify CRO: product page, checkout, bundles, trust, conversion friction, AOV, and approval-safe experiments.",
  whatsapp_sales: "WhatsApp Sales: customer objections, COD trust, scent recommendations, scripts, and sales handling without sending messages."
};

export async function POST(request: Request) {
  const payload = (await request.json()) as CloudAiPayload;
  const system = [
    `You are ${payload.botName}, an AI employee inside KHULOUD AI OS for Khuloud Perfumes.`,
    roleBriefs[payload.botKey] || `${payload.department || "Company"} specialist.`,
    "Answer like a capable ChatGPT-level operator, not a template.",
    "Be specific to the founder's exact message.",
    "Do not claim that you spent money, launched ads, messaged customers, changed prices, edited Shopify, refunded, cancelled orders, or performed live actions.",
    "If you mention those actions, mark them as drafts or proposals requiring founder approval.",
    "Keep the answer concise but useful. Use short labeled sections. Do not return JSON."
  ].join("\n");
  const user = [
    `Founder message: ${payload.userText}`,
    payload.existingBody ? `Current backend draft to improve: ${payload.existingBody}` : "",
    "Give the best expert response this bot should send in the company chat."
  ].filter(Boolean).join("\n\n");

  const ai = await callPollinations(system, user);
  return NextResponse.json({ body: ai || localFallback(payload) });
}

async function callPollinations(system: string, user: string) {
  try {
    const response = await fetch("https://text.pollinations.ai/openai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "openai",
        messages: [
          { role: "system", content: system },
          { role: "user", content: user }
        ],
        temperature: 0.7,
        max_tokens: 420
      }),
      signal: AbortSignal.timeout(18000)
    });
    if (!response.ok) {
      return "";
    }
    const data = await response.json();
    return String(data?.choices?.[0]?.message?.content || "").trim();
  } catch {
    return "";
  }
}

function localFallback(payload: CloudAiPayload) {
  const request = payload.userText.slice(0, 180);
  if (payload.botKey === "whatsapp_sales") {
    return [
      `Customer Context: For "${request}", I would prepare WhatsApp guidance only; I will not send anything automatically.`,
      "Suggested Script: Thank you for asking. This scent is designed for a refined luxury profile with a polished finish. If you prefer something softer, I can guide you to a lighter option; if you want stronger presence, this is the better choice.",
      "Approval Gate: Any customer-facing message, discount, delivery promise, refund, or order change needs founder approval."
    ].join("\n");
  }
  if (payload.botKey === "performance_marketing") {
    return [
      `Growth Read: "${request}" should become a controlled test plan, not an automatic ad launch.`,
      "Test Plan: Define the audience, creative angle, offer framing, budget proposal, stop-loss rule, and success metric before any spend.",
      "Approval Gate: No ad launch or budget change without founder approval."
    ].join("\n");
  }
  if (payload.botKey === "shopify_cro") {
    return [
      `CRO Read: For "${request}", the page needs scent clarity, trust, delivery reassurance, gifting context, and a clear next step.`,
      "Experiment: Draft a product-page section, bundle framing, WhatsApp assistance CTA, and checkout trust checklist before touching Shopify live.",
      "Approval Gate: No price, discount, checkout, or theme change without founder approval."
    ].join("\n");
  }
  if (payload.botKey === "creative_director") {
    return [
      `Creative Direction: For "${request}", I would keep the world black, gold, and deep purple, with the bottle as the first visual signal.`,
      "Assets: Hero image, product board, 3 hooks, short-form storyboard, and founder approval checklist.",
      "Approval Gate: Draft only until approved for public use."
    ].join("\n");
  }
  return [
    `CEO Summary: I received "${request}" and am routing it through the relevant departments.`,
    "Operating Move: Assign owner, collect specialist input, log the task, check approval gates, then return a founder-ready recommendation.",
    "Approval Gate: Money, ads, customer messaging, pricing, refunds, order changes, and live Shopify edits require founder approval."
  ].join("\n");
}
