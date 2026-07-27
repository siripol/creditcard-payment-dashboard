---
description: Group varying-token merchants under one name via a regex, or rename a merchant group — writes merchant_group.json only, confirming before every change.
argument-hint: 'paste example merchant lines / an image, or: rename <old> to <new>'
---

Collapse merchants whose descriptions differ only by a changing token (e.g.
`ExampleSub*AB12CD34 CITY`, `ExampleSub*EF56GH78 CITY`, …) into one **merchant
group**, or rename an existing group. Rules are written to **`merchant_group.json` only** (project
root, git-ignored, **not** shipped — so they survive plugin updates). Never edits `build_data.py`.

Config shape (ordered — **first matching regex wins**, so put specific patterns first):

```json
{ "groups": [ { "pattern": "<regex>", "group": "<display name>" } ] }
```

Only the derived `merchGroup` changes — the raw statement name (`tx.merch`) is **never renamed**;
drill-downs still show each original line. This is **user-curated** grouping with a mandatory
confirm step: automatic prefix collapse was reverted in v0.7.0 for silently merging distinct
merchants, so this command must **preview every match and refuse over-broad patterns**.

The user's input is: `$ARGUMENTS`

### Mode A — create a group from examples (pasted text OR an image)
1. Collect the example merchant strings. If an image was attached, read the strings off it
   (opt-in: the image is handled by Claude/Anthropic — say so).
2. **Derive a regex** that matches all the examples, keeping the invariant part and generalizing
   only the varying token (e.g. `ExampleSub\*\w+ CITY`). Prefer the tightest pattern that
   still covers every example.
3. **Confirm the PATTERN first.** Run the regex (case-insensitive) against every distinct merchant
   in `data.js` (`CCDATA.tx[].merch`). Show the full match list (count + tx + total). **If it
   matches merchants from more than one clearly-different store, refuse** and propose a tighter
   pattern — do not write. Ask the user to accept or edit the pattern.
4. **Then ask for the group name.** Propose a clean name (e.g. `Example Subscription`) and let the user
   accept or type their own.
5. On confirmation, upsert `{ "pattern": ..., "group": ... }` into `merchant_group.json` (create the
   file from `skills/credit-card-spending-dashboard/merchant_group.example.json` emptied to
   `{ "groups": [] }` — keep the `_comment` — if it doesn't exist), preserving existing entries.
6. Rebuild: `python3 build_data.py` (Python 3.12+; use `python3.12` if older). Report how many tx
   were regrouped (the build prints `merchant_group overrides: N rule(s) → M tx regrouped`).

### Mode B — rename an existing group  (`rename "<old>" -> "<new>"`)
1. Find entries in `merchant_group.json` where `group == "<old>"`. Show them and the affected
   merchants/tx (from `data.js`). Confirm the rename.
2. Update the `group` value on those entries, rebuild, report.

### Mode C — rename an auto-derived group (no override yet)
For a group whose name comes from the built-in instalment stripping (e.g. an auto-derived label like
`Acme-0000-Store`) and has no override: create a new override whose regex matches that group's members, mapping them
to the new name. Preview the matches (Mode A step 3) and confirm before writing, then rebuild.

Always end by showing the updated `merchant_group.json` entries and a one-line summary. On a build
error, show the error and stop — do not summarize from stale data.
