---
description: Re-categorize all transactions and rebuild the dashboard from the existing statements — no new statements needed.
argument-hint: (no arguments — uses statements already imported)
---

Refresh the dashboard from the **existing** statements after a config change (e.g. you edited
`cards.config.json` or changed the recurring rule). This does NOT import new PDFs — it re-runs
the build on all data and regenerates everything.

How it works: each build re-parses the cached statement text, re-runs `category()` (business
category), `merchant_name()` (display name) and `merchant_group()` (instalment grouping key)
on every transaction, and re-reads `cards.config.json`, `merchant_category.json` and
`recurring_rule.js`, then rewrites `data.js`, the Markdown reports, and the single-file
`dashboard.html`.

Do this:

1. **Check inputs.** Confirm `statements/` still holds the PDFs (or `.txt_cache/` is present).
   Source precedence is `statements/` PDFs → `.txt_cache/` → **`data.js`**: when there are no
   statements and no cache, the build falls back to the existing `data.js`, re-deriving
   `category()` / `merchant_name()` / `merchant_group()` from each transaction's stored `desc`
   and `merch` — enough to fix a stale dashboard whose rows predate `merchGroup`. This is
   best-effort: `data.js` stores `desc` up to 2048 chars, so a description built before that cap
   may be truncated; for a guaranteed full re-categorize, run `/update-statement` with the PDFs.
   If `data.js` is also missing, stop and tell the user to run `/update-statement` first.
2. **Record the baseline** for a before/after diff: current category totals and merchant count
   (from `data.js` / `spending_report.md` if present).
3. **Rebuild.** Run `python3 build_data.py` (Python 3.12+; use `python3.12` if `python3` is
   older). No new files are imported; existing statements are re-parsed and re-categorized.
4. **Report** any category totals that moved and the number of transactions whose category
   changed.
5. **Deliver** the refreshed `dashboard.html` and summarize what changed vs. the baseline.
6. **Never guess numbers** — every figure comes from the generated data/reports. On a build
   error, show the error and stop; do not summarize from stale data.
