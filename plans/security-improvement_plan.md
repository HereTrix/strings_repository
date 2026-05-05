# Security Improvement — Implementation Plan

## Context

Address all 9 findings from the 2026-05-02 security audit of StringsRepository (6 HIGH, 2
MEDIUM, 1 enhancement). Work spans: hardening Django settings, replacing a weak PRNG, adding
SSRF guards to outbound HTTP calls, fixing timezone-naive datetime comparisons, and implementing
full TOTP 2FA with project-level enforcement. See `plans/security-improvement_BA.md` for
acceptance criteria and `plans/security-improvement_ARCH.md` for file-level design decisions.

## Stack

Django 6.0 / DRF 3.17 backend (`api/` app) + React 18 / TypeScript SPA (`webui/src/`).
Knox token auth for the web UI. Tests: `python manage.py test api`. Frontend uses
`react-hook-form`, `react-bootstrap`, `react-router-dom`.

## Assumptions

1. **Backup codes use a custom `BackupCode` model** (not `django_otp.plugins.otp_static`).
   `otp_static.StaticToken` stores tokens in plaintext by default, conflicting with the BA
   requirement for hashed storage. A custom model with SHA-256 hashing is simpler and correct.
   `otp_static` is therefore NOT added to INSTALLED_APPS.

2. **`POST /api/2fa/login` response omits the token field.** Knox does not store the plaintext
   token after creation — only a hash. The client already holds the token from the 202 login
   response. The 2FA login response returns `{user, expired}` only; the client uses the stored
   token without needing to re-receive it.

3. **On 202 login, the partial Knox token is stored to `localStorage` immediately.** The
   `TwoFALoginPage` then calls `/api/2fa/login` using the normal auth header (read from
   localStorage). This avoids passing tokens through route state and handles page refresh cleanly.

4. **`CORS_ALLOWED_ORIGINS` becomes env-driven.** After removing `'null'`, the list is empty
   by default. The setting is replaced with
   `[o for o in env_value('CORS_ORIGINS', default='').split(',') if o]`.

---

## Tasks

---

### T1 — Refactor `app_env.py` to support optional defaults

**Goal:** Add an optional `default` parameter to `env_value()` so settings.py can safely read
absent env vars without raising `ImproperlyConfigured`.

**Files:**
- `repository/app_env.py` — modify

**Details:**
Change `env_value(key)` to `env_value(key, default=None)`.

When using the django-environ path (`use_env=True`), call `env(key, default=default)` instead
of `env(key)`. The `django-environ` `Env.__call__` accepts a `default` keyword argument.

When using the `os.environ` path (`use_env=False`), call `env.get(key, default)` (already
supports a default, just pass it through).

Final function:
```python
def env_value(key, default=None):
    if use_env:
        return env(key, default=default)
    else:
        return env.get(key, default)
```

No other files change in this task.

**Depends on:** none

**Done when:**
- Calling `env_value('NONEXISTENT_KEY')` with a `.env` file present returns `None` instead
  of raising.
- Calling `env_value('NONEXISTENT_KEY', default='fallback')` returns `'fallback'`.
- Existing callers of `env_value` that pass no default continue to work (default=None is
  backward-compatible with the previous always-returns-a-value-or-raises behavior).

**Status: done**

---

### T2 — Harden settings: DEBUG, ALLOWED_HOSTS, CSRF, CORS, MIDDLEWARE cleanup

**Goal:** Fix VULN-4, VULN-5, VULN-6, VULN-7 in `repository/settings.py` in one pass.

**Files:**
- `repository/settings.py` — modify

**Details:**

**VULN-4 — DEBUG:**
Replace `DEBUG = True` (line 27) with:
```python
import warnings
DEBUG = env_value('DEBUG', default='false').lower() == 'true'
```
The `import warnings` goes at the top of the file with the other imports.

**VULN-5 — ALLOWED_HOSTS:**
Replace the existing ALLOWED_HOSTS block:
```python
allowed = env_value('ALLOWED_HOSTS')
if allowed:
    ALLOWED_HOSTS = allowed.split(',')
else:
    ALLOWED_HOSTS = ['*']
```
With:
```python
_allowed_hosts_raw = env_value('ALLOWED_HOSTS', default='')
if _allowed_hosts_raw:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(',') if h.strip()]
else:
    warnings.warn(
        "ALLOWED_HOSTS env var is not set. Defaulting to ['localhost', '127.0.0.1']. "
        "Set ALLOWED_HOSTS in production.",
        stacklevel=2,
    )
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
```

**VULN-7 — CORS:**
Replace:
```python
CORS_ALLOWED_ORIGINS = [
    'null'
]
```
With:
```python
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in env_value('CORS_ORIGINS', default='').split(',') if o.strip()
]
```

**VULN-6 — CSRF and MIDDLEWARE cleanup:**
Replace the entire `MIDDLEWARE` list with the following canonical order (removes the duplicate
`CommonMiddleware` and adds `CsrfViewMiddleware` after `SessionMiddleware`):
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```
Note: `OTPMiddleware` will be added in T9. Do NOT add it here.

**Depends on:** T1

**Done when:**
- `settings.DEBUG` is `False` when the `DEBUG` env var is absent.
- `settings.DEBUG` is `True` only when `DEBUG=true` (or `DEBUG=True`, `DEBUG=TRUE`).
- `settings.ALLOWED_HOSTS` equals `['localhost', '127.0.0.1']` when `ALLOWED_HOSTS` env var
  is absent, and a `UserWarning` is emitted.
- `settings.ALLOWED_HOSTS` equals `['app.example.com']` when `ALLOWED_HOSTS=app.example.com`.
- `'django.middleware.csrf.CsrfViewMiddleware'` is in `settings.MIDDLEWARE`.
- `'django.middleware.common.CommonMiddleware'` appears exactly once (or zero times — it was
  removed entirely).
- `'null'` is not in `settings.CORS_ALLOWED_ORIGINS`.
- `CORS_ALLOWED_ORIGINS` is `[]` when `CORS_ORIGINS` env var is absent.

**Status: done**

---

### T3 — Fix VULN-8: timezone-aware datetime comparisons

**Goal:** Replace `datetime.datetime.now()` with `django.utils.timezone.now()` in all token
expiration checks so expired tokens are rejected cleanly rather than causing a 500 crash.

**Files:**
- `api/views/plugin.py` — modify `validate_access_token()`
- `api/views/roles.py` — modify `delete_expired_tokens()`

**Details:**

**`api/views/plugin.py`:**
At the top, replace `import datetime` with `from django.utils import timezone`.

In `validate_access_token()`, replace:
```python
if access.expiration and access.expiration < datetime.datetime.now():
```
with:
```python
if access.expiration and access.expiration < timezone.now():
```

**`api/views/roles.py`:**
At the top, add `from django.utils import timezone` and remove `from datetime import datetime`
(the `datetime` import is only used for `datetime.now()` which is being replaced).

In `delete_expired_tokens()`, replace:
```python
now = datetime.now()
```
with:
```python
now = timezone.now()
```

**Tests** — in `api/tests/views/roles.py` (or create `api/tests/views/plugin.py` if it
doesn't exist), add tests:
- Valid token (no expiration) → passes validation.
- Valid token (expiration in the future, timezone-aware) → passes.
- Expired token (expiration in the past, timezone-aware) → `validate_access_token` returns
  `(None, 403 JsonResponse)`.
- `delete_expired_tokens` with a mix of expired and valid tokens → returns only valid ones
  and the expired ones are purged from DB.

Use `from django.utils import timezone` and `timezone.now() + timedelta(days=-1)` to create
expired tokens in tests.

**Depends on:** none

**Done when:**
- `validate_access_token()` returns HTTP 403 for an expired token (not a 500 TypeError).
- `delete_expired_tokens()` correctly filters out expired tokens without raising.
- All four test scenarios pass.

---

### T4 — Create `api/url_validation.py` SSRF guard utility

**Goal:** Provide a shared `validate_url_for_outbound(url)` function used by both the webhook
dispatcher and the GenericAI provider to block requests to private/internal IP ranges.

**Files:**
- `api/url_validation.py` — create

**Details:**

Create `api/url_validation.py` with the following content:

```python
import ipaddress
import socket
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


