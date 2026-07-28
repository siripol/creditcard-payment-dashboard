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
  what counts as a recurring shop", "list my cards", "rebuild the dashboard",
  "categorize a merchant", "why is this merchant Other", "/set-expiryCard", "/set-recurringRule",
  "/list-cards", "/update-dashboard", "/set-category".
---

# Credit-Card Spending Dashboard

A reusable workflow for turning monthly credit-card statement PDFs into a clean, offline,
single-file HTML dashboard with supporting Markdown reports. This skill contains **no
personal data** — it describes the method. The user supplies their own statements and
configures their own cards and categorization.

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
`/update-dashboard` (re-categorize from existing statements, no new imports) both run the build;
`/set-expiryCard`, `/set-recurringRule`, and `/set-category` each edit exactly one small
config/hook file — never the main `build_data.py` logic; `/list-cards` is read-only.

### `/update-statement`

Run the monthly update. Collect the newly-attached PDFs (and any in `statements/`), rebuild
via `python3 build_data.py`, report the build stats and anomaly checks, deliver the refreshed
single-file `dashboard.html`, and summarize the latest month. This is the command form of the
"Standard update routine" at the bottom of this file; the skill also triggers on the phrase
"update the spending dashboard".

### `/update-dashboard`

Re-categorize and rebuild from the **existing** statements — **no new PDFs**. Use after editing
`cards.config.json` or the recurring rule. Same engine as `/update-statement` (each build
re-runs `category()`/`merchant_name()`/`merchant_group()` on every row), minus the import step.
Source precedence is `statements/` → `.txt_cache/` → `data.js`: with neither statements nor cache
the build falls back to the existing `data.js`, re-deriving category + grouping from each row's
stored `desc`/`merch` (best-effort — `desc` is stored capped at 2048 chars; full statement text
gives a guaranteed re-categorize). If `data.js` is also absent it stops.

### `/set-expiryCard <last4> <mm>`

Set a card's **cycle anchor month**. `<last4>` = the last 4 digits of the card. `<mm>` = `MM`,
the month the accumulation cycle anchors on (`01`–`12`).
Example: `/set-expiryCard 1234 10` → card ••1234, cycle anchors in October. Implementation:
upsert the entry in `cards.config.json`:

```json
{ "1234": { "name": "My Travel Card", "mm": "10" } }
```

Then rebuild so `cardMeta.anchor` picks up the month. (A legacy `"mmdd"` value still works — the
build reads its leading `MM`.)

**Default for new cards (`_default`).** A reserved `_default` key in `cards.config.json` sets an
`mm` fallback that `build()` applies automatically to any *newly-detected* card that has no
cycle month yet — e.g. `"_default": { "mm": "12" }` gives every new card a December anchor.
Existing entries are never overwritten (idempotent), and the new entry is persisted back to
`cards.config.json` so it stays editable. If `_default` is absent, an unlisted card keeps the
generic behaviour (anchor derived from its earliest statement month).

### `/list-cards`

List **every** card in one table: display name, last 4 digits, and cycle anchor month (`mm`).
Merges the detected card set from `CCDATA.cardMeta` (in `data.js`) with each card's `mm` from
`cards.config.json`; cards without a month fall back to `_default` or show `—`. `mm` is the
cycle anchor month, **not** a physical card-expiry year.

### `/list-category` and `/list-merchantGroup`

Read-only counterparts of `/set-category` and `/set-merchantGroup`. `/list-category` lists the
`merchant_category.json` overrides (keyword→category); `/list-merchantGroup` lists the
`merchant_group.json` overrides (regex→group name, first-match-wins). Each shows how many
merchants/tx the entry matches in `data.js` (counts computed from data, **never guessed**) and
flags stale entries that match nothing. Neither writes config or rebuilds.

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

**Default rule (shipped):** paid in **≥3 consecutive months**, OR appears in **≥3 months with
more than one charge** that month. Insurance is excluded before the rule runs.

### `/set-category [<keyword> <Category>]`

Fix merchants that fall into `Other`. Writes a keyword→category map into **`merchant_category.json`
only** (git-ignored, not shipped — survives updates). `category()` applies it after `EXCLUDE`,
before the built-in rules; a value not in `CAT_ORDER` is ignored. **Category-only — merchant names
are never changed.** Two modes: **manual** (`/set-category EXAMPLE INSURANCE Insurance`), or **no
args** → Claude reads the `Other` merchants (from the build's `UNCATEGORIZED MERCHANTS` report /
`data.js`), proposes a category for each, and **asks the user to confirm** before writing. Rebuild
applies it. Each written entry records provenance in a reserved `_source` map (`"user"` for manual,
`"llm"` for classified); `_`-prefixed keys are skipped by `load_category_overrides()`.

### `/auto-categorize`

Bulk LLM re-categorization of **all** merchants — corrects built-in mis-categorizations too, not
just `Other` — while **never touching any merchant already pinned in `merchant_category.json`**
(i.e. anything with an existing keyword). Claude proposes the correct category per non-pinned
merchant, **shows a summary table of the changes and asks the user to confirm**, then writes the
accepted entries with `_source="llm"` and rebuilds. Opt-in (merchant names are sent to Claude).
`/list-category` shows the `Source` column so user-pinned vs LLM entries are distinguishable.

### `/set-merchantGroup`

