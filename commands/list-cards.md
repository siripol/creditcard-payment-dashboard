---
description: List every credit card — display name, last-4 digits, and cycle/expiry date (mmdd).
argument-hint: (no arguments)
---

Show a table of all credit cards known to the dashboard.

Do this:

1. **Gather the card set.** The authoritative list of detected cards is `CCDATA.cardMeta` in
   `skills/credit-card-spending-dashboard/data.js` (each key = the card's last 4 digits, with a
   display `name` and cycle `anchor` month). If `data.js` does not exist yet (e.g. a fresh
   container), run `python3 build_data.py` first (requires Python 3.12+; use `python3.12` if
   `python3` is older). If there are still no statements to build from, fall back to reading
   `cards.config.json` alone and note that any not-yet-imported cards won't appear until a build.
2. **Read the cycle/expiry dates.** Open `cards.config.json` (project root, git-ignored) and read
   each card's `mmdd`. This is the **statement-cycle date**, not a physical card-expiry year:
   `MM` = cycle anchor month, `DD` = closing day. Cards with no `mmdd` inherit `_default.mmdd`
   if that reserved key is set; otherwise show `—`.
3. **Render one row per card** — merge the two sources on the last-5 key:

   | Name | Last 4 | Expiry (mmdd) |
   |------|--------|---------------|

   For the Expiry column show the raw `mmdd` plus a decode, e.g. `1231 → closes day 31, cycle
   anchor เดือน ธ.ค.`. Use the card's `name` from `cardMeta`; if unnamed it displays as
   `Card ••<last4>`.
4. **Confirm the count**: number of rows must equal the number of cards in `cardMeta`.
5. Note under the table that `mmdd` is the statement-cycle date (anchor month + closing day), not
   the physical card expiry. To change one, use `/set-expiryCard <last4> <mmdd>`.
