---
name: credit-card-spending-dashboard
description: >
  Build and maintain a personal credit-card spending dashboard from bank statement PDFs.
  Extract transactions, de-duplicate, categorize by merchant description, and render a
  single self-contained offline HTML dashboard plus Markdown reports. Auto-scales to ANY
  number of cards — drop in a new card's e-statements and it appears automatically. Use when
  the user wants to process statement PDFs, refresh the spending data / reports / dashboard,
  answer analytical questions about their spending, add a card, or edit the categorization,
  cycle, or recurring-merchant rules. Trigger phrases: "process my statements", "update the
  spending dashboard", "how much did I spend", "add a card", "set the closing date", "change
  what counts as a recurring shop", "list my cards", "map a merchant to a category",
  "re-group merchants / rebuild the dashboard", "/set-expiryCard", "/set-recurringRule",
  "/list-cards", "/set-merchantRule", "/list-merchantRules", "/update-dashboard".
---

# Credit-Card Spending Dashboard

A reusable workflow for turning monthly credit-card statement PDFs into a clean, offline,
single-file HTML dashboard with supporting Markdown reports. This skill contains **no
personal data** — it describes the method. The user supplies their own statements and
configures their own cards, categories, and merchant rules.

> **Privacy first.** Statement PDFs and the generated data contain personal financial
> information. Keep real statements, `data.js`, generated reports, `dashboard.html`, and
> `cards.config.json` **out of any public repository** (they are in `.gitignore`). Commit
> only the template code and this skill — never the user's data.

---

## Project layout

```
project/
├── statements/               # INPUT: the user's statement PDFs (git-ignored, never committed)
├── build_data.py             # processor: PDFs -> data + reports + dashboard
├── index.html                # dashboard TEMPLATE (loads data.js); card-count-agnostic
├── recurring_rule.js         # HOOK: the "recurring merchant" rule (see below)
├── data.sample.js            # tiny synthetic data so index.html previews with no real data
├── cards.config.example.json # copy to cards.config.json and fill in your cards
├── cards.config.json         # YOUR card names / closing dates / recurring rule (git-ignored)
├── vendor/
│   ├── chart.umd.js          # Chart.js UMD (offline)
│   └── fonts/                # bundled web font woff2 (offline)
├── data.js                   # GENERATED: window.CCDATA = {...}      (git-ignored)
├── report.md / brief.md      # GENERATED: reports                    (git-ignored)
└── dashboard.html            # GENERATED: single self-contained file (git-ignored)
```

Requirements at runtime: `python3` (**3.12+**), `pdftotext -layout` (poppler), and `node`
(only for the JS syntax check during verification).

> **Python 3.12+ is required.** The generator uses backslash escapes inside f-string
> expressions, which older Python rejects with a `SyntaxError`. If only an older Python is
> available, run with an explicit `python3.12` interpreter rather than editing the source.

---

## Auto N-card: the dashboard scales to any number of cards

The template carries **no hardcoded card names or count**. The build detects each card from
the statement text and emits `cards`, `cardMeta`, and `reduceGroups` into `window.CCDATA`;
`index.html` renders every card button, cycle block, comparison row, color, and anchor
**dynamically** from that payload. Consequences:

- **Adding a card = dropping its e-statements into `statements/` and rebuilding.** A new card
  appears on its own — no code edit.
- Each card is keyed by the **last 4 digits** of its number (read from the statement text).
- Colors are auto-assigned from a fixed palette by card order.
- If a card is not in `cards.config.json`, it still works — it shows as `Card ••<last4>` with
  its cycle anchor inferred from the earliest month seen.

`cards.config.json` only *names* and *tunes* cards; it never *enables* them.

---

## Commands

Commands the user can invoke. `/update-statement` (import new PDFs + rebuild) and
`/update-dashboard` (re-group/re-categorize from existing statements, no new imports) both run
the build; `/set-expiryCard`, `/set-recurringRule`, and `/set-merchantRule` each edit exactly
one small config/hook file — never the main `build_data.py` logic; `/list-cards` and
`/list-merchantRules` are read-only.

### `/update-statement`

