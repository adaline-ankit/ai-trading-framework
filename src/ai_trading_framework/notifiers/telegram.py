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

    async def send_message(self, message: str, chat_id: str | None = None) -> None:
        target_chat_id = chat_id or self.chat_id
        if not self.bot_token or not target_chat_id:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": target_chat_id, "text": message},
            )

    async def send_alert(self, message: str) -> None:
        await self.send_message(message)

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
        await self.send_message(message, chat_id=chat_id)
