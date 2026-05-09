# Threat Model and Assurance Case

This document is the project's assurance case. It identifies assets, trust boundaries, threat actors, mitigations, and residual risks, and justifies that the security requirements stated in [SECURITY.md](../SECURITY.md) are met.

---

## 1. Scope

StringsRepository is a self-hosted translation management service. Operators run it as a Docker container on infrastructure they control. The application exposes an HTTP API and a React web UI. It optionally connects to external services: third-party AI providers (translation, verification) and operator-configured webhook endpoints.

This threat model covers the application layer. Network-layer controls (firewall, DDoS protection, TLS termination) are the operator's responsibility and are explicitly out of scope.

---

## 2. Assets

| Asset | Sensitivity | Notes |
|-------|------------|-------|
| Translation strings and project data | Medium | Core product data; loss or leak affects the operator's product |
| User credentials (passwords, tokens, passkeys) | High | Enable impersonation |
| API keys and webhook auth tokens | High | Stored encrypted at rest; exposure could allow access to third-party services |
| AI provider API keys | High | Stored per-project encrypted at rest |
| Application secret key (`APP_SECRET_KEY`) | Critical | Compromise allows forging sessions and decrypting stored secrets |
| Database contents | High | Contains all of the above |
| Webhook signing secrets | Medium | Allow forging payloads to downstream webhook consumers |

---

## 3. Trust Boundaries

```
┌──────────────────────────────────────────────────────────┐
│  Internet / Untrusted Zone                               │
│  - End users (browsers, CLI, CI pipelines)               │
│  - AI provider APIs (outbound)                           │
│  - Webhook consumers (outbound)                          │
└────────────────┬─────────────────────────────────────────┘
                 │  TLS-terminating reverse proxy (operator responsibility)
                 ▼
┌──────────────────────────────────────────────────────────┐
│  Application Zone (Docker container)                     │
│  - Django REST Framework API                             │
│  - React frontend (served as static files)               │
│  - django-q2 async task worker                           │
│  - Knox token auth / WebAuthn / TOTP 2FA                 │
└────────────────┬─────────────────────────────────────────┘
                 │  DB connection (internal network, operator-configured)
                 ▼
┌──────────────────────────────────────────────────────────┐
│  Data Zone                                               │
│  - PostgreSQL / MySQL / SQLite database                  │
│  - Filesystem (uploaded scope images)                    │
└──────────────────────────────────────────────────────────┘
```