Run the monthly update. Collect the newly-attached PDFs (and any in `statements/`), rebuild
via `python3 build_data.py`, report the build stats and anomaly checks, deliver the refreshed
single-file `dashboard.html`, and summarize the latest month. This is the command form of the
"Standard update routine" at the bottom of this file; the skill also triggers on the phrase
"update the spending dashboard".

### `/update-dashboard`

Re-group merchants and re-categorize business types from the **current** rules, then rebuild —
**no new PDFs**. Use after `/set-merchantRule` or any rules edit. Same engine as
`/update-statement` (each build re-reads `merchant_rules.json` and re-runs `cat()`/`merch()` on
every row), minus the import step; requires `statements/` (or `.txt_cache/`) to still be present,
since the dashboard can't be re-categorized from `data.js` alone.

### `/set-expiryCard <last4> <mmdd>`

Set a card's **cycle closing date**. `<last4>` = the last 4 digits of the card. `<mmdd>` =
`MM` (the month the accumulation cycle anchors on) + `DD` (the statement closing day).
Example: `/set-expiryCard 1234 1015` → card ••1234, cycle anchors in October, closes on
the 15th. Implementation: upsert the entry in `cards.config.json`:

```json
{ "1234": { "name": "My Travel Card", "mmdd": "1015" } }
```

Then rebuild so `cardMeta.anchor` picks up the new month. (Only `MM` currently drives the
cycle-anchor month; `DD` is stored for reference/closing-day display.)

**Default for new cards (`_default`).** A reserved `_default` key in `cards.config.json` sets an
`mmdd` fallback that `build()` applies automatically to any *newly-detected* card that has no
`mmdd` yet — e.g. `"_default": { "mmdd": "1231" }` gives every new card a year-end cycle
(anchor Dec, closing day 31). Existing entries are never overwritten (idempotent), and the new
entry is persisted back to `cards.config.json` so it stays editable. If `_default` is absent, an
unlisted card keeps the generic behaviour (anchor derived from its earliest statement month).

### `/list-cards`

List **every** card in one table: display name, last 4 digits, and cycle/expiry date (`mmdd`).
Merges the detected card set from `CCDATA.cardMeta` (in `data.js`) with each card's `mmdd` from
`cards.config.json`; cards without an `mmdd` fall back to `_default` or show `—`. `mmdd` is the
statement-cycle date (anchor month + closing day), **not** a physical card-expiry year.

### `/set-recurringRule <describe the rule in plain words>`

Change what counts as a **recurring merchant ("ร้านค้าประจำ")** by *describing it in words* —
Claude translates the description into code and writes it into the **`recurring_rule.js`
hook only**. The main code is never touched. Examples the user might say:

- "ร้านที่จ่ายติดกันอย่างน้อย 4 เดือน หรือใช้เกิน 5 ครั้งรวม"
- "any merchant used in 6 or more different months"
- "paid every month with a total over 5000"

Claude rewrites the body of `window.CCRULE = function isRecurring(m){ ... }` accordingly.
The input object `m` and its fields are documented at the top of `recurring_rule.js`
(`maxRun` = longest consecutive-month run, `multi` = months with >1 charge, `mCount`,
`months`, `total`, `n`, `cat`, …). Return `true` = counts as recurring.

### `/set-merchantRule <describe the mapping in plain words>`

Map merchants to categories and clean up merchant names by *describing them in words*. Claude
writes the entries into **`merchant_rules.json` only** (git-ignored, **not** shipped — so it
survives plugin updates, unlike editing `build_data.py`). `cat()` / `merch()` read this file
and apply the user's rules on top of the built-in defaults. Three sections:

- **`category`** — `"KEYWORD": "CategoryKey"` (value must be a valid `CAT_ORDER` key). e.g.
  `GRAB → Transport & Ride-hailing`, `SHOPEE → Online Shopping`.
- **`cleanup`** — `"KEYWORD": "Display Name"` so one merchant stops splitting into many names
  (e.g. `GRAB → Grab`).
- **`exclude`** — extra non-spending keywords to drop (payments/cashback/refunds already are).

User rules win over defaults; EXCLUDE always applies first; an invalid category value is ignored.
Rebuild after editing so the rules take effect.

### `/list-merchantRules`

Read-only: print the current `merchant_rules.json` as tables (category, cleanup, exclude), and
flag any `category` value that is not a valid `CAT_ORDER` key (ignored at build time). If the
file is absent, report that only the built-in defaults apply.

