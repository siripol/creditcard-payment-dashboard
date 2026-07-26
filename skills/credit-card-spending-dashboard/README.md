# Credit-Card Spending Dashboard

Turn your monthly credit-card **statement PDFs** into a clean, offline, single-file
HTML dashboard plus Markdown reports. Generic and **card-count-agnostic**: drop in a
new card's statements and it shows up automatically — configure it by its **last 4
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
| `merchant_rules.example.json` | Merchant category + name-cleanup template (copy → `merchant_rules.json`) |
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

## Cards config (by last 4 digits)

Copy `cards.config.example.json` → `cards.config.json` (git-ignored) and map each
card's **last 4 digits** to a display name and its statement-cycle date:

```json
{
  "1234": { "name": "My Travel Card", "mmdd": "1001" },
  "6789": { "name": "My Cashback Card", "mmdd": "1115" }
}
```

- key = **last 4 digits** of the card number (how the dashboard identifies the card)
- `name` = display name shown in the dashboard
- `mmdd` = statement-cycle date. **MM** (month) is used as the rewards-accumulation
  **cycle anchor**; **DD** (closing day) is stored for reference.

Cards you don't configure still appear automatically — with a default name
(`Card ••<last4>`) and a cycle anchor guessed from the first month seen. Colors are
assigned automatically from a palette.

Optionally set a reserved `_default` entry to give every *new* card a fixed cycle date
instead of the guessed one:

```json
{ "_default": { "mmdd": "1231" }, "1234": { "name": "My Card", "mmdd": "1001" } }
```

On the next build, any detected card with no `mmdd` inherits `_default.mmdd` (here `1231`
= year-end) and it's saved back to `cards.config.json`. Existing entries are never
overwritten; omit `_default` to keep the guessed-from-first-month behavior.

### Commands

Monthly update (rebuild everything from newly-added PDFs):

```
/update-statement
```

Re-group merchants and re-categorize from the current rules and rebuild, **without** importing
new PDFs (use after changing a merchant rule):

```
/update-dashboard
```

Set a card's cycle from chat instead of editing JSON:

```
/set-expiryCard <last4> <mmdd>
```

e.g. `/set-expiryCard 1234 1001` — upserts that card in `cards.config.json`, then
rebuilds.

List every card (name, last 4 digits, cycle/expiry `mmdd`) in one table:

```
/list-cards
```

List all merchant rules (category / cleanup / exclude):

```
/list-merchantRules
```

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

## Merchant rules — categories & name cleanup (update-safe)

Map merchants to categories and clean up their display names in `merchant_rules.json`
(git-ignored, **not** shipped — so it survives plugin updates, unlike editing `build_data.py`).
Copy `merchant_rules.example.json` → `merchant_rules.json`, or describe rules in words:

```
/set-merchantRule GRAB is Transport, SHOPEE is Online Shopping, and clean GRAB up to "Grab"
```

Three sections: `category` (`"KEYWORD": "CategoryKey"`), `cleanup` (`"KEYWORD": "Display Name"`,
stops one merchant splitting), `exclude` (extra non-spending keywords). User rules win over the
built-in defaults; `EXCLUDE` always applies first; an invalid category value is ignored. Rebuild
to apply.

## Requirements

- `python3` (**3.12+** — the generator uses backslashes in f-string expressions)
- `pdftotext -layout` (poppler-utils)
- `node` (only for the JS syntax check during verification)

## Data storage

There is no database — everything is flat files. `statements/*.pdf` are the source; each is
extracted to `.txt_cache/<name>.txt` (the **complete** raw text, nothing dropped). `data.js`
(`window.CCDATA`) is the fully-regenerable processed dataset the dashboard reads. Because
`.txt_cache` keeps the full text, `build_data.py` can rebuild from it even after the source PDFs
are removed — so you can archive/delete the PDFs and still re-categorize and regenerate. All of
these (`statements/`, `.txt_cache/`, `data.js`, reports, `dashboard.html`) are git-ignored.

## Notes

- The dashboard is offline-first: `dashboard.html` inlines Chart.js + fonts + data,
  so it opens by double-click with no network and no companion files.
- `index.html` references the local `vendor/` assets, so it also works offline for
  development.
- Category rules and merchant display names in `build_data.py` are **generic
  examples** — replace them with your own.
