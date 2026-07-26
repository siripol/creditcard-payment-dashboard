# creditcard-payment-dashboard

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
│   ├── set-expiryCard.md               #   /set-expiryCard <last4> <mmdd>
│   ├── set-recurringRule.md            #   /set-recurringRule <words>
│   └── list-cards.md                   #   /list-cards
└── skills/credit-card-spending-dashboard/
    ├── SKILL.md                        # the skill (method + rules)
    ├── build_data.py                   # PDFs -> data.js + reports + dashboard.html
    ├── index.html                      # dashboard template (loads data.js)
    ├── recurring_rule.js               # hook: the "recurring merchant" rule
    ├── data.sample.js                  # synthetic sample data for instant preview
    ├── cards.config.example.json       # copy -> cards.config.json and fill in
    └── vendor/                         # Chart.js (MIT) + IBM Plex Sans Thai (OFL)
```

## Commands

- **`/update-statement`** — attach the new statement PDF(s), then run this to rebuild
  `data.js`, the reports, and the offline `dashboard.html`, with build stats and anomaly checks.
- **`/update-dashboard`** — re-categorize and rebuild the dashboard from the existing
  statements, **without** importing new PDFs. Use after changing a card/recurring rule.
- **`/set-expiryCard <last4> <mmdd>`** — set a card's cycle: `MM` = cycle anchor month, `DD` =
  statement closing day. Keyed by the card's last 4 digits. e.g. `/set-expiryCard 1234 1015`.
- **`/set-recurringRule <describe in words>`** — change what counts as a recurring merchant by
  describing it in plain language; it rewrites the `recurring_rule.js` hook only.
- **`/list-cards`** — list every card in one table: display name, last 4 digits, and cycle/expiry
  date (`mmdd`, decoded). Read-only.

**Default cycle date for new cards.** Add a reserved `_default` key to `cards.config.json` —
e.g. `"_default": { "mmdd": "1231" }` — and any newly-detected card with no `mmdd` inherits it
automatically on the next build (year-end = anchor Dec, closing day 31). Existing entries are
never overwritten; omit `_default` to keep the generic behavior (anchor from earliest statement
month).

## Install as a plugin

This repo *is* the plugin (it carries both `.claude-plugin/plugin.json` and a
`.claude-plugin/marketplace.json`). Works on every Claude Code surface — terminal CLI, VS Code
/ JetBrains extensions, desktop app, and web.

**From GitHub** — run in any Claude Code session:

```
/plugin marketplace add siripol/creditcard-payment-dashboard
/plugin install creditcard-payment-dashboard@creditcard-payment-dashboard
```

Then reload/restart the session. The four commands below and the
`credit-card-spending-dashboard` skill become available (namespaced
`creditcard-payment-dashboard:`).

**Pull later updates** — after new commits land on `main`, refresh the cache then update:

```
/plugin marketplace update creditcard-payment-dashboard
/plugin update creditcard-payment-dashboard@creditcard-payment-dashboard
```

**Manage / uninstall:**

```
/plugin list                                                  # what's installed
/plugin marketplace list                                      # configured marketplaces
/plugin uninstall creditcard-payment-dashboard@creditcard-payment-dashboard
/plugin marketplace remove creditcard-payment-dashboard
```

**Local / dev** — load a checkout without installing (session-only):

```bash
claude --plugin-dir /path/to/creditcard-payment-dashboard
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
