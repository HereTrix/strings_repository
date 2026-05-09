# Contributing to StringsRepository

Thank you for your interest in contributing! This document describes how to contribute and the requirements for acceptable contributions.

## Ways to Contribute

- Report bugs via [GitHub Issues](https://github.com/HereTrix/strings_repository/issues)
- Suggest features via GitHub Issues
- Submit pull requests for bug fixes or new features
- Improve documentation

## Developer Certificate of Origin

All contributions must be signed off with the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). Add a `Signed-off-by` line to each commit:

```
git commit -s -m "Your commit message"
```

This certifies that you wrote the code or have the right to submit it under the MIT license.

## Coding Standards

### Python (backend)

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide.
- Security linting is enforced via [Bandit](https://bandit.readthedocs.io/) — all PRs must pass the Bandit scan with no high-severity findings.
- Run locally: `bandit -c bandit.yml -r api/ -ll`

### TypeScript (frontend)

- Follow the project's [ESLint](https://eslint.org/) configuration in `webui/eslint.config.js`.
- All PRs must pass ESLint with zero errors **and** zero warnings (`--max-warnings 0`). Warnings are treated as errors.
- Run locally: `cd webui && npx eslint -c eslint.config.js --max-warnings 0`

Both checks run automatically in CI on every pull request.

## Testing Requirements

**All contributions must include tests.**

- **Bug fixes**: add a regression test that reproduces the bug before the fix. At least 50% of bugs fixed within any six-month period must have accompanying regression tests.
- **New functionality**: every major new feature must include automated tests covering the new behaviour. PRs that add significant functionality without tests will not be merged.
- **Test coverage**: the project targets ≥ 80% statement coverage. Do not submit changes that materially reduce coverage.

Run the backend test suite locally:

```bash
APP_SECRET_KEY=dev DB_ENGINE=sqlite3 DB_NAME=dev python manage.py test api
```

Run with coverage:

```bash
coverage run manage.py test api
coverage report
```

Run the frontend test suite:

```bash
cd webui && npm test
```

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes, following the coding standards above.
3. Add or update tests as required.
4. Ensure all CI checks pass (build, tests, Bandit, ESLint).
5. Sign off your commits with `git commit -s`.
6. Open a pull request against `main` with a clear description of what changed and why.
7. At least one maintainer review is required before merging.

## Reporting Bugs

Use [GitHub Issues](https://github.com/HereTrix/strings_repository/issues). For security vulnerabilities, see [SECURITY.md](SECURITY.md) instead.

## License

By contributing you agree that your contributions will be licensed under the [MIT License](LICENSE).
