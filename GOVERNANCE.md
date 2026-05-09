# Project Governance

## Overview

StringsRepository is an open-source project maintained by its core team. This document describes how the project is governed, how decisions are made, and the roles within the project.

## Key Roles

### Maintainer

Maintainers have write access to the repository and are responsible for:

- Reviewing and merging pull requests
- Triaging issues and bug reports
- Making release decisions
- Setting project direction
- Ensuring the security and quality of the codebase

Current maintainers:

| Name | GitHub |
|------|--------|
| HereTrix | [@HereTrix](https://github.com/HereTrix) |
| Andrei Makarov | [@anmcarrow](https://github.com/anmcarrow) |

### Contributor

Anyone who has had a pull request merged into the project. Contributors may propose changes, review PRs (non-binding), and participate in discussions.

### User

Anyone who uses StringsRepository. Users are encouraged to report bugs, request features, and participate in discussions via GitHub Issues.

## Decision Making

Day-to-day decisions (bug fixes, minor improvements, dependency updates) are made by any maintainer and require at least one approving review before merging.

Significant decisions (new major features, breaking changes, architectural changes, dependency additions) are discussed in a GitHub Issue or PR before work begins. If maintainers cannot reach consensus, the project lead has the final say.

## Becoming a Maintainer

Regular contributors who demonstrate sustained, high-quality involvement may be invited to become maintainers. Invitation is at the discretion of existing maintainers. There is no formal nomination process; maintainers identify strong contributors over time.

## Access Continuity

To ensure the project can continue if key individuals become unavailable:

- Repository admin access is held by at least two people.
- Credentials required to publish releases (package registries, container registry) are stored in GitHub repository secrets accessible to all maintainers.
- If all current maintainers become unavailable, the project may be forked under its MIT license by any interested party.

The project aims for a bus factor of 2 or more — no single person should be the sole holder of any access or knowledge required to maintain or release the project.

## Changes to Governance

Changes to this document require a pull request and approval from at least one other maintainer.
