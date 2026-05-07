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
        if self.settings.ollama_base_url:
            try:
                async with httpx.AsyncClient(timeout=25) as client:
                    response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content:
                        return content
            except Exception:
                pass

        return await self._cloud_free_chat(system_prompt, user_prompt)

    async def _cloud_free_chat(self, system_prompt: str, user_prompt: str) -> str:
        prompt = (
            f"{system_prompt}\n\n"
            f"{user_prompt}\n\n"
            "Answer as this specific AI employee. Be concrete, useful, and specific to the founder's exact message. "
            "Do not say you executed restricted actions. Keep it under 220 words."
        )
        url = "https://text.pollinations.ai/openai"
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.75,
            "max_tokens": 420,
        }
        try:
            async with httpx.AsyncClient(timeout=18) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception:
            pass
        return ""
