---
description: Apply the dashboard's on-screen edits (Display Card, group renames/merges, group categories) exported from the dashboard into the durable config, then rebuild.
argument-hint: '[path to cc_dashboard_edits.json]'
---

Persist the edits a user made **on the dashboard** into the real config files, then rebuild so the
screen, the Markdown reports, and the config all agree.

Why this exists: `dashboard.html` is a static offline file — its JavaScript **cannot write repo
files** (browser security). On-screen edits are kept in the browser's `localStorage` and can be
**Exported** (the ⚙ Settings panel → "Export config") to a JSON file:

```json
{ "hiddenCards": ["<last4>"],
  "groupRenames":  [ { "from": "<old group>", "to": "<new group>" } ],
  "categoryEdits": [ { "group": "<group>", "cat": "<Category>" } ] }
```

This command reads that file and writes the durable config. It writes only
`cards.config.json` / `merchant_group.json` / `merchant_category.json` (all git-ignored); it never
edits `build_data.py`.

The user's input is: `$ARGUMENTS`

Do this:

1. **Locate the export.** Use the path in `$ARGUMENTS` if given; else the newest
   `cc_dashboard_edits*.json` in `~/Downloads`; else in `skills/credit-card-spending-dashboard/`. If
   none is found, tell the user to Export from the dashboard's ⚙ panel first, and stop.
2. **Parse + summarize + confirm.** Show a summary of the pending changes (hidden cards; group
   renames/merges; category edits) and confirm before writing anything.
3. **Apply by type** (all writes preserve existing entries + `_comment`; idempotent):
   - **`hiddenCards`** → set reserved key `"_hidden": [<last4>,…]` in
     `$CC_DATA_DIR/cards.config.json` (create from the example emptied to
     `{}` if absent). An **empty** list ⇒ remove the `_hidden` key.
   - **`groupRenames`** → apply to `merchant_group.json` exactly like `/merge-merchantGroup`: for each
     `{from,to}`, set every rule whose `group == from` to `group = to`, and prepend a literal
     `{ "pattern":"^<escaped merch>$","group":"to" }` for any member of `from` that has no rule
     (instalment-auto). Two `from`s → same `to` (or a `to` that already exists) auto-merge.
   - **`categoryEdits`** → apply to `merchant_category.json`: for each `{group,cat}`, validate `cat`
     against `CAT_ORDER` (skip + warn if invalid); enumerate the group's distinct member `merch` from
     `data.js` and **upsert each** as a `"<merch>": "<Category>"` entry with `_source["<merch>"]="user"`
     (pinned), matching `/set-category` semantics.
4. **Rebuild:** `export CC_DATA_DIR="${CC_DATA_DIR:-$HOME/.credit-card-dashboard}"; python3 "$CLAUDE_PLUGIN_ROOT/skills/credit-card-spending-dashboard/build_data.py"` (Python 3.12+;
   `python3.12` if older).
5. **Report** what was applied. The dashboard now matches config — the user may clear the dashboard's
   pending edits (re-tick "แสดงทุกบัตร" / undo renames) since they are now durable. On a build error,
   show it and stop.
