# Public Launch Checklist

This checklist is the bar for calling `ai-trading-framework` publicly launch ready.

## Product

- [x] Interactive operator dashboard
- [x] Approval-first recommendation review flow
- [x] Paper trading preview and execution flow
- [x] Telegram webhook, command handling, and inline approval callbacks
- [x] Replay and explainability views
- [x] Runtime history reset for demos and staging cleanup
- [ ] Fully verified live Zerodha submit and status reconciliation on the production account
- [ ] Optional OIDC setup for multi-user operator access

## Framework

- [x] Strategy SDK
- [x] Plugin interfaces for providers, brokers, notifiers, risk policies, and LLMs
- [x] Event-driven workflow core
- [x] Risk policy chain
- [x] Replay engine
- [x] Benchmark service
- [x] CLI and FastAPI runtime

## Deployment

- [x] Railway deployment config
- [x] Docker image build
- [x] Railway Postgres-backed runtime state
- [x] Production dashboard deployed
- [x] Telegram webhook configured to production
- [ ] Custom domain, if desired

## Trust And Safety

- [x] Human approval required for non-paper execution
- [x] HOLD recommendations blocked from execution
- [x] Approval token lifecycle enforced
- [x] Broker auth state persisted in Postgres
- [x] Operator auth sessions persisted in Postgres
- [x] Password hashes removed from API responses
- [ ] External security review and credential rotation runbook

## Open Source Readiness

- [x] README
- [x] Quickstart
- [x] Architecture docs
- [x] Telegram docs
- [x] Zerodha docs
- [x] Railway docs
- [x] Contributing guide
- [x] Code of Conduct
- [x] Security policy
- [x] Issue templates
- [x] PR template
- [ ] PyPI publish flow enabled with package token

## Growth Readiness

- [x] Production demo path: scan -> explain -> approve -> execute -> replay
- [x] Telegram-first operator UX
- [x] GitHub Actions CI
- [x] Release tags
- [ ] Launch video / GIF
- [ ] Product Hunt assets
- [ ] Blog post / docs walkthrough
- [ ] Additional broker and data-provider examples

## What Still Requires Human Input

- Zerodha Kite app redirect URL must point to:
  - `https://ai-trading-framework-production.up.railway.app/v1/brokers/zerodha/callback`
- Zerodha live account login must be completed once on production.
- If switching to OIDC:
  - provider choice
  - discovery URL
  - client ID
  - client secret
  - allowed domains or emails
