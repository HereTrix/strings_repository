# Changelog

All notable changes to Strings Repository are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Planned
- **Internationalization (i18n):** Localize the web UI to support languages other than English, enabling non-English-speaking teams to use the application in their own language.

## [2.3.1] - 2026-05-09
- Fix ussue with 2FA enabled access

## [2.3.0] - 2026-05-09

### Added
- ARB (Application Resource Bundle) file format support for Flutter/Dart localization workflows

### Changed
- Improved MCP (Model Context Protocol) integration architecture for better stability and extensibility
- Enhanced project documentation and contributor guides

### Fixed
- Code quality improvements and CI pipeline enhancements
- OpenSSF Scorecard and code coverage reporting integration

## [2.0.0] - 2026-04-15

This is a major release introducing AI-assisted translation workflows, modern authentication, and significant platform improvements.

### Added
- **AI translation assistance**: Generic AI provider integration with configurable backends
- **Model Context Protocol (MCP)**: Built-in MCP server for AI tool integrations
- **Passkey/WebAuthn support**: Passwordless authentication using hardware security keys and biometrics
- **Two-factor authentication (2FA)**: TOTP-based 2FA for enhanced account security
- **Translation memory**: Automatic suggestions based on previously translated strings
- **Glossary**: Project-level terminology management to enforce consistent translations
- **Webhooks**: Event-driven notifications for translation workflow automation
- **Rate limiting**: API rate limiting to protect against abuse
- **CSV file processing**: Import and export translations via CSV format
- **AI verification**: Automated quality checks using AI to flag potential translation issues
- **Dark theme**: UI dark mode support
- **Scope feature**: Organize and filter translation keys by functional scope
- **Translation progress tracking**: Visual progress indicators per language

### Changed
- Significant URL structure refactoring for cleaner REST API paths
- MCP server improvements for better AI tool compatibility
- Security hardening: fixed exception detail exposure in API error responses

### Security
- Fixed API responses that exposed internal exception details to clients
- Added Dependabot for automated dependency vulnerability monitoring
- OpenSSF Scorecard integration for supply-chain security analysis
- All GitHub Actions pinned to specific commit SHAs

## [1.3.0] - 2026-03-14

### Added
- Markdown toolbar in the translation editor for rich-text string authoring
- Plural forms UI: edit and manage plural string variants directly in the interface
- JSON metadata format support for import and export

### Fixed
- Incorrect file name on exported translation files

## [1.2.0] - 2026-03-09

### Added
- xcstring file parser for Apple platform localization format
- Plural translation model: data model support for storing plural string variants
- Status field on tokens and translations for workflow state tracking
- Status filter on the translation list UI

### Changed
- Project API refactoring for cleaner endpoint structure
- Upgraded Python base container image
- Updated all library versions for improved security

### Fixed
- Missing language field on translation detail page
- Static files configuration issue
- Environment variable configuration issue

## [1.1.3] - 2025-08-22

### Fixed
- Webpack configuration issue affecting frontend build

## [1.1.2] - 2025-08-21

### Fixed
- History export issue
- Navigation issue

### Changed
- Dependency updates across frontend and backend packages

## [1.1.1] - 2025-07-04

### Fixed
- Apostrophe escaping in translation strings
- Various dependency updates for security and compatibility

### Added
- PO and MO (GNU gettext) file format support

## [1.1.0] - 2024-06-07

### Added
- Translation bundle export: export a set of translations as a single downloadable archive
- Bundle comparison export: compare two translation bundles and export the diff
- Translation history UI with filtering and export capability
- Webhook integration for external notification and automation

### Changed
- Backend structure refactoring for maintainability

## [1.0.0] - 2023-11-12

Initial public release of Strings Repository.

### Features
- String and translation management via REST API
- Web UI for translators and project managers
- Multi-language support with per-project language configuration
- User authentication and role-based access control
- Docker-based deployment with SQLite, PostgreSQL, and MySQL support

[Unreleased]: https://github.com/heretrix/strings_repository/compare/2.2.0...HEAD
[2.2.0]: https://github.com/heretrix/strings_repository/compare/v2.0.0...2.2.0
[2.0.0]: https://github.com/heretrix/strings_repository/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/heretrix/strings_repository/compare/1.2.0...v1.3.0
[1.2.0]: https://github.com/heretrix/strings_repository/compare/1.1.3...1.2.0
[1.1.3]: https://github.com/heretrix/strings_repository/compare/1.1.2...1.1.3
[1.1.2]: https://github.com/heretrix/strings_repository/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/heretrix/strings_repository/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/heretrix/strings_repository/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/heretrix/strings_repository/releases/tag/1.0.0
