# Security Audit Report — StringsRepository

**Date:** 2026-05-02  
**Scope:** Full codebase audit (branch `main`)  
**Auditor:** Claude Code (Security Review)

---

## Summary

| Severity | Count |
|----------|-------|
| HIGH     | 6     |
| MEDIUM   | 2     |
| ENHANCEMENT | 1  |

---

## HIGH Severity

---

### VULN-1: Weak PRNG for Security Tokens — `api/views/roles.py:14`

**Category:** `weak_randomness`  
**Confidence:** 9/10

**Description:**  
`generate_token()` uses `random.choices()` (Mersenne Twister PRNG) which is **not cryptographically secure**. This token is used for both project invitation codes (line 178) and project access tokens (line 234). Mersenne Twister's state can be reconstructed after observing ~624 consecutive outputs.

**Exploit Scenario:**  
An attacker who can observe multiple invitation codes or access tokens (e.g., by being an invited member) can reconstruct the PRNG state and predict future tokens, gaining unauthorised access to projects without an invitation.

**Affected code:**
```python
# roles.py:1
import random
# roles.py:13-14
def generate_token(length=16):
    return ''.join(random.choices(string.ascii_letters, k=length))
```

**Fix:**
```python
import secrets
def generate_token(length=16):
    return secrets.token_urlsafe(length)
```

---

### VULN-2: SSRF via Webhook URL — `api/dispatcher.py:45,50`

**Category:** `ssrf`  
**Confidence:** 9/10

**Description:**  
`_send_webhook()` decrypts the user-configured webhook URL from the database and passes it directly to `urllib.request.urlopen()` without validating the host. Any authenticated project admin can configure a webhook pointing to an internal service.

**Exploit Scenario:**  
An attacker with project admin access configures a webhook endpoint to `http://169.254.169.254/latest/meta-data/iam/security-credentials/` (AWS metadata). When any project event fires (translation created, member invited, etc.), the application fetches the internal URL and logs or returns the response, leaking cloud provider credentials.

**Affected code:**
```python
# dispatcher.py:45,49-50
url = decrypt(endpoint.url)
req = urllib.request.Request(url, data=body, headers=headers, method='POST')
with urllib.request.urlopen(req, timeout=10) as resp:
```

**Fix:**  
Validate the URL before use. Block private IP ranges:
```python
import ipaddress, socket
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
]

def _validate_webhook_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only http/https allowed")
    host = parsed.hostname
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except Exception:
        raise ValueError("Cannot resolve host")
    for net in BLOCKED_NETWORKS:
        if ip in net:
            raise ValueError(f"Host resolves to blocked network: {ip}")
```

---

### VULN-3: SSRF via Generic AI Provider Endpoint — `api/translation_providers/generic_ai.py:37-47`

**Category:** `ssrf`  
**Confidence:** 8/10

**Description:**  
`GenericAIProvider` accepts a user-configured `endpoint_url` and calls `urllib.request.urlopen()` on it without any host validation. An authenticated admin can set the endpoint to any internal address.

**Exploit Scenario:**  
An attacker with project admin access configures a Generic AI translation integration with `endpoint_url = "http://localhost:5432"` or `"http://10.0.0.1/admin"`. When a translation job runs, the app makes an HTTP POST to the internal address, potentially leaking internal service banners or triggering internal state changes.

**Affected code:**
```python
# generic_ai.py:37-47
req = urllib.request.Request(
    self.endpoint_url,
    data=json.dumps(payload).encode(),
    ...
)
with urllib.request.urlopen(req) as response:
```

**Fix:** Apply the same IP-range blocklist described in VULN-2 before creating the `Request` object.

---

### VULN-4: `DEBUG = True` Hardcoded in Production Settings — `repository/settings.py:27`

**Category:** `information_disclosure`  
**Confidence:** 9/10

**Description:**  
`DEBUG = True` is hardcoded and cannot be overridden via environment variable. Django's debug mode exposes full tracebacks (including local variables, database queries, and settings values) in HTTP error responses. Any 500 error reveals stack traces containing database credentials, SECRET_KEY derivation paths, and internal file paths.

**Exploit Scenario:**  
An attacker sends a malformed request to any API endpoint (e.g., invalid JSON, unexpected type). The 500 response body contains a Django debug page showing the full stack trace, local variables (which may include decrypted secrets or tokens), and all `settings.*` values.

