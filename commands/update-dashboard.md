---
description: Re-categorize all transactions and rebuild the dashboard from the existing statements — no new statements needed.
argument-hint: (no arguments — uses statements already imported)
---

Refresh the dashboard from the **existing** statements after a config change (e.g. you edited
`cards.config.json` or changed the recurring rule). This does NOT import new PDFs — it re-runs
the build on all data and regenerates everything.

How it works: each build re-parses the cached statement text, re-runs `cat()` (business
category) and `merch()` (merchant name) on every transaction, and re-reads `cards.config.json`
and `recurring_rule.js`, then rewrites `data.js`, the Markdown reports, and the single-file
`dashboard.html`.

Do this:

1. **Check inputs.** Confirm `statements/` still holds the PDFs (or `.txt_cache/` is present).
   If there are no statements and no cache, stop and tell the user to run `/update-statement`
   with the PDFs first — the dashboard can't be re-derived from `data.js` alone (it has no raw
   descriptions to re-categorize).
2. **Record the baseline** for a before/after diff: current category totals and merchant count
   (from `data.js` / `spending_report.md` if present).
3. **Rebuild.** Run `python3 build_data.py` (Python 3.12+; use `python3.12` if `python3` is
   older). No new files are imported; existing statements are re-parsed and re-categorized.
4. **Report** any category totals that moved and the number of transactions whose category
   changed.
5. **Deliver** the refreshed `dashboard.html` and summarize what changed vs. the baseline.
6. **Never guess numbers** — every figure comes from the generated data/reports. On a build
   error, show the error and stop; do not summarize from stale data.