def validate_url_for_outbound(url: str) -> None:
    """
    Raises ValueError if the URL should not be fetched due to SSRF risk.
    Checks: scheme must be http or https; hostname must resolve to a public IP.
    All resolved addresses (A and AAAA) are checked; rejects if any is private.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme!r}. Only http/https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname {hostname!r}: {e}") from e

    for (_, _, _, _, sockaddr) in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(
                    f"URL resolves to a blocked network address: {ip} (in {network})."
                )
```

Write tests for this module in `api/tests/test_url_validation.py` (new file):
- HTTP and HTTPS URLs with a public hostname → no exception raised (mock
  `socket.getaddrinfo` to return a public IP like `8.8.8.8`).
- `file://`, `ftp://` scheme → raises ValueError.
- URL with no hostname → raises ValueError.
- DNS resolution failure → raises ValueError.
- Hostname resolving to `127.0.0.1` → raises ValueError.
- Hostname resolving to `10.0.1.50` → raises ValueError.
- Hostname resolving to `169.254.169.254` (AWS metadata) → raises ValueError.
- Hostname resolving to `::1` → raises ValueError.
- Hostname resolving to `fc00::1` (IPv6 ULA) → raises ValueError.
- Hostname resolving to `fe80::1` (IPv6 link-local) → raises ValueError.
- Round-robin DNS (multiple IPs, one private) → raises ValueError (rejects if ANY is blocked).

Use `unittest.mock.patch('socket.getaddrinfo', ...)` to control DNS resolution without
making real network calls. Return value format for mock: list of tuples matching
`(family, type, proto, canonname, sockaddr)` where `sockaddr = (ip_string, port)`.

**Depends on:** none

**Done when:** All test cases for `validate_url_for_outbound` pass. No real DNS lookups
are needed (mocked). The function is importable as `from api.url_validation import validate_url_for_outbound`.

---

### T5 — Fix VULN-2: SSRF in webhook dispatcher

**Goal:** Validate webhook URLs against the SSRF blocklist before making any outbound request.

**Files:**
- `api/dispatcher.py` — modify `_send_webhook()`

**Details:**

At the top of `api/dispatcher.py`, add:
```python
from api.url_validation import validate_url_for_outbound
```

Inside `_send_webhook()`, after `url = decrypt(endpoint.url)` (currently line 45) and before
constructing `log = WebhookDeliveryLog(...)`, add:
```python
try:
    validate_url_for_outbound(url)
except ValueError as e:
    logger.warning('Webhook endpoint %s blocked by SSRF guard: %s', endpoint_id, e)
    return
```

The function returns early without firing the webhook and without saving a `WebhookDeliveryLog`
entry (no log needed for blocked attempts — the WARNING log is sufficient).

Write tests in `api/tests/views/webhook.py` (add to existing file). Mock
`socket.getaddrinfo` and `urllib.request.urlopen`. Test:
- Webhook with a public URL (mocked to return a public IP) → `urlopen` is called.
- Webhook with a URL resolving to `192.168.1.1` → `urlopen` is NOT called, WARNING logged.
- Webhook with `file://` scheme → `urlopen` is NOT called, WARNING logged.
- DNS failure → `urlopen` is NOT called, WARNING logged.

**Depends on:** T4

**Done when:** All four test cases pass. A webhook endpoint configured with an internal URL
does not cause any outbound HTTP request.

---

### T6 — Fix VULN-3: SSRF in GenericAI provider

**Goal:** Validate the AI endpoint URL before making any outbound request in `GenericAIProvider`.

**Files:**
- `api/translation_providers/generic_ai.py` — modify `translate()`

**Details:**

Add the import at the top:
```python
from api.url_validation import validate_url_for_outbound
```

At the start of the `translate()` method, before building `req`, add:
```python
validate_url_for_outbound(self.endpoint_url)
```
This raises `ValueError` on invalid URLs. Do NOT catch it here — let it propagate up to the
caller (`MachineTranslateAPI` view), which already wraps calls in a try/except and returns a
JSON error response. The raised error will manifest as a `RuntimeError`-equivalent to the
caller, producing a descriptive error message rather than a 500.

Actually: wrap it to keep error type consistent with how the AI provider signals errors:
```python
try:
    validate_url_for_outbound(self.endpoint_url)
except ValueError as e:
    raise RuntimeError(f'Invalid endpoint URL: {e}') from e
```

Write tests in `api/tests/views/integration.py` (add to existing file). Mock
`socket.getaddrinfo` and test:
- Valid public endpoint URL → translation proceeds (or raises the normal AI provider error,
  not an SSRF error).
- Endpoint URL resolving to `10.0.0.1` → raises `RuntimeError` with "Invalid endpoint URL"
  before any HTTP request is made.

**Depends on:** T4

**Done when:** Tests pass. Configuring a GenericAI integration with an internal endpoint URL
results in a `RuntimeError` being raised before any network connection attempt.

---

### T7 — Migration 0018: model field changes for VULN-1 and ENH-1

**Goal:** Apply all model schema changes needed before any code starts generating longer tokens
or using 2FA models.

**Files:**
- `api/models/project.py` — modify
- `api/models/users.py` — modify
- `api/migrations/0018_security_improvements.py` — create (via `makemigrations`)
- `api/models/__init__.py` — ensure new models exported
- `api/tests/helpers.py` — update `make_project`

**Details:**

**`api/models/project.py` changes:**

1. Change `Invitation.code` field: `max_length=16` → `max_length=64`.
2. Change `ProjectAccessToken.token` field: `max_length=16` → `max_length=64`.
3. Add field to `Project` model:
   ```python
   require_2fa = models.BooleanField(default=False)
   ```
   Place it after `description`.

**`api/models/users.py` changes:**

Add two new models at the bottom of the file (after `UserProfile`):

```python
import hashlib
import secrets as _secrets


class TwoFAVerification(models.Model):
    """Tracks which Knox token keys have completed the 2FA login step."""
    token_key = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BackupCode(models.Model):
    """Single-use hashed backup codes for TOTP 2FA recovery."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=64)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @staticmethod
    def generate(user, count=10):
        """Generate `count` fresh backup codes. Returns list of plaintext codes."""
        BackupCode.objects.filter(user=user).delete()
        codes = []
        for _ in range(count):
            plaintext = _secrets.token_urlsafe(8)
            code_hash = hashlib.sha256(plaintext.encode()).hexdigest()
            BackupCode.objects.create(user=user, code_hash=code_hash)
            codes.append(plaintext)
        return codes

    @staticmethod
    def verify_and_consume(user, plaintext_code: str) -> bool:
        """Returns True and marks the code used if valid; False otherwise."""
        code_hash = hashlib.sha256(plaintext_code.encode()).hexdigest()
        code = BackupCode.objects.filter(
            user=user, code_hash=code_hash, used=False
        ).first()
        if code:
            code.used = True
            code.save(update_fields=['used'])
            return True
        return False
