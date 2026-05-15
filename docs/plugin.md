# Figma Plugin API

The Figma plugin communicates with the server via project access tokens passed in the `Access-Token` header. Tokens are created in the project settings UI and have either **read** or **write** permission.

## `GET /api/plugin/tags`

Returns the available tags and scopes for the project so the plugin can populate its filter UI.

```json
{
  "tags": ["ios", "android", "onboarding"],
  "scopes": ["Home", "Settings", "Onboarding"]
}
```

Either array can be empty — the plugin hides the filter row when both are empty.

## `POST /api/plugin/pull`

Fetches translations for a list of localization keys. Accepts two optional filters:

| Field    | Type              | Description                                                         |
| -------- | ----------------- | ------------------------------------------------------------------- |
| `code`   | string (required) | Language code to fetch                                              |
| `tokens` | array (required)  | List of localization keys to fetch                                  |
| `tags`   | array             | If present, only return tokens that have **all** of the listed tags |
| `scope`  | string            | If present, only return tokens that belong to that scope            |

Filters are AND'd together. Omitting a filter means no restriction on that dimension.

Each item in the response array includes:

```json
[
  {
    "token": "home.title",
    "translation": "Willkommen",
    "tags": ["ios", "onboarding"],
    "scope": "Home"
  }
]
```

`tags` and `scope` are always present but may be an empty list or `null` respectively when the token has no tags or belongs to no scope.

## `POST /api/plugin/context`

Uploads a context screenshot for a scope. The request is multipart form data:

| Field   | Type   | Description                                     |
| ------- | ------ | ----------------------------------------------- |
| `scope` | string | Figma frame name — used as the scope identifier |
| `image` | file   | PNG exported at 2× scale                        |

The plugin sends one request per unique parent frame after every successful push. Images are appended — existing ones are not removed. The scope is created automatically if it does not exist yet.

Requires a **write** access token.

The scope name comes directly from the Figma frame name, so if your team names frames consistently (e.g. "Onboarding / Step 1", "Settings / Profile") the context images will map naturally to scopes in the platform.
