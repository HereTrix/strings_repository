# MCP Endpoint

StringsRepository exposes a [Model Context Protocol](https://modelcontextprotocol.io/) server at `/api/mcp`, allowing AI agents and IDE extensions to read and write localization data directly.

## Transport

| Property | Value |
|----------|-------|
| URL | `POST /api/mcp` |
| Protocol version | `2024-11-05` |
| Transport | Streamable HTTP (JSON-RPC 2.0 over plain HTTP) |
| Server name | `strings-repository` |

A `GET /api/mcp` request returns server metadata without authentication.

## Authentication

Use a project access token in the `Access-Token` header (same token used by the CLI and Figma plugin). Tokens are created in the project settings UI.

```
Access-Token: <your-token>
```

Tokens have either **read** or **write** permission. Write-gated tools return an error if called with a read-only token.

## Supported JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `initialize` | Handshake — returns protocol version and capabilities |
| `tools/list` | Returns the full tool catalogue |
| `tools/call` | Invoke a tool by name |
| `notifications/*` | Accepted and silently ignored |

## Tools

### Read-only tools

#### `get_project`
Returns the project linked to the access token.

**Returns:** `{ id, name, description }`

---

#### `get_languages`
Lists all language codes configured for the project.

**Returns:** `{ languages: string[] }`

---

#### `list_tokens`
Lists localization keys with optional filtering and pagination.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `search` | string | — | Filter by key name or translation text |
| `tags` | string | — | Comma-separated tag names |
| `limit` | integer | 50 | Max results (capped at 200) |
| `offset` | integer | 0 | Pagination offset |

**Returns:** `{ count, results: [{ id, token, comment, status, tags }] }`

---

#### `get_token`
Returns a single key with all its translations.

| Argument | Type | Required |
|----------|------|----------|
| `token_key` | string | yes |

**Returns:** `{ id, token, comment, status, tags, translations: [{ language, text, status }] }`

---

#### `search_similar_tokens`
Finds existing keys whose name or translations resemble the given text. Useful for deduplication before creating a new key.

| Argument | Type | Default |
|----------|------|---------|
| `text` | string | — |
| `limit` | integer | 10 (max 50) |

**Returns:** `{ results: [{ token, comment, translations }] }`

---

#### `suggest_token_key`
Derives a key name from source text following common naming conventions (first 5 words, underscored). Checks against a caller-supplied list of already-used keys to avoid collisions.

| Argument | Type | Required |
|----------|------|----------|
| `source_text` | string | yes |
| `existing_tokens` | string[] | no |

**Returns:** `{ suggested_key, rationale }`

---

#### `get_token_naming_patterns`
Analyses a sample of existing keys to infer the project's naming conventions (dot vs. underscore separator, common prefixes).

| Argument | Type | Default |
|----------|------|---------|
| `sample_size` | integer | 50 (max 200) |

**Returns:** `{ separator, dot_separator_count, underscore_separator_count, common_prefixes, examples }`

---

#### `check_glossary`
Checks whether any words or phrases in a source string match project glossary terms.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source_text` | string | yes | String to check |
| `language_code` | string | no | If provided, includes `preferred_translation` for that language |

**Returns:** `{ matches: [{ term, definition, case_sensitive, preferred_translation }] }`

---

#### `suggest_translation`
Returns translation memory suggestions: previously-translated strings with source text similar to `source_text`, translated into the target language. Uses `SequenceMatcher` with a similarity floor of 0.60; returns up to 5 results. Scans up to 500 candidates (random sample when the project exceeds 2 000 translations).

| Argument | Type | Required |
|----------|------|----------|
| `source_text` | string | yes |
| `language_code` | string | yes |

**Returns:** `{ suggestions: [{ token_key, source_text, translation_text, similarity_score }] }`

---

### Write tools (require write permission)

#### `create_token`
Creates a new localization key. Fails if the key already exists.

| Argument | Type | Required |
|----------|------|----------|
| `token_key` | string | yes |
| `comment` | string | no |
| `tags` | string[] | no |

**Returns:** `{ id, token, comment, status, tags }`

---

#### `set_translation`
Creates or updates a translation for a key in a given language.

| Argument | Type | Required |
|----------|------|----------|
| `token_key` | string | yes |
| `language_code` | string | yes |
| `text` | string | yes |

**Returns:** `{ token, language, text }`

---

#### `batch_create_tokens`
Creates multiple keys (with optional default-language translations) in one call. Already-existing keys are skipped rather than errored.

| Argument | Type | Required |
|----------|------|----------|
| `entries` | array of `{ token_key, comment?, language_code?, text? }` | yes |

**Returns:** `{ created: string[], skipped: string[], failed: [{ token_key, error }] }`

---

#### `verify_string`
Runs AI quality verification on a single source/translation pair. Requires the project to have an AI provider configured. Response time depends on the provider (typically several seconds).

Available checks: `semantic_accuracy`, `placeholder_preservation`, `omissions_additions`, `grammar_target`, `tone_match`. Defaults to all checks when `checks` is omitted.

| Argument | Type | Required |
|----------|------|----------|
| `source_text` | string | yes |
| `translation_text` | string | yes |
| `language_code` | string | yes |
| `checks` | string[] | no |

**Returns:** `{ severity: "ok" \| "warning" \| "error", suggestion, reason }`

## Error Codes

| Code | Meaning |
|------|---------|
| `-32700` | Parse error — request body is not valid JSON |
| `-32601` | Method or tool not found |
| `-32603` | Internal error (item not found, no AI provider, or unhandled exception) |
