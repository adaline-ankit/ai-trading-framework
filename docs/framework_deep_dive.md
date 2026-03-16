# Framework Deep Dive

This document explains how `ai-trading-framework` works internally, how the current implementation is assembled, and how developers should think about extending it.

## What The Framework Is

This repository is a reusable operator runtime for building AI trading systems with:

- research and market context gathering
- signal generation
- AI-assisted reasoning
- deterministic risk checks
- approval-gated execution
- Telegram and dashboard operator interaction
- replayable run history

It is not designed as an autonomous trading bot. The runtime assumes a human operator remains in the loop for live trading.

## Design Principles

The implementation is structured around a few strict principles:

- approval before execution for non-paper brokers
- deterministic guardrails around probabilistic reasoning
- replayable runs via event recording
- plugin-style extensibility
- deploy-anywhere runtime surfaces
- instrument-aware modeling so the framework can span more than cash equities

## Repository Mental Model

The current repository can be understood in six layers.

### 1. Domain Models

Located in [src/ai_trading_framework/models.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/models.py).

These define the framework vocabulary:

- `MarketContext`
- `InstrumentDescriptor`
- `Signal`
- `EvaluatedSignal`
- `Recommendation`
- `RecommendationExplanation`
- `RiskEvaluation`
- `ApprovalRequest`
- `OrderRequest`
- `ExecutionResult`
- `RunRecord`
- `Event`

If a developer wants to understand the data model, this is the starting point.

### 2. Analysis Layer

Located primarily in:

- [src/ai_trading_framework/core/orchestration/pipeline.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/orchestration/pipeline.py)
- [src/ai_trading_framework/sdk/strategies/base.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/sdk/strategies/base.py)
- [src/ai_trading_framework/core/plugin_system/interfaces.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/plugin_system/interfaces.py)

This layer gathers input data and turns it into recommendations.

### 3. Workflow Layer

Located in:

- [src/ai_trading_framework/core/engine/workflow.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/engine/workflow.py)
- [src/ai_trading_framework/core/events/bus.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/events/bus.py)
- [src/ai_trading_framework/core/explainability/service.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/explainability/service.py)
- [src/ai_trading_framework/risk/policies/base.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/risk/policies/base.py)

This layer takes recommendations and applies explainability, risk, approval, and execution orchestration.

### 4. Operator Runtime Layer

Located in:

- [src/ai_trading_framework/core/runtime/builder.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/runtime/builder.py)
- [src/ai_trading_framework/core/runtime/operator.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/runtime/operator.py)

This layer wires components together and exposes a stable façade to the API, dashboard, Telegram, and CLI.

### 5. Surface Layer

Located in:

- [src/ai_trading_framework/api/app.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/api/app.py)
- [src/ai_trading_framework/api/dashboard.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/api/dashboard.py)
- [src/ai_trading_framework/notifiers/telegram.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/notifiers/telegram.py)
- [src/ai_trading_framework/core/cli/main.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/cli/main.py)

These are the human and operator entry points.

### 6. Persistence And Security Layer

Located in:

- [src/ai_trading_framework/storage/sqlalchemy/repository.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/storage/sqlalchemy/repository.py)
- [src/ai_trading_framework/core/security/auth.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/core/security/auth.py)

This layer handles auth, session state, broker session durability, and historical run restoration.

## End-To-End Request Flow

The easiest way to understand the framework is to follow one scan.

### Step 1: App Startup

`create_app()` builds:

- settings
- `FrameworkBuilder`
- `OperatorRuntime`
- `AnalysisPipeline`

The builder also bootstraps:

- demo providers by default
- debate reasoning with an OpenAI provider
- paper, Zerodha, and Groww brokers
- Telegram notifier
- risk policy chain
- SQLAlchemy persistence

### Step 2: Scan Request

When a user calls `GET /v1/scan/{symbol}`, the analysis pipeline:

1. fetches price and candles
2. fetches fundamentals
3. fetches news
4. computes sentiment
5. creates `MarketContext`
6. calls `TradingStrategy.scan()`
7. runs each `SignalEngine`
8. passes evaluated signals into the `ReasoningEngine`
9. returns one or more `Recommendation` objects

### Step 3: Workflow Processing

The operator runtime then hands recommendations to `WorkflowEngine.process()`.

For each recommendation, the workflow engine:

1. appends `MarketContextBuilt`
2. appends `RecommendationCreated`
3. runs the `RiskPolicyChain`
4. appends `RiskEvaluated`
5. generates a structured explanation
6. appends `ExplanationGenerated`
7. creates an approval request
8. appends `ApprovalRequested`

If simulation is enabled for non-paper brokers, it can also approve automatically for test paths.

### Step 4: Operator Interaction

The runtime stores the recommendation, risk result, and run. Then the surface layer can:

- show it on the dashboard
- send it to Telegram
- expose it via the API
- print it in the CLI

### Step 5: Approval And Execution

On preview:

- the runtime builds an `OrderRequest`
- the broker adapter returns an `OrderPreview`

