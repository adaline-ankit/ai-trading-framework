# Build With The Framework

This document explains what developers can build with `ai-trading-framework` and how to choose the right extension path.

## What You Can Build

The framework is broad enough to support several product patterns.

With the new instrument-aware broker layer, the framework is no longer limited to plain cash-equity symbols. It can model and expose workflows around:

- equities
- ETFs
- futures
- options
- commodities
- currencies
- mutual fund discovery and holdings workflows

### 1. Telegram Trading Copilot

Build a bot that:

- scans a watchlist
- pushes explanations to Telegram
- shows `/why`, `/risk`, and `/positions`
- lets an operator approve or reject
- executes through paper or a live broker

This is the closest fit to the current first-party runtime.

### 2. Paper Trading Sandbox

Build a safe environment for:

- testing strategies
- simulating approvals
- demonstrating flows to users
- running CI-safe end-to-end tests

### 3. Internal Research Assistant

Build a workflow that:

- scans symbols
- ranks opportunities
- explains signal quality
- stops before execution

This is useful for research desks or analyst workflows.

### 4. Approval Console For A Brokerage Team

Build an internal review queue where:

- strategies propose trades
- risk policies validate them
- operators review explanations
- approvals are auditable
- execution is broker-specific

### 5. Strategy Plugin Package

Build and distribute packages like:

- `ai-trading-strategy-momentum`
- `ai-trading-strategy-news`
- `ai-trading-broker-binance`
- `ai-trading-provider-polygon`

This is the ecosystem direction of the framework.

### 6. Multi-Asset Broker Workspace

Build a workspace where operators can:

- inspect the broker's instrument master
- search futures and options contracts
- review equity and ETF holdings
- review mutual fund holdings
- run approval-based workflows per asset class

This is especially useful for brokers like Zerodha that expose multiple investible segments through one operator account.

### 7. AI Research Workflow API

Use the framework as a backend service that:

- receives symbols or watchlists
- returns structured recommendations
- persists audit trails
- provides replay for later analysis

## Choose The Right Extension Path

### Use `TradingStrategy` if:

- you are building a strategy quickly
- you want one file
- you want to control scan logic directly

### Use a custom `SignalEngine` if:

- you already generate raw signals elsewhere
- you want a scoring or ranking stage
- you want multiple evaluation passes

### Use a custom `ReasoningEngine` if:

- you want a different LLM stack
- you want your own prompting or agent loop
- you want more structured recommendations

### Use custom providers if:

- you need non-demo data
- you need premium APIs
- you need region-specific feeds

### Use a custom `BrokerClient` if:

- you want new execution venues
- you need venue-specific previews or capabilities
- you want to support US equities, crypto, or futures
- you want a broker-specific instrument inventory or holdings model

## Typical Build Patterns

### Pattern A: Single-File Strategy App

Use:

- a custom `TradingStrategy`
- the default signal engines
- the default reasoning engine
- paper broker

This is the easiest entry point.

### Pattern B: Custom Quant Engine

Use:

- external market data providers
- your own strategy or model
- custom signal engines
- default approval and risk layers

This is a good fit for teams with proprietary models.

### Pattern C: Operator Product

Use:

- dashboard
- Telegram
- auth
- broker adapters
- replay

This is the current product-oriented shape of the repository.

### Pattern D: Broker-Only Execution Gateway

Use:

- custom upstream recommendation source
- risk chain
- approval service
- execution service

In this model the framework acts as an audited approval and execution layer.

### Pattern E: Multi-Asset Operator Desk

Use:

- broker instrument inventory endpoints
- holdings endpoints
- approval and risk services
- dashboard or Telegram operator layer

This pattern is useful when one broker account spans cash equities, F&O, commodities, currencies, and mutual funds.

## Example: Custom Strategy

```python
from ai_trading_framework.models import Action, Recommendation, Signal
from ai_trading_framework.sdk.strategies import TradingStrategy


class BreakoutStrategy(TradingStrategy):
    name = "breakout"
    tags = ["momentum", "breakout"]

    async def scan(self, market_context):
        return [
            Signal(
                symbol=market_context.symbol,
                strategy_name=self.name,
                action=Action.BUY,
                confidence=0.78,
                rationale="Price closed above resistance with rising volume.",
            )
        ]

    async def analyze(self, signal, context):
        return Recommendation(
            symbol=signal.symbol,
            action=signal.action,
            confidence=signal.confidence,
            thesis=signal.rationale,
            strategy_name=self.name,
            supporting_evidence=["Resistance breakout", "Volume expansion"],
            entry_price=context.price.price,
            stop_loss=context.price.price * 0.97,
            target=context.price.price * 1.06,
        )
```

## Example: Custom Broker

Implement `BrokerClient` when you want a new broker:

```python
from ai_trading_framework.core.plugin_system.interfaces import BrokerClient
from ai_trading_framework.models import ExecutionResult, OrderPreview, OrderRequest


class MyBroker(BrokerClient):
    async def preview_order(self, order_request: OrderRequest) -> OrderPreview:
        ...

    async def submit_order(self, order_request: OrderRequest) -> ExecutionResult:
        ...

    async def get_positions(self):
        ...
```

## Example: Custom Reasoning Engine

Implement `ReasoningEngine` when you want a custom AI layer:

```python
from ai_trading_framework.core.plugin_system.interfaces import ReasoningEngine
from ai_trading_framework.models import Recommendation


class MyReasoningEngine(ReasoningEngine):
    async def analyze(self, evaluated_signal, market_context) -> Recommendation:
        ...
```

## What Developers Should Rely On

When building on the framework, developers should treat these as the stable integration seams:

- domain models
- Strategy SDK
- plugin interfaces
- FastAPI API surface
- event types
- runtime builder/operator runtime
- instrument and asset-class models

## What Developers Should Avoid Depending On Too Tightly

These areas are likely to evolve faster:

- exact dashboard HTML structure
- internal default prompt wording
- demo provider heuristics
- first-party strategy thresholds

## Recommended Build Journey

For most developers:

1. Start with the paper broker and demo providers.
2. Add one custom strategy.
3. Connect Telegram.
4. Add one real market data provider.
5. Add one real broker.
6. Enable OIDC if multiple operators are involved.

## What The Perfect Future Version Should Support

If the framework continues maturing, the ideal end state is:

- many third-party strategy packages
- many broker adapters
- multiple data vendors
- mature multi-asset strategy templates
- richer dashboard analytics
- deeper replay and benchmarking
- broader geographical coverage

That is what moves it from a strong open-source project into a true ecosystem framework.