Collapse merchants that differ only by a changing token (e.g. `ExampleSub*AB12CD34 CITY`,
`ExampleSub*EF56GH78 CITY`, …) into one **named group**, or rename a group. Writes a
regex→group-name map into **`merchant_group.json` only** (git-ignored, not shipped — survives
updates); `merchant_group()` applies it **before** instalment stripping (first matching regex wins).
**Grouping-only — the raw `tx.merch` is never renamed**, only the derived `merchGroup`. Modes:
**create** (paste example lines or an image → Claude derives the regex, previews every match against
`data.js` and **refuses over-broad patterns**, then asks for the group name), **rename existing**
(`rename "<old>" -> "<new>"`), and **rename an auto-derived group** (creates an override matching its
members). Every write is confirmed first. This is the user-curated, safe counterpart to the auto
prefix-collapse reverted in v0.7.0.

### `/add-merchantToGroup` and `/remove-merchantFromGroup`

The **per-merchant** counterpart to the regex-based `/set-merchantGroup` — same
`merchant_group.json`, same first-match-wins order, grouping-only (raw `tx.merch` never renamed).
A single merchant is written as a **literal, anchored** rule (`^<escaped merch>$`), **prepended**
so it beats any broad rule.

- **`/add-merchantToGroup <merchant> <group>`** — resolve the exact merchant from `data.js`
  (asks if fuzzy/multiple, refuses 0-match), show current→new group, confirm, then upsert the
  anchored rule (replaces an existing rule for the same merchant rather than duplicating).
- **`/remove-merchantFromGroup <merchant>`** — pull one merchant out so it stands alone. Covers
  all routes a merchant is grouped: if a literal `^merch$` entry exists → **delete it** (this both
  leaves a group and **undoes a self-pin**); else if grouped by a broad regex or instalment-strip
  → **prepend a self-pin** `{^merch$ → merch}` (others in the broad rule untouched); else already
  standalone → no-op. It distinguishes a self-pin from a never-grouped merchant by whether the
  entry exists, not just by `merchGroup == merch`.
- **`/remove-merchantFromGroup group "<G>"`** — dissolve a whole group: delete every entry whose
  `group == G`; members revert. Reports "nothing to delete" if `G` has no override entries.

### Instalment grouping (`merchGroup`)

Instalments like `2C2P *EXAMPLE INSURANCE 01/03`, `02/03`, `03/03` (same shop, different งวด) are
grouped into one merchant so per-merchant totals are correct. `merchant_group()` derives a
`tx.merchGroup` (the name with a recognised `N/M`/`งวด`/`ผ่อน` counter and any trailing amount
stripped) — the **raw `tx.merch` is kept untouched** (traceable). The dashboard aggregates merchants
by `merchGroup`; the monthly tab still shows each งวด; the all-transactions tab shows both
`ร้านค้า (ตามบิล)` and `กลุ่มร้านค้า`. Different-core merchants (e.g. `Shell` branches) never merge.

### Foreign-currency charges (`tx.fx`)

Some issuers append the original charge currency+amount (e.g. `… USD 12.34`) to an overseas
transaction's description, before the THB posting amount. `FX_CCY` + `foreign_charge()` capture
that trailing `<CCY> <amount>` into `tx.fx`; `merchant_name()` strips it so `merch`/`merchGroup`
stay clean (foreign merchants that differed only by that amount now group together). Raw `tx.desc`
keeps the full text. The dashboard shows `tx.fx` as a muted line under the amount (all-transactions
tab + drill-down) and as a CSV column. `FX_CCY` is a per-bank adaptation point — extend it to the
currency codes your statements print.

The dashboard's **Merchant Group** (mapping QA) tab — one screen per card — lists every
`merchGroup` with the distinct `ร้านค้า (ตามบิล)` names merged into it, its category, count and
total, flagging groups that merged >1 name (a count badge) and groups still in `Other` (dimmed).
Use it to eyeball that grouping and categorization are correct. In the ร้านค้า matrix and the
category matrix, **every month column header is click-to-sort** (like `เฉลี่ย/เดือน` / `รวม`).

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
- **Multi-card statements: attribute each row to its own card.** One statement PDF may list 2+
  cards (a card-number header, then that card's transactions). The parsers track a *current card*
  via `card_key_from_line()` and stamp each row; `build()` only fills the file-level
  `detect_card_key()` for rows left blank, never overwriting a per-section attribution. A header
  token must contain a mask char (`X`/`*`) so a long digit run in a merchant name isn't mistaken
  for a PAN. `_CARD_HEADER_RE` is the per-bank adaptation point. Card is part of the dedupe key and
  every per-card total, so a wrong card corrupts everything.
- **Categorize from the description text**, not the bank's MCC code.
- **De-duplication key (never change it):** `(card, transaction date, raw description, amount)`.
  Re-running on the same inputs must produce identical output. Dropping the same statement
  file in twice must not change totals. Accepted limitation: two genuinely separate, identical
  charges (same merchant, day, and exact amount) are counted once.

## Derived definitions (keep consistent everywhere)

- **Recurring merchant** = whatever `recurring_rule.js` returns (default: ≥3 consecutive
  months **or** ≥3 months with >1 charge). Insurance excluded.
- **Cycle accumulation** = per card, from its anchor month forward; **independent of the
  dashboard's month-range filter**. Anchor comes from `cards.config.json` `mm` (or a legacy
  `mmdd`'s leading MM), else the earliest month seen.
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
- **Cycle anchor month** per card: `cards.config.json` (via `/set-expiryCard`).
- **Merchant→category overrides**: `merchant_category.json` (via `/set-category`); git-ignored,
  not shipped, survives plugin updates. Category-only; the build reports what's still `Other`.
- **Merchant-group overrides**: `merchant_group.json` (via `/set-merchantGroup`); git-ignored, not
  shipped, survives updates. Regex→group-name; grouping-only (never renames raw `tx.merch`).

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
