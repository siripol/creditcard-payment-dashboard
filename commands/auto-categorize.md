---
description: Auto-correct spending categories for every merchant using Claude — skips anything already pinned in merchant_category.json, shows a table, and confirms before writing.
argument-hint: (no arguments)
---

Bulk-classify **all** merchants into the correct spending category with Claude, **except** any
merchant already pinned in `merchant_category.json` (those are locked and never touched). Unlike
`/set-category`, this also **corrects built-in mis-categorizations** (not just `Other`). Results
are written to **`merchant_category.json` only** (git-ignored, not shipped) with `_source="llm"`.
Never edits `build_data.py`.

> Privacy: merchant names are sent to Claude (Anthropic) for classification. Opt-in — it only
> happens when you run this command.

Valid categories (the value must be one of these): `Travel`, `Insurance`, `Shopping & Retail`,
`Food & Dining`, `Subscriptions & Digital`, `Groceries & Convenience`, `Transport & Ride-hailing`,
`Online Shopping`, `Health & Medical`, `Utilities & Telecom`, `Fuel`, `Card Fees`, `Other`.

Do this:

1. **Build fresh data if needed.** If `data.js` is missing, run `python3 build_data.py` (Python
   3.12+; use `python3.12` if older).
2. **List candidates (non-pinned merchants).** A merchant is **pinned** if any existing keyword in
   `merchant_category.json` matches it (case-insensitive substring). Skip pinned merchants entirely.
   Gather the rest with their current category, count and total — and **all figures use comma
   thousands separators**:

   ```bash
   python3 - <<'PY'
   import re,json,os
   d=json.loads(re.search(r'window\.CCDATA\s*=\s*(\{.*\})\s*;',open('skills/credit-card-spending-dashboard/data.js',encoding='utf-8').read(),re.S).group(1))
   ov={}
   if os.path.isfile('merchant_category.json'):
       ov={k:v for k,v in json.load(open('merchant_category.json',encoding='utf-8')).items() if not k.startswith('_')}
   def pinned(name): return any(kw.lower() in name.lower() for kw in ov)
   agg={}
   for t in d['tx']:
       g=t.get('merchGroup') or t['merch']
       if pinned(g) or pinned(t['desc']): continue
       a=agg.setdefault(g,{'cat':t['cat'],'n':0,'total':0.0,'desc':t['desc']})
       a['n']+=1; a['total']+=t['amt']
   for g,a in sorted(agg.items(),key=lambda kv:-kv[1]['total']):
       print(f"{g}\t{a['cat']}\t{a['n']:,}\t{a['total']:,.0f}\t{a['desc'][:60]}")
   PY
   ```
3. **Classify each candidate** into a valid category using your own knowledge of the merchant and
   the sample description. Only keep rows where your category **differs from the current** one (the
   corrections) — those are what will change.

   > **Caution — payment-facilitator passthrough.** Some merchant strings are
   > `<facilitator>*<real merchant>` — a payment aggregator prepends its name. Classify by the
   > **real merchant (the suffix), per merchant** — never assign one category to a whole prefix,
   > because the same prefix hides different merchants. Fabricated example:
   > `PayHub*Xx_BrandA` → `Utilities & Telecom`, `PayHub*Xx_BrandB` → `Transport & Ride-hailing`,
   > `PayHub*Xx_Delivery` → `Food & Dining` — same `PayHub*` prefix, three different categories.
   > Applies to any facilitator prefix.
4. **Show a summary table and confirm** before writing anything (amounts comma-formatted):

   | Merchant | Current → Proposed | Tx | Total |
   |----------|--------------------|---:|------:|

   Ask the user to confirm or edit.
5. **On confirmation**, for each accepted merchant upsert into `merchant_category.json`:
   a keyword (a distinctive substring of the merchant, usually the group name) → the chosen
   category, and `_source["<keyword>"] = "llm"`. Preserve every existing entry and all pinned
   `_source` values. Create the file from
   `skills/credit-card-spending-dashboard/merchant_group.example.json`'s sibling
   `merchant_category.example.json` (emptied to `{}`, keep the `_comment`) if it doesn't exist.
6. **Rebuild** `python3 build_data.py` and report how many transactions moved category (with commas).

Always end by showing the updated `merchant_category.json` entries and a one-line summary. On a
build error, show the error and stop — do not summarize from stale data.
