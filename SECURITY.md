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
- Run the application behind a TLS-terminating reverse proxy
- Keep the Docker image and host OS up to date
- Rotate `APP_SECRET_KEY` if it is ever exposed
- Restrict database access to the application process only