On submit:

- execution service blocks `HOLD`
- execution service blocks non-paper execution without approved risk
- execution service blocks non-paper execution without an approval token
- approval token is consumed once
- the selected broker adapter submits the order
- an execution event is appended to the run

### Step 6: Replay

The run can later be replayed from stored events. The replay engine exposes:

- event history
- latest payload for each event type
- reconstructed run metadata

## Current First-Party Components

The current repo ships with these first-party building blocks.

## Multi-Asset Model

The framework now has first-class instrument metadata so the same runtime can represent:

- cash equities
- ETFs
- futures
- options
- commodities
- currencies
- mutual funds

The core building blocks for this are:

- `AssetClass`
- `BrokerProduct`
- `OrderVariety`
- `InstrumentDescriptor`

These live in [src/ai_trading_framework/models.py](/Users/ankit/Desktop/trading-agent-platform/ai-trading-framework/src/ai_trading_framework/models.py) and are intended to stop the framework from collapsing everything into just `symbol`.

On the broker side, the Zerodha adapter now exposes:

- broker capabilities by asset class
- instrument master search
- mutual fund instrument search
- holdings
- mutual fund holdings

That gives developers enough surface area to build multi-asset operator workflows even before every asset class has a dedicated strategy template.

### Data Providers

- demo market provider
- demo news provider
- demo fundamentals provider
- demo sentiment provider
- Yahoo provider scaffold

### Signals And Strategies

- `MomentumStrategy`
- `MomentumSignalEngine`
- `FinRLSignalEngine`

### Reasoning

- debate reasoning engine
- OpenAI-backed LLM provider abstraction

### Risk

The default `RiskPolicyChain` includes policies for:

- minimum confidence
- max positions
- capital per trade
- daily loss
- symbol exposure
- restricted symbols
- liquidity
- spread

### Execution

- paper broker
- Zerodha broker
- Groww broker scaffold

### Operator Surfaces

- dashboard
- Telegram
- API
- CLI

## Approval Model In Depth

Approval is central to the framework.

An `ApprovalRequest` has:

- a recommendation id
- a run id
- a broker
- a token
- timestamps
- a state machine

The valid lifecycle is roughly:

`PENDING -> APPROVED -> CONSUMED`

or

`PENDING -> REJECTED`

or

`PENDING -> EXPIRED`

This gives the framework:

- idempotent execution gates
- auditable operator actions
- a clean human-in-the-loop model

## Explainability Model

Each recommendation can produce a structured explanation through `Recommendation.explain()`.

The explanation contains:

- `why_this_trade`
- `signals_used`
- `risk_checks`
- `ai_reasoning`
- `execution_constraints`

This is the payload used by:

- `/why`
- `/risk`
- replay
- dashboard recommendation detail views

## Event Bus And Replay Model

The current event bus is intentionally simple.

- subscribers attach to an `EventType`
- every published event is stored in in-memory history
- each `RunRecord` also stores its event list

This gives a clean base for future:

- async workers
- analytics sinks
- distributed tracing hooks
- compliance export pipelines

Replay currently returns the latest payload per event type plus the full event list. That makes debugging operator runs much easier than reconstructing behavior from logs alone.

## How Developers Should Extend It

Most developers should choose the shallowest extension point that solves their problem.

### Best starting point: Strategy SDK

Use a custom `TradingStrategy` when you want to:

- define scan logic
- emit your own signals
- keep implementation in one file

### Next level: Signal engine

Use a custom `SignalEngine` when you already have:

- ML scores
- external heuristics
- ranking logic

and want to plug them after signal generation.

### Next level: Reasoning engine

Use a custom `ReasoningEngine` when you want:

- different prompt logic
- multi-agent systems
- non-OpenAI reasoning backends

### Next level: Broker adapter

Use a custom `BrokerClient` when you want:

- a new broker
- a crypto venue
- a region-specific execution adapter

### Next level: Data provider

Use custom providers when you want:

- live market data
- premium fundamentals
- streaming quotes
- your own research feeds

## What The Framework Can Build Today

The current implementation is already suitable for building:

- Telegram trading copilots
- paper-trading operator consoles
- approval-first research assistants
- broker-connected human review systems
- strategy experimentation environments
- internal trading desks tools

## What It Is Not Yet

The framework is strong, but not complete in every area.

Current gaps or intentionally incomplete areas include:

- live Zerodha verification still depends on the external Kite redirect setup
- the event bus is in-process, not distributed
- analytics are present but still lightweight
- the dashboard is operator-focused rather than a full polished SaaS frontend
- mutual fund workflows are modeled and discoverable, but the runtime does not enable direct Coin order placement

## Recommended Reading Path

For new users:

1. [Quickstart](./quickstart.md)
2. [Architecture](./architecture.md)
3. [Build With The Framework](./build_with_framework.md)

For contributors:

1. [Framework Deep Dive](./framework_deep_dive.md)
2. [Plugins](./plugins.md)
3. [Strategy SDK](./strategy_sdk.md)
