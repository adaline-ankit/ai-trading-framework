# Unified Bot End State

This document describes what the finished product layer looks like in practice after the current unified-bot implementation work.

## What The Product Is

The product is a single installable trading copilot built on top of `ai-trading-framework`.

The user experience is:

1. install one package
2. generate one bot project
3. connect Telegram
4. connect broker
5. use one smart bot across portfolio, watchlist, recommendation, investing, replay, and execution workflows

The product is still approval-first by default for non-paper trading.

## What A User Gets Now

The current product layer supports:

- `ai-trading init` project generation
- `bot.yaml` configuration
- starter templates
- `ai-trading doctor`
- `ai-trading status`
- `ai-trading help-bot`
- `ai-trading portfolio`
- `ai-trading recommend`
- `ai-trading watchlist add|remove|list`
- `ai-trading connect-telegram`
- `ai-trading login-zerodha`
- `ai-trading start`
- Telegram commands for watchlist, recommendations, portfolio, holdings, investing, replay, why, risk, approve, reject, preview, submit, and help
- automatic broker-funds-aware `/invest wallet` flow when the broker exposes funds

## End-To-End User Flow

### Developer Or Builder

1. Install the package.
2. Run `ai-trading init my-bot`.
3. Use the interactive wizard or defaults to choose template, broker, Telegram, watchlist, and budget behavior.
4. Run `ai-trading doctor`.
5. Run `ai-trading connect-telegram`.
6. Run `ai-trading login-zerodha` if live broker usage is needed.
7. Run `ai-trading start`.
8. Use the dashboard, CLI, or Telegram bot on top of the same runtime.
9. Extend the generated project with custom strategies or providers later.

### Operator Or End User

1. Open Telegram.
2. Ask for:
   - `/portfolio`
   - `/holdings`
   - `/recommend`
   - `/invest 25000`
   - `/invest wallet`
   - `/why INFY`
   - `/risk INFY`
   - `/replay RUN_ID`
3. Review the recommendation and the risk output.
4. Approve the idea.
5. Preview and submit the order.
6. Replay the run later for audit and debugging.

## Depth Of Usage

The product is meant to support several depths of usage with the same runtime.

### 1. No-Custom-Code Operator Usage

Use the generated project plus the built-in templates and the built-in strategy.

This is suitable for:

- paper trading bots
- Telegram investing copilots
- watchlist scanners
- approval-first operator assistants

### 2. Config-First Product Usage

Use `bot.yaml` to configure:

- watchlist
- default budget
- recommendation universe
- broker
- Telegram
- funds source
- capability flags
- strategy preset
- risk defaults

This is suitable for:

- internal operator deployments
- self-hosted bots
- fast experiments without changing framework code

### 3. Framework Extension Usage

Advanced users can add:

- custom strategies
- custom providers
- custom brokers
- custom reasoning engines
- custom notifier flows

This is suitable for:

- building proprietary copilots
- adding regional brokers
- building verticalized investment assistants

## What The Product Can Be Used To Build

With the current unified-bot layer, users can build:

- Telegram trading assistants
- budget-aware investing copilots
- portfolio and holdings assistants
- watchlist management bots
- approval-first paper trading bots
- replayable operator workflows
- broker-connected research assistants

With additional framework extensions, they can build:

- sector-specific investing copilots
- mutual-fund assistants
- multi-broker operator consoles
- strategy marketplaces and templates
- hosted copilot products

## External Inputs Still Needed For A Fully Shipped Product

The following are not code gaps in the framework itself, but still require external setup:

- Zerodha app redirect URL must point to the framework callback
- live Zerodha login must be completed on the framework-owned runtime
- Railway service/domain mapping must serve this framework service instead of the older platform app
- optional OIDC provider credentials if you want SSO
- optional PyPI trusted publishing or token setup if you want public package publishing

## Final Product Standard

The product should feel like:

- one install
- one setup flow
- one bot
- one runtime
- many capabilities

That is the bar the unified bot layer is now targeting.
