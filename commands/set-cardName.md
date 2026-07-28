---
description: Set a credit card's display name by its last 4 digits — replaces the Card ••xxxx fallback shown on the dashboard buttons.
argument-hint: '<last4> "<name>"'
---

Give a card a real **display name** (the label on the dashboard card buttons). Cards with no name
show the fallback `Card ••<last4>`. Writes **`cards.config.json` only** (git-ignored, not shipped —
survives plugin updates). Never edits `build_data.py` — the build already reads the name
(`cardMeta[k].name`).

Argument reference: `$1` = the card's last 4 digits. The **name** is everything after `$1` (quotes
optional; strip surrounding quotes) — e.g. `/set-cardName 5006 "KBank Travel"`.

Do this:

1. **Validate.** `$1` must be exactly 4 digits. The name must be non-empty. If either is wrong,
   stop and show the format (`/set-cardName 5006 "KBank Travel"`).
2. **Open** `cards.config.json` in `skills/credit-card-spending-dashboard/` (the build's
   `CARDS_CONFIG` path, git-ignored). If it does not exist, create it from
   `cards.config.example.json` emptied to `{}` — keep the `_comment`.
3. **Upsert** the entry for key `$1`: set `"name"` to the given name. **Preserve** any existing
   `"mm"` / legacy `"mmdd"` and every other key. Never touch reserved `_`-keys (`_comment`,
   `_default`).
4. **Rebuild:** `cd skills/credit-card-spending-dashboard && python3 build_data.py` (Python 3.12+;
   use `python3.12` if `python3` is older). This refreshes `cardMeta.name`.
5. **Confirm** back: show the updated JSON entry and that the button now reads the name. Note that a
   card not yet detected from a statement can still be named, but its button only appears after a
   build detects it. On a build error, show the error and stop.

> To set the cycle anchor month instead, use `/set-expiryCard <last4> <mm>`. To see all cards, use
> `/list-cards`. To auto-discover names from statement text, run `/update-dashboard`.
