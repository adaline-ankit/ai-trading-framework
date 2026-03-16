# Unified Bot Checklist

This checklist tracks the work needed to turn the current framework into one installable, OpenClaw-style trading copilot product.

## Already Done

### Core Framework

- [x] workflow engine
- [x] event bus
- [x] replay engine
- [x] explainability engine
- [x] risk policy chain
- [x] approval service
- [x] execution service
- [x] plugin interfaces
- [x] Strategy SDK

### Surfaces

- [x] FastAPI app
- [x] interactive dashboard
- [x] Telegram notifier
- [x] Telegram webhook handling
- [x] CLI entrypoint

### Brokers And Data

- [x] paper broker
- [x] Zerodha auth flow
- [x] Zerodha positions
- [x] Zerodha holdings
- [x] Zerodha instrument inventory endpoints
- [x] Zerodha mutual fund inventory and holdings endpoints
- [x] demo market/news/fundamental/sentiment providers

### Safety And State

- [x] approval-first live execution guard
- [x] `HOLD` execution blocking
- [x] auth support
- [x] Postgres-backed operator and broker session persistence
- [x] run persistence and replayability

### OSS And Delivery

- [x] README
- [x] contributor docs
- [x] CI
- [x] Docker workflow
- [x] release workflow
- [x] CodeQL
- [x] Railway deployment
- [x] local Docker Compose stack

### User-Facing Planning Features

- [x] budget-aware investment planner
- [x] CLI `invest`
- [x] API `POST /v1/investment-plan`
- [x] Telegram `/invest`

### Automated Coverage

- [x] workflow tests
- [x] event bus tests
- [x] execution guard tests
- [x] API flow tests
- [x] OSS end-to-end tests for dashboard, Telegram, planner, and CLI

## Still To Implement

### Product Layer

- [ ] add `src/ai_trading_framework/product/`
- [ ] add product config model
- [ ] add generated user project layout
- [ ] add product templates as starter configs
- [ ] add persistent user state for watchlist and preferences

### Setup And Install Experience

- [ ] turn `ai-trading init` into a real interactive wizard
- [ ] generate `bot.yaml`
- [ ] generate `.env.example`
- [ ] generate starter project README
- [ ] add `ai-trading doctor`
- [ ] add `ai-trading status`
- [ ] add `ai-trading connect telegram`
- [ ] turn `ai-trading login zerodha` into first-class CLI flow
- [ ] publish package to PyPI
- [ ] validate `pipx install ai-trading`

### Unified One-Bot Runtime

- [ ] add intent router
- [ ] add deterministic command parser
- [ ] add natural-language fallback classifier
- [ ] route Telegram through capability modules instead of direct branching in `app.py`
- [ ] unify CLI, API, and Telegram over the same routed capabilities

### Capability Modules

- [ ] portfolio module
- [ ] watchlist module
- [ ] recommendation module
- [ ] execution module
- [ ] replay module
- [ ] help module

### Portfolio Intelligence

- [ ] Zerodha funds/margins sync
- [ ] auto-budget mode using available cash
- [ ] holdings-aware recommendations
- [ ] allocation across multiple ideas, not just best single idea
- [ ] rebalance suggestions

### Telegram UX

- [ ] `/watchlist add`
- [ ] `/watchlist remove`
- [ ] `/watchlist`
- [ ] `/recommend`
- [ ] `/holdings`
- [ ] `/replay`
- [ ] richer inline action flows
- [ ] daily briefing mode
- [ ] cleaner human-readable summaries

### Dashboard Product UX

- [ ] watchlist management UI
- [ ] investment planner UI
- [ ] holdings and funds cards
- [ ] capability toggles
- [ ] bot configuration page
- [ ] better replay timeline UI

### Documentation

- [ ] setup wizard docs
- [ ] product quickstart for end users
- [ ] “build your bot in 10 minutes” tutorial
- [ ] screenshots/GIFs for README and docs
- [ ] docs site beyond markdown files

### Live Trading Hardening

- [ ] fully verify live Zerodha execution on the production account
- [ ] implement richer live order status sync
- [ ] implement broker funds and margin endpoints
- [ ] add stronger execution telemetry

## Recommended Next Milestone

The best next milestone is:

### Milestone: First Unified Bot Product

- [ ] `ai-trading init` wizard
- [ ] `bot.yaml`
- [ ] watchlist persistence
- [ ] `/recommend`
- [ ] `/portfolio`
- [ ] `/invest`
- [ ] `ai-trading doctor`
- [ ] `ai-trading connect telegram`
- [ ] `ai-trading login zerodha`

If that milestone is complete, the framework will stop feeling like only a developer toolkit and start feeling like a real installable product.