```

**`api/models/__init__.py`:**
The file uses `from .users import *`. Since `users.py` now defines `TwoFAVerification` and
`BackupCode`, they are automatically included in the wildcard export. No change needed if
`users.py` does not restrict `__all__`. Verify they are importable via `from api.models import TwoFAVerification, BackupCode`.

**Migration:**
Run `python manage.py makemigrations api --name security_improvements` to auto-generate
`0018_security_improvements.py`. Review the generated file to confirm it contains:
- `AlterField` for `Invitation.code` max_length 16→64
- `AlterField` for `ProjectAccessToken.token` max_length 16→64
- `AddField` for `Project.require_2fa`
- `CreateModel` for `TwoFAVerification`
- `CreateModel` for `BackupCode`

Run `python manage.py migrate` to apply.

Migration safety: all operations are safe for zero-downtime deploy on Postgres/MySQL/SQLite.
`BooleanField(default=False)` is a non-nullable field with a DB default — safe. `AlterField`
for `max_length` on `CharField` does not lock tables on Postgres (VARCHAR without constraint).

**`api/tests/helpers.py`:**
Update `make_project` to accept an optional `require_2fa` parameter:
```python
def make_project(name='TestProject', owner=None, require_2fa=False):
    project = Project.objects.create(name=name, description='desc', require_2fa=require_2fa)
    if owner:
        ProjectRole.objects.create(user=owner, project=project, role=ProjectRole.Role.owner)
    return project
```

**Depends on:** none

**Done when:**
- `python manage.py migrate` completes without errors.
- `Project` model has `require_2fa` field defaulting to `False`.
- `Invitation.code` max_length is 64; `ProjectAccessToken.token` max_length is 64.
- `TwoFAVerification` and `BackupCode` models are importable from `api.models`.
- `BackupCode.generate(user)` returns 10 plaintext strings and creates 10 `BackupCode` DB rows.
- `BackupCode.verify_and_consume(user, code)` returns `True` once and `False` on second attempt.

---

### T8 — Fix VULN-1: replace weak PRNG in token generation

**Goal:** Replace `random.choices()` with `secrets.token_urlsafe()` in `generate_token()`.

**Files:**
- `api/views/roles.py` — modify

**Details:**

Remove `import random` and `import string` from the top of `api/views/roles.py`.
Add `import secrets`.

Replace `generate_token()`:
```python
def generate_token(length=16):
    return secrets.token_urlsafe(length)
```

`secrets.token_urlsafe(16)` returns a 22-character URL-safe base64 string. Both
`Invitation.code` and `ProjectAccessToken.token` now accept up to 64 chars (per T7 migration).

Add a test to `api/tests/views/roles.py`:
- Call `generate_token()` 100 times; assert every result is a non-empty string of length ≥ 16.
- Assert that two consecutive calls return different values (probabilistically certain).
- Assert that `import random` is no longer used in `roles.py` (optional: check via import
  inspection or simply confirm tests pass without `random` in scope).

**Depends on:** T7 (migration must be applied so max_length=64 is in effect)

**Done when:** `generate_token()` uses `secrets`; all existing invitation and access-token
creation tests continue to pass; the two new token-generation tests pass.

---

### T9 — Install django-otp and update settings for 2FA

**Goal:** Add `django-otp` to dependencies and wire it into Django settings and middleware.

**Files:**
- `requirements.txt` — modify
- `repository/settings.py` — modify

**Details:**

**`requirements.txt`:** Add two lines:
```
django-otp>=1.5
qrcode[pil]>=8.0
```
(Pinned to a minimum version; use the latest compatible versions available.)

**`repository/settings.py`:**

1. In `INSTALLED_APPS`, add after `'api'`:
   ```python
   'django_otp',
   'django_otp.plugins.otp_totp',
   ```

2. In `MIDDLEWARE` (the cleaned-up list from T2), add `'django_otp.middleware.OTPMiddleware'`
   immediately after `'django.contrib.auth.middleware.AuthenticationMiddleware'`:
   ```python
   MIDDLEWARE = [
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.security.SecurityMiddleware',
       'whitenoise.middleware.WhiteNoiseMiddleware',
       'django.contrib.sessions.middleware.SessionMiddleware',
       'django.middleware.csrf.CsrfViewMiddleware',
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'django_otp.middleware.OTPMiddleware',               # ADD
       'django.contrib.messages.middleware.MessageMiddleware',
       'django.middleware.clickjacking.XFrameOptionsMiddleware',
   ]
   ```

After adding, run `python manage.py migrate` to apply django-otp's own migrations
(creates `otp_totp_totpdevice` table).

**Depends on:** T2 (settings.py must be in its clean state from T2)

**Done when:**
- `python manage.py migrate` completes (django-otp tables created).
- `from django_otp.plugins.otp_totp.models import TOTPDevice` imports without error.
- `from django_otp import user_has_device` imports without error.
- `django_otp.middleware.OTPMiddleware` is in `settings.MIDDLEWARE`.

---

### T10 — Create `api/permissions.py` with `ProjectTwoFAPermission`

**Goal:** Implement the DRF permission class that enforces the project-level 2FA gate, and
register it as a global default so all project-scoped views are covered without modification.

**Files:**
- `api/permissions.py` — create
- `repository/settings.py` — modify `REST_FRAMEWORK`

**Details:**

Create `api/permissions.py`:

```python
import logging

from django_otp import user_has_device
from rest_framework.permissions import BasePermission

from api.models.project import Project
from api.models.users import TwoFAVerification

logger = logging.getLogger(__name__)

_GATE_MESSAGE = (
    "This project requires 2FA. "
    "Enable two-factor authentication to access it."
)


class ProjectTwoFAPermission(BasePermission):
    """
    Global permission applied via DEFAULT_PERMISSION_CLASSES.

    For any DRF view that has `pk` in its URL kwargs, checks whether the
    referenced project requires 2FA. If it does, the requesting user must:
      1. Have a confirmed TOTP device on their account, AND
      2. Have a TwoFAVerification record for their current Knox token key.

    Views with explicit permission_classes (e.g. AllowAny on plugin views)
    override DEFAULT_PERMISSION_CLASSES entirely and bypass this check —
    which is correct, since those views use ProjectAccessToken auth, not Knox.

    Views without `pk` in kwargs (login, signup, 2fa/* endpoints, etc.) pass
    through immediately.
    """

    message = _GATE_MESSAGE

    def has_permission(self, request, view):
        pk = view.kwargs.get('pk')
        if not pk:
            return True

        try:
            project = Project.objects.only('require_2fa').get(pk=pk)
        except Project.DoesNotExist:
            return True  # Let the view return 404

        if not project.require_2fa:
            return True

        # Project requires 2FA: user must have an active confirmed device
        if not user_has_device(request.user, confirmed=True):
            return False

        # AND the current Knox token must have completed the 2FA login step
        token_key = getattr(request.auth, 'token_key', None)
        if not token_key:
            return False

        return TwoFAVerification.objects.filter(token_key=token_key).exists()
