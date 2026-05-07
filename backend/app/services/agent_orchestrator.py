import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Approval, Bot, ChatMessage, Task
from app.services.memory import add_memory, search_memory
from app.services.ollama import OllamaClient
from app.services.queues import QueueClient


DANGEROUS_ACTIONS = [
    "spend",
    "budget",
    "launch ad",
    "message customer",
    "whatsapp reply",
    "change price",
    "discount",
    "refund",
    "cancel order",
    "edit theme",
    "shopify theme",
    "supplier payment",
]

ROUTE_KEYWORDS = {
    "creative_director": ["creative", "visual", "campaign", "packaging", "photo", "aesthetic"],
    "performance_marketing": ["ads", "meta", "roas", "cac", "ctr", "budget", "campaign"],
    "shopify_cro": ["shopify", "checkout", "conversion", "product page", "cart", "bundle"],
    "whatsapp_sales": ["whatsapp", "customer", "cod", "lead", "reply", "objection"],
}

COLLABORATION_MAP = {
    "creative_director": ["performance_marketing", "shopify_cro"],
    "performance_marketing": ["creative_director", "shopify_cro"],
    "shopify_cro": ["performance_marketing", "whatsapp_sales"],
    "whatsapp_sales": ["shopify_cro", "creative_director"],
    "ceo": ["creative_director", "performance_marketing", "shopify_cro"],
}

VISUAL_GENERATION_TERMS = [
    "image",
    "images",
    "visual",
    "visuals",
    "picture",
    "pictures",
    "photo",
    "photos",
    "render",
    "renders",
    "mockup",
    "mockups",
    "product board",
    "campaign board",
    "poster",
    "product shot",
    "ad creative",
    "creative asset",
]

VISUAL_ACTION_TERMS = [
    "generate",
    "create",
    "make",
    "design",
    "produce",
    "build",
    "give me",
    "i need",
    "i want",
    "show me",
]


@dataclass
class OrchestrationResult:
    messages: list[ChatMessage]
    task: Task | None
    approval: Approval | None


