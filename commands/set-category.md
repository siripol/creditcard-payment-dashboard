---
description: Set the spending category for merchants that land in Other — type the mapping yourself, or let Claude classify them.
argument-hint: <merchant keyword> <Category>  (or no args to auto-classify)
---

Fix merchants that fall into `Other` by mapping a keyword to a category. Rules are written to
**`merchant_category.json` only** (project root, git-ignored, **not** shipped — so they survive
plugin updates). This only sets the **category** — merchant display names are never changed.

Valid categories (the value must be one of these): `Travel`, `Insurance`, `Shopping & Retail`,
`Food & Dining`, `Subscriptions & Digital`, `Groceries & Convenience`, `Transport & Ride-hailing`,
`Online Shopping`, `Health & Medical`, `Utilities & Telecom`, `Fuel`, `Card Fees`, `Other`.

The user's input is: `$ARGUMENTS`

### If the user gave `<keyword> <Category>` (manual)
1. Validate the category against the list above; if it's not exact, pick the closest valid key and
   say which you used.
2. Open `merchant_category.json` (create from `skills/credit-card-spending-dashboard/merchant_category.example.json`
   emptied to `{}` — keep the `_comment` — if it doesn't exist). **Upsert** `"<keyword>": "<Category>"`,
   preserving all other entries. Also set provenance: `_source["<keyword>"] = "user"` (a reserved
   `_source` map; the build ignores `_`-prefixed keys). This marks the entry as **pinned** —
   `/auto-categorize` will never overwrite it.
3. Rebuild: `python3 build_data.py` (Python 3.12+; use `python3.12` if older). Report how many
   `Other` transactions moved to the new category.

### If there are no args (let Claude classify)
1. Read the distinct merchants still in `Other` — from the build's `UNCATEGORIZED MERCHANTS`
   report (run `python3 build_data.py` first if needed) or from `data.js` (`CCDATA.tx` where
   `cat === 'Other'`, grouped by `merchGroup`).
2. For each, propose a category **from the valid list** using your own knowledge of the merchant
   (e.g. `EXAMPLE MALL` → `Shopping & Retail`, `EXAMPLE INSURANCE` → `Insurance`). No external API is
   used — you (this session) do the classifying.
3. **Show the proposed keyword → category table and ask the user to confirm or edit** before
   writing anything.
4. On confirmation, upsert the entries into `merchant_category.json` — each with
   `_source["<keyword>"] = "llm"` (Claude classified it, not pinned by the user) — rebuild, and
   report what changed.

> Note: to bulk-fix categories across **all** merchants (not just `Other`, including correcting
> built-in mis-categorizations) while never touching entries you've pinned here, use
> `/auto-categorize`.

> Privacy: the classify path means the merchant names are handled by Claude (Anthropic). It is
> opt-in — it only happens when the user runs this command.

Always end by showing the updated `merchant_category.json` entries and a one-line summary.
