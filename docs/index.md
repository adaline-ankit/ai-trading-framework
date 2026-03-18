# AI Trading Framework

`ai-trading-framework` is an approval-first framework for building AI trading copilots, Telegram trading assistants, and broker-connected operator runtimes.

## What It Gives You

- one-bot product runtime with Telegram, API, CLI, and dashboard surfaces
- approval-first execution for non-paper trading
- replay, explainability, and risk controls
- paper trading and Zerodha integration
- project scaffolding through `ai-trading init`
- product-oriented bot config and templates

## Start Here

- [Quickstart](quickstart.md)
- [Architecture](architecture.md)
- [Build With The Framework](build_with_framework.md)
- [Build Your Bot In 10 Minutes](build_your_bot_in_10_minutes.md)
- [Unified Bot Product Spec](unified_bot_product_spec.md)
- [Unified Bot Checklist](unified_bot_checklist.md)
- [Unified Bot End State](unified_bot_end_state.md)

## Main Product Flow

1. install the package
2. run `ai-trading init my-bot`
3. connect Telegram and broker
4. start the runtime
5. use one smart bot for portfolio, watchlist, recommendation, invest, approval, execution, and replay

## Current Remaining External Inputs

The codebase is strong, but a few external steps may still be needed in a real deployment:

- update the Zerodha redirect URL to the framework callback
- complete a live Zerodha login on the framework runtime
- fix Railway service/domain mapping if the domain still points to the older platform app
- optionally configure OIDC and PyPI publishing
