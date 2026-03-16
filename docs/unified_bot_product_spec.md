# Unified Bot Product Spec

This document describes the next product layer on top of `ai-trading-framework`: one installable bot runtime that exposes multiple investing and trading capabilities through one Telegram bot, one dashboard, and one CLI.

## Product Goal

The user should not need to assemble framework pieces manually.

The desired experience is:

1. install one package
2. run one setup flow
3. connect broker
4. connect Telegram
5. start using one smart bot

The bot should then handle:

- portfolio questions
- watchlist management
- daily recommendations
- budget-aware investment planning
- approval-first execution
- replay and explainability

## Product Layers

The overall product should be structured in three layers.

### 1. Core Framework

Already exists in this repository:

- workflow engine
- plugin system
- risk policies
- approval service
- broker adapters
- replay
- API
- dashboard
- Telegram plumbing

### 2. Product Runtime

This is the missing layer to build now.

It should provide:

- configuration
- setup wizard
- user project generation
- intent routing
- capability modules
- unified Telegram UX
- product CLI

### 3. Hosted Or Managed Experience

Optional later:

- billing
- hosted runtime
- managed onboarding
- multi-tenant operator experience

## One Bot, Many Capabilities

Do not build four different bots as separate products.

Build:

- one bot
- one runtime
- one state store
- many routed capabilities

Templates still matter, but only as starter configurations, not as isolated products.

## Capability Model

Each user bot should support feature flags.

Example:

```yaml
bot:
  name: my-copilot

capabilities:
  portfolio: true
  watchlist: true
  recommendations: true
  budget_investing: true
  execution: true
  replay: true
```

The bot runtime decides which modules are enabled. The user interacts with one Telegram bot identity regardless.

## Recommended File Layout

Add a product layer inside the repo:

```text
src/ai_trading_framework/product/
  __init__.py
  config.py
  router.py
  state.py
  wizard.py
  templates/
    investor_copilot.yaml
    swing_trader.yaml
    paper_sandbox.yaml
  capabilities/
    __init__.py
    portfolio.py
    watchlist.py
    recommend.py
    invest.py
    execution.py
    replay.py
```

Generated user project after `ai-trading init my-bot`:

```text
my-bot/
  bot.yaml
  .env.example
  strategies/
  prompts/
  state/
  README.md
```

## Product Config

Add a user-facing config model in `product/config.py`.

Recommended config sections:

### Bot

- bot name
- mode: `local`, `self_hosted`
- default broker
- timezone

### Telegram

- enabled
- default chat
- webhook mode

### Broker

- broker name
- live or paper
- funds source: manual or broker

### Capabilities

- portfolio
- watchlist
- recommendations
- budget investing
- execution
- replay

### Defaults

- default watchlist
- default budget
- default recommendation universe
- recommendation cadence

### Strategy

- preset strategy
- optional custom strategy module path

### Risk

- max capital per trade
- max positions
- restricted symbols
- approval required

## Intent Router

Add `product/router.py`.

The router should map incoming messages to a deterministic intent before any action is taken.

### Routing priority

1. explicit slash command
2. structured parser
3. LLM fallback intent classification

### Core intents

- `portfolio_summary`
- `watchlist_add`
- `watchlist_remove`
- `watchlist_list`
- `watchlist_scan`
- `daily_recommendation`
- `budget_investment`
- `explain_trade`
- `risk_review`
- `positions`
- `holdings`
- `approve_trade`
- `reject_trade`
- `preview_order`
- `submit_order`
- `replay_run`
- `help`

The LLM may help classify or phrase the reply, but execution must remain deterministic.

## Capability Modules

Each capability should wrap existing framework services.

### `portfolio.py`

Uses:

- broker positions
- broker holdings
- broker funds later

Outputs:

- holdings summary
- exposure summary
- portfolio Q&A answers

### `watchlist.py`

Uses:

- stored watchlist
- scan/recommendation pipeline

Outputs:

- watchlist add/remove/list
- scan of tracked names

### `recommend.py`

Uses:

- analysis pipeline
- runtime analyze

Outputs:

- top recommendation now
- daily recommendation flow

### `invest.py`

Uses:

- `InvestmentPlanner`

Outputs:

- best approved BUY candidate under budget
- suggested quantity
- recommendation and approval token

### `execution.py`

Uses:

- preview
- approve
- submit

Outputs:

- preview summary
- approval handling
- submission result

### `replay.py`

Uses:

- replay engine

Outputs:

- run timeline
- why/risk/execution recap

## CLI Architecture

The user-facing package should remain Python-first.

Primary install target:

```bash
pipx install ai-trading
```

The CLI should act as the setup and ops shell, while Telegram becomes the primary daily interaction layer.

## OpenClaw-Style Command Spec

### Bootstrap

`ai-trading init [name]`

Responsibilities:

- interactive setup wizard
- choose template
- choose broker
- choose paper or live
- choose Telegram yes/no
- choose watchlist
- choose budget mode
- write `bot.yaml` and `.env.example`

Output:

- project folder
- next steps

### Validation

`ai-trading doctor`

Checks:

- config exists
- database reachable
- Telegram vars configured
- webhook reachable
- broker auth present
- runtime bootable

### Broker Connect

`ai-trading login zerodha`

Responsibilities:

- open browser or print URL
- complete callback
- persist session

### Telegram Connect

`ai-trading connect telegram`

Responsibilities:

- validate token
- validate chat id
- set webhook
- confirm bot is usable

### Runtime Start

`ai-trading start`

Responsibilities:

- start local API/runtime
- show dashboard URL
- confirm Telegram mode

### Daily Use Commands

`ai-trading recommend`

- run recommendation flow once

`ai-trading invest <amount> [symbols...] [--broker PAPER|ZERODHA]`

- run budget-aware planning

`ai-trading portfolio`

- show holdings/positions summary

`ai-trading replay <run_id>`

- show replay

### Management Commands

`ai-trading watchlist add <symbol>`

`ai-trading watchlist remove <symbol>`

`ai-trading watchlist list`

`ai-trading status`

`ai-trading deploy`

## Telegram UX Spec

Telegram should be the main operator surface.

### Explicit commands

- `/portfolio`
- `/positions`
- `/holdings`
- `/watchlist`
- `/watchlist add INFY`
- `/watchlist remove INFY`
- `/recommend`
- `/invest 25000`
- `/why INFY`
- `/risk INFY`
- `/approve`
- `/reject`
- `/replay`
- `/help`

### Natural language examples

- “What should I buy today?”
- “Best use of Rs 25,000?”
- “Show my holdings”
- “Why did you suggest INFY?”
- “Any swing trades in my watchlist?”

### Telegram response contract

Every actionable recommendation should include:

- action
- confidence
- why
- risk summary
- suggested quantity if relevant
- approval buttons

## User Experience Flow

### Developer user

1. discovers the repo or package
2. installs `ai-trading`
3. runs `ai-trading init`
4. gets a working local bot project
5. tests in paper mode
6. customizes strategy or providers if needed
7. deploys self-hosted

### End user or operator

1. discovers a demo showing Telegram + Zerodha
2. installs the product or uses a hosted onboarding flow
3. connects Zerodha
4. connects Telegram
5. enables watchlist and recommendation mode
6. starts asking the bot for ideas
7. approves and submits trades through the bot
8. uses replay later to inspect behavior

## Design Constraints

These must remain true even in the product layer:

- approval-first for non-paper execution
- deterministic execution gating
- replay preserved
- broker actions auditable
- LLM does not directly bypass controls

## Recommended Implementation Order

1. product config
2. setup wizard
3. intent router
4. watchlist + recommend + invest + portfolio modules
5. Telegram routing through the router
6. broker funds sync
7. natural-language fallback
8. polished dashboard and docs
