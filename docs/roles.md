# Roles and Permissions

Every user in a project has exactly one role. Roles are stored in the `ProjectRole` model (`api/models/project.py`).

## Roles

| Role | Description |
|------|-------------|
| `owner` | Full control. Typically the project creator. |
| `admin` | Can manage the project and its members, but cannot change another owner's role. |
| `editor` | Can create and edit localization keys and translations; can invite translators. |
| `translator` | Can edit translations only. Cannot manage the project or invite others. |

## Permission Groups

Role checks are centralised as class-level lists on `ProjectRole`, used in ORM filters and view-level guards throughout the codebase.

> **Future improvement:** the current pattern requires each view to manually apply its role filter (`roles__role__in=ProjectRole.change_X_roles`) in the ORM query. A new view that forgets this check silently becomes accessible to all project members. The fix is to introduce a `HasProjectRole` DRF permission class (factory pattern) so the enforcement is declared on the view and cannot be accidentally omitted. This is a non-trivial refactor because several views get their project ID from the request body rather than the URL `pk`, and some views need different role levels per HTTP method.

| Group | Roles included | Used for |
|-------|---------------|----------|
| `change_participants_roles` | owner, admin | View/add/remove members, manage invitations, manage integrations, webhooks, AI provider, import |
| `change_token_roles` | owner, admin, editor | Create/edit/delete localization keys and translations, manage bundles, import strings |
| `change_language_roles` | owner, admin | Add/remove languages, manage scopes |

## Capability Matrix

| Capability | owner | admin | editor | translator |
|------------|:-----:|:-----:|:------:|:----------:|
| View project & members | ✓ | ✓ | ✓ | ✓ |
| Edit translations | ✓ | ✓ | ✓ | ✓ |
| Create / edit / delete keys | ✓ | ✓ | ✓ | — |
| Manage bundles | ✓ | ✓ | ✓ | — |
| Import strings | ✓ | ✓ | ✓ | — |
| Add / remove languages | ✓ | ✓ | — | — |
| Manage scopes | ✓ | ✓ | — | — |
| Add / remove members | ✓ | ✓ | — | — |
| Manage invitations | ✓ | ✓ | — | — |
| Configure integrations | ✓ | ✓ | — | — |
| Configure webhooks | ✓ | ✓ | — | — |
| Configure AI provider | ✓ | ✓ | — | — |
| Change any member's role | ✓ | ✓ | — | — |
| Change an owner's role | ✓ | — | — | — |
| Invite admin / editor / translator | ✓ | ✓ | — | — |
| Invite editor / translator | — | — | ✓ | — |
| Invite translator only | — | — | — | — |

## Invitations

Invitations are single-use tokens with a fixed target role. The role a sender can invite is bounded by their own role:

- **owner** — can invite any role
- **admin** — can invite admin, editor, or translator
- **editor** — can invite editor or translator
- **translator** — cannot invite anyone

## Project Access Tokens

Project access tokens (used by the CLI, Figma plugin, and MCP endpoint) are independent of the role system. Any project member can create tokens for their own account. Each token carries its own permission:

| Token permission | Can read | Can write |
|-----------------|:--------:|:---------:|
| `read` | ✓ | — |
| `write` | ✓ | ✓ |

When a member is removed from a project, all their access tokens for that project are deleted automatically.
