from __future__ import annotations

from typing import Any, cast

from ai_trading_framework.analytics.investment_planner import InvestmentPlanner
from ai_trading_framework.core.orchestration.pipeline import AnalysisPipeline
from ai_trading_framework.core.runtime.operator import OperatorRuntime
from ai_trading_framework.models import BrokerName, OrderType
from ai_trading_framework.product.capabilities import (
    ExecutionCapability,
    HelpCapability,
    InvestmentCapability,
    PortfolioCapability,
    RecommendationCapability,
    ReplayCapability,
    WatchlistCapability,
)
from ai_trading_framework.product.config import BotConfig
from ai_trading_framework.product.state import WatchlistState


class ProductRouter:
    def __init__(
        self,
        *,
        config: BotConfig,
        runtime: OperatorRuntime,
        pipeline: AnalysisPipeline,
    ) -> None:
        self.config = config
        self.runtime = runtime
        self.pipeline = pipeline
        self.watchlist_state = WatchlistState(runtime.run_store, config.defaults.watchlist)
        self.watchlist = WatchlistCapability(self.watchlist_state)
        self.portfolio = PortfolioCapability(runtime)
        self.recommendations = RecommendationCapability(runtime, pipeline, self.watchlist_state)
        planner = InvestmentPlanner(runtime, pipeline)
        self.investment = InvestmentCapability(planner, self.watchlist_state, config)
        self.execution = ExecutionCapability(runtime)
        self.replay = ReplayCapability(runtime)
        self.help = HelpCapability(config.capabilities)

    async def handle_telegram(self, text: str, chat_id: str | None = None) -> str | None:
        del chat_id
        parts = text.strip().split()
        if not parts:
            return "No command received."
        command = parts[0].lower()

        if command == "/help":
            return self.help.render()
        if command == "/watchlist":
            return self._handle_watchlist(parts)
        if command == "/recommend":
            return await self._handle_recommend(parts[1:])
        if command in {"/portfolio", "/positions", "/holdings"}:
            return await self._handle_portfolio(command, parts[1:])
        if command == "/invest":
            return await self._handle_invest(parts[1:])
        if command == "/approve":
            return await self._handle_approve(parts[1:])
        if command == "/reject":
            return await self._handle_reject(parts[1:])
        if command == "/preview":
            return await self._handle_preview(parts[1:])
        if command == "/submit":
            return await self._handle_submit(parts[1:])
        if command == "/replay":
            return self._handle_replay(parts[1:])
        if command == "/why":
            return self._handle_why(parts[1:])
        if command == "/risk":
            return self._handle_risk(parts[1:])
        return await self._handle_natural_language(text)

    async def summarize_portfolio(self, broker: BrokerName | None = None) -> dict[str, Any]:
        return await self.portfolio.summary(broker or self.config.broker)

    async def recommend_now(
        self,
        *,
        broker: BrokerName | None = None,
        symbols: list[str] | None = None,
        notify: bool = False,
    ) -> dict[str, Any]:
        payload = await self.recommendations.recommend(
            broker=broker or self.config.broker,
            symbols=symbols,
            notify=notify,
        )
        return payload

    async def plan_investment(
        self,
        *,
        budget: float | None,
        symbols: list[str] | None,
        broker: BrokerName | None = None,
        prefer_broker_funds: bool = False,
    ) -> dict[str, Any]:
        target_broker = broker or self.config.broker
        funds = await self.runtime.get_funds(target_broker) if prefer_broker_funds else None
        plan = await self.investment.plan(
            budget=budget,
            symbols=symbols,
            broker=target_broker,
            available_cash=funds.available_cash if funds else None,
        )
        payload = plan.model_dump(mode="json")
        if funds:
            payload["funds"] = funds.model_dump(mode="json")
        return payload

    def _handle_watchlist(self, parts: list[str]) -> str:
        if len(parts) == 1 or parts[1].lower() == "list":
            items = self.watchlist.get_all()
            return "Watchlist: " + ", ".join(items) if items else "Watchlist is empty."
        if len(parts) >= 3 and parts[1].lower() == "add":
            items = self.watchlist.add(parts[2])
            return f"Added {parts[2].upper()}. Watchlist: {', '.join(items)}"
        if len(parts) >= 3 and parts[1].lower() == "remove":
            items = self.watchlist.remove(parts[2])
            return f"Removed {parts[2].upper()}. Watchlist: {', '.join(items)}"
        return "Usage: /watchlist [list|add SYMBOL|remove SYMBOL]"

    async def _handle_recommend(self, parts: list[str]) -> str:
        broker, symbols = self._extract_broker_and_symbols(parts)
        payload = await self.recommend_now(broker=broker, symbols=symbols or None, notify=True)
        top = cast(dict[str, Any] | None, payload["top"])
        if not top:
            return "No recommendation available for the current watchlist."
        return self._format_ranked_candidate(top)

    async def _handle_portfolio(self, command: str, parts: list[str]) -> str:
        broker = self._extract_broker(parts)
        summary = await self.summarize_portfolio(broker)
        funds = cast(dict[str, Any] | None, summary.get("funds"))
        items = (
            cast(list[dict[str, Any]], summary["holdings"])
            if command == "/holdings"
            else cast(list[dict[str, Any]], summary["positions"])
        )
        label = "holdings" if command == "/holdings" else "positions"
        lines = [f"{broker.value} {label}"]
        if funds:
            lines.append(
                f"Funds: available={funds['available_cash']:.2f} "
                f"net={funds['net']:.2f} collateral={funds['collateral']:.2f}"
            )
        if not items:
            lines.append(f"No {label} found.")
            return "\n".join(lines)
        lines.extend(
            (
                f"{item['symbol']}: qty={item['quantity']} "
                f"avg={item['average_price']} mark={item['market_price']}"
            )
            for item in items
        )
        return "\n".join(lines)

    async def _handle_invest(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /invest <amount|wallet> [SYMBOL ...] [PAPER|ZERODHA]"
        broker = self._extract_broker(parts)
        filtered_parts = [part for part in parts if part.upper() not in {"PAPER", "ZERODHA"}]
        first = filtered_parts[0].lower()
        prefer_wallet = first in {"wallet", "auto"}
        if prefer_wallet:
            budget = None
            symbols = [symbol.upper() for symbol in filtered_parts[1:]] or None
        else:
            try:
                budget = float(filtered_parts[0])
            except ValueError:
                return "Usage: /invest <amount|wallet> [SYMBOL ...] [PAPER|ZERODHA]"
            symbols = [symbol.upper() for symbol in filtered_parts[1:]] or None
        payload = await self.plan_investment(
            budget=budget,
            symbols=symbols,
            broker=broker,
            prefer_broker_funds=prefer_wallet,
        )
        selected = cast(dict[str, Any] | None, payload.get("selected"))
        if not selected:
            return str(payload.get("summary") or "No investment candidate available.")
        funds = cast(dict[str, Any] | None, payload.get("funds"))
        allocations = cast(list[dict[str, Any]], payload.get("allocations") or [])
        rebalance_actions = cast(list[dict[str, Any]], payload.get("rebalance_actions") or [])
        wallet_line = (
            f"\nWallet cash: {funds['available_cash']:.2f}" if funds and prefer_wallet else ""
        )
        allocation_line = ""
        if allocations:
            allocation_line = "\nAllocations: " + ", ".join(
                f"{item['symbol']} {item['target_weight']:.0%}" for item in allocations
            )
        rebalance_line = ""
        if rebalance_actions:
            rebalance_line = "\nRebalance: " + ", ".join(
                f"{item['action']} {item['symbol']}" for item in rebalance_actions[:3]
            )
        return (
            f"Best idea: {selected['symbol']} {selected['action']}\n"
            f"Confidence: {selected['confidence']:.0%}\n"
            f"Suggested quantity: {selected['suggested_quantity']}\n"
            f"Estimated notional: {selected['estimated_notional']:.2f}\n"
            f"Why: {selected['thesis']}{wallet_line}{allocation_line}{rebalance_line}"
        )

    async def _handle_approve(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /approve RECOMMENDATION_ID"
        payload = await self.execution.approve(parts[0])
        return f"Approved {payload['recommendation_id']}."

    async def _handle_reject(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /reject RECOMMENDATION_ID"
        payload = await self.execution.reject(parts[0])
        return f"Rejected {payload['recommendation_id']}."

    async def _handle_preview(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /preview RECOMMENDATION_ID [PAPER|ZERODHA] [QTY]"
        recommendation_id = parts[0]
        broker = self._extract_broker(parts[1:])
        quantity = self._extract_quantity(parts[1:], default=1.0)
        payload = await self.execution.preview(
            recommendation_id,
            broker=broker,
            quantity=quantity,
            order_type=OrderType.LIMIT,
        )
        warnings = cast(list[str], payload.get("warnings") or [])
        warning_block = f"\nWarnings: {'; '.join(warnings)}" if warnings else ""
        return (
            f"Preview {payload['symbol']} {payload['action']} via {payload['broker']}\n"
            f"Quantity: {payload['quantity']} Notional: {payload['estimated_notional']:.2f}"
            f"{warning_block}"
        )

    async def _handle_submit(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /submit RECOMMENDATION_ID [PAPER|ZERODHA] [QTY]"
        recommendation_id = parts[0]
        broker = self._extract_broker(parts[1:])
        quantity = self._extract_quantity(parts[1:], default=1.0)
        payload = await self.execution.submit(
            recommendation_id,
            broker=broker,
            quantity=quantity,
            order_type=OrderType.LIMIT,
        )
        result = cast(dict[str, Any], payload["result"])
        return (
            f"Execution {result['status']} for {result['recommendation_id']}\n{result['message']}"
        )

    def _handle_replay(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /replay RUN_ID"
        payload = self.replay.get(parts[0])
        if not payload:
            return "Run not found."
        events = cast(list[dict[str, Any]], payload.get("events") or [])
        event_names = [event.get("event_type", "unknown") for event in events]
        return f"Replay for {parts[0]}\nEvents: {', '.join(event_names)}"

    def _handle_why(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /why SYMBOL_OR_RECOMMENDATION_ID"
        recommendation = self.runtime.get_recommendation(parts[0])
        if not recommendation:
            return "Recommendation not found."
        explanation = recommendation.explain()
        return (
            f"{recommendation.symbol} {recommendation.action.value}\n"
            f"Why: {explanation.why_this_trade}\n"
            f"Signals: {', '.join(explanation.signals_used) or 'n/a'}\n"
            f"AI: {explanation.ai_reasoning or 'n/a'}"
        )

    def _handle_risk(self, parts: list[str]) -> str:
        if not parts:
            return "Usage: /risk SYMBOL_OR_RECOMMENDATION_ID"
        recommendation = self.runtime.get_recommendation(parts[0])
        if not recommendation:
            return "Recommendation not found."
        risk = self.runtime.get_risk(recommendation.recommendation_id)
        if not risk:
            return "Risk evaluation not found."
        reasons = [reason for check in risk.checks for reason in check.reasons]
        return "\n".join([f"{risk.decision}: {risk.summary}", *reasons])

    async def _handle_natural_language(self, text: str) -> str | None:
        lowered = text.lower().strip()
        if lowered.startswith("what should i buy") or lowered.startswith("best idea"):
            return await self._handle_recommend([])
        if lowered.startswith("show my holdings"):
            return await self._handle_portfolio("/holdings", [])
        if lowered.startswith("show my portfolio"):
            return await self._handle_portfolio("/portfolio", [])
        if lowered.startswith("show my positions"):
            return await self._handle_portfolio("/positions", [])
        if lowered.startswith("help"):
            return self.help.render()
        if lowered.startswith("best use of rs ") or lowered.startswith("best use of ₹"):
            amount = self._extract_first_number(lowered)
            if amount is not None:
                return await self._handle_invest([str(amount)])
        return None

    @staticmethod
    def _extract_first_number(text: str) -> float | None:
        digits = "".join(
            character if (character.isdigit() or character == ".") else " " for character in text
        )
        for part in digits.split():
            try:
                return float(part)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_quantity(parts: list[str], *, default: float) -> float:
        for part in reversed(parts):
            try:
                return float(part)
            except ValueError:
                continue
        return default

    def _extract_broker(self, parts: list[str]) -> BrokerName:
        if parts and parts[-1].upper() in {"PAPER", "ZERODHA"}:
            return BrokerName(parts[-1].upper())
        return self.config.broker

    def _extract_broker_and_symbols(self, parts: list[str]) -> tuple[BrokerName, list[str]]:
        broker = self._extract_broker(parts)
        symbols = [
            part.upper()
            for part in parts
            if part.upper() not in {"PAPER", "ZERODHA"} and not _is_float(part)
        ]
        return broker, symbols

    @staticmethod
    def _format_ranked_candidate(item: dict[str, Any]) -> str:
        recommendation = cast(dict[str, Any], item["recommendation"])
        risk = cast(dict[str, Any] | None, item.get("risk"))
        approval = cast(dict[str, Any] | None, item.get("approval"))
        return (
            f"Top idea: {recommendation['symbol']} {recommendation['action']}\n"
            f"Confidence: {recommendation['confidence']:.0%}\n"
            f"Why: {recommendation['thesis']}\n"
            f"Risk: {(risk or {}).get('decision', 'N/A')}\n"
            f"Approval: {(approval or {}).get('status', 'PENDING')}\n"
            f"Recommendation ID: {recommendation['recommendation_id']}"
        )


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
