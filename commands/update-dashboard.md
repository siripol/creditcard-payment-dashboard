---
description: Re-categorize all transactions and rebuild the dashboard from the existing statements — no new statements needed. Also looks up real names for any Card ••xxxx cards from statement text.
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

0. **Set the data dir + use the installed code.** `export CC_DATA_DIR="${CC_DATA_DIR:-$HOME/.credit-card-dashboard}"`
   and always run the build from `$CLAUDE_PLUGIN_ROOT` — never a copied script — so this uses the
   **newest** `build_data.py`/`index.html` against your existing data (see SKILL.md "Paths: CODE vs
   DATA"). **Staleness guard:** if `$CC_DATA_DIR/data.js` exists, compare its `CCDATA.version` with
   the plugin's `plugin.json` version; if they differ, the dashboard was built by an older plugin →
   **force a full rebuild** and say so (a version bump must never leave an old dashboard in place).
1. **Check inputs.** Confirm `$CC_DATA_DIR/statements/` still holds the PDFs (or `.txt_cache/` is present).
   Source precedence is `statements/` PDFs → `.txt_cache/` → **`data.js`**: when there are no
   statements and no cache, the build falls back to the existing `data.js`, re-deriving
   `category()` / `merchant_name()` / `merchant_group()` from each transaction's stored `desc`
   and `merch` — enough to fix a stale dashboard whose rows predate `merchGroup`. This is
   best-effort: `data.js` stores `desc` up to 2048 chars, so a description built before that cap
   may be truncated; for a guaranteed full re-categorize, run `/update-statement` with the PDFs.
   If `data.js` is also missing, stop and tell the user to run `/update-statement` first.
2. **Record the baseline** for a before/after diff: current category totals and merchant count
   (from `data.js` / `spending_report.md` if present).
3. **Rebuild.** Run `python3 "$CLAUDE_PLUGIN_ROOT/skills/credit-card-spending-dashboard/build_data.py"`
   (Python 3.12+; use `python3.12` if `python3` is older) with `CC_DATA_DIR` exported. No new files
   are imported; existing statements are re-parsed and re-categorized.
4. **Name any `Card ••xxxx` cards from statement text.** After the rebuild, look at
   `CCDATA.cardMeta`: any card whose `name` is still the fallback `Card ••<last4>` has no name in
   `cards.config.json`. For each such card, try to discover its real name:
   - In `.txt_cache/*.txt`, find the card's masked-PAN line — the PAN whose clear trailing 4 digits
     equal the card's last-4 (same anchor as the build's `_CARD_HEADER_RE` in `build_data.py`) — and
     read the lines around it (statement header block, or the lines just above/below the PAN) for a
     plausible **bank + card product name**. This reads statement text (handled by Claude) — say so.
   - **Propose → confirm:** show a table `last4 → suggested name (source line)` and ask the user to
     accept or edit each. **Never invent a name** — if none is found for a card, say so and point to
     `/set-cardName <last4> "<name>"`.
   - On confirmation, upsert each accepted `name` into `cards.config.json` (preserve `mm` / other
     keys, same as `/set-cardName`) and **rebuild again** so the buttons pick up the names.
   - If there is no `.txt_cache` (the source was `data.js` only), skip this step and note that
     naming needs statement text or `/set-cardName`.
5. **Report** any category totals that moved and the number of transactions whose category
   changed.
6. **Deliver** the refreshed `dashboard.html` and summarize what changed vs. the baseline.
7. **Never guess numbers** — every figure comes from the generated data/reports. On a build
   error, show the error and stop; do not summarize from stale data.
