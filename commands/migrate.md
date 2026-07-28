---
description: Migrate a user's local config/state from their last-migrated version to the current plugin version, then rebuild.
argument-hint: (no arguments)
---

Bring the user's **local, git-ignored state** (`cards.config.json`, `merchant_category.json`,
`merchant_group.json`, `recurring_rule.js`, and the generated `data.js`) up to the **current plugin
version** after a plugin update. Configs survive plugin updates (git-ignored), so they can drift
from a newer schema/behavior; this command applies the recorded, per-version migration steps.

Driven by two files in `skills/credit-card-spending-dashboard/`:
- **`MIGRATIONS.md`** — the ordered, per-version ledger (shipped). Single source of truth for what
  each version changed and the action to apply.
- **`.cc_migration.json`** — a git-ignored marker recording the last-migrated version:
  `{ "version": "<x.y.z>" }`.

Do this:

1. **Read the from-version.** Open `.cc_migration.json`; if absent, treat as **baseline** (older
   than the earliest ledger entry — run all steps; they are idempotent, so this is safe).
2. **Read the current version** from `.claude-plugin/plugin.json` (`version`).
3. **If equal**, report "already at current version" and stop (still safe to have run — no changes).
4. **Apply each `MIGRATIONS.md` entry** with `from < version <= current`, in order. Follow each
   entry's action. Every transform must be **idempotent** — detect already-migrated shape and no-op
   — so a missing or stale marker never double-applies or corrupts. Some entries are code-only (no
   config action); note them but do nothing.
5. **Rebuild:** `cd skills/credit-card-spending-dashboard && python3 build_data.py` (Python 3.12+;
   use `python3.12` if older). This regenerates `data.js` and re-derives fields (e.g. `merchGroup`,
   `fx`) — which covers most "migrations" on its own.
6. **On success, stamp the marker:** write `{ "version": "<current>" }` to `.cc_migration.json`.
   **On a build error, show it and stop — do NOT stamp the marker.**
7. **Report** the steps applied and any **manual** follow-ups the ledger calls out (e.g. after the
   0.16.1 rename, re-add the marketplace: `/plugin marketplace add siripol/credit-card-spending-dashboard`).

> Maintainer note: every version bump must add its entry to `MIGRATIONS.md` **before** committing
> (see the pre-commit checklist in `CLAUDE.md`).
