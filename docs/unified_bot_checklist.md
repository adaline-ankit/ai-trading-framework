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

- [x] add `src/ai_trading_framework/product/`
- [x] add product config model
- [x] add generated user project layout
- [x] add product templates as starter configs
- [x] add persistent user state for watchlist and preferences

### Setup And Install Experience

- [x] turn `ai-trading init` into a real interactive wizard
- [x] generate `bot.yaml`
- [x] generate `.env.example`
- [x] generate starter project README
- [x] add `ai-trading doctor`
- [x] add `ai-trading status`
- [x] add `ai-trading connect telegram`
- [x] turn `ai-trading login zerodha` into first-class CLI flow
- [x] add `ai-trading start`
- [x] add `ai-trading portfolio`
- [x] add `ai-trading help-bot`
- [ ] publish package to PyPI
- [ ] validate `pipx install ai-trading`

### Unified One-Bot Runtime

- [x] add intent router
- [x] add deterministic command parser
- [x] add natural-language fallback command fallback for core prompts
- [x] route Telegram through capability modules instead of direct branching in `app.py`
- [x] unify CLI, API, and Telegram over the same routed capabilities
- [ ] add true LLM-backed intent classification fallback beyond the current rule-based parser

### Capability Modules

- [x] portfolio module
- [x] watchlist module
- [x] recommendation module
- [x] execution module
- [x] replay module
- [x] help module
- [x] invest module

### Portfolio Intelligence

- [x] Zerodha funds/margins sync
- [x] auto-budget mode using available cash
- [x] paper broker funds support
- [x] holdings-aware recommendations
- [x] allocation across multiple ideas, not just best single idea
- [x] rebalance suggestions

### Telegram UX

- [x] `/watchlist add`
- [x] `/watchlist remove`
- [x] `/watchlist`
- [x] `/recommend`
- [x] `/holdings`
- [x] `/portfolio`
- [x] `/positions`
- [x] `/invest`
- [x] `/replay`
- [x] `/help`
- [x] `/approve`
- [x] `/reject`
- [x] `/preview`
- [x] `/submit`
- [ ] richer inline action flows
- [ ] daily briefing mode
- [x] cleaner human-readable summaries

### Dashboard Product UX

- [x] watchlist management UI
- [x] investment planner UI
- [x] holdings and funds cards
- [ ] capability toggles
- [ ] bot configuration page
- [ ] better replay timeline UI

### Documentation

- [x] setup wizard docs
- [x] product quickstart for end users
- [x] “build your bot in 10 minutes” tutorial
- [x] end-state product doc
- [ ] screenshots/GIFs for README and docs
- [x] docs site beyond markdown files

### Live Trading Hardening

- [ ] fully verify live Zerodha execution on the production account
- [ ] implement richer live order status sync
- [x] implement broker funds and margin endpoints
- [ ] add stronger execution telemetry

### External Inputs Still Needed

- [ ] update the Zerodha Kite app redirect URL to the framework callback URL
- [ ] complete a live Zerodha login on the framework-owned runtime
- [ ] fix the Railway service/domain mapping so the framework domain serves this repo instead of the older platform app
- [ ] provide OIDC provider details if you want SSO instead of password auth
- [ ] provide PyPI trusted publishing or package publish credentials if you want public package publishing

## Recommended Next Milestone

The best next milestone is:

### Milestone: First Unified Bot Product

- [x] `ai-trading init` wizard
- [x] `bot.yaml`
- [x] watchlist persistence
- [x] `/recommend`
- [x] `/portfolio`
- [x] `/invest`
- [x] `ai-trading doctor`
- [x] `ai-trading connect telegram`
- [x] `ai-trading login zerodha`
- [x] `ai-trading start`

If that milestone is complete, the framework will stop feeling like only a developer toolkit and start feeling like a real installable product.
