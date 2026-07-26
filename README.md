# creditcard-payment-dashboard

A **Cowork / Claude Code plugin** that turns monthly credit-card **statement PDFs** into a
single self-contained, offline HTML dashboard plus Markdown reports. It is **generic and
card-count-agnostic** — drop in a new card's e-statements and it appears automatically — and
ships with **no personal data**.

> **Privacy first.** Statement PDFs and generated data contain personal financial information.
> This repo commits only code. `statements/`, `data.js`, generated reports, `dashboard.html`,
> and `cards.config.json` are git-ignored — never commit them.

## What's in this repo

```
.
├── .claude-plugin/plugin.json          # plugin manifest
├── commands/                           # slash commands
│   ├── updateCreditCardStatement.md    #   /updateCreditCardStatement
│   ├── set-expiryCard.md               #   /set-expiryCard <last5> <mmdd>
│   └── set-recurringRule.md            #   /set-recurringRule <words>
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

- **`/updateCreditCardStatement`** — attach the new statement PDF(s), then run this to rebuild
  `data.js`, the reports, and the offline `dashboard.html`, with build stats and anomaly checks.
- **`/set-expiryCard <last5> <mmdd>`** — set a card's cycle: `MM` = cycle anchor month, `DD` =
  statement closing day. Keyed by the card's last 5 digits. e.g. `/set-expiryCard 12345 1015`.
- **`/set-recurringRule <describe in words>`** — change what counts as a recurring merchant by
  describing it in plain language; it rewrites the `recurring_rule.js` hook only.

## Install as a plugin

This repo *is* the plugin. Install it in Cowork / Claude Code from its Git URL (via a plugin
marketplace), or zip the repo into a `.plugin` bundle and open it in the Claude desktop app.

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
