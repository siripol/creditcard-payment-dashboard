---
description: Change what counts as a recurring merchant ("ร้านค้าประจำ") by describing the rule in plain words.
argument-hint: <describe the rule in your own words>
---

The user wants to change the recurring-merchant rule. Their description is:

"$ARGUMENTS"

Translate that description into a JavaScript predicate and write it into **`recurring_rule.js`
only**. Do NOT edit `build_data.py` or `index.html` — the rule lives entirely in this one hook.

Do this:

1. Open `recurring_rule.js`. Keep the header comment block intact (it documents the input `m`).
2. Rewrite ONLY the body of `window.CCRULE = function isRecurring(m){ ... }` so it returns
   `true` when a merchant matches the user's description. Fields available on `m`:
   - `name`, `cat` (category key), `total`, `n` (transaction count)
   - `months` (object `"YYYY-MM" -> amount`), `monthList` (sorted array), `mCount` (distinct months)
   - `maxRun` (longest run of consecutive months), `multi` (number of months with >1 charge)
   - Insurance is already excluded before this runs — do not special-case it.
3. If the description is ambiguous, state your interpretation in one line, choose the most
   reasonable predicate, and proceed (don't block).
4. Run `node --check recurring_rule.js` to confirm it parses. Fix and re-check if it fails.
5. If a `dashboard.html` exists / is being regenerated, re-run `python3 build_data.py` so the
   offline single-file re-inlines the new hook. Note: the rule drives the **dashboard**; the
   Markdown report's recurring list stays on the default unless the user asks to mirror it.
6. Show the user the new `isRecurring()` body and a one-line plain-English summary of the rule.

For reference, the shipped default is: `return m.maxRun >= 3 || m.multi >= 3;`
(paid in ≥3 consecutive months, OR ≥3 months with more than one charge).
