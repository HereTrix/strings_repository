# Security Improvement — Business Analysis

## Overview

Address all findings from the 2026-05-02 security audit of StringsRepository (`main` branch).
The work covers 6 HIGH-severity vulnerabilities, 2 MEDIUM-severity issues, and 1 security
enhancement (TOTP 2FA). Goals: eliminate exploitable attack surface, harden configuration
defaults, and add a second authentication factor for user accounts.

---

## User Stories

**VULN-1 — Secure token generation**
As a project owner, I want invitation codes and access tokens to be cryptographically
unpredictable, so that an attacker who observes past tokens cannot predict future ones.

**VULN-2 — Webhook SSRF protection**
As a platform operator, I want webhook URLs to be validated against private IP ranges before
any outbound HTTP request is made, so that a malicious admin cannot use the webhook feature
to probe internal infrastructure.

**VULN-3 — Generic AI endpoint SSRF protection**
As a platform operator, I want Generic AI translation endpoint URLs to be validated against
private IP ranges, so that a malicious admin cannot use the integration to reach internal
services.

**VULN-4 — Configurable DEBUG flag**
As a platform operator, I want Django's DEBUG mode to be controlled by an environment variable
(defaulting to False), so that production deployments never accidentally expose stack traces
containing secrets and settings values.

**VULN-5 — Explicit ALLOWED_HOSTS**
As a platform operator, I want ALLOWED_HOSTS to default to `['localhost', '127.0.0.1']` with a
logged warning when the env var is absent, so that production deployments are not silently
exposed to Host-header injection.

**VULN-6 — CSRF protection**
As a platform operator, I want CSRF middleware enabled for the whole application, so that the
Django admin panel and any session-authenticated views are protected against cross-site request
forgery. CLI/plugin endpoints using Knox token auth must continue to work without disruption.

**VULN-7 — Remove null CORS origin**
As a platform operator, I want `null` removed from `CORS_ALLOWED_ORIGINS`, so that local HTML
files cannot make credentialed cross-origin requests to the plugin/MCP endpoints.

**VULN-8 — Timezone-aware datetime comparisons**
As a platform operator, I want token expiration checks to use `django.utils.timezone.now()`
instead of `datetime.datetime.now()`, so that expired tokens are correctly rejected and the
expired-token cleanup task completes without crashing.

**ENH-1 — TOTP two-factor authentication**
As a user, I want to enable TOTP 2FA on my account using any standard authenticator app
(Google Authenticator, Authy, 1Password, etc.), so that my account is protected even if my
password is compromised.
As a project owner, I want to mark my project as requiring 2FA (at creation time or in project
settings), so that all project members must have 2FA enabled before they can access the project.
As a project member in a 2FA-required project, I want a clear message explaining that I must
enable 2FA to regain access, so that I understand what action to take.

---

## Acceptance Criteria

### VULN-1
1. `generate_token()` uses `secrets.token_urlsafe()` (no `import random` for security tokens).
2. Newly generated invitation codes and `ProjectAccessToken` values are URL-safe base64 strings.
3. Existing tokens in the database are **not** invalidated (no migration required).
4. Tests for token generation confirm the output is non-empty and of expected minimum length.

### VULN-2
5. `_send_webhook()` calls `_validate_webhook_url(url)` before constructing the request.
6. URLs with schemes other than `http`/`https` are rejected with a logged error (webhook not fired).
7. URLs that resolve to RFC-1918, loopback, link-local, or IPv6 loopback ranges are rejected.
8. A valid public URL passes validation and the webhook fires normally.
9. Validation failure is caught and logged; it does not raise an unhandled exception to the caller.

### VULN-3
10. `GenericAIProvider` applies the same `_validate_webhook_url` (or equivalent shared utility)
    before calling `urlopen()`.
11. An invalid endpoint URL causes the translation job to fail with a descriptive error, not a
    500 crash into internal network content.

### VULN-4
12. `DEBUG` in `settings.py` is set from an env var (`DEBUG`), defaulting to `False`.
13. `DEBUG=true` (case-insensitive) sets `DEBUG = True`; any other value (including absent) sets
    `DEBUG = False`.
