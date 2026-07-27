---
description: Set a credit card's cycle anchor month (the month its accumulation cycle resets) by its last 4 digits.
argument-hint: <last4> <mm>
---

Update the credit-card dashboard config for card `$1` with cycle anchor month `$2`.

Argument reference: `$1` = the last 4 digits of the card. `$2` = `MM`, the cycle anchor month
(the month the rewards/accumulation cycle resets on), `01`–`12`.

Do this:

1. Validate the arguments. `$1` must be exactly 4 digits. `$2` must be 2 digits `01`–`12`. If
   either is invalid, stop and explain the correct format (`/set-expiryCard 1234 10`).
2. Open `cards.config.json` in the project root (it is git-ignored). If it does not exist,
   create it by copying `cards.config.example.json` and emptying it to `{}` first.
3. Upsert the entry for key `$1`: set `"mm": "$2"`. **Preserve any existing `"name"`.** If
   there is no name yet, leave it unset — the dashboard will display `Card ••$1` until named.
   (A legacy `"mmdd"` value on an existing entry still works — the build reads its leading `MM`.)
4. Re-run the build so the change takes effect: `python3 build_data.py` (requires Python
   3.12+; use `python3.12` explicitly if `python3` is older). This refreshes `cardMeta.anchor`.
5. Confirm back to the user: show the updated JSON entry and the resulting cycle anchor month.
