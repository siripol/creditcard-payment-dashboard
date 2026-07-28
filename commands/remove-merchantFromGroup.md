---
description: Remove one merchant from its group (it stands alone), or dissolve a whole group — writes merchant_group.json only, confirming before every change.
argument-hint: '<merchant>   |   group "<group>"'
---

Pull **one merchant** out of its merchant group so it stands alone under its own name, or
**dissolve an entire group** so every member reverts. Per-merchant counterpart to
`/set-merchantGroup`. Rules are written to
**`$CC_DATA_DIR/merchant_group.json` only** (git-ignored, **not** shipped —
survives updates). Never edits `build_data.py`. Grouping-only — the raw `tx.merch` is never renamed,
only the derived `merchGroup`. Confirms before every write.

Recall the build's grouping order (`merchant_group()`): a user override regex wins first
(first-match-wins), else automatic instalment-stripping, else the name unchanged. So a merchant
gets its `merchGroup` from one of **5 routes**, and this command covers all of them.

The user's input is: `$ARGUMENTS`

**Mode detect:** if the input starts with `group ` (e.g. `group "Coffee"`), run **Dissolve-group
mode**. Otherwise run **Single-merchant mode**.

### Single-merchant mode  (`<merchant>`)
1. **Resolve the exact merchant** from `$CC_DATA_DIR/data.js`
   (`CCDATA.tx[].merch`) — run `python3 build_data.py` from that dir first if `data.js` is absent.
   0 matches → stop and say so. Fuzzy/partial hitting several → list candidates, ask which exact
   one. Show the merchant's current `merchGroup`.
2. **Decide the edit** from two facts: (a) does a literal `^<escaped merch>$` entry exist in
   `merchant_group.json`? (b) is `merchGroup == merch` already?
   - **A literal `^merch$` entry exists** → **delete that entry.** This covers both *leaving a
     group* (the entry mapped to a real group) and *undoing a self-pin* (the entry mapped the
     merchant to its own name). After deletion the merchant falls back to the next matching rule /
     instalment-strip / plain name.
   - **No literal entry, but the merchant is grouped** (via a broad regex, or via
     instalment-stripping — i.e. `merchGroup != merch`) → **prepend** a self-pin
     `{ "pattern": "^<escaped merch>$", "group": "<merch>" }`. Because overrides run before
     stripping and first-match-wins, this pulls only this merchant out; others in the broad rule
     stay put.
   - **No literal entry and `merchGroup == merch`** → the merchant is already standalone; report it
     and **stop** (write nothing).
   - Note: do **not** stop merely because `merchGroup == merch` — a self-pin also looks standalone
     but *has* an entry to delete. Distinguish by whether the `^merch$` entry exists.
3. **Explain which path** you're taking, **confirm**, apply the edit (preserve all other entries +
   the `_comment`).
4. **Rebuild:** `export CC_DATA_DIR="${CC_DATA_DIR:-$HOME/.credit-card-dashboard}"; python3 "$CLAUDE_PLUGIN_ROOT/skills/credit-card-spending-dashboard/build_data.py"` (Python 3.12+;
   `python3.12` if older). Report the tx that changed and show the updated entry (or that one was
   removed).

### Dissolve-group mode  (`group "<G>"`)
1. Find **all** entries in `merchant_group.json` where `group == "<G>"`. Show them plus the affected
   merchants/tx from `data.js`. If there are **none** (e.g. `<G>` is only an auto-derived
   instalment label with no override), report there is nothing to delete and **stop**.
2. **Confirm**, then **delete all** those entries (preserve others + `_comment`).
3. **Rebuild**, report which merchants reverted (each back to a broad rule / instalment-strip /
   own name).

On a build error, show the error and stop — do not summarize from stale data. Always end by showing
the resulting `merchant_group.json` entries and a one-line summary.