### Merchant grouping (auto + suggest)

`merch()` **auto-collapses** names that differ only by a trailing counter/ref, so
`Awn…Siam Paragon 01/10`, `…02/10`, `…03/10` become one merchant. When names share a leading
brand word but differ in the middle (e.g. `Shell 0186F Co Temjaib Bangkok` vs
`Shell 0202F Co Lertvan Bangkok`) it does **not** merge blindly — the build prints a
**MERCHANT GROUPING SUGGESTIONS** block listing the cluster and a ready `/set-merchantRule`
line. Relay those suggestions to the user and let them confirm (the "ask when unsure" path).
Nothing here changes totals; merchant grouping is display-only.

**Default rule (shipped):** paid in **≥3 consecutive months**, OR appears in **≥3 months with
more than one charge** that month. Insurance is excluded before the rule runs.

> Scope note: the hook is JavaScript and drives the **dashboard**. The Markdown report's
> recurring list uses the built-in default `3/3`. If the user wants the report to match a
> custom rule too, mirror the logic in `build_data.py`'s `recurring()` (a deliberate,
> separate edit) — otherwise leave the report on the default.

---

## Pipeline

```
statement PDFs
  → pdftotext -layout            (convert each PDF to text; cache the .txt in .txt_cache/)
                                 (no PDFs present? build from the cached .txt directly)
  → detect card (last 4 digits) + statement month FROM THE TEXT CONTENT (not the filename)
  → parse rows per card's layout  (transaction date, description, amount)
  → normalize + de-duplicate
  → categorize from the description text
  → write data.js (window.CCDATA: tx, cards, cardMeta, reduceGroups, …)
  → write report.md + brief.md
  → assemble dashboard.html (inline chart lib + data + fonts + recurring_rule.js → offline single file)
```

---

## Data rules (non-negotiable)

These keep the numbers correct and reproducible. Do not weaken them.

- **Count real spending only.** Exclude card payments, cashback, credit adjustments,
  refunds, and any negative/credit lines.
- **Remove cancelled reversal pairs.** When a charge and an equal, opposite entry match on
  (card, amount, description), drop both. The description is normalized first — a leading
  reversal marker (`REVERSAL`/`VOID`/`ยกเลิก`/…) is stripped so `REVERSAL X` pairs with `X`.
  Matching runs in two passes: same transaction date first, then any date for leftovers, so a
  same-day reversal is preferred but a cross-day one still cancels. (The dedupe key is separate
  and stays exact on date — see below.)
- **Use the transaction date**, not the posting date.
- **Read the statement month and card from the file content**, not the filename. Some issuers
  name files with an offset — always trust the content.
- **Categorize from the description text**, not the bank's MCC code.
- **De-duplication key (never change it):** `(card, transaction date, raw description, amount)`.
  Re-running on the same inputs must produce identical output. Dropping the same statement
  file in twice must not change totals. Accepted limitation: two genuinely separate, identical
  charges (same merchant, day, and exact amount) are counted once.

## Derived definitions (keep consistent everywhere)

- **Recurring merchant** = whatever `recurring_rule.js` returns (default: ≥3 consecutive
  months **or** ≥3 months with >1 charge). Insurance excluded.
- **Cycle accumulation** = per card, from its anchor month forward; **independent of the
  dashboard's month-range filter**. Anchor comes from `cards.config.json` `mmdd` (MM), else
  the earliest month seen.
- **Average per month** = total ÷ number of months that actually have transactions.
- **Reducible group** = categories grouped as `reduce` (surfaced as `reduceGroups`).
- **Estimated saving** = reducible total × a fixed percentage. Label it an estimate, not
  financial advice.

---

## Configuration the user provides (no defaults baked in)

Keep all identifying specifics out of the committed code:

- **Cards**: names + closing dates live only in `cards.config.json` (git-ignored). Detection
  from statement text (last-5) and the per-issuer parser layout live in clearly-marked config
  at the top of `build_data.py` using **generic** examples only.
- **Category rules**: `keyword(s) → category` mappings applied to the description. Ship only
  generic, non-identifying examples (`"SUPERMARKET" → Groceries`, `"FUEL"/"PETROL" → Fuel`).
  The user adds their own merchant keywords locally.
