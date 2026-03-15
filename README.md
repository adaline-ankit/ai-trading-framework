# AI Trading Framework

[![CI](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/ci.yml)
[![Docker](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/docker.yml/badge.svg)](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/docker.yml)
[![Release](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/release.yml/badge.svg)](https://github.com/adaline-ankit/ai-trading-framework/actions/workflows/release.yml)

Open-source framework for building AI trading copilots with replayable workflows, deterministic guardrails, human approval, and broker execution adapters.

This project is not an autonomous stock picker. The default operating model is:

`research -> signal generation -> AI reasoning -> explainability -> risk guardrails -> approval -> execution -> analytics`

## Why This Exists

Most AI trading repos are either notebooks, strategy bundles, or single-purpose bots. `ai-trading-framework` is intended to be the reusable layer underneath:

- Telegram trading assistants
- approval-first broker execution workflows
- AI research and signal copilots
- paper trading and replayable operator simulations
- plugin ecosystems for strategies, brokers, data providers, and models

## Core Capabilities

- Strategy SDK for one-file strategy authoring
- Plugin interfaces for strategies, providers, brokers, notifiers, risk policies, and LLMs
- Event-driven workflow engine with replay support
- Approval-first execution model for non-paper brokers
- Telegram, dashboard, API, and CLI surfaces on one runtime
- Explainability engine with `why_this_trade`, signal, and risk sections
- Risk policy chain with deterministic guardrails
- Sandbox mode, benchmarking, and paper trading
- India-first examples with market-agnostic framework interfaces

## Architecture

```text
Data -> Features -> Strategy SDK -> Signal Engines -> AI Reasoning
     -> Explainability -> Risk Policy Chain -> Approval -> Execution -> Analytics
```

For a fuller view, see [docs/architecture.md](docs/architecture.md).

## Quickstart

### 1. Install

```bash
uv sync --extra dev
```

### 2. Run local sandbox mode

```bash
uv run ai-trading sandbox
```

### 3. Generate a recommendation

```bash
uv run ai-trading scan INFY
```

### 4. Run the API

```bash
uv run uvicorn ai_trading_framework.api.app:create_app --factory --reload
```

### 5. Run tests

```bash
uv run pytest
```

## CLI

```bash
ai-trading init
ai-trading run
ai-trading scan INFY
ai-trading analyze INFY
ai-trading backtest INFY
ai-trading replay <run-id>
ai-trading benchmark
ai-trading sandbox
ai-trading deploy
```

## What Ships In v1

- Strategy SDK
- Event bus
- Explainability engine
- Replay engine
- Risk policy chain
- Paper broker
- Zerodha adapter
- Telegram notifier
- FastAPI runtime
- CLI
- Railway deployment files
- GitHub Actions for CI, Docker build, and releases

## Safety Model

- Human-in-the-loop by default
- Approval is mandatory for non-paper execution
- Deterministic risk policies run before execution
- Approval tokens are single-use and auditable
- Replay and event history are first-class features

## Examples

- [examples/paper_trading_bot](examples/paper_trading_bot)
- [examples/telegram_zerodha_bot](examples/telegram_zerodha_bot)
- [examples/custom_strategy](examples/custom_strategy)
- [examples/sandbox_demo](examples/sandbox_demo)

## Documentation

- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Strategy SDK](docs/strategy_sdk.md)
- [Plugins](docs/plugins.md)
- [Replay](docs/replay.md)
- [Explainability](docs/explainability.md)
- [Telegram](docs/telegram.md)
- [Zerodha](docs/brokers_zerodha.md)
- [Railway Deployment](docs/deployment_railway.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
