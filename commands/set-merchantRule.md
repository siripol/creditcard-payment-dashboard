---
description: Map merchants to categories and clean up merchant names by describing the rules in plain words.
argument-hint: <describe the mapping/cleanup in your own words>
---

The user wants to add or change merchant category / name-cleanup rules. Their description is:

"$ARGUMENTS"

Translate that into entries in **`merchant_rules.json` only** (project root, git-ignored, not
shipped — so it survives plugin updates). Do NOT edit `build_data.py` — the built-in `cat()` /
`merch()` read this file and apply the user's rules on top of the defaults.

Do this:

1. Open `merchant_rules.json`. If it does not exist, create it by copying
   `skills/credit-card-spending-dashboard/merchant_rules.example.json` and emptying the three
   sections (`exclude: []`, `category: {}`, `cleanup: {}`); keep the `_comment`.
2. Translate the description into entries (keywords match case-insensitively as substrings of the
   raw statement description):
   - **category** — `"KEYWORD": "CategoryKey"`. The value MUST be one of: `Travel`, `Insurance`,
     `Shopping & Retail`, `Food & Dining`, `Subscriptions & Digital`, `Groceries & Convenience`,
     `Transport & Ride-hailing`, `Online Shopping`, `Health & Medical`, `Utilities & Telecom`,
     `Fuel`, `Card Fees`, `Other`. If the user names a category that is not on this list, pick the
     closest valid key and say which you used.
   - **cleanup** — `"KEYWORD": "Display Name"` to stop one merchant splitting into many names
     (e.g. `"GRAB": "Grab"`, `"SHOPEE": "Shopee"`).
   - **exclude** — extra keywords for non-spending lines to drop (rarely needed; payments /
     cashback / refunds are already excluded).
3. **Upsert** — preserve existing entries; only add/replace the keys the user described. Never
   remove unrelated rules.
4. Validate: the file must be valid JSON and every `category` value must be a valid key above.
5. Rebuild so the rules take effect: `python3 build_data.py` (Python 3.12+; use `python3.12` if
   `python3` is older). Report how many transactions changed category, and whether any merchant
   names merged.
6. Show the user the updated `merchant_rules.json` sections and a one-line summary of each rule.
