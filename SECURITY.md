# Security Policy

## Reporting

If you discover a security issue, do not open a public GitHub issue with exploit details.

Use a private channel with:

- affected version
- impact summary
- reproduction steps
- suggested mitigation, if known

## Scope

The most security-sensitive areas in this framework are:

- operator authentication
- broker credentials and session storage
- Telegram webhook handling
- approval token lifecycle
- live order submission paths

## Deployment Guidance

- Use Postgres in production
- Keep non-paper execution approval-first
- Rotate broker and bot credentials regularly
- Prefer OIDC or hybrid auth for multi-user deployments
- Restrict Telegram access to an approved chat id
- Do not expose broker secrets in logs or client responses
