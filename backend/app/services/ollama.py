import httpx

from app.core.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
        except Exception as exc:
            return (
                "Local Ollama is not reachable yet, so I am using the deterministic V1 operating protocol.\n\n"
                f"Fallback reason: {exc}\n\n"
                "Summary: I will route this through the CEO approval-safe workflow, create/adjust tasks, "
                "save useful context to memory, and escalate anything that touches money, customer messaging, "
                "pricing, refunds, orders, or live Shopify changes."
            )
