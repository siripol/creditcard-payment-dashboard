---
description: Update the credit-card spending dashboard from new statement PDFs — rebuild data, reports, and the offline dashboard.
argument-hint: (attach the new statement PDF(s) first)
---

Run the monthly credit-card spending dashboard update.

Steps:

0. **Set the data dir.** `export CC_DATA_DIR="${CC_DATA_DIR:-$HOME/.credit-card-dashboard}"; mkdir -p "$CC_DATA_DIR/statements"`.
   All statements/config/outputs live under `$CC_DATA_DIR`; the build script is run from
   `$CLAUDE_PLUGIN_ROOT` (installed code) — see SKILL.md "Paths: CODE vs DATA".
1. **Find new statements.** Collect any PDF(s) the user just attached plus any already in
   `$CC_DATA_DIR/statements/`. Copy attached PDFs into `$CC_DATA_DIR/statements/`. If there are no
   new PDFs at all, tell the user there's nothing to update and stop.
2. **Record the baseline** for a before/after comparison: the current latest month and total
   (read `$CC_DATA_DIR/monthly_brief.md` if it exists).
3. **Build.** Run `python3 "$CLAUDE_PLUGIN_ROOT/skills/credit-card-spending-dashboard/build_data.py"`
   (requires Python 3.12+; use `python3.12` explicitly
   if `python3` is older). This converts each PDF to text (cached), extracts transactions,
   removes duplicates and reversal pairs, categorizes from the description, and regenerates
   `data.js`, the Markdown reports, and the self-contained `dashboard.html`.
4. **Report the build stats** as a small table: files / raw lines / duplicates removed /
   reversal pairs / final transactions / number of cards detected.
5. **Anomaly checks** before trusting the result:
   - duplicates-removed unusually high → a duplicate file may be in `statements/`.
   - latest month unchanged after adding a file → that file may not have been read.
   - total dropped vs. the last run → investigate before reporting.
   - an unexpected new card key appeared → confirm it's a real new card, not a mis-parse.
6. **Deliver** `dashboard.html` to the user and summarize the latest month: total, change vs.
   the previous month, top movers, top merchants, points to review, and a couple of concrete
   reduction ideas (framed as estimates, not financial advice).
7. **Never guess numbers** — every figure must come from the generated data/reports. On a
   build error, show the error and stop; do not summarize from stale data.
