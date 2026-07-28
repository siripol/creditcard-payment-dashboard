# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code / Cowork plugin** (`.claude-plugin/plugin.json`) that turns monthly
credit-card **statement PDFs** into one self-contained offline `dashboard.html` plus Markdown
reports. Generic and **card-count-agnostic**: dropping a new card's e-statements into
`statements/` makes it appear automatically — no code edit. Ships with **no personal data**.

The plugin surface = 3 slash commands (`commands/`) + 1 skill
(`skills/credit-card-spending-dashboard/`). All real logic lives in the skill.

## Commands (build / run)

No test suite, linter, or build system. The one build command is:

```bash
cd skills/credit-card-spending-dashboard
python3 build_data.py     # PDFs in statements/ -> data.js + reports + dashboard.html
```

- **Requires Python 3.12+** — the generator uses backslashes inside f-string expressions,
  which older Python rejects with `SyntaxError`. If `python3` is older, invoke `python3.12`
  explicitly; do NOT rewrite the source to satisfy an old interpreter.
- Also needs `pdftotext -layout` (poppler-utils) on PATH, and `node` (only for the
  `node --check` JS syntax step during verification).
- Preview with fake data, no build: `cp data.sample.js data.js && open index.html`
  (`index.html` also falls back to `data.sample.js` when `data.js` is absent).
- Env overrides: `CC_SOURCE_DIR` (PDF folder), `CC_OUT`, `CC_DASH`, `CC_MD`, `CC_BRIEF`.

## Slash commands (each maps to one narrow edit)

- `/update-statement` — the monthly run: build + report stats + anomaly checks +
  deliver `dashboard.html`. Command form of the "Standard update routine" in `SKILL.md`.
- `/update-dashboard` — re-categorize + rebuild from existing statements, **no new PDFs**.
  Same `build_data.py` engine (each build re-runs `category()`/`merchant_name()`/`merchant_group()`
  and re-reads `cards.config.json` / `merchant_category.json` / `recurring_rule.js`). Source
  precedence `statements/` → `.txt_cache/` → `data.js`: with neither statements nor cache it falls
  back to the existing `data.js`, re-deriving category + grouping from each row's stored
  `desc`/`merch` (best-effort — `desc` is stored capped, see below).
- `/set-category [<keyword> <Category>]` — map merchants stuck in `Other` to a category. Writes
  `merchant_category.json` **only** (git-ignored, not shipped). Manual (`<keyword> <Category>`,
  `_source="user"`) or, with no args, Claude classifies the `Other` merchants (`_source="llm"`,
  with a confirm step). Category-only — never renames a merchant.
- `/auto-categorize` — bulk LLM re-categorization of **all** merchants (also corrects built-in
  mis-categorizations, not just `Other`), **skipping any merchant already pinned in
  `merchant_category.json`**. Shows a summary table of proposed changes, confirms, writes entries
  with `_source="llm"`, rebuilds. Opt-in (merchant names go to Claude). Never edits `build_data.py`.
  The reserved `_source` map (`keyword → "user" | "llm"`) records provenance; `user`-sourced entries
  are pinned and never auto-changed. Loader ignores `_`-keys, so no `build_data.py` change.
- `/set-merchantGroup` — group varying-token merchants (e.g. `ExampleSub*XXXX CITY`) under one
  name via a **regex**, or rename a group. User pastes example lines / an image; Claude derives the
  pattern, previews every match against `data.js` and **refuses over-broad patterns**, then (create
  mode) asks for the group name. Writes `merchant_group.json` **only** (git-ignored, not shipped).
  Grouping-only — sets the derived `merchGroup`, never renames the raw `tx.merch`. Confirms before
  every write. This is the user-curated, safe counterpart to the auto prefix-collapse reverted in
  v0.7.0.
- `/add-merchantToGroup <merchant> <group>` — per-merchant counterpart to `/set-merchantGroup`:
  add one exact merchant to a group. Resolves the merchant from `data.js`, then **prepends** a
  literal anchored rule `{"pattern": "^<escaped merch>$", "group": "<G>"}` to `merchant_group.json`
  **only** (replaces an existing same-pattern rule, never duplicates). Grouping-only, confirms.
