from __future__ import annotations

from ai_trading_framework.core.plugin_system.interfaces import LLMProvider


class HeuristicLLMProvider(LLMProvider):
    async def complete(self, prompt: str) -> str:
        return prompt.splitlines()[-1] if prompt.splitlines() else prompt


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str = "gpt-5") -> None:
        self.model = model
        self.client = None
        if api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)

    async def complete(self, prompt: str) -> str:
        if not self.client:
            return prompt
        response = self.client.responses.create(model=self.model, input=prompt)
        return getattr(response, "output_text", "") or prompt
