"""Telegram bot notification provider.

Sends alerts to a Telegram chat via the Bot API. Supports text messages and
optional photo attachments (for snapshots when a person is detected).

Setup:
    1. Create a bot via @BotFather on Telegram, get the API token.
    2. Get your chat_id: send any message to your bot, then visit
       https://api.telegram.org/bot<TOKEN>/getUpdates — look for
       "chat":{"id": <NUMBER>}.
    3. Set environment variables:
        export CRANE_TELEGRAM_TOKEN="123456:ABC-DEF..."
        export CRANE_TELEGRAM_CHAT_ID="123456789"
    4. Notifications auto-enable when both token and chat_id are set.

Message format:
    🚨 Обнаружен человек
    Камера: Boras Security
    Время: 03:15:42
    [photo if available]

For errors / disconnects, a similar text-only message is sent.
"""
import logging
import time
from datetime import timezone

import requests

from services.notifications.base import NotificationEvent, NotificationProvider

logger = logging.getLogger("crane.notifications.telegram")


# Emoji prefixes by event type — gives quick visual scanning in Telegram
_EVENT_EMOJI = {
    "target_detected": "🚨",
    "target_lost":     "✅",
    "error":           "⚠️",
    "disconnected":    "📡",
    "state_changed":   "🔄",
    "default":         "ℹ️",
}

# Human-readable Russian titles for each event type
_EVENT_TITLE = {
    "target_detected": "Обнаружен человек",
    "target_lost":     "Цель потеряна — возврат в патруль",
    "error":           "Ошибка системы",
    "disconnected":    "Камера отключилась",
    "state_changed":   "Смена режима",
}


class TelegramNotificationProvider(NotificationProvider):
    """Sends notifications to a Telegram chat using the Bot API.

    Uses requests (already a project dependency) so no new deps required.
    Network errors are caught and logged — never raised.
    """

    API_BASE = "https://api.telegram.org/bot{token}/{method}"
    REQUEST_TIMEOUT = 10.0  # seconds

    def __init__(self, token: str, chat_id: str, camera_name: str = "Boras Security"):
        self._token = token
        self._chat_id = chat_id
        self._camera_name = camera_name

    @property
    def name(self) -> str:
        return "telegram"

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, event: NotificationEvent) -> bool:
        if not self.is_configured():
            return False

        text = self._format_text(event)
        try:
            if event.snapshot:
                return self._send_photo(event.snapshot, text)
            return self._send_text(text)
        except requests.exceptions.RequestException as e:
            logger.warning("Telegram send failed: %s", e)
            return False
        except Exception as e:
            # Defensive: never let provider crash NotificationService thread
            logger.error("Telegram unexpected error: %s", e)
            return False

    def _format_text(self, event: NotificationEvent) -> str:
        emoji = _EVENT_EMOJI.get(event.event_type, _EVENT_EMOJI["default"])
        title = _EVENT_TITLE.get(event.event_type, "Уведомление")
        # Format time in local timezone (Telegram clients display as-is)
        local_ts = event.timestamp.astimezone()
        time_str = local_ts.strftime("%H:%M:%S")

        lines = [
            f"{emoji} {title}",
            f"Камера: {self._camera_name}",
            f"Время: {time_str}",
        ]
        if event.detail:
            lines.append(f"Детали: {event.detail}")
        return "\n".join(lines)

    def _send_text(self, text: str) -> bool:
        url = self.API_BASE.format(token=self._token, method="sendMessage")
        resp = requests.post(
            url,
            json={
                "chat_id": self._chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=self.REQUEST_TIMEOUT,
        )
        ok = resp.status_code == 200
        if not ok:
            logger.warning("Telegram sendMessage -> HTTP %s: %s",
                           resp.status_code, resp.text[:200])
        return ok

    def _send_photo(self, jpeg_bytes: bytes, caption: str) -> bool:
        url = self.API_BASE.format(token=self._token, method="sendPhoto")
        resp = requests.post(
            url,
            data={"chat_id": self._chat_id, "caption": caption},
            files={"photo": ("snapshot.jpg", jpeg_bytes, "image/jpeg")},
            timeout=self.REQUEST_TIMEOUT,
        )
        ok = resp.status_code == 200
        if not ok:
            logger.warning("Telegram sendPhoto -> HTTP %s: %s",
                           resp.status_code, resp.text[:200])
            # Fallback: send text-only message so the alert still goes through
            logger.info("Falling back to text-only Telegram message")
            return self._send_text(caption)
        return ok
