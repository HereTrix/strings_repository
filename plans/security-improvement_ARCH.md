# Security Improvement — Architecture

## Stack Context

Django 6.0 / DRF 3.17 monolith with React 18 + TypeScript SPA. Knox token auth for the web
UI/API; `ProjectAccessToken` manual validation for CLI/Figma/MCP. SQLite default, Postgres/MySQL
supported. No Celery; background work done in daemon threads.

---

## Existing Code Map

| File | Current role | How this feature touches it |
|------|-------------|----------------------------|
| `repository/settings.py` | All app config | VULN-4 DEBUG, VULN-5 ALLOWED_HOSTS, VULN-6 CSRF, VULN-7 CORS, ENH-1 OTP apps/middleware |
| `repository/app_env.py` | `env_value(key)` helper | Needs optional `default` parameter to allow safe absent-key access |
| `api/views/roles.py` | Token generation, access token CRUD, participant mgmt | VULN-1 (generate_token), VULN-8 (delete_expired_tokens) |
| `api/views/plugin.py` | CLI/Figma plugin endpoints | VULN-8 (validate_access_token) |
| `api/dispatcher.py` | Webhook delivery in daemon threads | VULN-2 (SSRF before urlopen) |
| `api/translation_providers/generic_ai.py` | GenericAI HTTP calls | VULN-3 (SSRF before urlopen) |
| `api/models/project.py` | Project, ProjectRole, Invitation, ProjectAccessToken | ENH-1 (require_2fa on Project), VULN-1 (max_length on Invitation.code and ProjectAccessToken.token) |
| `api/models/users.py` | UserProfile (1 field) | ENH-1 (add TwoFAVerification model) |
| `api/views/generic.py` | Login (SignInAPI), signup, profile | ENH-1 (202 branch in SignInAPI) |
| `api/views/project.py` | Project CRUD, list, languages, tokens | ENH-1 (PATCH for require_2fa via ProjectAPI) |
| `api/serializers/project.py` | CreateProjectSerializer, ProjectDetailSerializer, ProjectSerializer | ENH-1 (require_2fa in all three) |
| `api/urls.py` | URL routing | ENH-1 (new 2fa/* paths, project PATCH) |
| `api/tests/helpers.py` | make_project, make_access_token, etc. | make_project needs optional require_2fa |
| `api/admin.py` | Admin registrations | ENH-1 (register TOTP device admin) |
| `webui/src/types/Project.ts` | Project interface | ENH-1 (add require_2fa field) |
| `webui/src/components/pages/LoginPage.tsx` | Login form | ENH-1 (handle 202, navigate to TOTP step) |
| `webui/src/components/Project/AddProjectPage.tsx` | Project creation modal | ENH-1 (require_2fa checkbox) |
| `webui/src/components/Project/ProjectInfo.tsx` | Project settings panel | ENH-1 (require_2fa toggle, owner-only) |
| `webui/src/components/Profile/ProfilePage.tsx` | Profile sections | ENH-1 (add 2FA setup section) |
| `webui/src/utils/network.tsx` | `http()` fetch utility | No changes needed; 202 already treated as ok by the utility |

---

## New Code Map

### Backend

**`api/url_validation.py`** — shared SSRF guard
```python
def validate_url_for_outbound(url: str) -> None:
    """Raises ValueError if url resolves to a private/loopback/link-local address."""
```
Blocked networks: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`,
`169.254.0.0/16`, `::1/128`, `fc00::/7` (IPv6 ULA), `fe80::/10` (IPv6 link-local).
Resolves via `socket.getaddrinfo` (returns all A/AAAA records), rejects if any resolved IP
falls in a blocked network.

**`api/permissions.py`** — DRF permission classes
```python
class ProjectTwoFAPermission(BasePermission):
    """
    Added to REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES.
    For any view with pk in kwargs: if project.require_2fa is True, the requesting
    user must have a confirmed TOTP device AND their Knox token must have a
    TwoFAVerification record. Returns HTTP 403 with detail message otherwise.
    Skips silently for views without pk (login, signup, 2fa endpoints, etc.).
    """
```

**`api/views/two_fa.py`** — four TOTP endpoints
```python
class TwoFASetupAPI(generics.GenericAPIView):
    """POST /api/2fa/setup — create pending TOTPDevice + 10 StaticTokens"""

class TwoFAVerifyAPI(generics.GenericAPIView):
    """POST /api/2fa/verify — confirm pending device"""

class TwoFADeleteAPI(generics.GenericAPIView):
    """DELETE /api/2fa — deactivate device (requires current code)"""

class TwoFALoginAPI(generics.GenericAPIView):
    """POST /api/2fa/login — second-step login, creates TwoFAVerification"""
```
All use `permission_classes = [IsAuthenticated]`. `TwoFALoginAPI` additionally accepts
an unverified Knox token (user with active TOTP device who got 202 at login).

**`api/migrations/0018_security_improvements.py`**
- `Project.require_2fa = BooleanField(default=False)` (safe; nullable not needed since default provided)
- `Invitation.code` max_length: 16 → 64
- `ProjectAccessToken.token` max_length: 16 → 64
- `TwoFAVerification` model

### Frontend

**`webui/src/components/Auth/TwoFALoginPage.tsx`**
New route at `/2fa-login`. Shown after `LoginPage` receives 202. Accepts 6-digit TOTP
code (or backup code), calls `POST /api/2fa/login`, stores token and navigates to `/`.

**`webui/src/components/Profile/TwoFASetupPage.tsx`**
New `CollapseSection` inside `ProfilePage`. Manages setup/verify flow and shows backup
codes on first setup. Shows "Disable 2FA" with code confirmation when device is active.

---

## Reuse Decisions

- **`api/views/helper.py:error_response()`** — reuse in new 2FA views for consistent error shape.
- **`api/tests/helpers.py:authed_client()`** — reuse in all new tests.
- **`CollapseSection`** — reuse in ProfilePage for 2FA section, matching existing Profile pattern.
- **`django_otp.plugins.otp_static.StaticDevice` + `StaticToken`** — use for backup codes instead
  of a custom model. Provides single-use enforcement and hashed storage out of the box.
- **`django_otp.plugins.otp_totp.TOTPDevice`** — the primary TOTP device model.
- **`django_otp.utils.default_device(user)`** — reuse to check if user has active device.
- **`qrcode` library** — generate QR code PNG in-memory, return as base64 in setup response.
- **`react-hook-form`** — already used in LoginPage and AddProjectPage; reuse in new 2FA forms.
- **`react-bootstrap` `Form.Check` switch** — for `require_2fa` toggles, matching existing UI patterns.

---

## Refactoring Required

### 1. `repository/app_env.py` — add optional default
`env_value(key)` raises `ImproperlyConfigured` when a key is missing from `.env`. The VULN-4
and VULN-5 fixes read `DEBUG` and need to handle its absence gracefully.

```python
def env_value(key, default=None):
    if use_env:
        return env(key, default=default)
    else:
        return env.get(key, default)
```

This must be done before touching `settings.py`; otherwise the DEBUG and ALLOWED_HOSTS
changes will raise on a fresh install that has no `.env` file.

### 2. `repository/settings.py` — fix duplicate `CommonMiddleware`
`'django.middleware.common.CommonMiddleware'` appears at positions 2 and 6. Remove the first
occurrence (before `SecurityMiddleware`). Clean this up as part of the CSRF middleware insertion
task so the final MIDDLEWARE list is canonical.

### 3. `api/models/project.py` — `ProjectAccessToken.token` and `Invitation.code` max_length
Both are `CharField(max_length=16)`. `secrets.token_urlsafe(16)` returns ~22 chars; using a
safe margin, bump both to `max_length=64`. This requires migration 0018. Do this before
implementing VULN-1 so the model is ready when `generate_token` starts returning longer strings.

### 4. `api/views/project.py` — extend `ProjectAPI` to support PATCH
`ProjectAPI` is currently `RetrieveDestroyAPIView`. Change base class to
`RetrieveUpdateDestroyAPIView`, add a `ProjectUpdateSerializer` (or extend
`ProjectDetailSerializer` to accept `require_2fa` on write), and restrict `require_2fa`
changes to owner role.

---

## Interface / Contract Definitions

### API contracts

**`POST /api/login`** — modified response
```
# 200 (no active TOTP device — unchanged)
{ "user": {...}, "token": "<knox>", "expired": "<iso>" }

# 202 (active TOTP device present — new)
{ "2fa_required": true, "token": "<partial-knox>" }
```

**`POST /api/2fa/setup`**
```
Request:  {} (empty — authenticated user inferred from Knox token)
Response 200: {
  "otpauth_uri": "otpauth://totp/...",
  "qr_code": "<base64 PNG>",
  "backup_codes": ["abc123", "def456", ...]  // 10 codes, shown once only
}
Response 400: { "error": "2FA already active; disable first" }
```

**`POST /api/2fa/verify`**
```
Request:  { "code": "123456" }
Response 200: {}
Response 400: { "error": "Invalid code" }
Response 404: { "error": "No pending 2FA device" }
```

**`DELETE /api/2fa`**
```
Request:  { "code": "123456" }  // TOTP code or backup code
Response 200: {}
Response 400: { "error": "Invalid code" }
```

**`POST /api/2fa/login`**
```
Request:  { "code": "123456" }  // TOTP code or backup code
            Authorization: Token <partial-knox>
Response 200: { "user": {...}, "token": "<same-knox>", "expired": "<iso>" }
Response 403: { "error": "Invalid code" }
```

**`GET /api/project/<pk>` — shape change**
```
// ProjectDetailSerializer gains require_2fa
{ "id": 1, "name": "...", "description": "...", "languages": [...],
  "role": "owner", "require_2fa": false }
```

**`POST /api/project`** — gains optional field
```
Request:  { "name": "...", "description": "...", "require_2fa": false }
```

**`PATCH /api/project/<pk>`** — new
```
Request:  { "require_2fa": true }  // owner only
Response 200: { ...ProjectDetail shape... }
Response 403: { "error": "Not allowed" }
```

**403 from project 2FA gate**
```json
{ "detail": "This project requires 2FA. Enable two-factor authentication to access it." }
```

### TypeScript types

```typescript
// webui/src/types/Project.ts — add field
interface Project {
  id: number
  name: string
  description: string | null
  languages: Language[]
  role: ProjectRole
  require_2fa: boolean  // NEW
}

// webui/src/types/TwoFA.ts — new file
export interface TwoFASetupResponse {
  otpauth_uri: string
  qr_code: string        // base64 PNG
  backup_codes: string[]
}
export interface TwoFALoginResponse {
  user: Profile
  token: string
  expired: string
}
```

### Python models

```python
# api/models/users.py — new model
class TwoFAVerification(models.Model):
    token_key = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        # No FK to Knox AuthToken (different app); orphans are harmless since
        # Knox's own auth will reject an expired/deleted token before this is checked.
        ordering = ['-created_at']

# api/models/project.py — Project model addition
class Project(models.Model):
    ...
    require_2fa = models.BooleanField(default=False)
```

---

## Risk Notes

### R1 — `env_value` raises on missing keys (blocks VULN-4/5 fix)
**Risk:** The django-environ path calls `env(key)` which raises `ImproperlyConfigured` when a
key is absent from `.env`. Without the `default` param refactor, setting
`DEBUG = env_value('DEBUG', default='false') == 'true'` will crash on existing installs
that have no `DEBUG` in their `.env`.
**Mitigation:** Do the `app_env.py` refactor first (see Refactoring Required §1).

### R2 — max_length migration must precede VULN-1 token generation change
**Risk:** If `generate_token()` is updated before migration 0018 runs, new tokens (~22 chars)
will be rejected by the DB with a truncation/constraint error.
**Mitigation:** Migration 0018 must be applied before any code change to `generate_token`.
In practice: ship migration first in the same deploy, or order the tasks so migration
precedes the view change.

### R3 — `ProjectTwoFAPermission` in DEFAULT_PERMISSION_CLASSES vs views with explicit `permission_classes`
**Risk:** DRF views that set `permission_classes = [AllowAny]` (plugin views, signup, login)
override `DEFAULT_PERMISSION_CLASSES` entirely, bypassing `ProjectTwoFAPermission`. This is
correct for plugin/auth views but would be a silent gap if any future project-scoped view
accidentally uses `AllowAny`.
**Mitigation:** Document this in the permission class docstring. Plugin views are intentionally
exempt (they use `ProjectAccessToken` auth, not Knox). `ProjectTwoFAPermission.has_permission`
also short-circuits on `pk=None`, so it is a no-op on all non-project-scoped views.

### R4 — TwoFAVerification orphan accumulation
**Risk:** `TwoFAVerification` records for expired/revoked Knox tokens are never deleted
(no FK cascade possible across apps). Over years they accumulate.
**Mitigation:** Add a management command `prune_2fa_verifications` (callable via cron or
manually) that bulk-deletes records whose `token_key` doesn't appear in Knox's
`AuthToken` table. Not required for launch — orphans are functionally harmless.

### R5 — CSRF middleware + Django admin session vs Knox token
**Risk:** Adding `CsrfViewMiddleware` could in theory require the React SPA to include CSRF
tokens. In practice it will not: DRF's Knox uses `TokenAuthentication`, which is
header-based and explicitly excluded from CSRF enforcement by DRF's `enforce_csrf` logic.
Only `SessionAuthentication` triggers CSRF in DRF.
**Mitigation:** Verify at test time that all existing API tests pass after adding the middleware.
The Django admin panel (which uses session auth) is the only surface that gains real CSRF
protection.

### R6 — `ALLOWED_HOSTS` startup warning in settings.py
**Risk:** Python's `logging` module is not configured at the point `settings.py` executes.
`logger.warning(...)` would silently drop the message.
**Mitigation:** Use `import warnings; warnings.warn(...)` (Python built-in, available before
logging setup) to emit the startup warning when `ALLOWED_HOSTS` env var is absent.

### R7 — 2FA login route conflict with PrivateRoute
**Risk:** The `/2fa-login` route must NOT be wrapped in `<RequireAuth>`. If it were, a user
with a partial Knox token (202 state) would be redirected away from it on page load.
**Mitigation:** Register `/2fa-login` as a public route in `App.tsx` (like `/login` and
`/activate` currently are).

### R8 — `django-otp` `OTPMiddleware` placement
**Risk:** `OTPMiddleware` must be placed after `AuthenticationMiddleware` in `MIDDLEWARE`.
Placing it before will result in `AttributeError: 'AnonymousUser' object has no attribute
'otp_device_set'`.
**Mitigation:** `OTPMiddleware` is placed immediately after `AuthenticationMiddleware` in the
final middleware list (see settings.py changes).

---

## Assumptions

1. **`ProjectUpdateSerializer`:** Rather than creating a new serializer, `ProjectDetailSerializer`
   will be extended with `require_2fa` as a writable field with an owner-only write validator.
   This avoids an extra serializer class.

2. **`TwoFALoginAPI` token handling:** On successful TOTP verification, the endpoint creates a
   `TwoFAVerification` record for the existing Knox token key and returns the same token with the
   full login response shape (200 with `{user, token, expired}`). The client updates its stored
   token state. No new Knox token is issued to avoid forcing the client to rotate storage.

3. **`otp_static` for backup codes:** `django-otp-static` (`django_otp.plugins.otp_static`) is
   added alongside `otp_totp`. Each `StaticDevice` holds up to 10 `StaticToken` objects.
   Setup creates one `StaticDevice` per user with 10 tokens. The plaintext codes are returned
   once at setup; after that only hashed values remain.

4. **`ProjectTwoFAPermission` as global default:** Added to `DEFAULT_PERMISSION_CLASSES`
   alongside `IsAuthenticated`. This is the only point of project 2FA enforcement — no mixin
   or per-view changes required for existing project-scoped views.

5. **No `require_2fa` changes via CLI/Figma/MCP:** `ProjectAccessToken`-authenticated plugin
   views bypass `DEFAULT_PERMISSION_CLASSES` (they use `AllowAny`). Changing `require_2fa`
   through those channels is out of scope. Only Knox-authenticated admin/owner users can toggle it.

6. **CORS null removal makes `CORS_ALLOWED_ORIGINS` potentially empty:** After removing `'null'`,
   the list `['null']` becomes `[]`. An empty list is valid for `django-cors-headers` and means
   no cross-origin requests are allowed. This is correct if no legitimate CORS origins exist.
   If a real origin needs to be added in future, it should be done via env var.
   Recommendation: replace the hardcoded list with env-driven config:
   `CORS_ALLOWED_ORIGINS = [o for o in env_value('CORS_ORIGINS', default='').split(',') if o]`
