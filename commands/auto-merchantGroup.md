---
description: Let Claude propose merchant groups (collapsing token-variants of the same real merchant) and confirm them one group at a time — writes merchant_group.json only.
argument-hint: (no arguments)
---

Bulk-grouping counterpart to `/auto-categorize`, but deliberately **safer**: a wrong grouping
corrupts per-merchant totals, so **nothing is written without per-group confirmation**. Writes
**`skills/credit-card-spending-dashboard/merchant_group.json` only** (git-ignored, not shipped).
Never edits `build_data.py`. Grouping-only — the raw `tx.merch` is never renamed. Opt-in (merchant
names are read by Claude).

Do this:

1. **Scan** the distinct merchants in `data.js` (`CCDATA.tx[].merch`; run `python3 build_data.py`
   from the skill dir first if absent). **Skip** any merchant already covered by a rule in
   `merchant_group.json` (don't touch curated groups).
2. **Propose groups** that collapse **only token-variants of the SAME real merchant**, producing a
   tight regex or per-member literal rule.
3. **Confirm ONE GROUP AT A TIME.** For each proposed group, show the proposed group name + every
   member `merch` + tx count + total, and ask **accept / edit the name / skip**. Never a single
   bulk approve-all. Refuse over-broad patterns (like `/set-merchantGroup`) — show the full match
   list before writing each rule.
4. On **accept**, upsert the group's rule into `merchant_group.json` (create the file from the
   example emptied to `{ "groups": [] }` if absent). After all groups are processed, **rebuild once**:
   `cd skills/credit-card-spending-dashboard && python3 build_data.py`. Report what was grouped. On a
   build error, show it and stop.

### The decision rule (critical — read before proposing)

Merchant strings often share a prefix but a token varies. Decide per group:

- **DO group** when only an **opaque / random token** varies and the meaningful name (and location)
  is invariant → same merchant. Fabricated example: `SubSvc*6F6PA6L83 CITY`, `SubSvc*I711M7IL3 CITY`,
  `SubSvc*Q143K7IO3 CITY` → one group **"SubSvc"** (regex `SubSvc\*\w+ CITY`). Also
  `ExampleSub*XXXX CITY` variants.
- **DO NOT group** when the varying part is a **meaningful, recognizable name** (a distinct merchant,
  brand, or venue) — even under a shared prefix. Two traps:
  - payment-facilitator passthrough (`<facilitator>*<real merchant>`): fabricated
    `PayHub*Xx_BrandA` vs `PayHub*Xx_BrandB` vs `PayHub*Xx_Delivery` are **different merchants** (the
    real merchant is the suffix) — keep separate.
  - same brand, different venue/department: `MegaMall Dept.` vs `MegaMall Food Hall` are **different
    venues** — keep separate.
- **Heuristic:** varying token is gibberish/opaque → group; a real word/name → keep apart. **When
  unsure, skip** (safer to under-group than to merge distinct merchants — that is exactly why the
  automatic prefix-collapse was reverted in v0.7.0).