**Fix:**
```python
# settings.py
DEBUG = env_value('DEBUG') == 'true'  # default False
```
Never deploy with `DEBUG=True`.

---

### VULN-5: ALLOWED_HOSTS Defaults to `['*']` — `repository/settings.py:29-33`

**Category:** `host_header_injection`  
**Confidence:** 9/10

**Description:**  
When the `ALLOWED_HOSTS` environment variable is not set, the app accepts requests with any `Host` header. This enables **HTTP Host header injection** attacks.

**Exploit Scenario:**  
An attacker triggers a password-reset email flow (Django's built-in auth). The password-reset email uses `request.get_host()` to build the reset URL. With `ALLOWED_HOSTS = ['*']`, the attacker can send a POST to `/accounts/password-reset/` with `Host: evil.com`. The victim receives a password-reset link pointing to `http://evil.com/...`, which the attacker controls.

**Fix:**
```python
# settings.py
allowed = env_value('ALLOWED_HOSTS')
ALLOWED_HOSTS = allowed.split(',') if allowed else ['localhost', '127.0.0.1']
```
Require explicit configuration in production.

---

### VULN-6: CSRF Middleware Absent — `repository/settings.py:65-75`

**Category:** `csrf`  
**Confidence:** 8/10

**Description:**  
`django.middleware.csrf.CsrfViewMiddleware` is completely missing from the `MIDDLEWARE` list. While the REST API uses Knox token authentication (immune to CSRF), the Django **admin panel** (`/admin/`) and the `webui` app use session-based authentication. Without CSRF protection, any authenticated admin visiting a malicious page can have state-changing admin actions executed on their behalf.

**Exploit Scenario:**  
An attacker sends a phishing link to a logged-in Django admin. The page contains a hidden form that POSTs to `https://target.com/admin/auth/user/1/change/` with a new password. Because there is no CSRF token check, the admin's session cookie is sent automatically and the request succeeds, giving the attacker full account control.

**Fix:**  
Add `'django.middleware.csrf.CsrfViewMiddleware'` to `MIDDLEWARE`, placed after `SessionMiddleware`:
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    ...
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',   # ADD THIS
    ...
]
```

---

## MEDIUM Severity

---

### VULN-7: `CORS_ALLOWED_ORIGINS = ['null']` Permits Local File Requests — `repository/settings.py:35-37`

**Category:** `cors_misconfiguration`  
**Confidence:** 8/10

**Description:**  
The `null` origin is sent by browsers from `file://` URLs and sandboxed iframes. By listing it in `CORS_ALLOWED_ORIGINS`, the app allows JavaScript from local HTML files (opened directly in a browser) to make credentialed cross-origin requests to the plugin/MCP endpoints. Scope is limited to `/api/plugin/*` and `/api/mcp` by `CORS_URLS_REGEX`.

**Exploit Scenario:**  
An attacker sends a victim a `.html` file attachment. When opened locally, the page's JavaScript calls `fetch('https://target.com/api/plugin/push', { headers: { 'Access-Token': storedToken }, ... })` — and the CORS preflight succeeds because `null` origin is explicitly trusted. This enables exfiltration of translation data or injection of malicious strings into the project.

**Fix:**  
Remove `'null'` from `CORS_ALLOWED_ORIGINS`. If local dev requires it, scope it with an environment variable:
```python
CORS_ALLOWED_ORIGINS = [o for o in env_value('CORS_ORIGINS', '').split(',') if o]
```

---

### VULN-8: Token Expiration Comparison Uses Timezone-Naive Datetime — `api/views/plugin.py:29` / `api/views/roles.py:18`

**Category:** `auth_logic_flaw`  
**Confidence:** 8/10

**Description:**  
`validate_access_token()` (plugin.py:29) and `delete_expired_tokens()` (roles.py:18) compare `token.expiration` (a Django `DateTimeField` — timezone-aware when `USE_TZ = True`) against `datetime.datetime.now()` (timezone-naive). In Python 3 this raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Impact:**  
- In `validate_access_token`: the TypeError propagates uncaught, causing a 500 error instead of a 403. An expired token cannot be cleanly rejected — the endpoint crashes rather than refusing access. Depending on how the caller handles 500 responses, this could result in a fallback that grants access.  
- In `delete_expired_tokens`: expired tokens are never deleted (the comparison crashes), so expired tokens accumulate indefinitely.