- `/remove-merchantFromGroup <merchant>` — pull one merchant out (stands alone), or
  `group "<name>"` to dissolve a whole group. Single-merchant: if a literal `^merch$` entry exists
  → **delete it** (covers leaving a group *and* undoing a self-pin); else grouped by broad regex /
  instalment-strip → **prepend a self-pin** `{^merch$ → own name}`; else already standalone → no-op
  (distinguishes self-pin from never-grouped by entry existence, not just `merchGroup == merch`).
  Dissolve: delete every entry with `group == name`. Writes `merchant_group.json` **only**, confirms.
- `/set-expiryCard <last4> <mm>` — upsert one entry in `cards.config.json` (cycle anchor
  month `MM`, `01`–`12`), then rebuild. Edits config only.
- `/set-recurringRule <plain words>` — translate a natural-language rule into the
  `recurring_rule.js` hook body **only**. Never touches `build_data.py` / `index.html`.
- `/list-cards` — read-only: print a table of every card (name, last 4 digits, cycle/expiry
  `mm`) by merging `CCDATA.cardMeta` (from `data.js`) with per-card `mm` in `cards.config.json`.
- `/list-category` — read-only: list the `merchant_category.json` overrides (keyword→category) with
  how many merchants/tx each matches in `data.js`; flags stale (0-match) entries. Counterpart of
  `/set-category`.
- `/list-merchantGroup` — read-only: list the `merchant_group.json` overrides (regex→group name)
  with match counts (first-match-wins) + example merchants; flags stale entries. Counterpart of
  `/set-merchantGroup`. Both list commands compute counts from `data.js` (never guessed) and write
  nothing.

## Architecture (the big picture)

Pipeline in `build_data.py::build()`:

```
statement PDFs
  -> pdftotext -layout (cached in .txt_cache/)   [no PDFs? build from .txt_cache directly]
  -> detect card = LAST 4 DIGITS (card_key) + statement month FROM TEXT CONTENT, not filename
     (a statement with 2+ cards: parsers stamp each row from its section header, see below)
  -> parse rows per layout (parse_card_a / parse_card_b — EXAMPLE parsers, adapt per bank)
  -> categorise (category(), + user overrides from merchant_category.json) + clean merchant name
     (merchant_name()) + grouping key (merchant_group() -> tx.merchGroup) from the DESCRIPTION text
  -> drop non-spending (payments/cashback/refunds/negatives), dedupe, cancel reversal pairs
  -> write data.js  (window.CCDATA = {tx:[{d,m,card,cat,merch,merchGroup,desc,fx,amt}], cards, cardMeta, ...})
  -> write spending_report.md + monthly_brief.md
  -> assemble dashboard.html (inline chart.umd.js + CCDATA + base64 fonts + recurring_rule.js)
```

**`.txt_cache/` is the complete text archive.** `pdftotext -layout` output is cached per
statement (full raw text, nothing dropped). `build()` uses it as a cache when PDFs are present,
and **falls back to it as the source when `statements/` has no PDFs** — so the PDFs can be
removed and rebuilds still work (re-parse, re-categorize, regenerate `data.js`/dashboard). It
stays git-ignored (personal data). This is why no database is needed: the raw text is the
durable store, and `data.js` is fully regenerable from it.

**Source precedence (`load_rows_from_data_js()`):** `build()` resolves rows from `statements/`
PDFs → `.txt_cache/` → **`data.js`** (last resort). When there is neither statement text nor
cache, it reconstructs parser rows from an existing `data.js` (`window.CCDATA.tx`, mapped back to
`card/stmt/date/desc/amt`) and re-derives `category()`/`merchant_name()`/`merchant_group()` from
the stored `desc`/`merch` — so a stale dashboard whose rows predate `merchGroup` can be fixed with
no raw statements. It's best-effort: `tx.desc` is stored capped at **2048 chars** (was 48), so a
description longer than the cap at build time may re-categorize imperfectly; full statement text
always beats it. The dedupe key and reversal pass run unchanged (idempotent on already-clean tx).

**Template ↔ data separation (do not break):** `index.html` is a static template that loads
data at runtime via `<script src="data.js">` (`window.CCDATA`). Never embed generated data
back into `index.html`. The delivered single-file `dashboard.html` is produced by
`write_single_html()`, which inlines everything into a *copy* of `index.html`.

