# Credit-Card Spending Dashboard

Turn your monthly credit-card **statement PDFs** into a clean, offline, single-file
HTML dashboard plus Markdown reports. Generic and **card-count-agnostic**: drop in a
new card's statements and it shows up automatically — configure it by its **last 5
digits**.

> **Privacy:** statement PDFs and generated data contain personal financial info.
> This repo commits only code. `statements/`, `data.js`, generated reports,
> `dashboard.html`, and `cards.config.json` are git-ignored — never commit them.

## What's in here

| File | Role |
|---|---|
| `build_data.py` | Reads statement PDFs → `data.js` + reports + `dashboard.html` |
| `index.html` | Dashboard template (loads `data.js`; edit the UI here) |
| `recurring_rule.js` | Hook: the "recurring merchant" rule (edit via `/set-recurringRule`) |
| `data.sample.js` | Fake sample data so you can preview the dashboard immediately |
| `cards.config.example.json` | Card config template (copy → `cards.config.json`) |
| `vendor/chart.umd.js` | Chart.js (MIT) — inlined into the single-file dashboard |
| `vendor/fonts/` | IBM Plex Sans Thai (OFL) — inlined into the single-file dashboard |

## Quick preview (no real data)

Copy the sample data and open the template:

```bash
cp data.sample.js data.js   # or just open index.html (it falls back to the sample)
open index.html
```

## Real use

1. Put your statement PDFs in `statements/`.
2. **Adapt the parsers** in `build_data.py` (`parse_card_a` / `parse_card_b` and
   `card_key`) to your bank's `pdftotext -layout` output. The example layouts are
   commented.
3. **Configure your cards** (see below).
4. Run the build, then open the generated single file:

```bash
python3 build_data.py        # needs python 3.12+, pdftotext (poppler)
open dashboard.html          # self-contained: no internet, no other files
```

## Cards config (by last 5 digits)

Copy `cards.config.example.json` → `cards.config.json` (git-ignored) and map each
card's **last 5 digits** to a display name and its statement-cycle date:

```json
{
  "01234": { "name": "My Travel Card", "mmdd": "1001" },
  "56789": { "name": "My Cashback Card", "mmdd": "1115" }
}
```

- key = **last 5 digits** of the card number (how the dashboard identifies the card)
- `name` = display name shown in the dashboard
- `mmdd` = statement-cycle date. **MM** (month) is used as the rewards-accumulation
  **cycle anchor**; **DD** (closing day) is stored for reference.

Cards you don't configure still appear automatically — with a default name
(`Card ••<last5>`) and a cycle anchor guessed from the first month seen. Colors are
assigned automatically from a palette.

### Commands

Monthly update (rebuild everything from newly-added PDFs):

```
/update-statement
```

Set a card's cycle from chat instead of editing JSON:

```
/set-expiryCard <last5> <mmdd>
```

e.g. `/set-expiryCard 01234 1001` — upserts that card in `cards.config.json`, then
rebuilds.

## Recurring-merchant rule (a hook — describe it in words)

What counts as a **recurring merchant** ("ร้านค้าประจำ") lives entirely in
`recurring_rule.js`. You don't edit the main code — you describe the rule in plain
words and let Claude translate it into the hook:

```
/set-recurringRule <describe the rule in your own words>
```

e.g. `/set-recurringRule paid in at least 4 months in a row, or used 6+ times total`.
Claude rewrites the body of `window.CCRULE = function isRecurring(m){ ... }`. The input
`m` (with `maxRun`, `multi`, `mCount`, `months`, `total`, `n`, `cat`, …) is documented
at the top of the file.

**Default:** paid in **≥3 consecutive months**, OR appears in **≥3 months with more than
one charge** that month (insurance excluded). If the hook is missing, the dashboard
falls back to this default. The rule drives the **dashboard**; the Markdown report's
recurring list uses the default.

## Requirements

- `python3` (**3.12+** — the generator uses backslashes in f-string expressions)
- `pdftotext -layout` (poppler-utils)
- `node` (only for the JS syntax check during verification)

## Notes

- The dashboard is offline-first: `dashboard.html` inlines Chart.js + fonts + data,
  so it opens by double-click with no network and no companion files.
- `index.html` references the local `vendor/` assets, so it also works offline for
  development.
- Category rules and merchant display names in `build_data.py` are **generic
  examples** — replace them with your own.
