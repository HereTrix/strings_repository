# Translation Bundles

Bundles are versioned snapshots of all project translations. They allow you to:

* Pin a specific translation state for a production release
* Roll back to a previous version by comparing and reviewing changes
* Test a specific version in QA without affecting live data

## How it works

1. **Create a bundle** — takes a point-in-time snapshot of all current translations across all languages. Version names are auto-generated (`v1`, `v2`, …) or you can provide a custom name (e.g. `release-2.1.0`).
2. **Activate a bundle** — marks it as the production bundle for the project. Only one bundle can be active at a time; activating a new one automatically deactivates the previous.
3. **Compare bundles** — diff any two bundles or compare a bundle against live translations to review what has changed, been added, or removed.
4. **Export from a bundle** — generate platform-specific files from any bundle snapshot in any supported format.

## Plugin / CLI integration

The export endpoint accepts an optional `bundle_version` field to control which translation source is used:

| `bundle_version` value | Behavior                                         | Use case                  |
| ---------------------- | ------------------------------------------------ | ------------------------- |
| omitted or `"live"`    | Live translations (latest edits in the database) | Local development         |
| `"active"`             | Currently active bundle                          | Production CI/CD          |
| `"v3"` (any name)      | That specific bundle                             | QA, rollback verification |

If `bundle_version='active'` is requested and no bundle is active, the API returns `404` with an explicit error message.

The version names `active` and `live` are reserved and cannot be used as bundle names.

## Live bundle serving

Activating a bundle also makes it the one served publicly if the project has **live bundle serving** enabled (Project → Info → Live Bundle) — "active" and "live" refer to the same bundle. See [docs/live-bundle.md](live-bundle.md) for the tokenized public API client applications use to fetch it directly.