**Fix:**
```python
# plugin.py:29
from django.utils import timezone
if access.expiration and access.expiration < timezone.now():

# roles.py:18
from django.utils import timezone
now = timezone.now()
```

---

## Security Enhancements

---

### ENH-1: Відсутня двофакторна автентифікація (2FA) — `api/models/users.py`, `repository/settings.py`

**Category:** `missing_mfa`  
**Priority:** P2 — Medium

**Description:**  
Додаток не підтримує 2FA через TOTP-додатки (Google Authenticator, Authy, 1Password тощо). Усі облікові записи захищені лише паролем. Компрометація пароля (phishing, credential stuffing, брутфорс) дає повний доступ без додаткового бар'єру.

**Ризик:**  
Адміністраторські та власницькі акаунти є особливо цінною ціллю — вони мають доступ до вебхуків, налаштувань інтеграцій (ключі AI-провайдерів), та всіх перекладів. Злом одного такого акаунту може призвести до SSRF (VULN-2, VULN-3) або витоку API-ключів.

**Рекомендований стек:**
- [`django-otp`](https://django-otp-official.readthedocs.io/) — основний пакет OTP для Django  
- [`django-otp-totp`](https://django-otp-official.readthedocs.io/en/stable/auth.html#totp-devices) — TOTP-пристрої (RFC 6238, сумісні з будь-яким auth-додатком)  
- [`qrcode`](https://pypi.org/project/qrcode/) — генерація QR-коду для налаштування

**Орієнтовний план впровадження:**

1. Додати залежності:
   ```
   django-otp
   django-otp-totp
   qrcode[pil]
   ```

2. Підключити в `settings.py`:
   ```python
   INSTALLED_APPS += ['django_otp', 'django_otp.plugins.otp_totp']
   MIDDLEWARE += ['django_otp.middleware.OTPMiddleware']  # після AuthenticationMiddleware
   ```

3. Додати ендпоінти в `api/urls.py`:
   - `POST /api/2fa/setup/` — генерує TOTP-пристрій і повертає `otpauth://` URI + QR-код (base64 PNG)
   - `POST /api/2fa/verify/` — підтверджує 6-значний код, активує пристрій
   - `DELETE /api/2fa/` — деактивує 2FA (потребує підтвердження поточним кодом)
   - `POST /api/2fa/login/` — другий крок входу після Knox-логіну (якщо 2FA увімкнено)

4. Модифікувати логін-ендпоінт: якщо для акаунта зареєстрований активний TOTP-пристрій, Knox-токен не видавати до проходження TOTP-верифікації.

5. Рекомендовано зробити 2FA обов'язковим для ролей `owner` та `admin`.

**Важливо:** Передбачити backup-коди (одноразові) на випадок втрати пристрою.

---

## Informational Notes (Not Security Vulnerabilities)

- **`api/crypto.py`:** Fernet key is derived via `SHA-256(SECRET_KEY)`. This is acceptable if `SECRET_KEY` is high-entropy (which Django enforces). No finding.  
- **`api/dispatcher.py` template rendering:** The `_render_template()` function is a plain string replacement — not a template engine — so SSTI is not applicable.  
- **Django ORM queries:** All database queries use Django ORM parameterisation. No SQL injection found.  
- **File upload (`api/views/scope.py:125`):** Image files go through Django's `ImageField` + Pillow validation. No direct path traversal or command injection found.

---

## Remediation Priority

| Priority | Finding | Effort |
|----------|---------|--------|
| P0 — Immediate | VULN-1: Weak PRNG for tokens | 5 min |
| P0 — Immediate | VULN-4: DEBUG=True | 5 min |
| P0 — Immediate | VULN-6: No CSRF middleware | 5 min |
| P1 — High | VULN-2: SSRF in webhooks | 1 hour |
| P1 — High | VULN-3: SSRF in GenericAI | 30 min |
| P1 — High | VULN-5: ALLOWED_HOSTS wildcard | 5 min |
| P2 — Medium | VULN-7: CORS null origin | 5 min |
| P2 — Medium | VULN-8: Naive datetime comparison | 15 min |
| P2 — Medium | ENH-1: Додати 2FA (TOTP) для входу | 1-2 дні |