```

**`repository/settings.py`:** Add `ProjectTwoFAPermission` to `DEFAULT_PERMISSION_CLASSES`:
```python
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'knox.auth.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'api.permissions.ProjectTwoFAPermission',
    ],
}
```

**Important:** Views that currently have `permission_classes = [permissions.IsAuthenticated]`
set explicitly will now have BOTH `IsAuthenticated` AND `ProjectTwoFAPermission` applied —
they will NOT be overridden, because DRF only overrides defaults when the view explicitly
sets its own list. Wait, this is incorrect — explicit `permission_classes` on a view DOES
override `DEFAULT_PERMISSION_CLASSES` entirely.

To ensure `ProjectTwoFAPermission` also runs on views that have explicit `permission_classes`,
we need to include it in those views. But there are many such views.

**Correct approach:** Instead of `DEFAULT_PERMISSION_CLASSES`, we rely on the fact that
all project-scoped views with `permission_classes = [permissions.IsAuthenticated]` will be
updated to include `ProjectTwoFAPermission` as well. To avoid touching every single view,
define a module-level constant in `api/permissions.py`:

```python
PROJECT_PERMISSIONS = [IsAuthenticated, ProjectTwoFAPermission]
```

Then update `REST_FRAMEWORK` defaults AND update all project-scoped views. But that's a lot
of views.

**Practical decision (overrides ARCH assumption 4):** Use a DRF permission class that is
also enforced via a separate mechanism — a Django middleware — for views that override
`permission_classes`. BUT middleware can't access Knox auth (as noted in ARCH R3).

**Revised approach:** Keep `DEFAULT_PERMISSION_CLASSES` as the enforcement mechanism.
For it to work, views that currently set `permission_classes = [permissions.IsAuthenticated]`
must be changed to `permission_classes = [permissions.IsAuthenticated, ProjectTwoFAPermission]`
OR the per-view `permission_classes` must be removed so they inherit from the default.

Since all project-scoped views already rely on queryset-level filtering (`.filter(roles__user=request.user)`) for their primary security, we can safely remove the explicit
`permission_classes = [permissions.IsAuthenticated]` from them and let the default handle it.

**Update all project-scoped views** in these files by removing their explicit
`permission_classes = [permissions.IsAuthenticated]` declaration so they fall through to
`DEFAULT_PERMISSION_CLASSES`:
- `api/views/project.py` — all 7 view classes
- `api/views/roles.py` — `RolesAPI`, `ProjectParticipantsAPI`, `ProjectInvitationAPI`,
  `ProjectAccessTokenAPI`
- `api/views/bundle.py` — all view classes
- `api/views/language.py` — `LanguageAPI`, `SetDefaultLanguageAPI`
- `api/views/translation.py` — all view classes
- `api/views/scope.py` — all view classes
- `api/views/history.py` — all view classes
- `api/views/export.py` — `ExportAPI`, `ExportFormatsAPI`
- `api/views/import_api.py` — `ImportAPI`
- `api/views/integration.py` — all view classes
- `api/views/webhook.py` — all view classes
- `api/views/plural_translation.py` — `PluralTranslationAPI`

**Keep** explicit `permission_classes` on:
- `api/views/generic.py`: `SignInAPI` (`AllowAny`), `SignUpAPI` (no class set — fine),
  `ChangePasswordAPI` (`IsAuthenticated` — keep, not project-scoped),
  `ProfileAPI` (`IsAuthenticated` — keep),
  `ActivateProjectAPI` (`IsAuthenticated` — keep, not scoped by pk).
- `api/views/plugin.py`: ALL views must keep `AllowAny` — these use ProjectAccessToken auth.
- `api/views/two_fa.py` (T11): explicit `IsAuthenticated` — not project-scoped.
- `api/views/mcp.py`: plain Django view, not DRF, unaffected.

After removing `permission_classes` from project-scoped views, verify the test suite passes
(all existing tests should continue to work since `authed_client()` uses `force_authenticate`
which satisfies `IsAuthenticated`).

**Depends on:** T7, T9

**Done when:**
- `api/permissions.py` exists and `ProjectTwoFAPermission` is importable.
- `DEFAULT_PERMISSION_CLASSES` in `REST_FRAMEWORK` includes `'api.permissions.ProjectTwoFAPermission'`.
- `python manage.py test api` passes (existing tests unaffected by the permission change).
- A project with `require_2fa=True`: a request from a user without a TOTP device returns 403
  with `{"detail": "This project requires 2FA..."}`.

---

### T11 — Create `api/views/two_fa.py` with four TOTP endpoints

**Goal:** Implement setup, verify, delete, and login views for TOTP 2FA.

**Files:**
- `api/views/two_fa.py` — create

**Details:**

```python
import base64
import io
import logging

import qrcode
from django_otp import user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.models.users import BackupCode, TwoFAVerification
from api.serializers.users import UserSerializer

