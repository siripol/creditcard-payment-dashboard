# Migrations ledger

Ordered, per-version record of changes that affect a user's **local, git-ignored state**
(`cards.config.json`, `merchant_category.json`, `merchant_group.json`, `recurring_rule.js`,
`data.js`). The `/migrate` command reads this ledger and applies every entry newer than the
version recorded in `.cc_migration.json`, then rebuilds and stamps the marker.

**Maintainer rule:** on every version bump, add a row here **before** committing — even if the
action is "none (rebuild covers it)". See the pre-commit checklist in `CLAUDE.md`.

Guidance for actions:
- **rebuild** — `python3 build_data.py` regenerates `data.js` and re-derives fields, so no manual
  edit is needed. This is the default for any change to derived data.
- **none** — code/UI/doc-only change; no local state is affected.
- **manual** — the user must do something the build can't (e.g. re-add a marketplace); `/migrate`
  reports it.

All config transforms must be **idempotent** — detect already-migrated shape and no-op — so a
missing or stale marker never double-applies.

| Version | Config / state change | Action |
|---------|-----------------------|--------|
| ≤0.14.x | Baseline. Legacy `cards.config.json` may use `"mmdd"` instead of `"mm"`. | none — the build reads the leading `MM` of a legacy `mmdd` value, so old configs keep working. |
| 0.15.0  | `tx.merchGroup` (instalment grouping) and `tx.fx` (foreign-charge) fields in `data.js`. | rebuild — re-derives `merchGroup`/`fx` from each row's stored `desc`. |
| 0.16.0  | Per-merchant group commands (`/add-merchantToGroup`, `/remove-merchantFromGroup`). No schema change; `merchant_group.json` format unchanged (`{"groups":[{"pattern","group"}]}`). | none |
| 0.16.1  | Plugin **id renamed** `creditcard-payment-dashboard` → `credit-card-spending-dashboard`. Install path changed; local configs unaffected. | manual — re-add the marketplace: `/plugin marketplace add siripol/credit-card-spending-dashboard`, then `/plugin update credit-card-spending-dashboard@credit-card-spending-dashboard`. |
| 0.17.0  | New commands `/set-cardName`, `/migrate`, `/merge-merchantGroup`, `/auto-merchantGroup`, `/apply-userConfig`. Dashboard on-screen edits (Display Card, right-click group rename/merge + category) via localStorage → Export → `/apply-userConfig`. Optional reserved `"_hidden"` list in `cards.config.json` (Display-Card default → `CCDATA.hiddenCards`). Merchant Group tab is now all-cards. New `/version` command; the build stamps `CCDATA.version` (from `plugin.json`) into `data.js` (dashboard footer + `/version` show it). All additive/opt-in; no schema change to existing keys. | none — rebuild regenerates `CCDATA` (incl. `hiddenCards`, `version`). |
| 0.18.0  | CODE vs DATA split: user data (statements, `.txt_cache`, config JSONs, outputs, `.cc_migration.json`) now resolves from `CC_DATA_DIR` (default = skill dir, backward compatible) so plugin updates never overwrite it or leave a stale template. `/update-dashboard` gains a staleness guard (`CCDATA.version` vs plugin version → force rebuild). | manual — set `CC_DATA_DIR` (e.g. `$HOME/.credit-card-dashboard`); `/migrate` moves any legacy in-skill-dir data into it once, then rebuild. |
| 0.18.1  | Docs only: added a "Fresh install (Claude Desktop)" section to the README (prerequisites, install, first build, parser caveat). | none. |
| 0.18.2  | UI: fixed page-level horizontal scroll on phones (≤480px) — the overview structure bar (`.gbarbar`) forced a min-width wider than an iPhone screen. `dashboard.html` now opens cleanly on iPhone (view-only). | none — `/update-dashboard` rebuilds with the new template. |
| 0.18.3  | Parser fixes in `build_data.py`: `merchant_name()` no longer relabels by substring (COFFEE/FUEL/SUPERMARKET → generic name) so real shop names survive; `detect_card_key()` + `_CARD_HEADER_RE` no longer over-run a masked PAN into a same-line balance (fixed phantom last-4 like `0135`→`1351/1353` per month) and tolerate `' - '` separators. Attribution + display names change; **totals unchanged**. | rebuild — `/update-dashboard` re-derives names + card attribution (or `/update-statement` with the PDFs for a full re-parse). |
