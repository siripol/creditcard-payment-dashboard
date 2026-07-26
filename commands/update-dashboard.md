---
description: Re-group all merchants and re-categorize business types from the current rules, then rebuild the dashboard — no new statements needed.
argument-hint: (no arguments — uses statements already imported)
---

Refresh the dashboard from the **existing** statements after a rules change (e.g. you just ran
`/set-merchantRule`, edited `merchant_rules.json` / `cards.config.json`, or changed the recurring
rule). This does NOT import new PDFs — it re-applies the current rules to all data and
regenerates everything.

How it works: `build_data.py` re-reads `merchant_rules.json` and re-runs `cat()` (business
category) and `merch()` (merchant grouping/cleanup) on every transaction each build, then
rewrites `data.js`, the Markdown reports, and the single-file `dashboard.html`. So one rebuild
re-groups merchants and re-categorizes correctly.

Do this:

1. **Check inputs.** Confirm `statements/` still holds the PDFs (or `.txt_cache/` is present).
   If there are no statements and no cache, stop and tell the user to run `/update-statement`
   with the PDFs first — the dashboard can't be re-derived from `data.js` alone (it has no raw
   descriptions to re-categorize).
2. **Record the baseline** for a before/after diff: current category totals and merchant count
   (from `data.js` / `spending_report.md` if present).
3. **Rebuild.** Run `python3 build_data.py` (Python 3.12+; use `python3.12` if `python3` is
   older). No new files are imported; existing statements are re-parsed and re-grouped with the
   current rules.
4. **Report the re-grouping** as a short table: number of merchants before → after (how many
   collapsed), any category totals that moved, and the number of transactions whose category
   changed.
5. **Relay merchant-grouping suggestions.** If the build prints a `MERCHANT GROUPING
   SUGGESTIONS` block, show it and offer the ready `/set-merchantRule` line — do not auto-apply.
6. **Deliver** the refreshed `dashboard.html` and summarize what changed vs. the baseline.
7. **Never guess numbers** — every figure comes from the generated data/reports. On a build
   error, show the error and stop; do not summarize from stale data.
