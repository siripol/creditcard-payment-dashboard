---
description: Show the plugin version — the installed/declared version, the version the current dashboard was built with, and the last-migrated marker.
argument-hint: (no arguments)
---

Print which version of the plugin is in play, so it's easy to confirm an update actually took
effect. **Read-only** — writes nothing, builds nothing.

Do this — report each of these (skip any that are absent, and say so):

1. **Declared version** — read `version` from `.claude-plugin/plugin.json` (and confirm
   `.claude-plugin/marketplace.json` matches; flag if they differ).
2. **Dashboard build version** — if `skills/credit-card-spending-dashboard/data.js` exists, read
   `CCDATA.version` (also shown in the dashboard footer). This is the version that produced the
   **current** `data.js` / `dashboard.html`. If it differs from the declared version, the dashboard
   is stale — run `/update-dashboard` to rebuild.
3. **Last-migrated marker** — if `skills/credit-card-spending-dashboard/.cc_migration.json` exists,
   read its `version` (what `/migrate` last stamped).
4. **Source (optional)** — if this is a git checkout, show `git -C . describe --tags --always` /
   the latest `credit-card-spending-dashboard--v*` tag.

Render a short table, e.g.:

| | Version |
|---|---|
| Declared (plugin.json) | 0.17.0 |
| Dashboard (data.js) | 0.17.0 |
| Last migrated (.cc_migration.json) | 0.17.0 |

Close with one line: if declared == dashboard, "up to date"; else point to `/update-dashboard`
(dashboard stale) or `/migrate` (config behind).
