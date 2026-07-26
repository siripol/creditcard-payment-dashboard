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

- `/updateCreditCardStatement` — the monthly run: build + report stats + anomaly checks +
  deliver `dashboard.html`. Command form of the "Standard update routine" in `SKILL.md`.
- `/set-expiryCard <last5> <mmdd>` — upsert one entry in `cards.config.json` (cycle anchor
  month `MM` + closing day `DD`), then rebuild. Edits config only.
- `/set-recurringRule <plain words>` — translate a natural-language rule into the
  `recurring_rule.js` hook body **only**. Never touches `build_data.py` / `index.html`.

## Architecture (the big picture)

Pipeline in `build_data.py::build()`:

```
statement PDFs
  -> pdftotext -layout (cached in .txt_cache/)
  -> detect card = LAST 5 DIGITS (card_key) + statement month FROM TEXT CONTENT, not filename
  -> parse rows per layout (parse_card_a / parse_card_b — EXAMPLE parsers, adapt per bank)
  -> categorise (cat) + clean merchant name (merch) from the DESCRIPTION text
  -> drop non-spending (payments/cashback/refunds/negatives), dedupe, cancel reversal pairs
  -> write data.js  (window.CCDATA = {tx, cards, cardMeta, reduceGroups, catOrder, ...})
  -> write spending_report.md + monthly_brief.md
  -> assemble dashboard.html (inline chart.umd.js + CCDATA + base64 fonts + recurring_rule.js)
```

**Template ↔ data separation (do not break):** `index.html` is a static template that loads
data at runtime via `<script src="data.js">` (`window.CCDATA`). Never embed generated data
back into `index.html`. The delivered single-file `dashboard.html` is produced by
`write_single_html()`, which inlines everything into a *copy* of `index.html`.

**Auto N-card:** no card names/count are hardcoded. `build()` emits `cards` + `cardMeta`
(name, cycle `anchor`, colors from `CARD_PALETTE`) + `reduceGroups`; `index.html` renders
every card button, cycle block, and color dynamically from that payload.
`cards.config.json` only *names/tunes* cards — it never *enables* them (unlisted cards show
as `Card ••<last5>`).

**The recurring-merchant hook is intentionally duplicated:** the JS `window.CCRULE` in
`recurring_rule.js` drives the **dashboard**; `build_data.py::recurring()` hardcodes the
default `maxRun>=3 || multi>=3` for the **Markdown report**. `/set-recurringRule` edits only
the JS hook — the report stays on the default unless the user explicitly asks to mirror it in
`recurring()`. Insurance is excluded before either rule runs.

**Per-bank adaptation points** (marked as generic EXAMPLES in `build_data.py`): `card_key()`
regex, `parse_card_a` / `parse_card_b` layouts + their routing in `build()`, the `cat()`
keyword→category map, and `merch()` name cleanup. Category keys must stay consistent across
`cat()`, `CAT_ORDER`, `TH`, `COLORS`, `GROUP`.

## Data-integrity rules (non-negotiable — never weaken)

- Count real spending only; exclude payments, cashback, credit adjustments, refunds, negatives.
- Remove matched reversal pairs (same card+date+desc+amount, opposite sign).
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

## Answering spending questions

Never guess numbers — every figure must come from the generated reports or a small script
querying `data.js`. On a build/script error, show the error and stop; do not summarize from
stale data.

## Privacy (hard rule)

Commit only code. `statements/`, `data.js`, `dashboard.html`, `cards.config.json`, and the
generated `*_report.md` / `*_brief.md` are git-ignored — never commit them.