**Trust boundary crossings:**
1. Client → reverse proxy (encrypted by operator's TLS config)
2. Reverse proxy → application (internal network; operator's responsibility)
3. Application → database (internal network; credential-protected)
4. Application → third-party AI APIs (outbound HTTPS with TLS cert verification)
5. Application → webhook endpoints (outbound HTTPS with TLS cert verification)

---

## 4. Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| Unauthenticated internet user | HTTP access to public endpoints | Data theft, unauthorized access |
| Authenticated user (low-privilege role) | Valid session, project-scoped access | Privilege escalation, data exfiltration |
| Compromised third-party AI endpoint | Malicious responses to API calls | Prompt injection, data exfiltration |
| Supply chain attacker | Malicious package in dependency graph | Code execution, backdoor |
| Insider / rogue maintainer | Repository write access | Backdoor, credential theft |

---

## 5. Threat Analysis and Mitigations

### 5.1 Authentication and Session Management

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Password brute-force | Rate limiting at reverse proxy layer (operator responsibility); TOTP 2FA available | Low (with 2FA enabled) |
| Session token theft | Knox tokens are cryptographically random; short expiry on project access tokens; token revocation supported | Low |
| Credential replay | Tokens are per-device; revocation removes all issued tokens for a user | Low |
| Passkey / WebAuthn bypass | WebAuthn challenge/response is origin-bound and replay-resistant by design | Low |
| TOTP replay | django-otp enforces single-use codes within the validity window | Low |

### 5.2 Authorization and Access Control

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Horizontal privilege escalation (accessing another project) | All views enforce per-project role checks; project membership verified on every request | Low |
| Vertical privilege escalation (viewer → admin) | Role checks use DB-persisted role field; no client-side trust | Low |
| Insecure Direct Object Reference | Django ORM queries always scope resources to the authenticated user's projects | Low |
| Unauthenticated API access | All non-auth endpoints require a valid Knox token; enforced by DRF permission class | Low |

### 5.3 Input Validation and Injection

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| SQL injection | Django ORM with parameterised queries used exclusively; no raw SQL in application code | Low |
| XSS (stored) | DRF serializers return JSON; React escapes values by default; Django template auto-escaping | Low |
| XML external entity (XXE) | `defusedxml` used for all XML parsing (Android resources, .resx files) | Low |
| Path traversal in file upload | Uploaded files written to a media directory with no execution permission; filenames sanitised | Low |
| Malicious import file (fuzz-tested formats) | Atheris fuzzing over all file parsers runs on every PR and weekly; parsers use safe libraries | Low |
| CSRF | Django's CSRF middleware enabled for all state-changing requests | Low |

### 5.4 Sensitive Data Protection

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| API key / webhook token exposure via API response | Sensitive fields are write-only in serializers; never returned in responses | Low |
| Database dump exposes credentials | Passwords hashed with Django's PBKDF2-SHA256 (iterated, salted); sensitive fields encrypted with `cryptography` library using a key derived from `APP_SECRET_KEY` | Medium (depends on strength of APP_SECRET_KEY) |
| Log exposure of credentials | No credentials or tokens are passed via URL query parameters; request logging would not capture Authorization headers | Low |

### 5.5 Third-Party Integrations

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Malicious AI provider response (prompt injection) | AI provider responses are treated as suggestion data only; applied as standard translation updates with history; no code execution from responses | Low |
| SSRF via webhook URL | Webhook URLs are operator-configured, not end-user-configured; only project admins/owners can set them | Low |
| TLS MITM on outbound requests | `requests` library verifies TLS certificates on all outbound calls; disabled only by explicit per-project setting (for self-signed certs in lab environments) | Low |
| Compromised AI provider returns sensitive data | AI requests contain only the string text to translate/verify; no user credentials or PII are sent | Low |

### 5.6 Supply Chain

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Malicious dependency | Dependabot monitors Python and npm dependencies; Trivy scans the Docker image for known CVEs on every release | Medium (zero-day window) |
| Compromised GitHub Action | All GitHub Actions are pinned to exact commit SHAs, not mutable tags | Low |
| Build environment compromise | Builds run in GitHub-hosted ephemeral runners; no persistent state between runs | Low |

### 5.7 Release and Distribution

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Tampered release artifact | Docker image digest published in `checksums.txt`; file signed with maintainer GPG key | Low |
| Rogue release | Release workflow requires a git tag signed by a maintainer; only maintainers can create tags | Low |

---

## 6. Security Requirements and Justification

This section maps each security requirement from [SECURITY.md](../SECURITY.md) to the mitigations above.

| Requirement | Justification |
|-------------|--------------|
| Knox token authentication | All API endpoints require a valid token (§5.1). Tokens are cryptographically random and revocable. |
| Per-project RBAC | Role is checked on every request; no client-side trust (§5.2). |
| TOTP 2FA | Single-use codes with django-otp; replay-resistant (§5.1). |
| Passkeys (WebAuthn) | Origin-bound challenge/response; phishing-resistant (§5.1). |
| Encrypted storage of sensitive fields | `cryptography` library AES encryption with key derived from APP_SECRET_KEY (§5.4). |
| HMAC-SHA256 webhook signing | Consumers can verify payload integrity; signing secret not exposed via API (§5.4). |
| TLS cert verification on outbound requests | Prevents MITM on AI provider / webhook calls (§5.5). |
| Input validation on all endpoints | DRF serializers validate types and values; allowlist approach for enums (§5.3). |
| Django CSRF, SQL injection, XSS protections | Framework-level controls covering the most common web vulnerabilities (§5.3). |

---

## 7. Residual Risks and Operator Responsibilities

The following risks are **not mitigated by the application** and remain the operator's responsibility:

1. **Network-level attacks** — The application relies on the operator's reverse proxy for TLS termination, rate limiting, and DDoS protection.
2. **Weak APP_SECRET_KEY** — If this key is short or guessable, encrypted-at-rest fields and Django sessions are weakened. Operators must use a strong random key (≥ 50 characters).
3. **Database access control** — The application assumes the database is not directly reachable from the internet. Operators must enforce network-level restrictions.
4. **Third-party AI provider trust** — The application cannot verify the security practices of configured AI providers. Operators should only use trusted providers.
5. **Host OS and container security** — The application runs as a container; host isolation and OS patching are the operator's responsibility.

---

## 8. Review

This threat model is reviewed and updated when:
- New authentication mechanisms are added
- New external integrations are introduced
- A security vulnerability is reported and resolved
- The deployment model changes significantly
