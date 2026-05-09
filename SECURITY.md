# Security Policy

## Supported Versions

Security fixes are applied to the latest release only. We encourage all users to run the most recent version.

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues via [GitHub Security Advisories](https://github.com/HereTrix/strings_repository/security/advisories/new). This keeps the report private until a fix is ready.

Include as much of the following as possible:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (optional)

## Response Process

1. **Acknowledgement** — we will acknowledge receipt within 5 business days.
2. **Assessment** — we will assess severity and reproduce the issue within 10 business days.
3. **Fix** — a patch will be developed and tested. Timeline depends on severity:
   - Critical / High: within 14 days
   - Medium: within 30 days
   - Low: included in the next scheduled release
4. **Disclosure** — once a fix is released, the advisory will be published and the reporter credited (see below).

## Reporter Credit

We publicly credit reporters in the release notes and security advisory unless the reporter requests anonymity. If you would like to remain anonymous, state that in your report.

## Security Expectations

StringsRepository is a self-hosted application. The following security properties apply:

**What the software provides:**
- Knox token-based authentication for all API endpoints
- Per-project role-based access control (viewer, translator, editor, admin, owner)
- TOTP-based two-factor authentication (2FA) per user account
- Passkeys (FIDO2/WebAuthn) as a passwordless alternative
- Encrypted storage of sensitive fields (API keys, webhook URLs, webhook auth tokens) at rest
- HMAC-SHA256 webhook payload signing
- TLS certificate verification enforced on all outbound HTTP requests
- Input validation on all API endpoints
- Django's built-in CSRF protection, SQL injection protection, and XSS escaping

## Threat Model and Assurance Case

A complete threat model covering assets, trust boundaries, threat actors, and mitigations is published in [docs/threat-model.md](docs/threat-model.md). It documents how each security requirement stated in this policy is justified.

## Cryptographic Algorithm Agility

The application is designed so that operators can switch cryptographic algorithms without a code change if a primitive is broken.

**Password hashing** is controlled by Django's `PASSWORD_HASHERS` setting (see `repository/settings.py`). The default is PBKDF2-SHA256. To switch to Argon2id or bcrypt, install the required extra dependency (`argon2-cffi` or `bcrypt`) and move the desired hasher to the top of the list. Existing password hashes are automatically re-hashed on next login.

**Field encryption key derivation** is controlled by the `FIELD_ENCRYPTION_KEY_HASH` environment variable. Supported values: `sha256` (default), `sha384`, `sha512`. The derived key feeds into Fernet (AES-128-CBC + HMAC-SHA256) for at-rest encryption of API keys, webhook URLs, and webhook auth tokens. **Changing this value requires re-encrypting all stored fields** — rotate it only during a planned maintenance window with a documented migration.

**Webhook payload signing** uses HMAC-SHA256. This is part of the external API contract and cannot be changed without a versioned API migration.

**TOTP** uses HMAC-SHA1 by default for broad authenticator-app compatibility (see note below).

## Cryptographic Design Notes

**TOTP and HMAC-SHA1**

TOTP two-factor authentication (RFC 6238) uses HMAC-SHA1 as its pseudorandom function. SHA-1 has known collision weaknesses, but those weaknesses do not affect this use case: TOTP codes are short-lived, single-use, and the attacker does not control the HMAC input (the counter value). The relevant security property is second-preimage resistance, which SHA-1 retains at full strength.

The HMAC-SHA1 default is retained for broad authenticator-app compatibility. RFC 6238 specifies HMAC-SHA1 as the baseline algorithm, and widely-deployed apps (Google Authenticator, Apple Passwords) implement only HMAC-SHA1. Switching to HMAC-SHA256 would silently break setup for users of those apps. Operators who control their user base and can standardise on a modern authenticator (e.g. Aegis) may change the algorithm by setting the `algorithm` field on `TOTPDevice` objects at provisioning time.

**What the software does not provide:**
- Network-level security (firewall rules, DDoS protection) — these are the responsibility of the operator
- Automatic TLS termination — operators must configure a reverse proxy (nginx, Caddy, etc.) with TLS
- Rate limiting on authentication endpoints by default — operators should add this at the reverse proxy layer
- Guarantees about the security of third-party AI provider endpoints configured per-project

## Verifying Releases

Each release on the [GitHub Releases page](https://github.com/HereTrix/strings_repository/releases) includes a `checksums.txt` file containing the Docker image digest, and `checksums.txt.asc` — a detached GPG signature.

To verify a release:

```bash
# Import the maintainer's public key (one-time setup)
gpg --keyserver keys.openpgp.org --recv-keys 0F3FC613F74F07A3

# Verify the signature
gpg --verify checksums.txt.asc checksums.txt

# Check the image digest matches
cat checksums.txt
```

Git tags for each release are also GPG-signed. Verify a tag with:

```bash
git tag --verify v1.2.3
```

**Operator responsibilities:**
- Run the application behind a TLS-terminating reverse proxy configured to use TLS 1.2 or later. Use TLS 1.3 where possible — it mandates perfect forward secrecy (PFS) for all cipher suites. For TLS 1.2, restrict the configuration to ECDHE-based cipher suites (e.g. `ECDHE-RSA-AES256-GCM-SHA384`) to ensure PFS; disable static RSA key exchange (`RSA` prefix ciphers), which does not provide PFS.
- Keep the Docker image and host OS up to date
- Rotate `APP_SECRET_KEY` if it is ever exposed
- Restrict database access to the application process only
