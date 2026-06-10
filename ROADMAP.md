# Roadmap

This document describes the planned direction for StringsRepository over the next 12+ months. Items are not guaranteed and priorities may shift based on community feedback.

## Near Term (next 3 months)

- **Signed releases** — GPG-signed git tags and release artifacts so users can verify authenticity
- **Developer Certificate of Origin (DCO) enforcement** — automated DCO check on all pull requests
- **Improved test coverage** — expand automated test suite toward and beyond 80% statement coverage
- **Audit log API** — expose the full change history via a queryable REST endpoint for compliance workflows

## Medium Term (3–6 months)

- **Webhook retry and delivery log** — automatic retry on failed webhook deliveries with a per-endpoint delivery history UI
- **Batch translation import improvements** — conflict resolution UI when importing strings that already exist
- **Translation progress dashboard** — per-language and per-scope completion percentages with exportable reports
- **SAML / SSO support** — enterprise single sign-on via SAML 2.0 for organisations that require it
- **Rate limiting** — configurable per-endpoint rate limiting built into the application layer

## Long Term (6–12 months)

- **Live serving URL** - possibility to update translations using live URL
- **Plugin API** — stable, versioned extension point for community plugins (custom file formats, translation providers, etc.)
- **Offline CLI mode** — allow the CLI to queue changes locally and sync when connectivity is restored
- **Android `.xml` plural support improvements** — full parity with iOS CLDR plural handling for Android projects

## Out of Scope

The following are explicitly not planned:

- Replacing or wrapping existing general-purpose translation management platforms (the project targets teams that want full data ownership)
- Built-in payment or billing features
- Native mobile applications

## Feedback

Have a feature request or want to influence priorities? Open a [GitHub Issue](https://github.com/HereTrix/strings_repository/issues) with the `enhancement` label.