logger = logging.getLogger(__name__)
```

**`TwoFASetupAPI` — `POST /api/2fa/setup`:**
```python
class TwoFASetupAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        # Block if confirmed device exists
        if user_has_device(user, confirmed=True):
            return JsonResponse(
                {'error': '2FA already active; disable first'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete any unconfirmed (pending) device
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        # Create new pending TOTP device
        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=False,
        )

        # Build otpauth URI
        issuer = 'StringsRepository'
        otpauth_uri = device.config_url  # django-otp provides this

        # Generate QR code as base64 PNG
        img = qrcode.make(otpauth_uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

        # Generate 10 backup codes (deletes old ones first)
        backup_codes = BackupCode.generate(user)

        return JsonResponse({
            'otpauth_uri': otpauth_uri,
            'qr_code': qr_b64,
            'backup_codes': backup_codes,
        })
```

Note: `TOTPDevice.config_url` is a property on the `TOTPDevice` model provided by django-otp
that builds the `otpauth://totp/...` URI. It uses `device.key` (base32-encoded secret) and
`device.name`. The `name` field is used as the account name in authenticator apps — set it to
`user.email` for better UX: `name=user.email or user.username`.

**`TwoFAVerifyAPI` — `POST /api/2fa/verify`:**
```python
class TwoFAVerifyAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '')

        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if not device:
            return JsonResponse(
                {'error': 'No pending 2FA device'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not device.verify_token(code):
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save(update_fields=['confirmed'])
        return JsonResponse({})
```

**`TwoFADeleteAPI` — `DELETE /api/2fa`:**
```python
class TwoFADeleteAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        code = request.data.get('code', '')

        # Try TOTP code
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            return JsonResponse(
                {'error': 'No active 2FA device'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp_valid = device.verify_token(code)
        backup_valid = not totp_valid and BackupCode.verify_and_consume(user, code)

        if not totp_valid and not backup_valid:
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete TOTP device and all backup codes
        device.delete()
        BackupCode.objects.filter(user=user).delete()

        # Invalidate all TwoFAVerification records for this user's Knox tokens
        from knox.models import AuthToken
        user_token_keys = AuthToken.objects.filter(
            user=user
        ).values_list('token_key', flat=True)
        TwoFAVerification.objects.filter(token_key__in=user_token_keys).delete()

        return JsonResponse({})
```

**`TwoFALoginAPI` — `POST /api/2fa/login`:**
```python
class TwoFALoginAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '')

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            return JsonResponse(
                {'error': 'No active 2FA device'},
                status=status.HTTP_403_FORBIDDEN,
            )

        totp_valid = device.verify_token(code)
        backup_valid = not totp_valid and BackupCode.verify_and_consume(user, code)

        if not totp_valid and not backup_valid:
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Mark this Knox token as 2FA-verified (upsert)
        token_key = request.auth.token_key
        TwoFAVerification.objects.get_or_create(token_key=token_key)

        return JsonResponse({
            'user': UserSerializer(user).data,
            'expired': request.auth.expiry.isoformat() if request.auth.expiry else None,
        })
```

**Depends on:** T7, T9

**Done when:** All four view classes exist in `api/views/two_fa.py` and are importable
without error. (URLs are wired in T13. Tests are in T18.)

---

### T12 — Modify `SignInAPI` login to return 202 for 2FA users

**Goal:** When a user with an active confirmed TOTP device logs in, return HTTP 202 instead
of 200 so the client knows to proceed to the TOTP step.

**Files:**
- `api/views/generic.py` — modify `SignInAPI.post()`

**Details:**

Add import at the top of `api/views/generic.py`:
```python
from django_otp import user_has_device
```

In `SignInAPI.post()`, after `token = AuthToken.objects.create(user)`, insert:
```python
if user_has_device(user, confirmed=True):
    return JsonResponse(
        {'2fa_required': True, 'token': token[1]},
        status=202,
    )
```

The existing return statement (HTTP 200 with full user + token + expired) stays in place and
is reached only when the user has no active TOTP device.

**Depends on:** T9

**Done when:** Logging in with a user that has a confirmed `TOTPDevice` returns HTTP 202 with
`{"2fa_required": true, "token": "..."}`. Logging in with a user without a device returns
HTTP 200 with `{"user": {...}, "token": "...", "expired": "..."}` as before.

---

### T13 — Add `require_2fa` to project serializers and enable PATCH on `ProjectAPI`

**Goal:** Expose `require_2fa` in project create/read responses and allow owners to update it
via PATCH.

**Files:**
- `api/serializers/project.py` — modify three serializers
- `api/views/project.py` — modify `ProjectAPI`, add `update()` logic

**Details:**

**`api/serializers/project.py`:**

1. `CreateProjectSerializer`: add `require_2fa` to `Meta.fields`:
   ```python
   class Meta:
       model = Project
       fields = ['name', 'description', 'require_2fa']
   ```

2. `ProjectSerializer` (list): add `require_2fa` to `Meta.fields`:
   ```python
   class Meta:
       model = Project
       fields = ['id', 'name', 'description', 'role', 'require_2fa']
   ```

3. `ProjectDetailSerializer` (detail/update): add `require_2fa` to `Meta.fields` and make it
   writable but owner-only validated:
   ```python
   class Meta:
       model = Project
       fields = ['id', 'name', 'description', 'languages', 'role', 'require_2fa']
   ```
   Add a `validate_require_2fa` method:
   ```python
   def validate_require_2fa(self, value):
       request = self.context.get('request')
       if request and self.instance:
           try:
               role = self.instance.roles.get(user=request.user)
           except Exception:
               raise serializers.ValidationError("Not allowed.")
           if role.role != ProjectRole.Role.owner:
               raise serializers.ValidationError(
                   "Only project owners can change the 2FA requirement."
               )
       return value
   ```
   Add `from api.models.project import ProjectRole` to imports if not already present.

**`api/views/project.py`:**

Change `ProjectAPI` base class from `generics.RetrieveDestroyAPIView` to
`generics.RetrieveUpdateDestroyAPIView`:
```python
class ProjectAPI(generics.RetrieveUpdateDestroyAPIView):
```

Override `partial_update` to enforce owner-only for any update and use `ProjectDetailSerializer`:
The existing `get_queryset` already filters by `roles__user=self.request.user`. The serializer
`validate_require_2fa` handles the owner check. Set `http_method_names` so only `GET`,
`PATCH`, and `DELETE` are accepted (not `PUT`):
```python
http_method_names = ['get', 'patch', 'delete', 'head', 'options']
```

Remove `permission_classes` from `ProjectAPI` (it inherits `DEFAULT_PERMISSION_CLASSES`
via T10's changes — `IsAuthenticated` + `ProjectTwoFAPermission`).

**Depends on:** T7, T10

**Done when:**
- `GET /api/project/<pk>` response includes `require_2fa` field.
- `POST /api/project` with `{"name": "X", "description": "", "require_2fa": true}` creates
  a project with `require_2fa=True`.
- `PATCH /api/project/<pk>` with `{"require_2fa": true}` by the project owner succeeds (200).
- `PATCH /api/project/<pk>` with `{"require_2fa": true}` by a non-owner returns 400 with
  "Only project owners can change the 2FA requirement."
- `PUT /api/project/<pk>` returns 405 Method Not Allowed.

---

### T14 — Register all new 2FA URLs and project PATCH in `api/urls.py`

**Goal:** Wire the four 2FA endpoints and make the project PATCH route reachable.

**Files:**
- `api/urls.py` — modify

**Details:**

Add imports at the top:
```python
from api.views.two_fa import TwoFASetupAPI, TwoFAVerifyAPI, TwoFADeleteAPI, TwoFALoginAPI
```

Add four URL patterns (place them before the `# mcp` section for logical grouping):
```python
# 2FA
path('2fa/setup', TwoFASetupAPI.as_view()),
path('2fa/verify', TwoFAVerifyAPI.as_view()),
path('2fa', TwoFADeleteAPI.as_view()),
path('2fa/login', TwoFALoginAPI.as_view()),
```

The PATCH on `project/<int:pk>` is already handled by changing `ProjectAPI` to
`RetrieveUpdateDestroyAPIView` in T13 — no new URL pattern needed, the existing
`path('project/<int:pk>', ProjectAPI.as_view())` now handles GET, PATCH, and DELETE.

**Depends on:** T11, T12, T13

**Done when:**
- `GET /api/2fa/setup` returns 405 (Method Not Allowed — only POST is valid).
- `POST /api/2fa/setup` with a valid Knox token returns 200 or 400 depending on user state.
- `POST /api/2fa/login` returns 403 with `{"error": "No active 2FA device"}` for a user
  without a TOTP device.
- `DELETE /api/2fa` returns 400 with `{"error": "No active 2FA device"}` for a user
  without a TOTP device.
- `PATCH /api/project/1` is accepted (no 405).

---

### T15 — Register TOTP devices in Django admin

**Goal:** Allow operators to inspect and delete TOTP devices and backup codes via the admin
panel (e.g. for user recovery).

**Files:**
- `api/admin.py` — modify

**Details:**

Add imports and registrations:
```python
from django_otp.plugins.otp_totp.models import TOTPDevice
from api.models.users import TwoFAVerification, BackupCode

admin.site.register(TOTPDevice)

@admin.register(TwoFAVerification)
class TwoFAVerificationAdmin(admin.ModelAdmin):
    list_display = ['token_key', 'created_at']
    search_fields = ['token_key']

@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['user__username', 'user__email']
```

**Depends on:** T7, T9

**Done when:** `/admin/` page lists TOTP Devices, TwoFA Verifications, and Backup Codes
sections. Devices can be deleted via admin to allow manual recovery for locked-out users.

---

### T16 — Tests for VULN-1, VULN-2, VULN-3, VULN-8

**Goal:** Comprehensive test coverage for all non-2FA security fixes.

**Files:**
- `api/tests/views/roles.py` — add tests
- `api/tests/views/webhook.py` — add tests
- `api/tests/views/integration.py` — add tests
- `api/tests/test_url_validation.py` — already written in T4

**Details:**

Tests were partially specified in T3, T4, T5, T6, T8. Consolidate and add any missing coverage
here. Specifically ensure the following are all present and passing:

**VULN-1 (`api/tests/views/roles.py`):**
- `test_generate_token_is_not_empty`: `generate_token()` returns non-empty string.
- `test_generate_token_minimum_length`: length ≥ 16.
- `test_generate_token_uniqueness`: 100 calls produce 100 distinct values.
- `test_invitation_code_uses_secrets`: calling `POST /api/project/<pk>/invite` creates an
  `Invitation` with `.code` of length > 16 (i.e. not the old 16-char format).
- `test_access_token_uses_secrets`: calling `POST /api/project/<pk>/access_token` creates a
  `ProjectAccessToken` with `.token` of length > 16.

**VULN-2 (`api/tests/views/webhook.py`):**
Use `unittest.mock.patch` for `socket.getaddrinfo` and `urllib.request.urlopen`.
- `test_webhook_fires_for_public_url`: mock getaddrinfo → `8.8.8.8`; confirm urlopen called.
- `test_webhook_blocked_for_private_url`: mock getaddrinfo → `192.168.1.1`; confirm urlopen
  NOT called.
- `test_webhook_blocked_for_file_scheme`: confirm urlopen NOT called, WARNING emitted.
- `test_webhook_blocked_for_dns_failure`: mock getaddrinfo to raise `socket.gaierror`;
  confirm urlopen NOT called.

**VULN-3 (`api/tests/views/integration.py`):**
- `test_generic_ai_blocked_for_private_url`: configure a GenericAI integration with an
  internal endpoint; mock getaddrinfo → `10.0.0.1`; call the translate endpoint; assert
  response contains an error and no external request was made.

**VULN-8 (`api/tests/views/roles.py` + plugin tests):**
These were specified in T3. Confirm they exist:
- `test_validate_access_token_valid_no_expiry`
- `test_validate_access_token_expired_returns_403`
- `test_validate_access_token_future_expiry_valid`
- `test_delete_expired_tokens_filters_correctly`

**Depends on:** T3, T4, T5, T6, T8

**Done when:** `python manage.py test api.tests.views.roles api.tests.views.webhook api.tests.views.integration api.tests.test_url_validation` passes with all new tests green.

---

### T17 — Tests for VULN-4, VULN-5, VULN-6, VULN-7 (settings)

**Goal:** Verify settings hardening is correctly applied.

**Files:**
- `api/tests/test_settings.py` — create

**Details:**

Create `api/tests/test_settings.py`:

```python
from django.test import TestCase, override_settings
from django.conf import settings


class SettingsSecurityTest(TestCase):

    def test_debug_is_false_by_default(self):
        self.assertFalse(settings.DEBUG)

    def test_csrf_middleware_present(self):
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

    def test_csrf_after_session_middleware(self):
        mw = settings.MIDDLEWARE
        session_idx = mw.index('django.contrib.sessions.middleware.SessionMiddleware')
        csrf_idx = mw.index('django.middleware.csrf.CsrfViewMiddleware')
        self.assertGreater(csrf_idx, session_idx)

    def test_common_middleware_not_duplicated(self):
        count = settings.MIDDLEWARE.count('django.middleware.common.CommonMiddleware')
        self.assertLessEqual(count, 1)

    def test_null_not_in_cors_origins(self):
        self.assertNotIn('null', settings.CORS_ALLOWED_ORIGINS)

    def test_wildcard_not_in_allowed_hosts_unless_debug(self):
        if not settings.DEBUG:
            self.assertNotIn('*', settings.ALLOWED_HOSTS)
```

Note: `test_debug_is_false_by_default` will pass because the test runner sets `DEBUG=False`
unless the env var is explicitly set. Ensure the CI environment does not set `DEBUG=true`.

**Depends on:** T2

**Done when:** `python manage.py test api.tests.test_settings` passes all 6 tests.

---

### T18 — Tests for ENH-1: 2FA backend flows

**Goal:** Full test coverage for the 2FA endpoints, login modification, project gate, and
project create/update flows.

**Files:**
- `api/tests/views/two_fa.py` — create

**Details:**

Create `api/tests/views/two_fa.py`. All tests use `helpers.make_user()`,
`helpers.make_project()`, `helpers.authed_client()`. Import
`TOTPDevice`, `BackupCode`, `TwoFAVerification` from `api.models`.

**Setup / Verify flow:**
- `test_setup_creates_pending_device_and_backup_codes`: POST to `/api/2fa/setup`; assert
  response has `otpauth_uri`, `qr_code`, `backup_codes` (10 items); assert DB has 1
  `TOTPDevice(confirmed=False)` and 10 `BackupCode` rows for user.
- `test_setup_blocked_if_device_already_confirmed`: create a confirmed `TOTPDevice` for user;
  POST to `/api/2fa/setup`; assert 400 "2FA already active; disable first".
- `test_setup_replaces_unconfirmed_device`: POST setup twice; assert only 1 pending device.
- `test_verify_activates_device`: POST setup, then POST verify with correct TOTP code (use
  `device.verify_token(device.generate_challenge())` or mock TOTP); assert device confirmed.
- `test_verify_returns_400_on_wrong_code`: POST verify with `"000000"`; assert 400.
- `test_verify_returns_404_if_no_pending_device`: POST verify with no prior setup; assert 404.

**Delete flow:**
- `test_delete_requires_valid_code`: DELETE `/api/2fa` with wrong code; assert 400.
- `test_delete_succeeds_with_totp_code`: DELETE with correct code; device and backup codes deleted.
- `test_delete_succeeds_with_backup_code`: DELETE with a valid backup code; assert 200.
- `test_delete_clears_2fa_verifications`: create `TwoFAVerification` for user; DELETE 2FA;
  assert `TwoFAVerification` records gone.

**Login 202 flow:**
- `test_login_returns_200_without_2fa`: user has no TOTP device; POST to `/api/login`; assert 200.
- `test_login_returns_202_with_2fa`: user has confirmed TOTP device; POST to `/api/login`;
  assert 202, body has `{"2fa_required": true, "token": "..."}`.

**2FA login step:**
- `test_2fa_login_success`: user has confirmed device; send valid TOTP code to
  `POST /api/2fa/login`; assert 200, response has `user` + `expired`; assert
  `TwoFAVerification` record created for the Knox token key.
- `test_2fa_login_success_with_backup_code`: use a valid backup code; assert 200; assert
  code is marked used.
- `test_2fa_login_wrong_code_returns_403`: send `"000000"`; assert 403.
- `test_backup_code_single_use`: use same backup code twice; second use returns 403.

**Project 2FA gate:**
- `test_project_gate_blocks_user_without_2fa_on_required_project`: create project with
  `require_2fa=True`; GET `/api/project/<pk>`; assert 403 with `{"detail": "This project
  requires 2FA..."}`.
- `test_project_gate_blocks_unverified_knox_token`: user has confirmed TOTP device but no
  `TwoFAVerification` record; GET `/api/project/<pk>`; assert 403.
- `test_project_gate_allows_user_with_verified_2fa`: user has confirmed device AND
  `TwoFAVerification` for their token; GET `/api/project/<pk>`; assert 200.
- `test_project_gate_not_triggered_on_non_2fa_project`: project with `require_2fa=False`
  accessible by user without 2FA; assert 200.
- `test_project_gate_not_triggered_on_profile_endpoint`: GET `/api/profile` with user having
  no 2FA; assert 200 (not a project-scoped view).

**Project create/update:**
- `test_create_project_with_require_2fa`: POST `/api/project` with `require_2fa=true`; assert
  project created with `require_2fa=True`.
- `test_patch_require_2fa_by_owner`: PATCH `/api/project/<pk>` `{"require_2fa": true}` as
  owner; assert 200, project updated.
- `test_patch_require_2fa_by_non_owner`: PATCH as admin role; assert 400 "Only project
  owners can change the 2FA requirement."

For TOTP code generation in tests, use `unittest.mock.patch.object(TOTPDevice, 'verify_token', return_value=True)` to bypass real TOTP validation, OR use `device.verify_token(str(device.totp.now()))` if `pyotp` is available via `django-otp`'s internals.

**Depends on:** T10, T11, T12, T13, T14

**Done when:** `python manage.py test api.tests.views.two_fa` passes all ~22 test cases.

---

### T19 — Frontend: TypeScript types for Project and 2FA

**Goal:** Add `require_2fa` to the `Project` interface and create the `TwoFA` type file.

**Files:**
- `webui/src/types/Project.ts` — modify
- `webui/src/types/TwoFA.ts` — create

**Details:**

**`webui/src/types/Project.ts`:**
Add `require_2fa: boolean` to the `Project` interface:
```typescript
import Language from "./Language"

export enum ProjectRole {
    owner = 'owner',
    admin = 'admin',
    editor = 'editor',
    translator = 'translator'
}

interface Project {
    id: number
    name: string
    description: string | null
    languages: Language[]
    role: ProjectRole
    require_2fa: boolean
}

export default Project
```

**`webui/src/types/TwoFA.ts`** (new file):
```typescript
import Profile from "./Profile"

export interface TwoFASetupResponse {
    otpauth_uri: string
    qr_code: string        // base64-encoded PNG
    backup_codes: string[] // 10 plaintext codes, shown once
}

export interface TwoFALoginResponse {
    user: Profile
    expired: string | null
}

export interface LoginWith2FAResponse {
    '2fa_required': true
    token: string
}

export interface LoginResponse {
    user: Profile
    token: string
    expired: string
}
```

**Depends on:** none

**Done when:** TypeScript compilation (`tsc --noEmit` or webpack build) succeeds without
errors related to these type files.

---

### T20 — Frontend: LoginPage 2FA handling + TwoFALoginPage + route

**Goal:** After a 202 login response, store the partial token and redirect to the TOTP step.
Implement the TOTP code entry page that completes authentication.

**Files:**
- `webui/src/components/pages/LoginPage.tsx` — modify
- `webui/src/components/Auth/TwoFALoginPage.tsx` — create
- `webui/src/components/App.tsx` — modify (add route)

**Details:**

**`webui/src/components/pages/LoginPage.tsx`:**

Update `LoginResponse` type (local to this file):
```typescript
type LoginResponse = {
    token: string
    '2fa_required'?: true
    user?: Profile
    expired?: string
}
```

In `onSubmit`, after receiving a successful result, check for the 202 case:
```typescript
const onSubmit: SubmitHandler<Inputs> = async (data) => {
    const result = await http<LoginResponse>({
        isAuth: true,
        method: APIMethod.post,
        path: "/api/login",
        data: { "username": data.login, "password": data.password }
    })

    if (result.error) {
        setError(result.error)
        return
    }

    const value = result.value
    if (!value) return

    if (value['2fa_required']) {
        // Store partial token; TwoFALoginPage will use it
        localStorage.setItem("auth", "Token " + value.token)
        navigate("/2fa-login", { replace: true })
        return
    }

    // Normal 200 login
    if (value.token) {
        localStorage.setItem("auth", "Token " + value.token)
        navigate("/", { replace: true })
    }
}
```

**`webui/src/components/Auth/TwoFALoginPage.tsx`** (new file):

```typescript
import { useState } from "react"
import { Button, Container, Form } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import ErrorAlert from "../UI/ErrorAlert"
import { TwoFALoginResponse } from "../../types/TwoFA"

type Inputs = {
    code: string
}

const TwoFALoginPage = () => {
    const navigate = useNavigate()
    const [error, setError] = useState<string>()

    const { register, handleSubmit } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const result = await http<TwoFALoginResponse>({
            method: APIMethod.post,
            path: "/api/2fa/login",
            data: { code: data.code },
        })

        if (result.error) {
            setError(result.error)
            return
        }

        // Token already in localStorage from the 202 step; just navigate home
        navigate("/", { replace: true })
    }

    return (
        <>
            <Container fluid className="align-content-center">
                <Form onSubmit={handleSubmit(onSubmit)} className="container my-2">
                    <Form.Group className="border rounded m-4 p-5 shadow">
                        <h5>Two-Factor Authentication</h5>
                        <Form.Text className="text-muted d-block mb-3">
                            Enter the 6-digit code from your authenticator app,
                            or one of your backup codes.
                        </Form.Text>
                        <Form.Group className="my-2">
                            <Form.Label>Authentication Code</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="123456"
                                autoComplete="one-time-code"
                                {...register("code")}
                            />
                        </Form.Group>
                        <Button type="submit" className="my-2">
                            Verify
                        </Button>
                    </Form.Group>
                </Form>
            </Container>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default TwoFALoginPage
```

**`webui/src/components/App.tsx`:**

Add a lazy import for `TwoFALoginPage`:
```typescript
const TwoFALoginPage = React.lazy(() => import("./Auth/TwoFALoginPage"))
```

Add the route (public, NOT wrapped in `<RequireAuth>`, same level as `/login`):
```typescript
<Route path="/2fa-login" element={<TwoFALoginPage />} />
```
Place it alongside the existing `/login` route.

**Depends on:** T14, T19

**Done when:**
- Login with a user that has 2FA → redirected to `/2fa-login`, token in localStorage.
- At `/2fa-login`, entering the correct TOTP code → redirected to `/`.
- Entering wrong code → error displayed, stay on page.
- Refreshing `/2fa-login` page (token still in localStorage) → form still shows.
- Login with a user without 2FA → redirected directly to `/` as before.

---

### T21 — Frontend: TwoFASetupPage + ProfilePage integration

**Goal:** Allow users to set up, verify, and disable TOTP 2FA from their profile page.

**Files:**
- `webui/src/components/Profile/TwoFASetupPage.tsx` — create
- `webui/src/components/Profile/ProfilePage.tsx` — modify

**Details:**

**`webui/src/components/Profile/TwoFASetupPage.tsx`** (new file):

The component manages three states:
1. **`idle`** — no device (or after deletion). Shows "Enable 2FA" button.
2. **`setup`** — after calling setup endpoint. Shows QR code image, OTP URI, backup codes,
   and a code entry form to confirm the device.
3. **`active`** — confirmed device exists. Shows "Disable 2FA" with a code entry form.

State detection: on mount, call `GET /api/2fa/setup` — but there's no GET endpoint. Instead,
store setup state locally using component state. Initially assume `idle`. After successful setup
response, move to `setup`. After verify, move to `active`. After delete, move to `idle`.

However, on ProfilePage load the component needs to know if 2FA is already active. Add a
simple endpoint check: `POST /api/2fa/setup` will return 400 with
`"2FA already active; disable first"` if active. So on mount, make a silent `POST /api/2fa/setup` — if it returns 400 with that specific message, the user is in `active` state. If it
returns 200, we just got a new QR code and move to `setup` state. 

Actually, this is bad UX (calling setup on mount would show backup codes unexpectedly).
Better: add a minimal `GET /api/2fa/status` endpoint — but that requires a backend task.

**Practical approach without a status endpoint:** Use a `status` state initialized to `'loading'`.
On mount, do NOT call setup. Instead, track state via component-internal logic:
- Start at `idle`.
- When user clicks "Enable 2FA": call setup endpoint; on 200 → move to `setup`; on 400
  "already active" → move to `active`.
- When in `setup` and user verifies: move to `active`.
- When in `active` and user disables: call delete endpoint with code; on 200 → move to `idle`.

BUT we need to show the current state on load without user interaction. **Solution:** Add a
`GET /api/2fa/setup` endpoint in T11 that returns `{"active": true/false, "pending": true/false}`.
Wait — this wasn't in the original design.

**Revised plan for TwoFASetupPage:** Accept an initial `hasTwoFA` prop (boolean), passed from
`ProfilePage` after loading profile data. But `Profile` type doesn't have a `has_2fa` field.

**Simplest working approach:** extend the `GET /api/profile` response to include `has_2fa: boolean`.

Add `has_2fa` to `ProfileAPI.get()` in `api/views/generic.py`:
```python
from django_otp import user_has_device
...
def get(self, request):
    user = request.user
    serializer = UserSerializer(user)
    data = serializer.data
    data['has_2fa'] = user_has_device(user, confirmed=True)
    return JsonResponse(data)
```

Update `Profile` TypeScript type:
```typescript
// webui/src/types/Profile.ts
interface Profile {
    email: string
    first_name: string
    last_name: string
    has_2fa: boolean
}
```

**Now `TwoFASetupPage`** receives `hasTwoFA: boolean` as a prop from `ProfilePage`.

```typescript
// Simplified component — show "Enable 2FA" or "Disable 2FA"
type Props = { hasTwoFA: boolean; onStatusChange: () => void }
```

When `hasTwoFA=false`:
- Show "Enable 2FA" button.
- On click: POST to `/api/2fa/setup`; show QR code, OTP URI, backup codes list, and a verify
  form with a code input.
- The QR code is rendered as `<img src={"data:image/png;base64," + qr_code} alt="QR Code" />`.
- On verify success: show "2FA enabled" message, call `onStatusChange()` to reload profile.

When `hasTwoFA=true`:
- Show "Disable 2FA" with a `Form.Control` for the code and a "Disable" button.
- On submit: DELETE to `/api/2fa` with `{"code": enteredCode}`.
- On success: call `onStatusChange()` to reload profile.

Local state within the component:
```typescript
type SetupState = 
  | { phase: 'idle' }
  | { phase: 'setup'; otpauth_uri: string; qr_code: string; backup_codes: string[] }
  | { phase: 'verify_pending' }
  | { phase: 'done' }

type DisableState =
  | { phase: 'idle' }
  | { phase: 'confirm' }
```

Show backup codes in a `<pre>` block with a "Copy" button (plain text, newline-separated).
Include a warning: "These codes will not be shown again. Store them safely."

**`webui/src/components/Profile/ProfilePage.tsx`:**

Update to pass `has_2fa` to `TwoFASetupPage` and reload profile on 2FA status change:
```typescript
import TwoFASetupPage from "./TwoFASetupPage"

// In render, after existing CollapseSection blocks:
{profile &&
    <CollapseSection title="Two-Factor Authentication">
        <TwoFASetupPage
            hasTwoFA={profile.has_2fa}
            onStatusChange={loadProfile}
        />
    </CollapseSection>
}
```

Also update `ProfileAPI` in `api/views/generic.py` and `webui/src/types/Profile.ts` as
described above.

**Depends on:** T14, T19

**Done when:**
- Profile page shows "Two-Factor Authentication" section.
- A user without 2FA sees an "Enable 2FA" button; clicking it shows QR code + backup codes +
  verify form.
- Entering the correct code → section updates to show "Disable 2FA" option.
- Entering incorrect code → error message shown.
- Disabling 2FA with correct code → section resets to "Enable 2FA".

---

### T22 — Frontend: `require_2fa` in project creation and settings

**Goal:** Allow owners to set and update `require_2fa` from the project creation modal and
from the project info settings panel.

**Files:**
- `webui/src/components/Project/AddProjectPage.tsx` — modify
- `webui/src/components/Project/ProjectInfo.tsx` — modify

**Details:**

**`webui/src/components/Project/AddProjectPage.tsx`:**

Add `require_2fa` to the `Inputs` type:
```typescript
type Inputs = {
    projectName: string
    description: string
    require_2fa: boolean
}
```

Add a `Form.Check` switch control inside the form:
```tsx
<Form.Group className="my-2">
    <Form.Check
        type="switch"
        id="require-2fa-switch"
        label="Require 2FA for all project members"
        {...register("require_2fa")}
    />
</Form.Group>
```

In `onSubmit`, include `require_2fa` in the request payload:
```typescript
data: {
    "name": data.projectName,
    "description": data.description,
    "require_2fa": data.require_2fa ?? false
}
```

**`webui/src/components/ProjectInfo.tsx`:**

The `project` prop is `Project` which now includes `require_2fa`.

Add state variable: `const [require2fa, setRequire2fa] = useState(project.require_2fa)`.

Show the toggle only to owners (`project.role === ProjectRole.owner`). Place it inside the
existing settings area (after the description label), or as a new `CollapseSection` titled
"Security Settings":

```tsx
{project.role === ProjectRole.owner && (
    <CollapseSection title="Security Settings">
        <Form.Check
            type="switch"
            id="require-2fa-toggle"
            label="Require 2FA for all project members"
            checked={require2fa}
            onChange={async (e) => {
                const newValue = e.target.checked
                const result = await http({
                    method: APIMethod.patch,
                    path: `/api/project/${project.id}`,
                    data: { require_2fa: newValue }
                })
                if (result.error) {
                    setError(result.error)
                } else {
                    setRequire2fa(newValue)
                }
            }}
        />
        <Form.Text className="text-muted">
            When enabled, all project members must have 2FA active to access this project.
        </Form.Text>
    </CollapseSection>
)}
```

Import `APIMethod` if not already imported (it is already imported in `ProjectInfo.tsx`).

**Depends on:** T13, T19

**Done when:**
- Project creation modal has a "Require 2FA" toggle switch (default off).
- Creating a project with the toggle on → `project.require_2fa` is `true` in the API response.
- Project info page shows "Security Settings" section only for owners.
- Toggling it and confirming → PATCH request succeeds, toggle state persists.
- Non-owners do not see the Security Settings section.
