# credit-card-spending-dashboard

A **Cowork / Claude Code plugin** that turns monthly credit-card **statement PDFs** into a
single self-contained, offline HTML dashboard plus Markdown reports. It is **generic and
card-count-agnostic** — drop in a new card's e-statements and it appears automatically — and
ships with **no personal data**.

> **Privacy first.** Statement PDFs and generated data contain personal financial information.
> This repo commits only code. `statements/`, `.txt_cache/`, `data.js`, generated reports,
> `dashboard.html`, and `cards.config.json` are git-ignored — never commit them.

**No database — flat files only.** PDFs in `statements/` are the source; each is extracted to
`.txt_cache/<name>.txt` (the complete raw text). `data.js` (`window.CCDATA`) is the regenerable
processed dataset the dashboard reads. Since `.txt_cache` keeps the full text, a rebuild works
even after the source PDFs are removed — archive/delete the PDFs and you can still
re-categorize and regenerate. `.txt_cache` is git-ignored and local, so back it up yourself if
you delete the PDFs.

## What's in this repo

```
.
├── .claude-plugin/plugin.json          # plugin manifest
├── commands/                           # slash commands
│   ├── update-statement.md             #   /update-statement
│   ├── update-dashboard.md             #   /update-dashboard
│   ├── set-expiryCard.md               #   /set-expiryCard <last4> <mm>
│   ├── set-recurringRule.md            #   /set-recurringRule <words>
│   ├── list-cards.md                   #   /list-cards
│   ├── set-category.md                 #   /set-category [<keyword> <Category>]
│   ├── set-merchantGroup.md            #   /set-merchantGroup (regex group + rename)
│   ├── list-category.md                #   /list-category (read-only)
│   ├── list-merchantGroup.md           #   /list-merchantGroup (read-only)
│   └── auto-categorize.md              #   /auto-categorize (bulk LLM, confirm)
└── skills/credit-card-spending-dashboard/
    ├── SKILL.md                        # the skill (method + rules)
    ├── build_data.py                   # PDFs -> data.js + reports + dashboard.html
    ├── index.html                      # dashboard template (loads data.js)
    ├── recurring_rule.js               # hook: the "recurring merchant" rule
    ├── data.sample.js                  # synthetic sample data for instant preview
    ├── cards.config.example.json       # copy -> cards.config.json and fill in
    ├── merchant_category.example.json  # copy -> merchant_category.json (merchant -> category)
    └── vendor/                         # Chart.js (MIT) + IBM Plex Sans Thai (OFL)
```

## Commands

- **`/update-statement`** — attach the new statement PDF(s), then run this to rebuild
  `data.js`, the reports, and the offline `dashboard.html`, with build stats and anomaly checks.
- **`/update-dashboard`** — re-categorize and rebuild the dashboard from the existing
  statements, **without** importing new PDFs. Use after changing a card/recurring rule. Source
  precedence `statements/` → `.txt_cache/` → `data.js`: with no statements or cache it rebuilds
  from the existing `data.js` (re-deriving category + merchant grouping), so a stale dashboard
  missing instalment grouping can be fixed without the PDFs. Also **looks up a real name for any
  `Card ••xxxx` card** from the cached statement text, proposes it, and (on confirm) names it.
- **`/set-expiryCard <last4> <mm>`** — set a card's cycle anchor month (`MM`, `01`–`12`).
  Keyed by the card's last 4 digits. e.g. `/set-expiryCard 1234 10`.
