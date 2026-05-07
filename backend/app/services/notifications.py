import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import get_settings


class NotificationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def notify_founder(self, subject: str, body: str) -> dict:
        telegram = await self._telegram(subject, body)
        email = self._email(subject, body)
        return {"telegram": telegram, "email": email}

    async def _telegram(self, subject: str, body: str) -> str:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            return "not_configured"
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        text = f"{subject}\n\n{body}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json={"chat_id": self.settings.telegram_chat_id, "text": text})
                response.raise_for_status()
            return "sent"
        except Exception as exc:
            return f"failed: {exc}"

    def _email(self, subject: str, body: str) -> str:
        if not self.settings.smtp_host or not self.settings.smtp_user or not self.settings.smtp_password:
            return "not_configured"
        try:
            message = EmailMessage()
            message["From"] = self.settings.smtp_user
            message["To"] = self.settings.founder_email
            message["Subject"] = subject
            message.set_content(body)
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
                smtp.send_message(message)
            return "sent"
        except Exception as exc:
            return f"failed: {exc}"