14. Verified: a 500 error in production mode returns a plain JSON error, not a Django debug page.

### VULN-5
15. `ALLOWED_HOSTS` is read from the `ALLOWED_HOSTS` env var (comma-separated).
16. When the env var is absent, defaults to `['localhost', '127.0.0.1']` and logs a `WARNING`
    at startup.
17. Docker `entrypoint.sh` or deployment documentation notes that `ALLOWED_HOSTS` should be set.

### VULN-6
18. `django.middleware.csrf.CsrfViewMiddleware` is present in `MIDDLEWARE`, placed after
    `SessionMiddleware`.
19. Knox token-authenticated API endpoints (`/api/`) continue to function without a CSRF token
    (Knox uses `TokenAuthentication`, which DRF exempts from CSRF).
20. Plugin endpoints (`/api/plugin/*`) and MCP endpoint (`/api/mcp`) continue to function from
    CLI and Figma plugin without a CSRF token.
21. Django admin panel (`/admin/`) rejects state-changing requests without a valid CSRF token.

### VULN-7
22. `'null'` is removed from `CORS_ALLOWED_ORIGINS` (and `CORS_ORIGIN_WHITELIST` if present).
23. A request with `Origin: null` to `/api/plugin/*` or `/api/mcp` receives no
    `Access-Control-Allow-Origin` header.

### VULN-8
24. `validate_access_token()` uses `timezone.now()` for the expiration comparison.
25. `delete_expired_tokens()` uses `timezone.now()`.
26. Passing an expired token returns HTTP 403 (not 500).
27. Tests cover: valid token, expired token (expects 403), no expiration set (expects pass-through).

### ENH-1 (TOTP 2FA)
28. New endpoints:
    - `POST /api/2fa/setup/` — creates a pending TOTP device, returns `otpauth://` URI and a
      base64-encoded QR code PNG. Requires authenticated user (Knox token). Idempotent: calling
      again replaces any unconfirmed device.
    - `POST /api/2fa/verify/` — accepts `{"code": "123456"}`, confirms the pending device,
      marks it active. Returns 400 on wrong code, 404 if no pending device exists.
    - `DELETE /api/2fa/` — deactivates 2FA. Requires a valid current TOTP code in the request
      body. Returns 400 on wrong code.
    - `POST /api/2fa/login/` — second-step login. Accepts `{"token": "<knox-token>", "code":
      "123456"}`. If the Knox token belongs to a user with an active TOTP device, validates the
      code and returns the same Knox token (or a new one). Returns 403 on wrong code.
29. Login flow: if a user has an active TOTP device, the existing `POST /api/auth/login/`
    endpoint returns HTTP 202 with `{"2fa_required": true, "token": "<knox-token>"}` instead of
    200. The client must complete `/api/2fa/login/` before the token is treated as fully
    authenticated. Fully-authenticated tokens (no 2FA required, or 2FA verified) return 200 as
    before.
30. Project-level 2FA requirement:
    - `Project` model gains a boolean field `require_2fa` (default `False`).
    - Project creation endpoint (`POST /api/projects/`) accepts `require_2fa` in the request body.
    - Project settings endpoint (PATCH `/api/projects/<id>/`) accepts `require_2fa`; only project
      owners may change it.
    - Any project-scoped endpoint (tokens, translations, members, webhooks, etc.) checks: if
      `project.require_2fa` is True and the requesting user does not have an active confirmed TOTP
      device, the request is rejected with HTTP 403 and `{"detail": "This project requires 2FA.
      Enable two-factor authentication to access it."}`.
    - A Knox token that has not completed the 2FA login step is also rejected with the same 403
      on 2FA-required projects.
    - Endpoints that are not project-scoped (user profile, 2FA setup/verify, login) are never
      blocked by the project 2FA gate.
31. Backup codes: `POST /api/2fa/setup/` also returns 10 single-use backup codes. Codes are
    stored hashed. Accepted in place of a TOTP code at `/api/2fa/login/` and `DELETE /api/2fa/`.
