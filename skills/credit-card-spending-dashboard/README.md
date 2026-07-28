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
| `merchant_category.example.json` | Merchant→category override template (copy → `merchant_category.json`) |
| `merchant_group.example.json` | Merchant-group (regex→name) override template (copy → `merchant_group.json`) |
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
card's **last 4 digits** to a display name and its cycle anchor month:

```json
{
  "1234": { "name": "My Travel Card", "mm": "10" },
  "6789": { "name": "My Cashback Card", "mm": "11" }
}
```

- key = **last 4 digits** of the card number (how the dashboard identifies the card)
- `name` = display name shown in the dashboard
- `mm` = **cycle anchor month** (`01`–`12`), the month the rewards/accumulation cycle
  resets. (A legacy `mmdd` value still works — the build reads its leading `MM`.)

Cards you don't configure still appear automatically — with a default name
(`Card ••<last4>`) and a cycle anchor guessed from the first month seen. Colors are
assigned automatically from a palette.

Optionally set a reserved `_default` entry to give every *new* card a fixed anchor month
instead of the guessed one:

```json
{ "_default": { "mm": "12" }, "1234": { "name": "My Card", "mm": "10" } }
```

On the next build, any detected card with no month inherits `_default.mm` (here `12` =
December) and it's saved back to `cards.config.json`. Existing entries are never
overwritten; omit `_default` to keep the guessed-from-first-month behavior.

### Commands

Monthly update (rebuild everything from newly-added PDFs):

```
/update-statement
```

Re-categorize and rebuild from the existing statements, **without** importing new PDFs (use
after changing a card/recurring rule):

```
/update-dashboard
```

Set a card's cycle anchor month from chat instead of editing JSON:

```
/set-expiryCard <last4> <mm>
```

e.g. `/set-expiryCard 1234 10` — upserts that card in `cards.config.json`, then
rebuilds.

List every card (name, last 4 digits, cycle anchor month `mm`) in one table:

```
/list-cards
```

Review the override configs you've set (read-only; shows match counts + flags stale entries):

```
/list-category           # merchant_category.json entries (keyword -> category)
/list-merchantGroup      # merchant_group.json entries (regex -> group name)
```

Categorize merchants that fall into `Other` (writes `merchant_category.json`, category-only):

```
/set-category EXAMPLE INSURANCE Insurance     # manual (source=user, pinned)
/set-category                                # no args -> Claude classifies Other, you confirm
/auto-categorize                             # bulk LLM fix for ALL non-pinned merchants, you confirm
```

`/auto-categorize` corrects built-in mis-categorizations across every merchant but never touches
entries you've pinned (anything already in `merchant_category.json`). A reserved `_source` map
records who set each entry (`user` / `llm`); `/list-category` shows it as a Source column.

Group varying-token merchants under one name, or rename a group (writes `merchant_group.json`,
grouping-only — never renames the raw merchant name):

```
/set-merchantGroup                           # paste example lines / an image -> regex + name it
/set-merchantGroup rename "Example Subscription" -> "Example Sub"
```

Add or remove **one specific merchant** to/from a group (per-merchant counterpart to
`/set-merchantGroup`, same `merchant_group.json`, grouping-only):

```
/add-merchantToGroup "STARBUCKS TH" "Coffee"     # add one merchant to a group
/remove-merchantFromGroup "STARBUCKS TH"         # pull one merchant out (stands alone)
/remove-merchantFromGroup group "Coffee"         # dissolve a whole group
```

`/remove-merchantFromGroup` covers every way a merchant is grouped: it deletes the merchant's own
rule (which both leaves a group **and** undoes a prior self-pin), or self-pins it out of a broad /
instalment group, else reports it is already standalone.

## Merchant category overrides & instalment grouping

- **Category overrides** — copy `merchant_category.example.json` → `merchant_category.json`
  (git-ignored, survives updates) and map `"KEYWORD": "Category"`. `category()` applies it on top
  of the built-in rules; an invalid category value is ignored. The build prints an
  `UNCATEGORIZED MERCHANTS` list so you know what still needs a rule. Merchant **names are never
  changed** — only their category.
- **Instalment grouping** — งวด rows like `... 01/03`, `02/03` are grouped into one merchant via a
  derived `tx.merchGroup` (counter + trailing amount stripped); the raw `tx.merch` is preserved.
  The merchants tab and recurring list aggregate by `merchGroup`, the all-transactions tab shows
  both `ร้านค้า (ตามบิล)` and `กลุ่มร้านค้า`, and the build reports each detected series.
- **Foreign-currency charges** — a trailing `<CCY> <amount>` some issuers add (e.g. `… USD 12.34`)
  is captured into `tx.fx` and stripped from the display name, so `merch`/`merchGroup` stay clean
  (and foreign merchants that differed only by that amount now group). Raw `tx.desc` keeps it. The
  dashboard shows `tx.fx` under the amount + as a CSV column. Extend `FX_CCY` in `build_data.py` to
  your statements' currency codes.
- **Merchant-group overrides** — copy `merchant_group.example.json` → `merchant_group.json`
  (git-ignored, survives updates) and map `{"pattern": "<regex>", "group": "<name>"}` entries.
  `merchant_group()` applies them **before** instalment stripping (first matching regex wins), so
  varying-token merchants (`ExampleSub*XXXX CITY`) collapse into one named group. Set/rename
  via `/set-merchantGroup` (regex), or add/remove one merchant at a time via
  `/add-merchantToGroup` and `/remove-merchantFromGroup` (which also dissolves a whole group).
  Grouping-only — the raw `tx.merch` is never renamed. The per-card **Merchant Group** tab lets
  you eyeball that each group maps the right member merchants.

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

## Data storage

There is no database — everything is flat files. `statements/*.pdf` are the source; each is
extracted to `.txt_cache/<name>.txt` (the **complete** raw text, nothing dropped). `data.js`
(`window.CCDATA`) is the fully-regenerable processed dataset the dashboard reads. Because
`.txt_cache` keeps the full text, `build_data.py` can rebuild from it even after the source PDFs
are removed — so you can archive/delete the PDFs and still re-categorize and regenerate. As a
last resort, when neither statements nor `.txt_cache` remain, the build rebuilds from the
existing `data.js` itself: it re-derives category and merchant grouping from each transaction's
stored `desc`/`merch` (best-effort — `desc` is stored capped at 2048 chars, so full statement
text still gives the most accurate re-categorize). All of these (`statements/`, `.txt_cache/`,
`data.js`, reports, `dashboard.html`) are git-ignored.

## Notes

- The dashboard is offline-first: `dashboard.html` inlines Chart.js + fonts + data,
  so it opens by double-click with no network and no companion files.
- `index.html` references the local `vendor/` assets, so it also works offline for
  development.
- Category rules and merchant display names in `build_data.py` are **generic
  examples** — replace them with your own.
