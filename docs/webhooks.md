# Webhooks

Webhooks allow external services to receive real-time notifications when events occur in a project.

## Configuration

Each webhook endpoint is configured with:

* **URL** — the destination endpoint (stored encrypted at rest)
* **Events** — one or more event types to subscribe to
* **Auth token** (optional) — sent as `Authorization: Bearer <token>` (stored encrypted at rest)
* **Template** (optional) — a Jinja-style text template for the payload body (e.g. for Slack/Teams integrations)
* **Signing secret** — auto-generated HMAC-SHA256 secret sent in the `X-Signature` header for payload verification

## Supported Events

| Event                        | Triggered when                               |
| ---------------------------- | -------------------------------------------- |
| `translation.created`        | A new translation is added                   |
| `translation.updated`        | A translation value is changed               |
| `translation.status_changed` | A translation status changes                 |
| `token.created`              | A new string key is created                  |
| `token.deleted`              | A string key is deleted                      |
| `token.status_changed`       | A string key status changes                  |
| `language.added`             | A language is added to the project           |
| `language.removed`           | A language is removed from the project       |
| `import.completed`           | A file import completes                      |
| `member.invited`             | A team member is invited                     |
| `member.role_changed`        | A team member's role is changed              |
| `verification.completed`     | An AI verification job finishes (any status) |
