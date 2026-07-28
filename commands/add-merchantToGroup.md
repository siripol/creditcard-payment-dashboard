---
description: Add one specific merchant to a merchant group — writes merchant_group.json only, confirming before the change.
argument-hint: '<merchant> <group>   (e.g. "STARBUCKS TH" "Coffee")'
---

Put **one exact merchant** into a named **merchant group**. This is the per-merchant counterpart
to the regex-based `/set-merchantGroup`: instead of a pattern, it pins a single merchant by its
exact name. Rules are written to **`$CC_DATA_DIR/merchant_group.json`
only** (git-ignored, **not** shipped — so they survive plugin updates). Never edits `build_data.py`.

Config shape (ordered list — **first matching regex wins**, so per-merchant literal rules are
**prepended** to beat any broad rule):

```json
{ "groups": [ { "pattern": "^<escaped merchant>$", "group": "<group name>" } ] }
```

Only the derived `merchGroup` changes — the raw statement name (`tx.merch`) is **never renamed**;
drill-downs still show each original line. Grouping-only, confirmed before every write.

The user's input is: `$ARGUMENTS`

Do this:

1. **Parse** `<merchant>` and `<group>` from the input (quoted strings). If the group is missing,
   ask for it.
2. **Resolve the exact merchant.** Match `<merchant>` against the distinct `CCDATA.tx[].merch`
   values in `$CC_DATA_DIR/data.js` (run `python3 build_data.py` from that
   dir first if `data.js` is absent). If it matches **0** merchants, stop and say so. If it's a
   fuzzy/partial match hitting several distinct merchants, **list the candidates and ask which
   exact one** — never guess.
3. **Show before → after.** Report the merchant's **current** `merchGroup` and what it will become
   (`<group>`). If it is already in `<group>`, say so and stop (nothing to write).
4. **Confirm**, then **upsert**: build `"^" + re.escape(merch) + "$"` as the pattern and
   **prepend** `{ "pattern": ..., "group": "<group>" }` into `merchant_group.json` — if an entry
   with that same anchored pattern already exists (e.g. a leftover self-pin or a prior mapping),
   **replace its `group`** in place instead of adding a duplicate. Preserve all other entries and
   the `_comment`. Create the file from
   `skills/credit-card-spending-dashboard/merchant_group.example.json` emptied to `{ "groups": [] }`
   (keep the `_comment`) if it doesn't exist.
5. **Rebuild:** `export CC_DATA_DIR="${CC_DATA_DIR:-$HOME/.credit-card-dashboard}"; python3 "$CLAUDE_PLUGIN_ROOT/skills/credit-card-spending-dashboard/build_data.py"` (Python 3.12+;
   use `python3.12` if older). Report how many tx were regrouped (the build prints
   `merchant_group overrides: N rule(s) → M tx regrouped`).
6. End by showing the updated `merchant_group.json` entry and a one-line summary. On a build error,
   show the error and stop — do not summarize from stale data.

> To pull a merchant back out of a group (or dissolve a whole group), use
> `/remove-merchantFromGroup`.