**Auto N-card:** no card names/count are hardcoded. `build()` emits `cards` + `cardMeta`
(name, cycle `anchor`, colors from `CARD_PALETTE`) + `reduceGroups`; `index.html` renders
every card button, cycle block, and color dynamically from that payload.
`cards.config.json` only *names/tunes* cards — it never *enables* them (unlisted cards show
as `Card ••<last4>`).

**`_default` cycle month:** a reserved `_default` key in `cards.config.json`
(`"_default": {"mm": "12"}`) is a per-user opt-in. `build()` calls `ensure_card_defaults()`
to give any newly-detected card with no cycle month that fallback, then persists it back to
`cards.config.json` (the one build-time write of that file) — idempotent, existing entries never
overwritten. Absent `_default` = generic behavior (anchor from the card's earliest statement
month). Reserved keys are `_`-prefixed and skipped by the `cardMeta` loop.

**The recurring-merchant hook is intentionally duplicated:** the JS `window.CCRULE` in
`recurring_rule.js` drives the **dashboard**; `build_data.py::recurring()` hardcodes the
default `maxRun>=3 || multi>=3` for the **Markdown report**. `/set-recurringRule` edits only
the JS hook — the report stays on the default unless the user explicitly asks to mirror it in
`recurring()`. Insurance is excluded before either rule runs.

**Per-bank adaptation points** (marked as generic EXAMPLES in `build_data.py`): `detect_card_key()`
regex, `_CARD_HEADER_RE` / `card_key_from_line()` (multi-card section headers), `parse_card_a` /
`parse_card_b` layouts + their routing in `build()`, the `category()` keyword→category map, and
`merchant_name()` name cleanup. Category keys must stay consistent across `category()`, `CAT_ORDER`
(module-level), `TH`, `COLORS`, `GROUP`.