32. CLI / Figma plugin / MCP endpoints use `ProjectAccessToken` (not Knox), so they are
    unaffected by the 2FA gate.
33. `django-otp`, `django-otp-totp`, `qrcode[pil]` added to dependencies.
34. Tests: setup flow, verify flow, login with/without 2FA, expired TOTP code, backup code usage,
    backup code single-use enforcement, project 2FA gate (user with/without 2FA on required
    project), project creation with require_2fa, project settings update require_2fa.

---

## Edge Cases & Error States

- **VULN-2/3:** Host resolves to multiple IPs (round-robin DNS) — validate all resolved
  addresses; reject if any is in a blocked range.
- **VULN-2/3:** Hostname resolves to IPv6 — blocklist covers `::1/128`; extend to cover
  `fc00::/7` (ULA) and `fe80::/10` (link-local).
- **VULN-2/3:** DNS resolution failure — treat as validation failure; log and skip webhook.
- **VULN-5:** App startup with no `ALLOWED_HOSTS` env var — log `WARNING`, default to localhost.
  This is intentional developer ergonomics; production operators must set the var.
- **VULN-6:** Existing React SPA fetches that lack CSRF tokens — these use Knox token auth, so
  DRF `TokenAuthentication` classes are not subject to CSRF enforcement. No SPA changes needed.
- **ENH-1:** User loses authenticator device — backup codes are the recovery path. No
  admin-bypass reset flow in scope; operator can delete TOTP devices via Django admin.
- **ENH-1:** User calls `/api/2fa/setup/` while a confirmed device already exists — return
  400 ("2FA already active; disable first").
- **ENH-1:** Replay attack on TOTP code — `django-otp` enforces single-use per time window
  by default.
- **ENH-1:** Clock skew — `django-otp` allows ±1 time step (30 s) tolerance by default.
- **ENH-1 / project gate:** Owner enables `require_2fa` on a project while members without 2FA
  are already active — those members immediately lose access and see the 403 message until they
  set up 2FA. No grace period.
- **ENH-1 / project gate:** User is a member of multiple projects; only 2FA-required projects
  block them. Projects where `require_2fa = False` remain accessible without 2FA.
- **ENH-1 / project gate:** User enables 2FA after being blocked — access is restored on the
  next request without any extra step (the gate re-checks device status on every request).

---

## Integration Points

| Component | Findings |
|-----------|----------|
| `api/views/roles.py` | VULN-1 (generate_token), VULN-8 (delete_expired_tokens) |
| `api/dispatcher.py` | VULN-2 (webhook SSRF) |
| `api/translation_providers/generic_ai.py` | VULN-3 (AI endpoint SSRF) |
| `repository/settings.py` | VULN-4 (DEBUG), VULN-5 (ALLOWED_HOSTS), VULN-6 (CSRF middleware), VULN-7 (CORS null) |
| `api/views/plugin.py` | VULN-8 (validate_access_token), ENH-1 (unaffected — ProjectAccessToken path) |
| `api/urls.py` | ENH-1 (new 2FA endpoints) |
| `api/models/users.py` | ENH-1 (TOTP device model, backup code model) |
| `api/models/projects.py` (or equivalent) | ENH-1 (`require_2fa` field on Project model) |
| `api/views/projects.py` (or equivalent) | ENH-1 (accept `require_2fa` on create/update) |
| `api/views/auth.py` (or equivalent login view) | ENH-1 (202 response for 2FA-required users) |
| All project-scoped views | ENH-1 (project 2FA gate check) |
| `webui/` (React SPA) | ENH-1 (2FA setup UI, project settings toggle, blocked-access message) |
| `requirements.txt` / `pyproject.toml` | ENH-1 (new dependencies) |
| `api/tests/` | All findings |

---

## Non-Functional Requirements

- **Security:** No new credentials or tokens stored in plaintext. TOTP secrets stored via
  `django-otp`'s model (uses Django ORM; encrypt at rest if `SECRET_KEY` is rotated).
