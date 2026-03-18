# Build Your Bot In 10 Minutes

This is the fastest path from install to a working approval-first trading copilot.

## What You Will End Up With

At the end of this flow you will have:

- a local bot project with `bot.yaml`
- a running API and dashboard
- a Telegram-connected bot
- paper-trading recommendations, approvals, previews, and submissions
- replay and explainability for every decision

## 1. Install The Framework

```bash
uv sync --extra dev
```

If you want the local docs site too:

```bash
uv sync --extra docs
```

## 2. Scaffold A Bot

```bash
uv run ai-trading init my-bot --template paper-sandbox
cd my-bot
cp .env.example .env
```

This creates:

```text
my-bot/
  bot.yaml
  .env.example
  README.md
  strategies/
  prompts/
  state/
```

## 3. Validate The Setup

```bash
uv run ai-trading doctor
uv run ai-trading status
```

You should see:

- bot name
- broker mode
- watchlist
- funds summary
- config validation

## 4. Start In Safe Paper Mode

```bash
uv run ai-trading start
```

Or run the API directly:

```bash
uv run ai-trading run --reload
```

Then open the dashboard:

```text
http://127.0.0.1:8000
```

## 5. Generate Your First Ideas

CLI:

```bash
uv run ai-trading recommend
uv run ai-trading invest 25000 INFY TCS SBIN --broker PAPER
```

API:

```bash
curl http://127.0.0.1:8000/v1/recommend
curl -X POST http://127.0.0.1:8000/v1/investment-plan \
  -H "content-type: application/json" \
  -d '{"budget":25000,"symbols":["INFY","TCS","SBIN"],"broker":"PAPER"}'
```

Dashboard:

- run a scan
- review the recommendation card
- inspect the planner output
- review watchlist and funds

## 6. Connect Telegram

Add these to `.env`:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_DEFAULT_CHAT_ID=...
TELEGRAM_WEBHOOK_SECRET=...
PUBLIC_BASE_URL=https://your-host-or-tunnel-url
```

Then configure the webhook:

```bash
uv run ai-trading connect-telegram
```

Useful Telegram commands:

- `/help`
- `/portfolio`
- `/watchlist add INFY`
- `/recommend`
- `/invest 25000 INFY TCS SBIN PAPER`
- `/invest wallet INFY TCS PAPER`
- `/why <recommendation_id>`
- `/risk <recommendation_id>`
- `/approve <recommendation_id>`
- `/preview <recommendation_id> PAPER 1`
- `/submit <recommendation_id> PAPER 1`
- `/replay <run_id>`

## 7. Connect Zerodha Later

Stay in paper mode until the workflow feels right.

When you are ready:

```bash
uv run ai-trading login-zerodha
```

Then complete the Zerodha login flow in the browser.

## 8. What This Already Gives You

Without writing custom code, you can already use the product as:

- a Telegram trading copilot
- a watchlist scanner
- a budget-aware investment assistant
- a replayable paper-trading operator console

## 9. What To Customize Next

If you want your own edge, customize:

- `bot.yaml` for broker, watchlist, budget defaults, and enabled capabilities
- `strategies/` for custom strategy logic
- provider and reasoning plugins if you need non-default integrations

## 10. Production Path

When the local flow works:

1. move from SQLite to Postgres
2. deploy with Docker or Railway
3. connect Telegram on the hosted URL
4. connect Zerodha
5. verify approval, preview, and replay before live execution

## Recommended First Real Use Case

The cleanest first product flow is:

1. start with a watchlist of 5 to 10 symbols
2. run `/recommend` every morning
3. use `/invest <amount>` for budget-aware suggestions
4. only approve trades you understand from `/why` and `/risk`
5. use replay after each run to tune the bot