class AgentOrchestrator:
    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.queue = QueueClient()

    async def handle_founder_message(self, db: Session, channel_key: str, text: str) -> OrchestrationResult:
        owner_key = self._route_owner(text)
        owner = db.query(Bot).filter(Bot.key == owner_key).one()
        ceo = db.query(Bot).filter(Bot.key == "ceo").one()
        approval_needed = self._needs_approval(text)
        status = "needs_approval" if approval_needed else "assigned"

        task = Task(
            title=self._task_title(text),
            owner_key=owner_key,
            objective=text,
            status=status,
            priority="high" if approval_needed else "medium",
            risk="high" if approval_needed else "low",
            next_step="Founder approval required before execution." if approval_needed else f"{owner.name} should produce the first operating response.",
            approval_needed=approval_needed,
            deadline="Founder-defined",
            related_channel=channel_key,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        approval = None
        if approval_needed:
            approval = Approval(
                task_id=task.id,
                requested_by="ceo",
                action_type="restricted_action",
                summary=f"Founder approval required before {owner.name} executes: {text}",
                risk="high",
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)

        context = self._memory_context(db, ceo, text)
        ceo_body = self._operating_response(
            ceo,
            text,
            context,
            extra=f"Route to {owner.name}. Approval needed: {approval_needed}. Task id: {task.id}.",
        )
        messages = [ChatMessage(channel_key=channel_key, sender_key="ceo", sender_name=ceo.name, sender_type="bot", body=ceo_body)]
        messages.insert(
            0,
            ChatMessage(
                channel_key=channel_key,
                sender_key="system",
                sender_name="Live Workstream",
                sender_type="bot",
                body=(
                    "Working live: CEO checked routing, approval gates, shared memory, and active department ownership. "
                    f"Primary owner: {owner.name}. Relevant bots are joining with their specialist input."
                ),
            ),
        )
        if owner.key != "ceo":
            owner_context = self._memory_context(db, owner, text)
            owner_body = self._operating_response(owner, text, owner_context, extra=f"Respond as assigned owner. Do not execute restricted actions. Approval needed: {approval_needed}.")
            messages.append(ChatMessage(channel_key=channel_key, sender_key=owner.key, sender_name=owner.name, sender_type="bot", body=owner_body))
        for collaborator_key in self._collaborators(owner.key, text):
            collaborator = db.query(Bot).filter(Bot.key == collaborator_key, Bot.active.is_(True)).one_or_none()
            if collaborator and collaborator.key not in {message.sender_key for message in messages}:
                collaborator_context = self._memory_context(db, collaborator, text)
                collaborator_body = self._operating_response(
                    collaborator,
                    text,
                    collaborator_context,
                    extra=f"Collaborate with {owner.name}. Stay inside authority: {collaborator.authority_level}.",
                )
                messages.append(ChatMessage(channel_key=channel_key, sender_key=collaborator.key, sender_name=collaborator.name, sender_type="bot", body=collaborator_body))
        if self._requests_visual_generation(text):
            messages.append(self._create_auto_visual_request(db, channel_key, text))
        db.add_all(messages)
        add_memory(
            db,
            scope="operating_activity",
            title=f"Founder request routed to {owner.name}",
            content=f"Request: {text}\nTask: {task.id}\nApproval needed: {approval_needed}",
            created_by="ceo",
        )
        self.queue.enqueue("agent_tasks", {"task_id": task.id, "owner_key": owner_key, "approval_needed": approval_needed})
        db.commit()
        for message in messages:
            db.refresh(message)
        return OrchestrationResult(messages=messages, task=task, approval=approval)

    async def handle_direct_bot_message(self, db: Session, channel_key: str, bot_key: str, text: str) -> OrchestrationResult:
        bot = db.query(Bot).filter(Bot.key == bot_key).one()
        approval_needed = self._needs_approval(text)
        task = Task(
            title=f"Direct request to {bot.name}: {self._task_title(text)}",
            owner_key=bot.key,
            objective=text,
            status="needs_approval" if approval_needed else "assigned",
            priority="high" if approval_needed else "medium",
            risk="high" if approval_needed else "low",
            next_step=f"{bot.name} will respond directly while staying inside authority level: {bot.authority_level}.",
            approval_needed=approval_needed,
            deadline="Founder-defined",
            related_channel=channel_key,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        approval = None
        if approval_needed:
            approval = Approval(
                task_id=task.id,
                requested_by=bot.key,
                action_type="restricted_direct_request",
                summary=f"Founder approval required before {bot.name} executes direct request: {text}",
                risk="high",
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)

        context = self._memory_context(db, bot, text)
        body = self._operating_response(bot, text, context, extra=f"Direct conversation with founder. Task id: {task.id}.")
        message = ChatMessage(channel_key=channel_key, sender_key=bot.key, sender_name=bot.name, sender_type="bot", body=body)
        messages = [message]
        if self._requests_visual_generation(text):
            messages.append(self._create_auto_visual_request(db, channel_key, text))
        db.add_all(messages)
        add_memory(
            db,
            scope="direct_bot_activity",
            title=f"Founder direct message to {bot.name}",
            content=f"Request: {text}\nTask: {task.id}\nApproval needed: {approval_needed}",
            created_by=bot.key,
        )
        self.queue.enqueue("direct_bot_tasks", {"task_id": task.id, "owner_key": bot.key, "approval_needed": approval_needed})
        db.commit()
        for outbound in messages:
            db.refresh(outbound)
        return OrchestrationResult(messages=messages, task=task, approval=approval)

    def crewai_status(self) -> dict:
        try:
            import crewai  # noqa: F401

            return {"available": True, "mode": "installed_ready"}
        except Exception as exc:
            return {"available": False, "mode": "fallback_orchestrator", "reason": str(exc)}

    def _route_owner(self, text: str) -> str:
        normalized = text.lower()
        for owner, keywords in ROUTE_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return owner
        return "ceo"

    def _collaborators(self, owner_key: str, text: str) -> list[str]:
        normalized = text.lower()
        collaborators = list(COLLABORATION_MAP.get(owner_key, []))
        if "whatsapp" in normalized or "customer" in normalized:
            collaborators.append("whatsapp_sales")
        if "shopify" in normalized or "checkout" in normalized or "product page" in normalized:
            collaborators.append("shopify_cro")
        if "ad" in normalized or "meta" in normalized or "budget" in normalized:
            collaborators.append("performance_marketing")
        if "visual" in normalized or "campaign" in normalized or "creative" in normalized:
            collaborators.append("creative_director")
        deduped: list[str] = []
        for key in collaborators:
            if key != owner_key and key not in deduped:
                deduped.append(key)
        return deduped[:3]

    def _needs_approval(self, text: str) -> bool:
        normalized = text.lower()
        return any(action in normalized for action in DANGEROUS_ACTIONS)

    def _requests_visual_generation(self, text: str) -> bool:
        normalized = " ".join(text.lower().split())
        has_visual_subject = any(term in normalized for term in VISUAL_GENERATION_TERMS)
        has_creation_action = any(term in normalized for term in VISUAL_ACTION_TERMS)
        return has_visual_subject and has_creation_action

    def _create_auto_visual_request(self, db: Session, channel_key: str, text: str) -> ChatMessage:
        creative_director = db.query(Bot).filter(Bot.key == "creative_director").one()
        task = Task(
            title=f"Auto image generation: {self._task_title(text)}",
            owner_key="creative_director",
            objective=(
                "Automatically detected visual-generation intent from founder message. "
                f"Create or queue campaign/product visuals from this prompt: {text}"
            ),
            status="pending",
            priority="high",
            risk="medium",
            next_step=(
                "Visual workflow was started automatically from chat. In local mode, generate assets through the image service; "
                "in free cloud mode, keep the request queued if image services are unavailable."
            ),
            approval_needed=False,
            deadline="Immediate when image service is available",
            related_channel=channel_key,
        )
        db.add(task)
        db.flush()
        self.queue.enqueue(
            "image_generation_requests",
            {
                "task_id": task.id,
                "prompt": text,
                "requested_by": "ceo_auto_detection",
                "channel_key": channel_key,
            },
        )
        add_memory(
            db,
            scope="approved_creatives",
            title=f"Auto visual request queued: {self._task_title(text)}",
            content=(
                "The founder asked for images/visuals in chat, so the CEO workflow automatically created an image-generation "
                f"task without requiring the Create Visuals or Queue Image Generation button. Prompt: {text}"
            ),
            created_by="ceo",
        )
        return ChatMessage(
            channel_key=channel_key,
            sender_key="creative_director",
            sender_name=creative_director.name,
            sender_type="bot",
            body=(
                "Detected image-generation intent. I started the visual workflow automatically, so you do not need to click "
                "Create Visuals or Queue Image Generation.\n"
                f"Visual task: {task.id}\n"
                "Status: Queued for generation through the available image service.\n"
                "Next step: I will treat follow-up messages in this chat as live creative direction for the same visual request."
            ),
            metadata_json=json.dumps(
                {
                    "operation": True,
                    "auto_visual_request": True,
                    "task_id": task.id,
                    "queue": "image_generation_requests",
                }
            ),
        )

    def _task_title(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        return cleaned[:90] if cleaned else "Founder-directed task"

    def _memory_context(self, db: Session, bot: Bot, text: str) -> str:
        scopes = json.loads(bot.memory_scope)
        items = search_memory(db, text, scopes=scopes)
        if not items:
            return "No prior memory matched this request."
        return "\n".join([f"- [{item.scope}] {item.title}: {item.content}" for item in items])

    async def _bot_response(self, bot: Bot, user_text: str, memory_context: str, extra: str) -> str:
        system = f"""
You are {bot.name}, part of KHULOUD AI OS, a serious local-first AI operating system for Khuloud Perfumes.
Department: {bot.department}
Authority: {bot.authority_level}
Role: {bot.role_description}
Personality: {bot.personality_style}
Approval rules: {bot.approval_requirements}
Output structure: {bot.output_structure}

Never claim you executed restricted actions. Draft, analyze, route, and request founder approval when required.
Use concise executive operating language.
"""
        prompt = f"Founder/request context:\n{user_text}\n\nRelevant memory:\n{memory_context}\n\nOperating note:\n{extra}"
        return await self.ollama.chat(system, prompt)

    def _operating_response(self, bot: Bot, user_text: str, memory_context: str, extra: str) -> str:
        approval_flag = "Yes" if self._needs_approval(user_text) else "No"
        output = json.loads(bot.output_structure)
        memory_line = memory_context.splitlines()[0] if memory_context and memory_context != "No prior memory matched this request." else "No direct memory match; using role policy and approval rules."
        if bot.key == "ceo":
            return (
                f"Summary: I received the founder request and routed it through the company hierarchy.\n"
                f"Owners: Primary owner assigned based on the request. {extra}\n"
                f"Risks: Restricted actions are blocked until founder approval. Approval needed: {approval_flag}.\n"
                f"Approvals: I created an approval record when required and logged this routing decision.\n"
                f"Next steps: Department bots will respond in-channel with their operating slice, and all important outputs are saved to shared memory."
            )
        if bot.key == "creative_director":
            return (
                "Concept: Build a luxury campaign direction with restrained black, deep purple, and gold art direction; focus on product desirability, sensory storytelling, and premium composition.\n"
                "Visual direction: Define hero visual, content angles, shot list, packaging/product treatment, and approval-safe creative notes.\n"
                f"Brand fit: {memory_line}\n"
                "Risks: No public claim, paid campaign launch, or final creative usage should happen before founder approval.\n"
                f"Assets needed: Product render/photo, campaign headline options, short-form creative cuts, approval checklist.\n"
                f"Approval needed: {approval_flag}."
            )
        if bot.key == "performance_marketing":
            return (
                "Finding: This request has growth implications, so I will turn it into a test plan instead of executing spend.\n"
                "Metric context: Track CAC, CTR, CVR, ROAS, spend pacing, and audience learning before scaling.\n"
                "Hypothesis: A luxury-positioned creative angle can be tested safely if budget, audience, and success criteria are approved first.\n"
                "Test plan: Draft campaign objective, audience, creative variants, daily budget, stop-loss rules, and reporting cadence.\n"
                "Spend risk: No ad launch or budget change will execute without founder approval.\n"
                f"Approval needed: {approval_flag}."
            )
        if bot.key == "shopify_cro":
            return (
                "Issue: I will review product-page and checkout friction related to this request before any live Shopify changes.\n"
                "Evidence: Pull order/cart/customer-objection context when Shopify credentials are connected; for now use stored objections and founder direction.\n"
                "Experiment: Draft a non-live CRO proposal covering product page clarity, bundle framing, checkout trust, and COD/customer reassurance.\n"
                "Expected lift: Define target impact before implementation rather than claiming a fake result.\n"
                "Risk: Price, discount, checkout copy, refund, order, or live theme changes remain approval-gated.\n"
                f"Approval needed: {approval_flag}."
            )
        if bot.key == "whatsapp_sales":
            return (
                "Customer context: I will prepare customer-facing drafts only, not send messages.\n"
                "Recommended reply: Draft concise WhatsApp responses for scent fit, longevity, delivery/COD trust, gifting, and objections.\n"
                "Risk: Any direct customer message, discount, refund, cancellation, or delivery commitment requires founder approval.\n"
                f"Approval needed: {approval_flag}."
            )
        return (
            f"{bot.name} operating response.\n"
            f"Structure: {', '.join(output)}.\n"
            f"Context: {user_text}\n"
            f"Memory: {memory_line}\n"
            f"Approval needed: {approval_flag}."
        )
