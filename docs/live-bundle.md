# Live Bundle Serving

Live bundle serving exposes a project's currently **live** bundle (the bundle marked active — see [Translation Bundles](bundles.md)) over a public, tokenized HTTP API, so client applications (mobile apps, backend services) can fetch translations directly at runtime instead of a human distributing export files manually.

"Live" and "active" are the same thing — activating a bundle in the Bundles tab is what makes it the one served here. There is no separate flag to manage.

## Enabling live bundle serving

Live bundle serving is configured per project in **Project → Info → Live Bundle**.

| Action | Required role |
|--------|---------------|
| View whether it's enabled | any project member |
| View the access token | owner, admin, editor |
| Enable / disable | owner, admin |
| Regenerate the access token | owner, admin |
| Mark a bundle as live (activate it) | owner, admin |

Enabling the feature generates a dedicated access token, separate from the general-purpose [project access tokens](roles.md#project-access-tokens) used by the CLI, Figma plugin, and MCP endpoint. This token authenticates **only** against the two live bundle endpoints below — it cannot be used to call any other API.

Disabling the feature immediately invalidates the token. Regenerating it invalidates the previous value with no grace period.

## `GET /api/live-bundle/version`

Header: `Access-Token: <live-bundle-token>` — the project is resolved from the token itself, so no project ID appears in the URL.

Returns the identifier of the project's current live bundle:

```json
{
  "version_name": "v3",
  "created_at": "2026-07-01T12:00:00Z"
}
```

If no bundle has ever been activated for the project, returns `{}` (not an error) with `200 OK`.

| Condition | Response |
|-----------|----------|
| Missing token | `403` |
| Invalid, expired, or disabled-project token | `403` |
| No active bundle | `200`, `{}` |
| Active bundle exists | `200`, version info |

## `GET /api/live-bundle/content`

Header: `Access-Token: <live-bundle-token>`.

| Query param | Type | Description |
|-------------|------|--------------|
| `version_name` | string, optional | Conditional-fetch hint — see below |
| `type` | string, optional | Any [supported export format](../README.md#supported-file-formats); defaults to `json` |
| `codes` | string, optional | Comma-separated language codes (e.g. `EN,DE`); defaults to all project languages |
| `tags` | string, optional | Comma-separated tags — only tokens carrying **all** listed tags are returned |
| `scope` | number, optional | Scope ID — only tokens in that scope are returned |

### Conditional fetch (`version_name`)

There is only ever one servable version — the current live bundle — so `version_name` is a freshness hint, not a strict lookup key:

| `version_name` | Behavior |
|-----------------|----------|
| omitted | Full content returned, current version communicated via `X-Bundle-Version` response header |
| matches current live bundle | `204 No Content` — your cached copy is already current |
| stale or unknown | Full content returned for the **actual** current bundle (never `404` for a stale value) — self-heals a client stuck on an old version without a separate versions call |

`X-Bundle-Version` is percent-encoded (bundle version names are free-form project data); decode it with your platform's URL-decode function.

### Filtering

`tags` and `scope` narrow the returned content — useful when a mobile app only needs strings tagged `mobile`, or a backend service only needs strings in a specific microservice's scope. Filters are ANDed; an unknown tag or scope simply yields an empty result, not an error.

### Caching

Generated content is cached to disk per unique (bundle version, format, language selection, tag filter, scope filter) combination, so repeated requests — e.g. many app instances polling the same filtered view — don't regenerate content from the database each time. The cache is automatically bypassed once a different bundle becomes the live one.

| Condition | Response |
|-----------|----------|
| Missing/invalid token | `403` |
| No bundle ever activated | `404` |
| Unsupported `type` | `400` |
| Success | `200`, file content, `Content-Type` per format, `X-Bundle-Version` header |

There is no `Content-Disposition` header — this is an API response for a client application, not a browser file download.

## Example

```bash
# Check whether a client's cached copy is stale
curl -H "Access-Token: $LIVE_BUNDLE_TOKEN" \
  https://your-instance/api/live-bundle/version

# Fetch mobile-tagged strings as JSON, only if newer than v3
curl -i -H "Access-Token: $LIVE_BUNDLE_TOKEN" \
  "https://your-instance/api/live-bundle/content?tags=mobile&version_name=v3"
```
