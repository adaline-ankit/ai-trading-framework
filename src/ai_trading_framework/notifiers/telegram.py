from __future__ import annotations

import httpx

from ai_trading_framework.core.plugin_system.interfaces import Notifier
from ai_trading_framework.models import Recommendation


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(
        self,
        message: str,
        chat_id: str | None = None,
        *,
        reply_markup: dict | None = None,
    ) -> None:
        target_chat_id = chat_id or self.chat_id
        if not self.bot_token or not target_chat_id:
            return
        payload: dict[str, object] = {"chat_id": target_chat_id, "text": message}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json=payload,
            )

    async def send_alert(self, message: str) -> None:
        await self.send_message(message)

    async def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        if not self.bot_token:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
            )

    async def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> dict:
        if not self.bot_token:
            return {"ok": False, "description": "Bot token is not configured."}
        payload: dict[str, object] = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/setWebhook",
                json=payload,
            )
        return response.json()

    async def get_webhook_info(self) -> dict:
        if not self.bot_token:
            return {"ok": False, "description": "Bot token is not configured."}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
            )
        return response.json()

    async def send_recommendation(
        self,
        recommendation: Recommendation,
        approval_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        message = (
            f"Trade alert: {recommendation.symbol}\n"
            f"Action: {recommendation.action.value}\n"
            f"Confidence: {recommendation.confidence:.0%}\n"
            f"Why: {recommendation.explain().why_this_trade}\n"
            f"Use /why {recommendation.symbol}, /risk {recommendation.symbol}, "
            f"/approve {recommendation.recommendation_id} {approval_token or 'TOKEN'}\n"
            f"Approval token: {approval_token or 'pending'}"
        )
        callback_prefix = recommendation.recommendation_id
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Approve", "callback_data": f"approve|{callback_prefix}"},
                    {"text": "Reject", "callback_data": f"reject|{callback_prefix}"},
                ],
                [
                    {"text": "Why", "callback_data": f"why|{callback_prefix}"},
                    {"text": "Risk", "callback_data": f"risk|{callback_prefix}"},
                ],
            ]
        }
        await self.send_message(message, chat_id=chat_id, reply_markup=reply_markup)