- **Performance:** SSRF validation adds one DNS lookup + IP check per webhook/AI call. This
  is acceptable; webhooks are already async (daemon threads).
- **Backwards compatibility:** Token format changes (VULN-1) only affect newly generated tokens.
  Existing `ProjectAccessToken` values continue to work.
- **Logging:** SSRF validation failures must be logged at `WARNING` level with the offending URL
  (redact auth parts). DEBUG/ALLOWED_HOSTS warnings logged at `WARNING` at startup.
- **i18n:** ENH-1 UI strings (QR setup page, error messages) should use Django's `gettext` if
  the project has i18n wiring; otherwise English only is acceptable.
- **Dependencies:** `django-otp`, `django-otp-totp`, `qrcode[pil]` added. No Celery or task
  queue introduced.

---

## Assumptions

1. **VULN-6 / CSRF + Knox:** Knox `TokenAuthentication` (header-based) is inherently CSRF-exempt
   in DRF. The SPA sends `Authorization: Token <knox>` headers; no CSRF token injection into
   React is needed.
2. **VULN-2/3 / IPv6 ULA:** IPv6 ULA (`fc00::/7`) and link-local (`fe80::/10`) are added to
   the blocklist even though the audit only lists `::1`. This is the correct comprehensive fix.
3. **VULN-5 / startup warning:** Defaulting to `localhost` with a warning (rather than refusing
   to start) is chosen to avoid breaking `docker-compose` dev setups that omit the env var.
4. **ENH-1 / 2FA gate scope:** The gate is per-project, not per-role. Any member of a project
   where `require_2fa = True` loses access to that project until they enable 2FA on their account.
   Any user can voluntarily enable 2FA regardless of project settings. Projects where
   `require_2fa = False` are accessible without 2FA to all members.
5. **ENH-1 / login step:** The 2FA second step uses the same Knox token issued by the first step
   (not a separate ephemeral token). The token is "promoted" to fully-authenticated by marking
   it in session or a model flag after TOTP verification.
6. **ENH-1 / backup codes:** 10 backup codes generated at setup. Codes shown only once (at setup).
   No email-based recovery in scope.
7. **No token invalidation (VULN-1):** Existing weak tokens are left in the database. The risk
   window is the time between now and natural token expiry/rotation. Acceptable per team decision.

---

## Resolved Questions

**Q: Is ENH-1 (TOTP 2FA) in scope?**
A: Yes. Full TOTP 2FA including setup, verify, login step, backup codes, and project-level gate.

**Q: CSRF middleware — whole app or admin only?**
A: Whole app. Plugin.py and MCP endpoints use `AllowAny` + manual token validation (not session
auth), so they are not subject to CSRF by design. Knox token endpoints use header auth, which
is CSRF-exempt in DRF. No changes needed to CLI/Figma/MCP callers.

**Q: What is the 2FA gate scope — role-based or project-based?**
A: Project-based. A project owner can enable `require_2fa` on a project (at creation or in
settings). Any member of that project — regardless of role — must have an active TOTP device
to access it. Any user may voluntarily enable 2FA. Projects without `require_2fa` are unaffected.

**Q: Should existing weak tokens be invalidated?**
A: No. Only future tokens will be cryptographically secure. No migration required.

**Q: Can the token format/length change (VULN-1)?**
A: Yes. `secrets.token_urlsafe()` format and length is acceptable.

**Q: SSRF — stricter DNS-rebinding-resistant approach?**
A: No. Connecting to a pre-resolved IP breaks TLS/SNI on cloud-hosted services (CDNs, AWS ALB).
Single-check approach (resolve → validate → pass original URL to urlopen) is accepted for this
threat model.

**Q: ALLOWED_HOSTS default when env var absent?**
A: Default to `['localhost', '127.0.0.1']` and log a WARNING.

**Q: Is `null` CORS origin used by any legitimate tool?**
A: No. Remove it unconditionally.

**Q: Are tests required for all fixes?**
A: Yes. All changes must include new or updated tests in `api/tests/`.
