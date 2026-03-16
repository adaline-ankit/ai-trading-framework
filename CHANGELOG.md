# Changelog

All notable changes to `ai-trading-framework` are documented in this file.

The format is based on Keep a Changelog and the project follows Semantic Versioning.

## [0.5.0] - 2026-03-17

### Added
- Real unified-bot capability modules for invest, execution, replay, and help flows.
- Broker funds support for paper trading and Zerodha, including wallet-aware investment planning.
- Interactive bot-init wizard and new CLI flows for `start`, `portfolio`, and `help-bot`.
- Product end-state documentation and updated unified-bot checklist/spec alignment docs.
- Additional API routes for product help, portfolio summary, and Zerodha funds.

### Changed
- Routed more Telegram, CLI, and API behavior through the product router so the one-bot runtime is more consistent.
- Expanded bot configuration depth to cover strategy, risk, broker funds source, and Telegram webhook mode.
- Updated quickstart and product docs to reflect the actual end-to-end user flow and remaining external setup dependencies.

## [0.4.0] - 2026-03-17

### Added
- Product-layer foundations for a unified one-bot experience: bot config, starter templates, persistent watchlists, capability routing, and a Telegram/product router.
- New CLI workflows for `init`, `doctor`, `status`, `recommend`, `watchlist`, `connect-telegram`, and `login-zerodha`.
- New API routes for product-style watchlist and recommendation flows.
- Additional end-to-end tests for project scaffolding, local operator status, watchlist state, and unified Telegram routing.

### Changed
- Expanded local package dependencies to support YAML-backed bot configuration and typing stubs in CI/dev.
- Improved the repo docs so the new unified-bot milestone is visible from the README and quickstart flow.

## [0.3.1] - 2026-03-16

### Changed
- Improved the GitHub repository surface with stronger OSS documentation, contributor guides, metadata, and deployment portability docs.
- Hardened CI, Docker, release, and CodeQL workflows and fixed the release workflow secret gating bug.
- Added Docker Compose, Makefile shortcuts, CODEOWNERS, support policy, citation metadata, Dependabot, and issue contact routing.

## [0.3.0] - 2026-03-16

### Added
- Interactive operator dashboard with scan, approval, preview, submit, replay, and history controls.
- Telegram inbound webhook commands and inline callback actions.
- Durable Postgres-backed operator auth and broker session persistence.
- Generic deployment guide, Docker Compose stack, CodeQL, Dependabot, CODEOWNERS, support guide, and citation metadata.

### Changed
- Reframed deployment docs to be deploy-anywhere with Railway as an example.
- Hardened CI, Docker, and release workflows for a more OSS-friendly repository surface.
- Improved README, quickstart, and contributor guidance.

## [0.2.0] - 2026-03-16

### Added
- Approval-first operator runtime, dashboard, Telegram notifier, paper broker, replay, and explainability.

## [0.1.0] - 2026-03-16

### Added
- Initial public extraction of the AI trading framework core, plugin interfaces, examples, docs, and baseline deployment assets.
