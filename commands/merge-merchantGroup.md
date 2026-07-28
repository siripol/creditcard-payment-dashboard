---
description: Merge two (or more) merchant groups into one named group — writes merchant_group.json only, confirming before the change.
argument-hint: '"<groupA>" "<groupB>" [as "<name>"]'
---

Fold two or more existing **merchant groups** into a single group under one name. Per-merchant
counterpart family member of `/set-merchantGroup` / `/add-merchantToGroup`. Writes
**`skills/credit-card-spending-dashboard/merchant_group.json` only** (git-ignored, not shipped —
survives updates). Never edits `build_data.py`. Grouping-only — the raw `tx.merch` is never renamed.

A group's members = the transactions whose `merchGroup` equals that group. Merging groups A, B → new
name **N** means every member of A and B must map to N under the first-match-wins loader.

The user's input is: `$ARGUMENTS`

Do this:

1. **Parse** the group names (2 or more, quoted) and an optional `as "<name>"`. Resolve each group's
   members from `skills/credit-card-spending-dashboard/data.js` (`CCDATA.tx[].merchGroup`; run
   `python3 build_data.py` from that dir first if `data.js` is absent). If a named group matches
   **0** transactions, warn it is stale and ask whether to continue.
2. **Choose the new name N:** if `as "<name>"` was given, use it. Otherwise propose one (e.g. the
   input group with the most transactions) and let the user accept or type their own.
3. **Preview + confirm.** Show the combined member list — distinct `merch`, tx count, total —
   grouped by source group, and state they will all move under **N**. Confirm before writing.
4. **Write** `merchant_group.json`:
   - For every existing rule whose `group` is one of the inputs, set its `group = N` (a renamed
     broad/literal rule keeps matching its members — instant merge).
   - For each member that is grouped only by the built-in instalment-stripping (no override rule),
     **prepend** a literal rule `{ "pattern": "^<escaped merch>$", "group": "N" }` (idempotent — skip
     if an equal rule already exists).
   - Preserve all other entries + the `_comment`. Create the file from
     `merchant_group.example.json` emptied to `{ "groups": [] }` (keep `_comment`) if absent.
5. **Rebuild:** `cd skills/credit-card-spending-dashboard && python3 build_data.py` (Python 3.12+;
   `python3.12` if older). Report how many tx were regrouped and show the resulting entries.
6. On a build error, show it and stop — do not summarize from stale data.

> This is the command-line merge. The dashboard's **Merchant Group** tab also lets you merge by
> right-clicking a group and renaming it to an existing group's name; run `/apply-userConfig` to
> persist those on-screen edits into `merchant_group.json`.
