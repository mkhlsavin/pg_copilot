"""
Telegram Bot API notification service.

Sends lead notifications to a Telegram chat/channel.
"""

import logging
from typing import Any, Dict

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram Bot API notification service."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram Bot API token
            chat_id: Target chat/channel ID
        """
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._enabled = bool(self.bot_token and self.chat_id)

    @property
    def enabled(self) -> bool:
        """Check if Telegram notifications are enabled."""
        return self._enabled

    async def send_new_lead_notification(self, lead_data: Dict[str, Any]) -> bool:
        """
        Send Telegram notification for new lead.

        Args:
            lead_data: Lead data dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping")
            return False

        message = self._format_lead_message(lead_data)
        return await self._send_message(message)

    def _format_lead_message(self, lead: Dict[str, Any]) -> str:
        """Format lead data into Telegram message."""
        team_size = lead.get("team_size") or "N/A"
        language = lead.get("language") or "N/A"
        position = lead.get("position") or "N/A"

        # Emoji mapping for team size
        team_emoji = {
            "1-10": "👤",
            "11-50": "👥",
            "51-200": "🏢",
            "200+": "🏭",
        }.get(team_size, "📊")

        # Language display names
        language_names = {
            "c-cpp": "C/C++",
            "java": "Java",
            "python": "Python",
            "go": "Go",
            "javascript": "JavaScript/TypeScript",
            "csharp": "C#",
            "other": "Other",
        }
        language_display = language_names.get(language, language)

        # Format created_at
        created_at = lead.get("created_at", "N/A")
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d %H:%M")

        return f"""
🎯 *Новая заявка на демо CodeGraph*

👤 *Имя:* {self._escape_markdown(lead['name'])}
📧 *Email:* {self._escape_markdown(lead['email'])}
🏢 *Компания:* {self._escape_markdown(lead['company'])}
💼 *Должность:* {self._escape_markdown(position)}
{team_emoji} *Размер команды:* {team_size}
💻 *Основной язык:* {language_display}

📅 _Отправлено: {created_at}_
        """.strip()

    def _escape_markdown(self, text: str) -> str:
        """Escape special Markdown characters."""
        if not text:
            return "N/A"
        special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    async def _send_message(self, text: str) -> bool:
        """
        Send message via Telegram Bot API.

        Args:
            text: Message text with Markdown formatting

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info(f"Telegram notification sent to {self.chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return False

        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram HTTP error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.exception(f"Failed to send Telegram notification: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test Telegram bot connection.

        Returns:
            True if bot is working, False otherwise
        """
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/getMe",
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()
                if result.get("ok"):
                    bot_name = result.get("result", {}).get("username", "unknown")
                    logger.info(f"Telegram bot connected: @{bot_name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