- **Merchant name cleanup**: raw-description → display-name mappings (user-supplied).
- **Category grouping**: which categories are essential / reducible / one-off.
- **Recurring rule**: `recurring_rule.js` (via `/set-recurringRule`).
- **Cycle anchor / closing day** per card: `cards.config.json` (via `/set-expiryCard`).
- **Merchant→category + name cleanup**: `merchant_rules.json` (via `/set-merchantRule`);
  git-ignored, not shipped, so it survives plugin updates.

---

## Dashboard conventions (hard-won; follow them)

The dashboard is a template `index.html` that loads `data.js` (data stays separate from
markup — never embed data back into the source `index.html`). The **delivered** artifact is a
single self-contained `dashboard.html`.

**Single-file / offline output.** Generate `dashboard.html` by inlining, into a copy of
`index.html`: (1) the vendored Chart.js UMD, (2) the data (`window.CCDATA`), (3) the web font
as base64 `@font-face`, and (4) the `recurring_rule.js` hook. Drop the `data.sample.js` tag
(the real data overrides it). Result: one file that opens by double-click with no companion
files and no network. Guard inlined scripts by escaping any literal `</script>`.

**Table alignment (uniform across every table).** Text columns → left-aligned. Numeric /
amount columns → **right-aligned, always**, including inside nested / expandable / drilled-down
tables. Column headers → centered. Keep any "total" summary row pinned at the bottom when
sorting.

**Numbers.** One consistent format (e.g. one decimal on abbreviated values like `1.2K`). On
charts, draw value labels on the bars; keep axis labels terse (`K`/`M`, no trailing `.0`).

**Sorting.** One generic "make this table sortable" helper: clicking any header sorts by that
column, toggles direction, shows an arrow, auto-detects type (number / date / text). Apply to
every table.

**Cross-navigation.** Make a category/label clickable to jump to a filtered view (e.g. click a
category in the monthly-by-category comparison → open the merchants view filtered to it).

**Layout.** Left-align content with a sensible max-width; no page-level horizontal scrollbar.
Wide tables may scroll inside their own container. Verify alignment rules still hold at narrow
widths (a mobile media query can accidentally override number alignment).

---

## Mandatory verification before delivering any UI/code change

Never hand over an edited dashboard or generator without running these:

1. **Syntax** — `node --check` on the dashboard's scripts; parse the generator
   (`python3.12 -m py_compile` / `ast.parse`).
2. **Functional (headless browser).** Load `dashboard.html` headless and drive it: switch every
   tab, change every filter (card, month range, category), click sortable headers, open a
   drill-down, click a cross-navigation link. Assert **zero console/page errors** and that
   charts rendered (canvas non-zero size).
3. **Auto N-card.** Confirm the number of card buttons / cycle blocks equals the number of
   cards in the data, with distinct colors and working per-card filtering.
4. **Recurring hook.** Confirm `recurring_rule.js` loads and the recurring list reflects it;
   confirm that removing the hook falls back to the default without errors.
5. **De-dup idempotency.** Duplicate one statement file under a new name, rebuild, confirm the
   transaction count is unchanged; then remove the test file.
6. **No page-level horizontal scroll** at the target width.

If any check fails, fix it before delivering, and show the check results.

---

## Answering analytical questions

- **Never guess numbers.** Every figure must come from the generated reports or from a small
  script that queries `data.js`. If the data doesn't support an answer, say so.
- On a build/script error, show the error and stop — do **not** summarize from stale data.
- Reply in the user's language; keep it concise.

---

## Standard "update" routine

1. Count PDFs in `statements/`; if nothing new, say so and stop.
2. Note the current latest month and total from `brief.md`.
3. Run the build.
4. Report a small table: files / raw lines / duplicates removed / reversal pairs / final
   transactions / number of cards detected.
5. Anomaly checks: duplicates-removed unusually high → possible duplicate file; latest month
   unchanged → new file may not have been read; total dropped vs last run → investigate;
   an unexpected new card key appearing → confirm it's really a new card, not a mis-parse.
6. Summarize the latest month: total, change vs previous month, top movers, top merchants,
   points to review, and a couple of concrete reduction ideas (framed as estimates).