**Multi-card statements (never mis-attribute):** a single statement PDF may list **more than one
card** (each card's number as a section header, then its transactions). `detect_card_key()` alone
finds only the *first* card, so the parsers track a **current card** via `card_key_from_line()` and
stamp every row with it; `build()` only fills the file-level `detect_card_key()` for rows the parser
left blank (single-card files, or rows before the first header) — it **never overwrites** a
per-section attribution. Safeguard: a header token must contain a mask char (`X`/`*`), so a long
digit run inside a merchant name (e.g. `ACME STORE 1234567890123`) is never mistaken for a PAN. This
matters because card is part of the dedupe key, cycle, and every per-card total — a wrong card
corrupts all of them. `_CARD_HEADER_RE` is the per-bank adaptation point.

**Category overrides (update-safe):** `category()` takes a keyword→category map from
`merchant_category.json` (`load_category_overrides()`, git-ignored, ships only
`merchant_category.example.json`). Applied after `EXCLUDE`, before the built-in rules; a value not
in `CAT_ORDER` is ignored. Category-only — never renames a merchant. Set via `/set-category`
(single) or `/auto-categorize` (bulk LLM, all non-pinned merchants). A reserved `_source` map in
the same file records provenance (`keyword → "user" | "llm"`); `user`-pinned entries are never
auto-changed. `_`-prefixed keys (`_comment`, `_source`) are skipped by `load_category_overrides()`,
so provenance needs no `build_data.py` change. The build prints an `UNCATEGORIZED MERCHANTS` report
so the user knows what still needs mapping.

**Numeric display:** every number shown in the dashboard uses comma thousands separators — amounts
via `fmt()`, integer counts via `nf()` (`Number(v).toLocaleString('en-US')`). Command-output tables
format with `:,` too. `fk()`/`_cyK()` keep the compact `฿3.8K`/`฿1.2M` form in the dense month
matrix on purpose (full numbers would widen columns and risk horizontal scroll).

**Instalment grouping (`tx.merchGroup`):** `merchant_group()` strips a recognised instalment counter
(`N/M` + `งวด`/`ผ่อน`/`INSTALLMENT` variants, and a trailing amount the parser may have left in) so
all งวด of a series share a core; `merchant_name()` output (`tx.merch`) is left untouched. Merge is
by identical core only (different cores like `Shell` branches never merge). `index.html` aggregates
merchants by `merchGroup` (`agg()`), drill-down shows the original `merch`; the all-transactions tab
has both `ร้านค้า (ตามบิล)` and `กลุ่มร้านค้า` columns, and the **Merchant Group** tab is a per-card
QA view of `merchGroup` ↔ member `merch`. The build reports each detected series (≥2 `N/M` rows of
equal amount).

**Merchant-group overrides (update-safe):** `merchant_group()` also takes a user regex→group-name
map from `merchant_group.json` (`load_group_overrides()`, git-ignored, ships only
`merchant_group.example.json`). Applied **before** the instalment stripping — the first matching
regex wins — so varying-token merchants (`ExampleSub*XXXX CITY`) collapse into one named group.
Set via `/set-merchantGroup`. This is the **user-curated, confirmed** form of merchant grouping;
automatic prefix collapse was reverted in v0.7.0 for silently merging distinct merchants, so overrides
are explicit and previewed. Grouping-only — the raw `tx.merch` is never renamed (only `merchGroup`).

**Foreign-currency charges (`tx.fx`):** some issuers append the original charge currency+amount to
an overseas transaction's description (e.g. `… USD 12.34`) before the THB posting amount. `FX_CCY`
+ `foreign_charge()` capture that trailing `<CCY> <amount>` into `tx.fx`, and `merchant_name()`
strips it so the display `merch`/`merchGroup` stay clean (a bonus: foreign merchants that differed
only by that amount now group together). Preserve-source holds: raw `tx.desc` keeps the full text;
only the derived `merch`/`merchGroup` are cleaned. `index.html` shows `tx.fx` as a muted sub-line
under the amount in the all-transactions tab + drill-down, and as a CSV column. `FX_CCY` is a
per-bank adaptation point (extend to the currency codes your statements print).

## Data-integrity rules (non-negotiable — never weaken)

- Count real spending only; exclude payments, cashback, credit adjustments, refunds, negatives.
- **Never overwrite a statement-sourced value; derive into a new field so the original is
  traceable.** e.g. instalment grouping keeps the raw `tx.merch` and adds `tx.merchGroup`; the
  dashboard aggregates by the derived field but the drill-down shows the original.
- Remove matched reversal pairs: opposite-sign entries on same `card`+`amount` with a
  **normalized** description (leading `REVERSAL`/`VOID`/`ยกเลิก`/… stripped, so `REVERSAL X`
  pairs with `X`). Two-pass: same transaction date first, then any date for leftovers. This is
  looser than the dedupe key on purpose — do not fold the two together; the dedupe key below
  stays exact on date and never changes.
- Use the **transaction date**, not posting date.
- Read statement month + card from **file content**, not the filename (issuers offset names).
- Categorize from the **description text**, not the bank MCC code.
- **Dedupe key = `(card, transaction date, raw description, amount)` — never change it.**
  Re-running on the same inputs must produce identical output; importing the same file twice
  must not change totals.

## Mandatory verification before delivering any UI/code change

Per `SKILL.md`, do not hand over an edited dashboard/generator without: `node --check` on the
dashboard scripts + parse the generator; load `dashboard.html` headless and drive every
tab/filter/sort/drill-down/cross-nav asserting zero console errors + charts rendered; confirm
N card buttons == N cards; confirm the recurring hook loads and falls back cleanly when
removed; confirm dedupe idempotency (duplicate a statement, rebuild, count unchanged); confirm
no page-level horizontal scroll. Show the check results.

## Commit discipline (docs before code)

**Before committing any code change, update ALL affected docs in the same commit.** A commit that
changes behavior, commands, or config without matching docs is incomplete. Concretely, sync
whichever of these the change touches: `README.md`, this `CLAUDE.md`, `skills/credit-card-spending-dashboard/{SKILL.md,README.md}`,
the relevant `commands/*.md`, and the command lists in `.claude-plugin/{plugin.json,marketplace.json}`.
Bump the version in **both** manifests. Grep the docs for anything the change touched (command
names, config filenames, version, pipeline behavior) and reconcile before `git add`. Applies to
feature adds, reverts, and behavior changes alike.

## Answering spending questions

Never guess numbers — every figure must come from the generated reports or a small script
querying `data.js`. On a build/script error, show the error and stop; do not summarize from
stale data.

## Privacy (hard rule)

Commit only code. `statements/`, `data.js`, `dashboard.html`, `cards.config.json`, and the
generated `*_report.md` / `*_brief.md` are git-ignored — never commit them.