- **`/set-cardName <last4> "<name>"`** — set a card's display name (the label on the dashboard
  buttons), replacing the `Card ••<last4>` fallback. Writes `cards.config.json` (preserves the
  card's `mm`); rebuilds. e.g. `/set-cardName 5006 "KBank Travel"`.
- **`/set-recurringRule <describe in words>`** — change what counts as a recurring merchant by
  describing it in plain language; it rewrites the `recurring_rule.js` hook only.
- **`/list-cards`** — list every card in one table: display name, last 4 digits, and cycle/expiry
  month (`mm`). Read-only.
- **`/list-category`** — list your `merchant_category.json` overrides (keyword→category) with how
  many merchants/transactions each matches; flags stale entries. Read-only.
- **`/list-merchantGroup`** — list your `merchant_group.json` overrides (regex→group name) with
  match counts and example merchants; flags stale entries. Read-only.
- **`/set-category [<keyword> <Category>]`** — map merchants stuck in `Other` to a category
  (e.g. `EXAMPLE INSURANCE → Insurance`). Manual, or with no args Claude classifies the `Other`
  merchants for you to confirm. Writes `merchant_category.json` (git-ignored, survives updates);
  category-only, never renames a merchant.
- **`/auto-categorize`** — bulk LLM re-categorization of **all** merchants (corrects built-in
  mistakes too, not just `Other`), **skipping anything you've pinned** in `merchant_category.json`.
  Shows a summary table → confirm → writes with `_source="llm"` → rebuilds. Opt-in (merchant names
  go to Claude).
- **`/set-merchantGroup`** — collapse merchants that differ only by a changing token
  (e.g. `ExampleSub*AB12CD34 CITY`, `ExampleSub*EF56GH78 CITY`) into one named group via a regex,
  or rename a group. Paste example lines or an image; Claude derives the pattern, previews every
  match and refuses over-broad ones, then you name the group. Writes `merchant_group.json`
  (git-ignored, survives updates); grouping-only, never renames the raw merchant name. Confirms
  before every write.
- **`/add-merchantToGroup <merchant> <group>`** — add one specific merchant to a group by its
  exact name (per-merchant counterpart to `/set-merchantGroup`). Writes a literal anchored rule to
  `merchant_group.json`; grouping-only, confirms before writing.
- **`/remove-merchantFromGroup <merchant>`** — pull one merchant out of its group so it stands
  alone (deletes its own rule, or self-pins it out of a broad rule; also undoes a prior self-pin).
  `/remove-merchantFromGroup group "<name>"` dissolves a whole group. Confirms before every write.
- **`/merge-merchantGroup "<A>" "<B>" [as "<N>"]`** — merge two (or more) groups into one named
  group; previews the combined members and confirms. Writes `merchant_group.json`.
- **`/auto-merchantGroup`** — Claude proposes groups (collapsing opaque-token variants of the **same**
  merchant), **confirmed one group at a time**, and is prefix-safe: it never merges different
  merchants that merely share a prefix (e.g. a payment-facilitator prefix, or same brand/different
  venue). Opt-in.
- **`/apply-userConfig [path]`** — apply the edits you made **on the dashboard** (⚙ Display Card,
  right-click group rename/merge, right-click group category) — exported as `cc_dashboard_edits.json`
  — into the durable config, then rebuild. Bridges the browser (which can't write files) to config.
- **`/migrate`** — after updating the plugin, upgrade your local (git-ignored) config/state to the
  current version. Applies the per-version steps in `MIGRATIONS.md` newer than the recorded
  `.cc_migration.json` marker (idempotent), rebuilds, then stamps the marker. Most steps are just a
  rebuild; it flags any manual follow-up (e.g. re-adding the marketplace after a rename).
- **`/version`** — show which version is in play: the declared version (`plugin.json`), the version
  the current dashboard was built with (`CCDATA.version`, also in the dashboard footer), and the
  last-migrated marker. Flags a stale dashboard so you know when to rebuild. Read-only.

**Default cycle month for new cards.** Add a reserved `_default` key to `cards.config.json` —
e.g. `"_default": { "mm": "12" }` — and any newly-detected card with no month inherits it
automatically on the next build (December anchor). Existing entries are never overwritten; omit
`_default` to keep the generic behavior (anchor from earliest statement month).

## Install as a plugin

This repo *is* the plugin (it carries both `.claude-plugin/plugin.json` and a
`.claude-plugin/marketplace.json`). Works on every Claude Code surface — terminal CLI, VS Code
/ JetBrains extensions, desktop app, and web.

**From GitHub** — run in any Claude Code session:

```
/plugin marketplace add siripol/credit-card-spending-dashboard
/plugin install credit-card-spending-dashboard@credit-card-spending-dashboard
```

Then reload/restart the session. The commands below and the
`credit-card-spending-dashboard` skill become available (namespaced
`credit-card-spending-dashboard:`).

**Pull later updates** — after new commits land on `main`, refresh the cache then update:

```
/plugin marketplace update credit-card-spending-dashboard
/plugin update credit-card-spending-dashboard@credit-card-spending-dashboard
```

**Manage / uninstall:**

```
/plugin list                                                  # what's installed
/plugin marketplace list                                      # configured marketplaces
/plugin uninstall credit-card-spending-dashboard@credit-card-spending-dashboard
/plugin marketplace remove credit-card-spending-dashboard
```

**Local / dev** — load a checkout without installing (session-only):

```bash
claude --plugin-dir /path/to/credit-card-spending-dashboard
```

## Quick start (standalone, no install)

```bash
cd skills/credit-card-spending-dashboard

# preview with fake data
cp data.sample.js data.js && open index.html      # index.html also falls back to the sample

# real use
mkdir -p statements && cp /path/to/your/*.pdf statements/
cp cards.config.example.json cards.config.json     # then edit names / cycles
python3 build_data.py                              # needs python 3.12+, pdftotext (poppler)
open dashboard.html                                # self-contained: no internet, no other files
```

Adapt the example parsers (`parse_card_a` / `parse_card_b` / `card_key`) and the category
keywords in `build_data.py` to your bank's `pdftotext -layout` output — they ship as generic
examples.

## Requirements

- `python3` **3.12+** (the generator uses backslashes in f-string expressions)
- `pdftotext -layout` (poppler-utils)
- `node` (only for the JS syntax check during verification)

## Third-party assets

- `vendor/chart.umd.js` — Chart.js, MIT License.
- `vendor/fonts/ibmplex-*.woff2` — IBM Plex Sans Thai, SIL Open Font License 1.1.

## License

No license file is included — add your own (e.g. MIT) before publishing if you want to allow
reuse. Note the third-party assets above keep their original licenses.
